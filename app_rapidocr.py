#!/usr/bin/env python3
"""
RapidOCR Lite - 超轻量级OCR服务
仅8MB模型，专为CPU优化，秒装秒用！
"""
import sys
import time
import io
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any

# Windows GBK console/pipe: force UTF-8 stdio so non-GBK characters
# (emoji, ⚠, ...) cannot crash the process at the first print().
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# 尝试导入RapidOCR
try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False
    print("[ERROR] RapidOCR未安装，请运行：pip install rapidocr-onnxruntime")
    sys.exit(1)

# FastAPI
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    from typing import Union, Optional
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# ──────────────────────────────────────────────
# OCR引擎（单例）
# ──────────────────────────────────────────────
class OCREngine:
    """RapidOCR轻量级引擎"""
    
    _instance: Optional['OCREngine'] = None
    _engine = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._engine is not None:
            return
        
        print("[INFO] 初始化RapidOCR引擎...")
        print("[INFO] 模型大小: 仅8MB")
        
        # 轻量配置
        self._engine = RapidOCR(
            det_model_path=None,  # 自动下载
            rec_model_path=None,
            cls_model_path=None,
            # CPU优化参数
            det_use_cpu=True,
            rec_use_cpu=True,
            cls_use_cpu=True,
            det_score_threshold=0.3,
            rec_score_threshold=0.5,
            verbose=False
        )
        
        print("[INFO] RapidOCR引擎初始化完成")
    
    def recognize(self, image) -> Dict[str, Any]:
        """识别图片文字"""
        if self._engine is None:
            raise RuntimeError("OCR引擎未初始化")
        
        # 转换为RGB
        import cv2
        import numpy as np
        
        img_array = np.array(image.convert('RGB'))
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        t0 = time.time()
        result, elapse = self._engine(img_bgr)
        elapsed_ms = round((time.time() - t0) * 1000)
        
        # 解析结果 (兼容 rapidocr 新旧版返回结构:
        #   新版: [box, text, conf] 每项 3 元组
        #   老版: [box, (text, conf)] 每项 2 元、第二项是 (text, conf) tuple)
        texts = []
        if result:
            for item in result:
                box = item[0]
                if len(item) >= 3:
                    text, conf = item[1], item[2]
                else:
                    # 老版: item[1] 是 (text, conf) tuple
                    text, conf = item[1][0], item[1][1]
                # conf 可能被包成 (conf,) 或已是 float, 统一取标量
                if isinstance(conf, (list, tuple)):
                    conf = conf[0] if conf else 0.0
                texts.append({
                    "text": text,
                    "confidence": round(float(conf), 4),
                    "box": box
                })
        
        return {
            "texts": texts,
            "full_text": "\n".join([t["text"] for t in texts]),
            "count": len(texts),
            "elapsed_ms": elapsed_ms
        }
    
    @classmethod
    def get_instance(cls) -> 'OCREngine':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# ──────────────────────────────────────────────
# FastAPI应用
# ──────────────────────────────────────────────
app = None
MODEL_NAME = "rapidocr-lite"
HOST = "127.0.0.1"
PORT = 8004

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title=f"RapidOCR (OpenAI-Compatible) [{MODEL_NAME}]",
        description="RapidOCR - 超轻量级CPU OCR（仅8MB）",
        version="1.0.0",
    )
    
    class ChatCompletionRequest(BaseModel):
        model: str
        messages: List[Dict[str, Any]]
        temperature: Optional[float] = None
        max_tokens: Optional[int] = None
        stream: bool = False
    
    @app.get("/healthz")
    async def healthz():
        return {
            "status": "ok",
            "model": MODEL_NAME,
            "host": HOST,
            "port": PORT,
            "engine": "RapidOCR",
            "model_size_mb": "~8MB"
        }
    
    @app.get("/v1/models")
    async def list_models():
        return {
            "object": "list",
            "data": [{
                "id": MODEL_NAME,
                "object": "model",
                "owned_by": "rapidocr",
                "capabilities": ["cpu-ocr", "chinese", "english"]
            }]
        }
    
    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest):
        if request.model != MODEL_NAME:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{request.model}' not found (supported: {MODEL_NAME})",
            )
        
        # 提取图片
        images = []
        for msg in request.messages:
            content = msg.get("content", [])
            if isinstance(content, list):
                for part in content:
                    if part.get("type") == "image_url":
                        image_url = part.get("image_url", {}).get("url", "")
                        if image_url.startswith("data:image"):
                            header, b64_data = image_url.split(",", 1)
                            img_bytes = base64.b64decode(b64_data)
                            from PIL import Image
                            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                            images.append(img)
        
        if not images:
            raise HTTPException(
                status_code=400,
                detail="No image found in messages.",
            )
        
        # 调用OCR
        engine = OCREngine.get_instance()
        results = []
        
        for img in images:
            result = engine.recognize(img)
            results.append(result)
        
        # 合并结果
        full_text = "\n\n".join([r["full_text"] for r in results])
        
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": MODEL_NAME,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": full_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            "metadata": {
                "engine": "RapidOCR",
                "mode": "CPU",
                "processing_time_ms": results[0]["elapsed_ms"] if results else 0,
                "texts_count": results[0]["count"] if results else 0
            }
        }
    
    @app.post("/v1/ocr")
    async def ocr_direct(request):
        """直接OCR接口"""
        body = await request.json()
        image_path = body.get("image_path")
        
        if not image_path or not Path(image_path).exists():
            raise HTTPException(status_code=400, detail="Invalid image path")
        
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        
        engine = OCREngine.get_instance()
        result = engine.recognize(img)
        
        return {
            "success": True,
            "texts": result["texts"],
            "full_text": result["full_text"],
            "count": result["count"],
            "elapsed_ms": result["elapsed_ms"]
        }


# ──────────────────────────────────────────────
# 主函数
# ──────────────────────────────────────────────
def main():
    global HOST, PORT, MODEL_NAME
    
    import argparse
    parser = argparse.ArgumentParser(description="RapidOCR CPU Server")
    parser.add_argument("--host", default=HOST, help="服务地址")
    parser.add_argument("--port", type=int, default=PORT, help="服务端口")
    args = parser.parse_args()
    
    HOST = args.host
    PORT = args.port
    
    print("=" * 60)
    print("RapidOCR CPU Server")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Host: {HOST}:{PORT}")
    print(f"  Mode: CPU (超轻量)")
    print(f"  Model Size: ~8MB")
    print("=" * 60)
    
    if FASTAPI_AVAILABLE:
        import uvicorn
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    else:
        print("[ERROR] FastAPI未安装")
        sys.exit(1)


if __name__ == "__main__":
    main()

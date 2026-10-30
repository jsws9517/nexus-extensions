#!/usr/bin/env python3
"""
PaddleOCR Lite - 轻量级OCR服务（Mobile版模型）
模型大小: ~15MB（vs 完整版700MB）
"""
import os
import sys
import time

# 必须在 import paddle 之前设置，强制关闭 OneDNN/MKL-DNN CPU 后端，
# 规避 Paddle fused_conv2d 在 OneDNN 路径上报 "OneDnnContext does not have the input Filter" 的 bug。
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("PADDLE_ENABLE_MKLDNN", "0")

# Windows GBK console/pipe: force UTF-8 stdio so non-GBK characters
# (emoji, ⚠, ...) cannot crash the process at the first print().
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
import io
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    print("[ERROR] PaddleOCR未安装，请运行：pip install paddlepaddle paddleocr")
    sys.exit(1)

try:
    from fastapi import FastAPI, HTTPException, Request
    from pydantic import BaseModel
    from typing import Union, Optional
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

class OCREngine:
    _instance: Optional['OCREngine'] = None
    _ocr = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._ocr is not None:
            return
        
        print("[INFO] 初始化PaddleOCR Mobile引擎...")
        print("[INFO] 模型大小: ~15MB")
        
        # Mobile版轻量配置（PaddleOCR v2.8.1 API）
        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
            use_gpu=False,  # CPU模式
            enable_mkldnn=False,  # 关闭 OneDNN，规避 fused_conv2d Filter 缺失 bug
            det_db_box_thresh=0.5,
            det_db_unclip_ratio=1.5,
            verbose=False
        )
        
        print("[INFO] PaddleOCR Mobile引擎初始化完成")
    
    def recognize(self, image) -> Dict[str, Any]:
        if self._ocr is None:
            raise RuntimeError("OCR引擎未初始化")
        
        import numpy as np
        img_array = np.array(image.convert('RGB'))
        
        t0 = time.time()
        result = self._ocr.ocr(img_array, cls=True)
        elapsed_ms = round((time.time() - t0) * 1000)
        
        texts = []
        if result and result[0]:
            for line in result[0]:
                bbox, (text, conf) = line
                texts.append({
                    "text": text,
                    "confidence": round(conf, 4),
                    "box": bbox
                })
        
        lines = [t["text"] for t in texts]
        return {
            "lines": lines,             # 逐行文本，直接可读
            "text": "\n".join(lines),  # 完整文本（程序用）
            "texts": texts,             # 含坐标/置信度的明细
            "full_text": "\n".join(lines),
            "count": len(texts),
            "elapsed_ms": elapsed_ms
        }
    
    @classmethod
    def get_instance(cls) -> 'OCREngine':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


app = None
MODEL_NAME = "paddleocr-mobile"
HOST = "127.0.0.1"
PORT = 8005

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title=f"PaddleOCR Mobile (OpenAI-Compatible) [{MODEL_NAME}]",
        description="PaddleOCR - 轻量级CPU OCR（Mobile模型，~15MB）",
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
        # 读全局实时值, 避免闭包捕获 create_app 阶段的默认 HOST/PORT,
        # 使 --port 自定义后 healthz 回显与实际监听端口一致
        g = globals()
        return {
            "status": "ok",
            "model": MODEL_NAME,
            "host": g.get("HOST", HOST),
            "port": g.get("PORT", PORT),
            "engine": "PaddleOCR Mobile",
            "model_size_mb": "~15MB"
        }
    
    @app.get("/v1/models")
    async def list_models():
        return {
            "object": "list",
            "data": [{
                "id": MODEL_NAME,
                "object": "model",
                "owned_by": "paddleocr",
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
        
        engine = OCREngine.get_instance()
        results = []
        
        for img in images:
            result = engine.recognize(img)
            results.append(result)
        
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
                "engine": "PaddleOCR Mobile",
                "mode": "CPU",
                "processing_time_ms": results[0]["elapsed_ms"] if results else 0,
                "texts_count": results[0]["count"] if results else 0
            }
        }
    
    @app.post("/v1/ocr")
    async def ocr_direct(request: Request):
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
            "lines": result["lines"],          # 逐行文本，直接可读
            "text": result["text"],            # 完整文本（程序用）
            "texts": result["texts"],
            "full_text": result["full_text"],
            "count": result["count"],
            "elapsed_ms": result["elapsed_ms"]
        }


def main():
    global HOST, PORT, MODEL_NAME
    
    import argparse
    parser = argparse.ArgumentParser(description="PaddleOCR Mobile Server")
    parser.add_argument("--host", default=HOST, help="服务地址")
    parser.add_argument("--port", type=int, default=PORT, help="服务端口")
    args = parser.parse_args()
    
    HOST = args.host
    PORT = args.port
    
    print("=" * 60)
    print("PaddleOCR Mobile Server")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Host: {HOST}:{PORT}")
    print(f"  Mode: CPU (Mobile轻量)")
    print(f"  Model Size: ~15MB")
    print("=" * 60)
    
    if FASTAPI_AVAILABLE:
        import uvicorn
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    else:
        print("[ERROR] FastAPI未安装")
        sys.exit(1)


if __name__ == "__main__":
    main()

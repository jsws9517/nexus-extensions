from __future__ import annotations
import base64
import io
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from PIL import Image
from rapidocr import RapidOCR
from pydantic import BaseModel

# ──────────────────────────────────────────────
# OpenAI-compatible constants
# ──────────────────────────────────────────────
FAKE_API_KEY = "sk-paddle-ocr-local"
MODEL_NAME   = "paddle-ocr"            # 客户端填写此 model
IMGBASE64_MIME_PREFIX = "data:image/png;base64,"

# ──────────────────────────────────────────────
# Pydantic schemas（镜像 openai.chat.completions 请求体）
# ──────────────────────────────────────────────
class ImageContentPart(BaseModel):
    type: str
    image_url: dict[str, str] = {}

class TextContentPart(BaseModel):
    type: str
    text: str

class MessageItem(BaseModel):
    role: str          # "user" / "system" / "assistant"
    content: list | str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[MessageItem]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False

class Choice(BaseModel):
    index: int
    message: dict
    finish_reason: str

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage

# ──────────────────────────────────────────────
# RapidOCR 引擎（单例，懒加载）
# ──────────────────────────────────────────────
_engine: RapidOCR | None = None

def get_engine() -> RapidOCR:
    global _engine
    if _engine is None:
        _engine = RapidOCR()
    return _engine

# ──────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────
app = FastAPI(
    title="Paddle OCR (OpenAI-Compatible)",
    description="将 RapidOCR 封装为 OpenAI chat/completions 兼容接口",
    version="1.0.0",
)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "model": MODEL_NAME}


@app.get("/v1/models")
async def list_models():
    """返回 OpenAI 风格模型列表"""
    return {
        "object": "list",
        "data": [{
            "id": MODEL_NAME,
            "object": "model",
            "owned_by": "paddle-ocr",
        }]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # ── 1. 伪造 key 校验（全部通过）─────────────
    api_key = request.headers.get("authorization", "")
    if not api_key.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")

    # ── 2. model 白名单校验 ────────────────────
    if request.model != MODEL_NAME:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{request.model}' not found (supported: {MODEL_NAME})",
        )

    # ── 3. 从 messages 中提取 base64 图片 ──────
    images: list[Image.Image] = []
    for msg in request.messages:
        if isinstance(msg.content, str):
            continue
        for part in msg.content:
            if isinstance(part, ImageContentPart) and part.image_url:
                raw = part.image_url.get("url", "")
                if raw.startswith(IMGBASE64_MIME_PREFIX):
                    b64_data = raw[len(IMGBASE64_MIME_PREFIX):]
                else:
                    b64_data = raw
                try:
                    img_bytes = base64.b64decode(b64_data)
                    images.append(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    if not images:
        raise HTTPException(
            status_code=400,
            detail="No image found in messages. Provide an image_url content part.",
        )

    # ── 4. 调用 RapidOCR ───────────────────────
    engine = get_engine()
    all_texts: list[str] = []
    t0 = time.time()
    for img in images:
        result, _ = engine(img)          # result: list[(box, (text, confidence))]
        texts = [item[1][0] for item in result if item[1][0].strip()]
        all_texts.extend(texts)

    elapsed_ms = round((time.time() - t0) * 1000)
    full_text = "\n".join(all_texts)

    # ── 5. 组装 OpenAI 响应 ────────────────────
    resp = ChatCompletionResponse(
        id=f"chatcmpl-{int(time.time()*1000)}",
        created=int(time.time()),
        model=MODEL_NAME,
        choices=[Choice(
            index=0,
            message={"role": "assistant", "content": full_text},
            finish_reason="stop",
        )],
        usage=Usage(
            prompt_tokens=len(full_text),
            completion_tokens=len(full_text),
            total_tokens=len(full_text) * 2,
        ),
    )
    return resp


# 可选：流式输出（暂不支持，返回错误提示）
@app.post("/v1/chat/completions/stream")
async def chat_completions_stream(request: ChatCompletionRequest):
    raise HTTPException(status_code=501, detail="stream=true not yet supported")

# PaddleOCR Standalone — Docker 容器版

基于 **RapidOCR (ONNX)** 的独立 OCR 容器，**不依赖 PaddlePaddle 框架**（纯 ONNX Runtime 推理）。
内置 PaddleOCR 模型，随依赖包自动命中，**离线可用、不联网下载**。

> 本 README 只讲 **Docker 部署线**。详细接口说明、调用示例与故障排查见 [`docker/rapidocr/README.md`](docker/rapidocr/README.md)。

## 镜像与编排

- 镜像构建：`docker/rapidocr/Dockerfile`
- 编排：`docker/rapidocr/docker-compose.yml`（默认端口 **8006**，含健康检查）
- 启动脚本：`entrypoint-rapidocr.sh`（`RAPID_PORT` / `RAPID_HOST` 自适应）
- 构建上下文忽略：根目录 `.dockerignore`
- 线专用依赖：`requirements-rapidocr-docker.txt`（锁定 `onnxruntime` + `rapidocr`）

## 快速开始

```bash
# 项目根执行（build context = 项目根，.dockerignore 生效）
docker compose -f docker/rapidocr/docker-compose.yml up -d --build

# 自定义端口
RAPID_PORT=9001 docker compose -f docker/rapidocr/docker-compose.yml up -d
```

## 接口（OpenAI 兼容）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/healthz` | 健康检查 |
| GET | `/v1/models` | 列出模型（`paddle-ocr`） |
| POST | `/v1/chat/completions` | OpenAI 协议：messages 内嵌 base64 `image_url`（需 Bearer key） |

调用示例（图片走 base64 data-URI）：

```bash
curl -s http://127.0.0.1:8006/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ***" \
  -d '{
    "model": "paddle-ocr",
    "messages": [
      {"role": "user",
       "content": [
         {"type": "text", "text": "识别图片文字"},
         {"type": "image_url",
          "image_url": {"url": "data:image/png;base64,<BASE64>"}}
       ]}
    ]
  }'
```

## 目录结构（docker 线）

```
.
├── app.py                            # FastAPI 入口（OpenAI 兼容协议）
├── app_rapidocr.py                   # 同上（RapidOCR ONNX 版，docker/exe 共用）
├── ocr.py                            # 纯 OCR 函数（无 Web 层，可被其他脚本 import）
├── upload.py                         # 文件上传辅助
├── entrypoint-rapidocr.sh            # Docker 容器启动脚本
├── requirements.txt                  # Web 栈依赖
├── requirements-rapidocr-docker.txt  # Docker 线专用依赖
├── .dockerignore                     # Docker 构建上下文忽略
└── docker/rapidocr/
    ├── Dockerfile                    # RapidOCR ONNX 镜像构建
    ├── docker-compose.yml            # 编排（默认 8006 + 健康检查）
    └── README.md                     # 详细部署文档
```

# RapidOCR Mobile — Docker 部署 (ONNX Runtime 版)

> **超轻量级 CPU OCR 服务**。引擎为 `onnxruntime`（CPU），**不依赖 PaddlePaddle 框架**，
> 镜像仅 ~350MB（Paddle 版因内嵌 Paddle 库达 ~1.1GB）。默认 ONNX 模型（~15MB）随
> `rapidocr-onnxruntime` 包内置，运行时自动命中，**不联网下载**。

## 与 Paddle 版的差异

| 维度 | Paddle 版 | RapidOCR 版（本目录） |
|---|---|---|
| 推理引擎 | PaddlePaddle（框架 ~600MB+） | ONNX Runtime（~150MB，无 Paddle 框架） |
| 镜像体积 | ~1.1GB | **~350MB** |
| 模型格式 | Paddle `.pdmodel` (whl 目录) | ONNX `.onnx`（包内 `models/`） |
| 默认端口 | `PADDLE_PORT` 8005 | `RAPID_PORT` 8006 |
| 协议 | OpenAI 兼容 | **OpenAI 兼容（同一套）** |
| 识别效果 | 基准 | **同源模型，效果打平**（详见项目 `probe_compare.py` 结论） |

> 两版用的是**同一套 PaddleOCR v4 模型**（Paddle 格式 vs ONNX 格式），因此识别结果实质等价，
> 差异仅在 3 处空格 / 框切法（`CICT Mobile` vs `CICTMobile` 等），无错字。

## 文件清单

| 文件 | 作用 |
|---|---|
| `Dockerfile` | 构建 RapidOCR 镜像（`python:3.12-slim-bookworm` + onnxruntime 栈） |
| `docker-compose.yml` | 部署编排（端口透传 + 健康检查，默认 8006） |
| `../entrypoint-rapidocr.sh`（项目根） | 启动脚本（`RAPID_PORT`/`RAPID_HOST` 自适应） |
| `../../requirements-rapidocr-docker.txt`（项目根） | 依赖清单（onnxruntime + rapidocr + Web 栈） |

## 构建 & 运行

```bash
# 在项目根执行 (build context 为项目根)
docker compose -f docker/rapidocr/docker-compose.yml up -d --build

# 自定义端口 (例: 9001)
RAPID_PORT=9001 docker compose -f docker/rapidocr/docker-compose.yml up -d
```

## 接口（OpenAI 兼容）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/healthz` | 健康检查（含 model_size_mb、engine） |
| GET | `/v1/models` | 列出模型（`rapidocr-lite`） |
| POST | `/v1/chat/completions` | OpenAI 协议：messages 内嵌 base64 `image_url` |
| POST | `/v1/ocr` | 直接 OCR：`{"image_path": "/opt/ocr/xx.jpg"}` |

调用示例（OpenAI 兼容，图片走 base64 data-URI）：

```bash
curl -s http://127.0.0.1:8006/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rapidocr-lite",
    "messages": [
      {"role": "user",
       "content": [
         {"type": "text", "text": "识别图片文字"},
         {"type": "image_url",
          "image_url": {"url": "data:image/jpeg;base64,<BASE64>"}}
       ]}
    ]
  }'
```

## 资源说明

- 默认 `start_period: 30s`（RapidOCR 比 Paddle 初始化更快）
- 如需限制 CPU，解开 compose 中 `deploy.resources.limits` 注释

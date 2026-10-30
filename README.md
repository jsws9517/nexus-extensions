# PaddleOCR Standalone — 独立部署 OCR 服务

超轻量级 CPU OCR 服务的多个部署形态，**不依赖 PaddlePaddle 框架**（纯 ONNX Runtime 推理）。
内置 PaddleOCR v4 Mobile 模型（ch_PP-OCRv4 det/rec + cls，约 15MB），随依赖包自动命中，**离线可用、不联网下载**。

## 方案总览

| 形态 | 入口 / 位置 | 说明 | 分支 |
|---|---|---|---|
| Docker 容器版 | `docker/rapidocr/` | 官方镜像 + compose 编排，CPU 推理，~350MB 镜像 | `feat/docker-rapidocr` |
| 独立 exe 便携版 | 项目根 `paddle-ocr.spec` + `app_rapidocr.py` | PyInstaller 打包单文件 exe | `feat/rapidocr-portable` |
| FastAPI 直接跑 | `app.py` | 本地 `uvicorn` 起服务 | `feat/fastapi-service` |

> 两版识别模型同源（Paddle 格式 vs ONNX 格式），结果实质等价，详见 `docker/rapidocr/README.md` 的对比说明。

## 目录结构

```
.
├── app.py                            # FastAPI 入口（PaddleOCR 协议风格）
├── app_rapidocr.py                   # FastAPI 入口（RapidOCR ONNX 版，exe/docker 共用）
├── ocr.py                            # 纯 OCR 函数（无 Web 层，可被其他脚本 import）
├── upload.py                         # 文件上传辅助
├── entrypoint-rapidocr.sh            # Docker 容器启动脚本（RAPID_PORT/RAPID_HOST 自适应）
├── paddle-ocr.spec                   # PyInstaller 打包配置（独立 exe）
├── paddle-ocr.ico / paddle-ocr.jpeg  # 打包图标 / 示例图
├── requirements.txt                  # Web 栈依赖（exe / 直接跑）
├── requirements-rapidocr-docker.txt  # Docker 线专用依赖（锁定 onnxruntime + rapidocr）
├── .dockerignore                     # Docker 构建上下文忽略
├── .gitignore                        # 仓库忽略（.venv/、__pycache__/、.nexus/ 等）
└── docker/rapidocr/
    ├── Dockerfile                    # RapidOCR ONNX 镜像构建
    ├── docker-compose.yml            # 编排（默认端口 8006 + 健康检查）
    └── README.md                     # Docker 版详细部署文档
```

## 快速开始

### 方式一：本地直接跑（uvicorn）

```bash
pip install -r requirements.txt
python app_rapidocr.py          # 起 FastAPI（含 /healthz、/v1/models、/v1/ocr）
# 或
uvicorn app_rapidocr:app --host 0.0.0.0 --port 8006
```

### 方式二：Docker 容器版

```bash
# 项目根执行（build context = 项目根，.dockerignore 生效）
docker compose -f docker/rapidocr/docker-compose.yml up -d --build

# 自定义端口
RAPID_PORT=9001 docker compose -f docker/rapidocr/docker-compose.yml up -d
```

详细接口与调用示例见 [`docker/rapidocr/README.md`](docker/rapidocr/README.md)。

### 方式三：打包独立 exe（便携版）

```bash
pip install pyinstaller
pyinstaller --noconsole paddle-ocr.spec
# 产物在 dist/，upx.exe 压缩（可选）
```

## 接口（OpenAI 兼容）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/healthz` | 健康检查（含 model_size_mb、engine） |
| GET | `/v1/models` | 列出模型（`rapidocr-lite`） |
| POST | `/v1/ocr` | 直接 OCR：`{"image_path": "/opt/ocr/xx.jpg"}` 或 base64 |
| POST | `/v1/chat/completions` | OpenAI 协议：messages 内嵌 base64 `image_url` |

调用示例（图片走 base64 data-URI）：

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

## 分支说明

| 分支 | 远端 | 用途 |
|---|---|---|
| `feat/docker-rapidocr` | ✓ | 容器化部署（Docker + compose） |
| `feat/rapidocr-portable` | ✓ | 独立 exe 便携版（PyInstaller + UPX） |
| `feat/fastapi-service` | 本地 | 早期 PaddleOCR FastAPI 服务线 |

## 忽略规则

`.gitignore` 已覆盖：`.venv/`、`__pycache__/`、`*.pyc`、`.nexus/`（本地 Nexus 工作区，不入库）。
Docker 构建时 `.dockerignore` 控制上下文体积。

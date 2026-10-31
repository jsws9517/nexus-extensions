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

# 仅重建镜像（app 代码 / Dockerfile 改了才需要；只改端口等编排用 up -d 即可）
docker compose -f docker/rapidocr/docker-compose.yml build

# 自定义端口
RAPID_PORT=9001 docker compose -f docker/rapidocr/docker-compose.yml up -d
```

### build 时的环境变量说明

> **`COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=0` 不是必需的。**
> 默认 compose v2 的 build 已走 BuildKit，正常情况直接 `... up -d --build` / `... build` 即可。
> **仅当 `docker compose build` 报版本不兼容（如 `BuildKit is required`、`no such constraint` 之类）**，再前置这两个变量走旧 CLI 构建器：
>
> ```bash
> COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=0 \
>   docker compose -f docker/rapidocr/docker-compose.yml build
> ```

### build 时的 mirror（pip 源）参数

Dockerfile 里 pip 安装已**默认走阿里云镜像源**（`-i https://mirrors.aliyun.com/pypi/simple/`，写死在 `Dockerfile` 的 `RUN pip install` 里，build 时自动生效，**不需要额外传参**）。

- **默认就够用**：国内网络 build 速度由阿里云源保证，直接 `build` 即可。
- **想换源 / 临时切官方源**：改 `Dockerfile` 里 `pip install` 那行的 `-i` 地址后重新 build；或给 build 显式注入 `--build-arg PIP_INDEX_URL=...`（需 `Dockerfile` 对应声明 `ARG PIP_INDEX_URL`，当前未声明，改 Dockerfile 即可）。
- **传 `--build-arg` 注意**：`--build-arg` 是给 `docker build` 用的；走 compose 时用 `build.args`（见 `docker-compose.yml` 的 `build` 段），CLI 形式 `docker build --build-arg K=V` 需手动 build 镜像 tag。

## 运行状态测试样例（真实 OCR 闭环验证）

build 成功 + 容器 `up` + `healthz` OK 之后，**真实推理端到端验证**用下面这条（大图 base64 走文件喂，避开 shell ARG_MAX）：

```bash
# 1. 确认容器 healthy + 探活
curl http://127.0.0.1:8006/healthz
# 期望: {"status":"ok","model":"rapidocr-lite",...,"engine":"RapidOCR",...}

# 2. 真实 OCR（图放 /sf_linux/test.jpg；B64 走 heredoc 写进临时 JSON，再 -d @file，不超 ARG_MAX）
cd /sf_linux
B64=$(base64 -w0 test.jpg)   # 注意: 是 $(base64 ...), 不要打成 $9base64 (手抖坑)
cat > /tmp/ocr_req.json <<EOF
{"model":"rapidocr-lite","messages":[{"role":"user","content":[{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,${B64}"}},{"type":"text","text":"识别图中文字"}]}]}
EOF
curl -s -X POST http://127.0.0.1:8006/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @/tmp/ocr_req.json
```

**期望返回**（真实 OCR 识别结果，非 500、非空）：

```json
{
  "choices":[{"index":0,"message":{"role":"assistant",
    "content":"8:30\n详情\n中信科移动\nCICTMobile\n...\n端午物资兑换链接"},
    "finish_reason":"stop"}],
  "metadata":{"engine":"RapidOCR","mode":"CPU","processing_time_ms":3147,"texts_count":21}
}
```

`choices[0].message.content` 有识别文字串 + `finish_reason` 为 `stop` = **全链路通了**（build → 起容器 → healthz OK → 真实 ONNX 推理 + 结果解析）。

## 踩坑排障（本线实际踩过的 4 个坑）

| 症状 | 根因 | 修复 |
|---|---|---|
| 容器 `Restarting`，日志 `ImportError: libGL.so.1 not found` / `cv2` import 崩 | `opencv-python-headless` 与系统 cv2 残留 / 非 headless .so 混装 | `force-reinstall opencv-python-headless` + 删残留 + 构建期自检（commit `922fd5e`） |
| build 极慢 / `pip install` 卡住 | 走官方 PyPI，国内网络慢 | `pip` 切阿里云源（`-i mirrors.aliyun.com`，已写死在 Dockerfile，commit `8618251`） |
| `curl -d "..."` 报 `参数列表过长` (ARG_MAX) | 大图 base64 塞进 curl argv，超 `ARG_MAX`(~2MB) | 先写临时 JSON 文件，再 `curl -d @file`（走文件不走 argv） |
| `/v1/chat/completions` 返回 `Internal Server Error`，日志 `ValueError: too many values to unpack (expected 2)` | RapidOCR 2.x 返回 3 元组 `[box, text, conf]`，旧代码按 2 元组解包 | 版本兼容解包（commit `7495365`） |

**通用排障口诀**：
1. 容器反复 `Restarting` → `sudo docker logs rapidocr-mobile 2>&1 | tail -40`，看最后一行 traceback（区分是 import 崩还是推理崩）。
2. `healthz` 绿但 `/v1/...` 500 → **health 只探活、不跑推理**，500 一定是推理路径崩，看日志 `File "...app_rapidocr.py", line N` 那行。
3. 请求体可疑 → `head -c 80 /tmp/ocr_req.json` 看 `base64,` 后面是不是空的（B64 没展开 = 路径错 / `base64` 没跑成，不是容器 500 的锅）。
4. `B64=$(base64 -w0 ...)` 手抖打成 `B64=$9base64` 会报 `-w0: 未找到命令`——确认是 `$(base64 ...)` 不是 `$9base64`。

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

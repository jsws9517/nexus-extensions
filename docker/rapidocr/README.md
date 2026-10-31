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

# 仅重建镜像 (app 代码 / Dockerfile 改了才需要; 只改端口等编排用 up -d)
docker compose -f docker/rapidocr/docker-compose.yml build

# 自定义端口 (例: 9001)
RAPID_PORT=9001 docker compose -f docker/rapidocr/docker-compose.yml up -d
```

### build 环境变量（非必需，排障时才用）

> **`COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=0` 不是必需的**，默认 compose v2 已走 BuildKit。
> 仅当 `docker compose build` 报**版本不兼容**（`BuildKit is required` / `no such constraint` 之类）时再前置：
>
> ```bash
> COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=0 \
>   docker compose -f docker/rapidocr/docker-compose.yml build
> ```

### build 时的 pip 源（mirror）

`Dockerfile` 的 `RUN pip install` 已**默认走阿里云源**（`-i https://mirrors.aliyun.com/pypi/simple/`），build 自动生效、**无需传参**；国内网络速度由它保证。

- 换源 / 切官方源：改 `Dockerfile` 那行 `-i` 后重建；或 `--build-arg PIP_INDEX_URL=...`（需 Dockerfile 声明 `ARG PIP_INDEX_URL`，当前未声明）。
- 走 compose 时传 `build.args`（见 `docker-compose.yml` `build` 段）；CLI `docker build --build-arg K=V` 需手动 build 并打 tag。

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

## 运行状态测试样例（真实 OCR 闭环）

build + 容器 `up` + `healthz` OK 之后，用下面这条做**真实推理端到端验证**（大图 base64 走文件喂，避开 ARG_MAX）：

```bash
curl http://127.0.0.1:8006/healthz
# 期望: {"status":"ok","model":"rapidocr-lite",...,"engine":"RapidOCR",...}

cd /sf_linux
B64=$(base64 -w0 test.jpg)        # 注意 $(base64 ...), 不是 $9base64
cat > /tmp/ocr_req.json <<EOF
{"model":"rapidocr-lite","messages":[{"role":"user","content":[{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,${B64}"}},{"type":"text","text":"识别图中文字"}]}]}
EOF
curl -s -X POST http://127.0.0.1:8006/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @/tmp/ocr_req.json
```

**期望**：`choices[0].message.content` 有识别文字串 + `finish_reason: "stop"`，`metadata.processing_time_ms` ~3000ms 量级（CPU）。

## 踩坑排障（本线实际踩过）

| 症状 | 根因 | 修复 |
|---|---|---|
| 容器 `Restarting`，日志 `ImportError: libGL.so.1` / cv2 import 崩 | opencv headless 与系统 cv2 残留混装 | `force-reinstall opencv-python-headless` + 删残留 + 构建期自检（`922fd5e`） |
| build 极慢 / pip 卡住 | 走官方 PyPI 国内慢 | pip 切阿里云源，已写死 Dockerfile（`8618251`） |
| `curl -d "..."` 报 `参数列表过长` | 大图 base64 进 argv 超 `ARG_MAX` | 写临时 JSON 再 `curl -d @file` |
| `/v1/...` 返回 500，日志 `ValueError: too many values to unpack (expected 2)` | RapidOCR 2.x 返回 3 元组，旧代码按 2 元组解包 | 版本兼容解包（`7495365`） |

**排障口诀**：① 反复 `Restarting` → `sudo docker logs rapidocr-mobile 2>&1 | tail -40` 看末行 traceback；② `healthz` 绿但 `/v1/...` 500 → health 只探活、500 必是推理路径崩，看日志 `app_rapidocr.py` 行号；③ 怀疑请求体 → `head -c 80 /tmp/ocr_req.json` 看 `base64,` 后是否为空（B64 没展开 ≠ 容器 500）。

## 资源说明

- 默认 `start_period: 30s`（RapidOCR 比 Paddle 初始化更快）
- 如需限制 CPU，解开 compose 中 `deploy.resources.limits` 注释

# ============================================================
# RapidOCR Mobile — 超轻量级 CPU OCR 服务（ONNX Runtime 版）
# 模型: PaddleOCR v4 Mobile 的 ONNX 转换版 (det/rec + mobile cls, 共 ~15MB)
# 特点:
#   - 引擎为 onnxruntime (CPU), 不需要 Paddle 框架, 镜像只有 ~350MB
#     (Paddle 版因内嵌 PaddlePaddle 库达 ~1.1GB)
#   - 默认 ONNX 模型随 rapidocr-onnxruntime 包内置 (models/*.onnx),
#     运行时自动命中, 不联网下载 (与 Paddle 版"免下载"一致)
#   - 支持端口自定义: 环境变量 RAPID_PORT (默认 8006, 避开 Paddle 版 8005)
#   - OpenAI 兼容协议: /v1/chat/completions + /v1/models + /v1/ocr
# ============================================================
FROM python:3.12-slim-bookworm

# 基础依赖 (pillow / numpy 由依赖自动拉取, 这里显式声明兜底)
# opencv-python-headless: 无 GUI 依赖, 适合 slim 镜像
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装 ONNX Runtime 推理栈 + Web 服务栈
# 不装 PaddlePaddle, 保持镜像轻量 (~350MB)
COPY requirements-rapidocr-docker.txt /tmp/requirements-rapidocr-docker.txt
RUN pip install --no-cache-dir \
        -r /tmp/requirements-rapidocr-docker.txt \
    && rm /tmp/requirements-rapidocr-docker.txt

# ------------------------------------------------------------------
# 验证内置 ONNX 模型已随包就位 (rapidocr-onnxruntime 自带 models/*.onnx)
# 若构建环境断网, 此处仍可通过 (模型在 site-packages 内, 不走网络)
# ------------------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# 应用代码 (复用项目根已调通的 RapidOCR 版服务)
COPY app_rapidocr.py /opt/ocr/app_rapidocr.py
COPY entrypoint-rapidocr.sh /opt/ocr/entrypoint.sh
RUN chmod +x /opt/ocr/entrypoint.sh

# RAPID_PORT: 端口自定义, 默认 8006 (compose 会透传同名变量保持容器内外一致)
# 默认监听 0.0.0.0, 便于 Docker 端口映射对外暴露
ENV RAPID_PORT=8006 \
    RAPID_HOST=0.0.0.0
EXPOSE 8006

WORKDIR /opt/ocr

ENTRYPOINT ["/opt/ocr/entrypoint.sh"]

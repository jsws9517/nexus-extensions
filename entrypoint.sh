#!/bin/sh
# PaddleOCR Mobile 服务启动脚本
# 端口自动适配: PADDLE_PORT (默认 8005) 决定容器监听端口
# 监听 0.0.0.0 以便 compose 端口映射对外暴露
set -eu

PORT="${PADDLE_PORT:-8005}"
HOST="${PADDLE_HOST:-0.0.0.0}"

echo "===================================================="
echo " PaddleOCR Mobile Service"
echo "   Listen : ${HOST}:${PORT}"
echo "   Model  : PaddleOCR Mobile (CPU, bundled whl)"
echo "   Health : GET  http://${HOST}:${PORT}/healthz"
echo "   OCR    : POST http://${HOST}:${PORT}/v1/ocr"
echo "===================================================="

exec python /opt/ocr/app_paddle_mobile.py --host "${HOST}" --port "${PORT}"

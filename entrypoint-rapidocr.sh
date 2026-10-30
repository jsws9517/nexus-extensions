#!/bin/sh
# RapidOCR Mobile 服务启动脚本 (ONNX Runtime 版)
# 端口自动适配: RAPID_PORT (默认 8006) 决定容器监听端口
# 监听 RAPID_HOST (默认 0.0.0.0) 以便 compose 端口映射对外暴露
set -eu

PORT="${RAPID_PORT:-8006}"
HOST="${RAPID_HOST:-0.0.0.0}"

echo "===================================================="
echo " RapidOCR Mobile Service (ONNX Runtime, CPU)"
echo "   Listen : ${HOST}:${PORT}"
echo "   Model  : PaddleOCR v4 Mobile ONNX (~15MB, bundled)"
echo "   Health : GET  http://${HOST}:${PORT}/healthz"
echo "   OpenAI : POST http://${HOST}:${PORT}/v1/chat/completions"
echo "   OCR    : POST http://${HOST}:${PORT}/v1/ocr"
echo "===================================================="

exec python /opt/ocr/app_rapidocr.py --host "${HOST}" --port "${PORT}"

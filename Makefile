.DEFAULT_GOAL = help

.PHONY: help sync check-install probe-models probe-paddle probe-compare \
       test-ocr test-client serve serve-rapid serve-easy serve-paddle \
       package package-upx release zip upload clean

help: ## 显示所有目标
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────
# uv 环境
# ──────────────────────────────────────────────
sync: ## 同步 uv 虚拟环境与依赖（快速还原环境）
	uv sync

# ──────────────────────────────────────────────
# 调测
# ──────────────────────────────────────────────
check-install: ## 检查 PaddlePaddle 是否安装
	uv run python check_install.py

probe-models: ## 探测 PaddleOCR 模型缓存位置
	uv run python probe_models.py

probe-paddle: ## 探测 Paddle 包位置
	uv run python probe_paddle.py

probe-compare: ## 对比 PaddleOCR vs RapidOCR 在同一图上的识别
	uv run python probe_compare.py

test-ocr: ## 测试 OCR HTTP 接口（urllib，无需额外依赖）
	uv run python test_ocr.py

test-client: ## 测试 OpenAI 兼容客户端（需 requests）
	uv run python test_client.py

serve: ## 启动 PaddleOCR Mobile 服务（端口 8005）
	uv run python app_paddle_mobile.py --host 0.0.0.0 --port 8005

serve-rapid: ## 启动 RapidOCR(ONNX) 服务（端口 8006）
	uv run python app_rapidocr.py --host 0.0.0.0 --port 8006

serve-easy: ## 启动 EasyOCR 轻量服务（端口 8003）
	uv run python app_easyocr.py --host 0.0.0.0 --port 8003

# ──────────────────────────────────────────────
# 打包（uv 运行 pyinstaller）
# ──────────────────────────────────────────────
package: ## 打包 exe（console 版，默认 spec）
	uv run pyinstaller --noconfirm paddle-ocr.spec

package-upx: package ## 打包并 UPX 压缩（若 upx 在 PATH 中）
	@if command -v upx >/dev/null 2>&1; then upx dist/paddle-ocr/paddle-ocr.exe; else echo "upx not found, skipping"; fi

release: package-upx zip ## 一键 打包+压缩+打 zip
	@echo "Release ready: $(shell ls -la paddle-ocr.zip 2>/dev/null || echo paddle-ocr.zip)"

zip: ## 把 dist 打成 paddle-ocr.zip
	cd dist && zip -r ../paddle-ocr.zip paddle-ocr/

upload: zip ## 上传到 GitHub Release（需 .nexus/auth/token）
	uv run python upload.py

clean: ## 清理 build / dist / zip 产物
	rm -rf build dist paddle-ocr.zip
	@echo "cleaned."

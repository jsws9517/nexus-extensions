.DEFAULT_GOAL = help

.PHONY: help sync package package-upx release zip clean

help: ## 显示所有目标
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────
# uv 环境
# ──────────────────────────────────────────────
sync: ## 同步 uv 虚拟环境与依赖（快速还原环境）
	uv sync

# ──────────────────────────────────────────────
# 打包（uv 运行 pyinstaller，入口 ocr.py）
# ──────────────────────────────────────────────
package: ## 打包 exe（console 版，默认 spec）
	uv run pyinstaller --noconfirm paddle-ocr.spec

package-upx: package ## 打包并 UPX 压缩（若 upx 在 PATH 中）
	@if command -v upx >/dev/null 2>&1; then upx dist/paddle-ocr/paddle-ocr.exe; else echo "upx not found, skipping"; fi

release: package-upx zip ## 一键 打包+压缩+打 zip
	@echo "Release ready: $(shell ls -la paddle-ocr.zip 2>/dev/null || echo paddle-ocr.zip)"

zip: ## 把 dist 打成 paddle-ocr.zip
	cd dist && zip -r ../paddle-ocr.zip paddle-ocr/

clean: ## 清理 build / dist / zip 产物
	rm -rf build dist paddle-ocr.zip
	@echo "cleaned."

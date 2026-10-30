# PaddleOCR Standalone

`paddle-ocr` —— 基于 **RapidOCR + ONNX Runtime** 的独立 OCR 可执行程序（exe）。

不依赖 PaddlePaddle，使用 **PP-OCRv6** 模型，CPU 即可运行。从图片中提取文字，
支持中英文等多语言识别，单文件 exe 可离线分发。

## 特性

- **单文件 exe**：PyInstaller 打包成 onefile，免安装、免 Python 环境，直接运行。
- **纯 CPU / 离线**：ONNX Runtime CPU 推理，无需 GPU，可脱离外网使用。
- **多语言**：内置中文（简繁）、英文、日文、韩文、法文、德文等。
- **JSON / 文本双输出**：结构化结果含识别文本、置信度、行数；`--show-boxes` 可输出逐行框。
- **管道集成**：支持 `--stdin` 从标准输入读取图片路径。

## 项目结构

```
paddle-standalone/
├── ocr.py               # CLI 入口（argparse + rapidocr 调用）
├── paddle-ocr.spec      # PyInstaller 打包脚本
├── pyproject.toml       # uv 依赖清单（rapidocr + onnxruntime）
├── uv.lock              # uv 锁文件（含 onnxruntime 依赖链）
├── Makefile             # 打包 / 同步 / 发布入口
├── .dockerignore        # 父级 Docker 镜像构建排除清单（与本项目打包无关）
└── .nexus/gitignore     # 临时目录忽略规则
```

## 依赖

| 依赖 | 版本 | 说明 |
|---|---|---|
| `rapidocr` | `>=3.9.2` | 模型封装，PP-OCRv6 |
| `onnxruntime` | `>=1.17.0` | ONNX 推理引擎（CPU） |
| `pyinstaller` | `>=6.21.0` | 开发依赖，打包用 |

> ⚠️ **onnxruntime 必须随 rapidocr 一起安装**（rapidocr 懒加载，不会自动带）。
> 已写入 `pyproject.toml`，`uv sync` 会自动装齐。若手动装，国内建议用中科大镜像：
>
> ```
> uv pip install onnxruntime -i https://pypi.mirrors.ustc.edu.cn/simple
> ```

## 环境还原

```bash
# 一键还原 .venv + 所有依赖
make sync
# 等价于：uv sync
```

## 本地运行（不打包）

```bash
uv run python ocr.py --image screenshot.png
uv run python ocr.py --image photo.jpg --lang en --output text
```

## 打包 exe

```bash
# 打包（onefile console 版）
make package
# 打包 + UPX 压缩（upx 在 PATH 时生效）
make package-upx
# 一键 打包 + 压缩 + 打 zip
make release
```

产物：

- `dist/paddle-ocr.exe` —— 单文件可执行程序
- `paddle-ocr.zip` —— 发布压缩包（`make release` 生成）

> 打包脚本 `paddle-ocr.spec` 已通过 `collect_all` 收集 `rapidocr` 与
> `onnxruntime` 的全部数据 / 二进制，无需手动维护 hiddenimports。

## 使用方法

### 基本用法

```bash
paddle-ocr.exe --image screenshot.png
```

输出（默认 JSON）：

```json
{"text": "HELLOOCR123", "confidence": 0.9996, "count": 1}
```

### 参数

| 参数 | 说明 | 默认 |
|---|---|---|
| `--image PATH` | 图片路径（png/jpg/gif/bmp/tiff/webp） | 必填 |
| `--lang LANG` | 语言：`ch` / `en` / `japan` / `korean` / `fr` / `de` | `ch` |
| `--output FORMAT` | 输出格式：`json` / `text` | `json` |
| `--show-boxes` | JSON 中附带逐行置信度框 | 关 |
| `--stdin` | 从标准输入读取图片路径（管道用） | 关 |
| `--version` | 显示版本 | - |
| `-h`, `--help` | 帮助 | - |

### 示例

```bash
# 纯文本输出
paddle-ocr.exe --image doc.png --output text

# 指定英文 + 逐行框
paddle-ocr.exe --image photo.jpg --lang en --show-boxes

# 管道集成：路径来自 stdin
echo "C:\\path\\to\\img.png" | paddle-ocr.exe --stdin
```

### 输出格式

- **JSON**：`{"text": "…", "confidence": 0.95, "count": 25}`，`--show-boxes` 时
  追加 `"boxes": [{"text": "…", "confidence": 0.98}, ...]`。
- **TEXT**：多行文本以换行符拼接直接输出。

### 退出码

| 码 | 含义 |
|---|---|
| `0` | 成功（含空图：返回空文本） |
| `1` | 错误（文件不存在 / OCR 失败等） |

## 故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| `ImportError: onnxruntime is not installed` | onnxruntime 未进 venv / 未打进 exe | `uv sync` 装齐；确认 spec 含 `collect_all('onnxruntime')` |
| 打包后 exe 缺 dll / hidden import 报错 | onnxruntime 缺失导致模块图解析失败 | 装 onnxruntime 后重新 `make package` |
| 官网 PyPI 拉包卡死 | 国内网络访问 onnxruntime（~14MB）慢 | 切中科大镜像 `pypi.mirrors.ustc.edu.cn` |

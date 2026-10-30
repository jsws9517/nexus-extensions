# -*- mode: python ; coding: utf-8 -*-
"""
paddle-ocr.spec — 独立版 CLI 打包配置（PyInstaller onefile）。
入口 ocr.py，rapidocr（onnxruntime）推理栈，内置 RapidOCR 模型。
onnxruntime 的 native 扩展用 collect_all 整体收集，确保 exe 可独立运行。
"""
from PyInstaller.utils.hooks import collect_all

ROOT = r'D:\agent-cli\paddle-standalone'
SITE = ROOT + r'\.venv\Lib\site-packages'

# 整体收集 onnxruntime（包含其 native 扩展 .pyd/.dll 与数据）
onnx_datas, onnx_binaries, onnx_hiddenimports = collect_all('onnxruntime')

# collect_all 收的是已知子模块 + native 扩展；但 rapidocr 的 get_engine 用
# import_package("onnxruntime") 做动态字符串 import 探测，onefile 里必须把
# onnxruntime 的顶层包与推理核心子模块显式登记为 hidden import，否则探测失败。
# 只收推理必需子包（capi + backend），不收 tools/transformers/quantization 等
# 与 OCR 无关的庞大子包，控制体积。
ORT_CORE = [
    'onnxruntime',
    'onnxruntime.capi',
    'onnxruntime.capi._ld_preload',
    'onnxruntime.capi._pybind_state',
    'onnxruntime.capi.onnxruntime_inference_collection',
    'onnxruntime.capi.onnxruntime_validation',
    'onnxruntime.capi.version_info',
    'onnxruntime.backend',
    'onnxruntime.backend.backend',
    'onnxruntime.backend.backend_rep',
]
onnx_hiddenimports += ORT_CORE

a = Analysis(
    [ROOT + r'\ocr.py'],
    pathex=[],
    binaries=onnx_binaries,
    datas=onnx_datas + [
        (SITE + r'\rapidocr\default_models.yaml', 'rapidocr'),
        (SITE + r'\rapidocr\config.yaml', 'rapidocr'),
        (SITE + r'\rapidocr\models', 'rapidocr/models'),
    ],
    hiddenimports=onnx_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'scipy', 'matplotlib', 'pandas', 'setuptools'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='paddle-ocr',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[ROOT + r'\paddle-ocr.ico'],
)

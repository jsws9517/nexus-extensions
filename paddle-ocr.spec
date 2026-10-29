# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\agent-cli\\paddle-standalone\\ocr.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\agent-cli\\paddle-standalone\\.venv\\Lib\\site-packages\\rapidocr\\default_models.yaml', 'rapidocr'), ('D:\\agent-cli\\paddle-standalone\\.venv\\Lib\\site-packages\\rapidocr\\config.yaml', 'rapidocr'), ('D:\\agent-cli\\paddle-standalone\\.venv\\Lib\\site-packages\\rapidocr\\models', 'rapidocr/models')],
    hiddenimports=[],
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
    icon=['D:\\agent-cli\\paddle-standalone\\paddle-ocr.ico'],
)

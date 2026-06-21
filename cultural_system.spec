# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置：生成独立的 cultural_system 桌面应用目录。
本地调试：
    pyinstaller cultural_system.spec --clean --noconfirm
"""
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.api import PYZ, EXE, COLLECT
import os

block_cipher = None

# 项目根目录
root = os.path.abspath(SPECPATH)

# 需要额外包含的数据文件/目录：(源路径, 目标目录)
datas = [
    ("style.qss", "."),
    ("database", "database"),
    ("views", "views"),
    ("core", "core"),
    ("config.py", "."),
]

a = Analysis(
    ["main.py"],
    pathex=[root],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "pandas", "scipy", "PIL"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="文化矩阵引擎",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(root, "assets", "app.ico") if os.path.exists(os.path.join(root, "assets", "app.ico")) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="文化矩阵引擎",
)

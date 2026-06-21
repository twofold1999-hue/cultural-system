"""
构建脚本：先调用 PyInstaller 生成独立应用目录，再调用 Inno Setup 生成安装包。

用法：
    python scripts/build.py
环境要求：
    - Windows
    - Python 已安装 pyinstaller
    - Inno Setup 6 已安装且 iscc.exe 在 PATH 中（GitHub Actions 会自动安装）
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
INSTALLER_DIR = ROOT / "installer"


def run(cmd, cwd=None):
    print(f">>> {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def clean():
    print("清理旧构建产物...")
    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            shutil.rmtree(d)


def build_pyinstaller():
    print("PyInstaller 打包中...")
    run([sys.executable, "-m", "PyInstaller", "cultural_system.spec", "--clean", "--noconfirm"])


def build_installer():
    print("生成 Windows 安装包...")
    iscc_candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    iscc = shutil.which("iscc")
    if iscc:
        iscc_path = Path(iscc)
    else:
        iscc_path = next((p for p in iscc_candidates if p.exists()), None)

    if not iscc_path or not iscc_path.exists():
        raise FileNotFoundError("未找到 Inno Setup 的 ISCC.exe，请安装 Inno Setup 6")

    run([str(iscc_path), str(ROOT / "installer.iss")])


def main():
    clean()
    build_pyinstaller()
    build_installer()
    print("构建完成。安装包位于 dist/ 目录。")


if __name__ == "__main__":
    main()

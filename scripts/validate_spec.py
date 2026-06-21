"""验证 PyInstaller spec 文件可解析"""
import sys
from pathlib import Path

spec_path = Path(__file__).resolve().parent.parent / "cultural_system.spec"
print(f"验证 spec: {spec_path}")

# 通过 exec 执行 spec 文件，PyInstaller 会构建 Analysis 对象
globs = {"__file__": str(spec_path), "SPECPATH": str(spec_path.parent)}
with open(spec_path, "r", encoding="utf-8") as f:
    code = compile(f.read(), str(spec_path), "exec")
exec(code, globs)

# 如果执行到这里，说明 spec 配置可解析
print("spec 文件解析成功")
print(f"  分析脚本数量: {len(globs['a'].scripts)}")
print(f"  数据文件数量: {len(globs['a'].datas)}")
print(f"  二进制数量: {len(globs['a'].binaries)}")

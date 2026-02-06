#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将程序打包成exe
"""

import subprocess
import sys
from pathlib import Path

def build_exe():
    """使用PyInstaller打包"""
    
    # 确保PyInstaller已安装
    try:
        import PyInstaller
        print("PyInstaller 已安装")
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # 获取当前脚本所在目录
    auto_dir = Path(__file__).parent
    main_script = str(auto_dir / "main.py")
    icon_file = None  # 如果有图标文件，可以指定路径
    
    # 构建命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",           # 打包成单个exe文件
        "--windowed",          # 使用GUI模式，不显示控制台
        "--name", "SpineDressManager",  # exe文件名
        "--add-data", f"{auto_dir / 'modules'};modules",  # 包含modules文件夹
        "--hidden-import", "sqlite3",  # 显式包含sqlite3
        "--hidden-import", "json",
        "--hidden-import", "pathlib",
        "--hidden-import", "datetime",
        "--clean",             # 清理临时文件
        main_script
    ]
    
    # 如果有图标，添加图标
    if icon_file and Path(icon_file).exists():
        cmd.extend(["--icon", icon_file])
    
    print(f"执行命令: {' '.join(cmd)}")
    print("开始打包...")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 打包成功!")
        print(f"exe文件位置: {Path('dist/SpineDressManager.exe').absolute()}")
    else:
        print("❌ 打包失败!")
        print("错误输出:")
        print(result.stderr)
        print("标准输出:")
        print(result.stdout)

if __name__ == "__main__":
    build_exe()

# Spine Dress Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

一款开源的2D服装素材管理工具，专为Spine动画设计。支持素材导入、自动分类、打标管理和角色合成。

## ✨ 功能特性

- 📦 **批量导入** - 自动扫描并导入服装素材
- 🏷️ **智能打标** - 给服装添加自定义名称和描述
- 🎨 **Spine合成** - 一键合成完整角色JSON
- 📁 **自动分类** - 按服装类型自动整理
- 🎬 **动画支持** - 支持动画文件合并
- 🔍 **素材预览** - 可视化浏览所有素材

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Windows 10/11

### 安装运行

```bash
# 克隆仓库
git clone https://github.com/chengsisi/SpineDressManager.git
cd SpineDressManager

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

### 打包成EXE

```bash
python build_exe.py
```

打包后的文件位于 `dist/SpineDressManager.exe`

## 📖 使用教程

### 1. 导入素材
- 点击菜单 `文件` → `导入素材`
- 选择包含服装素材的文件夹
- 软件会自动扫描所有 dress.json 文件并分类

### 2. 服装打标
- 切换到 `服装打标` 标签页
- 选择要打标的服装
- 输入自定义名称和描述
- 点击保存

### 3. Spine角色合成
- 切换到 `Spine合成` 标签页
- 选择 role.json 基础文件
- 从下拉菜单选择各部位服装
- 设置角色名称
- 点击开始合成

### 4. 导入Spine
- 打开 Spine 软件
- 文件 → 导入数据
- 选择生成的 JSON 文件
- 完成！

## 📁 项目结构

```
SpineDressManager/
├── main.py                 # 主程序入口
├── build_exe.py           # 打包脚本
├── requirements.txt       # 依赖列表
├── modules/               # 核心模块
│   ├── database.py       # 数据库管理
│   ├── asset_processor.py # 素材处理
│   └── spine_builder.py  # Spine合成
└── README.md             # 项目说明
```

## 🛠️ 技术栈

- **GUI**: Tkinter
- **数据库**: SQLite3
- **打包**: PyInstaller
- **开发语言**: Python 3

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议

**免费使用，开源共享！**

## 👨‍💻 开发者

**程思思**

- 开源项目，欢迎贡献
- 有问题请提交 Issue
- 欢迎Star和Fork

## 🙏 致谢

感谢 [Spine](http://esotericsoftware.com/) 提供的优秀2D动画工具

---

## ⚖️ 法律声明

### 商标声明
- **Spine** 是 [Esoteric Software](http://esotericsoftware.com/) 的注册商标
- 本工具与Esoteric Software无官方关联

### 免责声明
1. 本工具仅供学习交流使用
2. 用户需自行确保导入的素材文件（dress.json、action.json、图片等）拥有合法使用权
3. 本工具不存储、分发任何受版权保护的素材
4. 使用本工具产生的任何法律责任由用户自行承担

### 开源协议
本项目采用 [MIT License](LICENSE) 开源协议，免费使用，开源共享！

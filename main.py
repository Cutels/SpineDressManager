#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spine Dress Manager - 2D服装素材管理工具
功能：素材导入、分类、打标、Spine合成
开源项目，免费使用
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import sys
import os
import json
from datetime import datetime

# 获取资源路径（支持打包后的exe）
def get_resource_path(relative_path):
    """获取资源文件的绝对路径（支持开发和打包环境）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = Path(sys._MEIPASS)
    else:
        # 开发环境
        base_path = Path(__file__).parent
    return base_path / relative_path

# 添加模块路径
modules_path = get_resource_path("modules")
sys.path.insert(0, str(modules_path))

from database import ClothingDatabase
from asset_processor import AssetProcessor
from spine_builder import SpineBuilder

class ClothingManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spine Dress Manager v1.0 - 程思思开发，免费，开源！！")
        self.root.geometry("1200x800")
        
        # 初始化数据库（存储在当前程序目录下）
        if hasattr(sys, '_MEIPASS'):
            # 打包后的exe环境，使用exe所在目录
            db_dir = Path(sys.executable).parent / "database"
        else:
            # 开发环境，使用脚本所在目录
            db_dir = Path(__file__).parent / "database"
        db_dir.mkdir(exist_ok=True)
        self.db = ClothingDatabase(str(db_dir / "clothing.db"))
        self.processor = AssetProcessor("", self.db)
        self.builder = SpineBuilder(self.db)
        
        # 当前选中的素材
        self.current_selection = {}
        
        self.setup_ui()
        self.refresh_statistics()
        
    def setup_ui(self):
        """设置主界面"""
        # 菜单栏
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导入素材", command=self.show_import_dialog)
        file_menu.add_command(label="分离动画", command=self.separate_animations)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 主标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标签页1：素材管理
        self.frame_manage = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_manage, text="📦 素材管理")
        self.setup_manage_tab()
        
        # 标签页2：打标工具
        self.frame_label = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_label, text="🏷️ 打标工具")
        self.setup_label_tab()
        
        # 标签页3：Spine合成
        self.frame_build = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_build, text="🔧 Spine合成")
        self.setup_build_tab()
        
        # 标签页4：统计信息
        self.frame_stats = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_stats, text="📊 统计信息")
        self.setup_stats_tab()
        
        # 状态栏
        self.status_label = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_manage_tab(self):
        """设置素材管理标签页"""
        # 工具栏
        toolbar = ttk.Frame(self.frame_manage)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="📥 导入素材", command=self.show_import_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🎬 分离动画", command=self.separate_animations).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_manage_list).pack(side=tk.LEFT, padx=5)
        
        # 分类列表
        paned = ttk.PanedWindow(self.frame_manage, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧类型列表
        type_frame = ttk.LabelFrame(paned, text="服装类型")
        paned.add(type_frame, weight=1)
        
        self.type_listbox = tk.Listbox(type_frame, width=25)
        self.type_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.type_listbox.bind('<<ListboxSelect>>', self.on_type_select)
        
        # 右侧素材列表
        item_frame = ttk.LabelFrame(paned, text="素材列表")
        paned.add(item_frame, weight=3)
        
        columns = ('md5', 'name', 'type', 'labeled', 'animation')
        self.item_tree = ttk.Treeview(item_frame, columns=columns, show='headings')
        
        self.item_tree.heading('md5', text='MD5')
        self.item_tree.heading('name', text='名称')
        self.item_tree.heading('type', text='类型')
        self.item_tree.heading('labeled', text='已打标')
        self.item_tree.heading('animation', text='动画')
        
        self.item_tree.column('md5', width=200)
        self.item_tree.column('name', width=150)
        self.item_tree.column('type', width=100)
        self.item_tree.column('labeled', width=60)
        self.item_tree.column('animation', width=60)
        
        self.item_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(item_frame, orient=tk.VERTICAL, command=self.item_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.item_tree.configure(yscrollcommand=scrollbar.set)
        
        # 加载类型列表
        self.refresh_type_list()
        
    def setup_label_tab(self):
        """设置打标工具标签页 - 优化版"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.frame_label)
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_label_view).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📁 切换动画/服装", command=self.toggle_label_mode).pack(side=tk.LEFT, padx=5)
        self.label_mode_var = tk.StringVar(value="clothing")
        ttk.Label(toolbar, textvariable=self.label_mode_var, font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10)
        
        # 主分割窗口
        paned = ttk.PanedWindow(self.frame_label, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧：类型和文件夹树
        left_paned = ttk.PanedWindow(paned, orient=tk.VERTICAL)
        paned.add(left_paned, weight=1)
        
        # 类型列表
        type_frame = ttk.LabelFrame(left_paned, text="服装类型")
        left_paned.add(type_frame, weight=1)
        
        self.label_type_tree = tk.Listbox(type_frame, width=30)
        self.label_type_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.label_type_tree.bind('<<ListboxSelect>>', self.on_label_type_select)
        
        # 文件夹列表
        folder_frame = ttk.LabelFrame(left_paned, text="文件夹")
        left_paned.add(folder_frame, weight=2)
        
        self.label_folder_tree = tk.Listbox(folder_frame, width=30)
        self.label_folder_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.label_folder_tree.bind('<<ListboxSelect>>', self.on_label_folder_select)
        
        # 右侧：编辑区和预览
        right_paned = ttk.PanedWindow(paned, orient=tk.VERTICAL)
        paned.add(right_paned, weight=3)
        
        # 编辑区
        edit_frame = ttk.LabelFrame(right_paned, text="打标编辑")
        right_paned.add(edit_frame, weight=1)
        
        # 表单
        form_frame = ttk.Frame(edit_frame)
        form_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(form_frame, text="MD5(数据库):", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.label_md5_db = ttk.Label(form_frame, text="-", foreground='gray')
        self.label_md5_db.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(form_frame, text="当前文件夹名:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.label_folder_name = ttk.Label(form_frame, text="-")
        self.label_folder_name.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(form_frame, text="类型:", font=('Arial', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.label_type_name = ttk.Label(form_frame, text="-")
        self.label_type_name.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(form_frame, text="新名称:", font=('Arial', 9, 'bold'), foreground='blue').grid(row=3, column=0, sticky=tk.W, pady=5)
        self.entry_new_name = ttk.Entry(form_frame, width=40)
        self.entry_new_name.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(form_frame, text="描述:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.entry_label_desc = ttk.Entry(form_frame, width=40)
        self.entry_label_desc.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # 按钮
        btn_frame = ttk.Frame(edit_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="💾 保存标签", command=self.save_label, width=20).pack(side=tk.LEFT, padx=5)
        
        # 预览区 - 显示文件夹内所有图片
        preview_frame = ttk.LabelFrame(right_paned, text="文件夹内容预览")
        right_paned.add(preview_frame, weight=2)
        
        # 创建Canvas用于显示图片网格
        self.preview_canvas = tk.Canvas(preview_frame, bg='#f0f0f0')
        self.preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_canvas.yview)
        self.preview_inner_frame = ttk.Frame(self.preview_canvas)
        
        self.preview_canvas.configure(yscrollcommand=self.preview_scrollbar.set)
        
        self.preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.preview_canvas_window = self.preview_canvas.create_window((0, 0), window=self.preview_inner_frame, anchor=tk.NW)
        
        def on_preview_configure(event):
            self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
        self.preview_inner_frame.bind('<Configure>', on_preview_configure)
        
        def on_preview_canvas_configure(event):
            self.preview_canvas.itemconfig(self.preview_canvas_window, width=event.width)
        self.preview_canvas.bind('<Configure>', on_preview_canvas_configure)
        
        self.preview_images = []  # 保持图片引用
        
        # 当前选中项
        self.current_label_item = None
        
        # 加载数据
        self.refresh_label_view()
        
    def setup_build_tab(self):
        """设置Spine合成标签页"""
        # 角色配置
        config_frame = ttk.LabelFrame(self.frame_build, text="角色配置")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # role.json 选择
        ttk.Label(config_frame, text="role.json:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.role_path_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.role_path_var, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(config_frame, text="浏览...", command=self.browse_role).grid(row=0, column=2, padx=5, pady=5)
        
        # 角色名称
        ttk.Label(config_frame, text="角色名称:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.char_name_var = tk.StringVar(value="character_001")
        ttk.Entry(config_frame, textvariable=self.char_name_var, width=40).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 动画选项
        self.include_anim_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(config_frame, text="包含动画", variable=self.include_anim_var).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(config_frame, text="动画文件:").grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        self.anim_path_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.anim_path_var, width=50).grid(row=2, column=1, padx=(100, 5), pady=5)
        ttk.Button(config_frame, text="浏览...", command=self.browse_animation).grid(row=2, column=2, padx=5, pady=5)
        
        # 服装选择区
        select_frame = ttk.LabelFrame(self.frame_build, text="服装选择")
        select_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建滚动区域
        canvas = tk.Canvas(select_frame)
        scrollbar = ttk.Scrollbar(select_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.build_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas_window = canvas.create_window((0, 0), window=self.build_frame, anchor=tk.NW)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self.build_frame.bind('<Configure>', on_frame_configure)
        
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', on_canvas_configure)
        
        # 加载服装选择控件
        self.load_build_selections()
        
        # 合成按钮
        ttk.Button(self.frame_build, text="🔨 开始合成", command=self.build_character).pack(pady=20)
        
    def setup_stats_tab(self):
        """设置统计信息标签页"""
        self.stats_text = tk.Text(self.frame_stats, wrap=tk.WORD, font=('Consolas', 11))
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Button(self.frame_stats, text="🔄 刷新统计", command=self.refresh_statistics).pack(pady=10)
        
    # ==================== 功能方法 ====================
    
    def show_import_dialog(self):
        """显示导入对话框"""
        folder = filedialog.askdirectory(title="选择素材文件夹（v1.0）")
        if not folder:
            return
        
        self.status_label.config(text=f"正在导入: {folder}...")
        self.root.update()
        
        # 创建处理器
        processor = AssetProcessor(folder, self.db, self.update_import_progress)
        
        # 执行导入
        results = processor.scan_and_import()
        
        # 显示结果
        message = f"导入完成！\n总计: {results['total']}\n成功: {results['success']}\n跳过: {results['skipped']}\n失败: {results['failed']}"
        messagebox.showinfo("导入完成", message)
        
        self.status_label.config(text="导入完成")
        self.refresh_statistics()
        self.refresh_type_list()
        
    def update_import_progress(self, current, results):
        """更新导入进度"""
        self.status_label.config(text=f"导入中... {current} 个已处理")
        self.root.update()
        
    def separate_animations(self):
        """分离动画"""
        # 扫描动画
        animations = self.db.get_all_animations()
        if not animations:
            messagebox.showinfo("提示", "数据库中没有动画素材")
            return
        
        # 选择目标目录
        target = filedialog.askdirectory(title="选择动画存放目录")
        if not target:
            return
        
        # 执行分离
        processor = AssetProcessor("", self.db)
        count = processor.separate_animations(target)
        
        messagebox.showinfo("完成", f"已分离 {count} 个动画到 {target}")
        self.refresh_statistics()
        
    def refresh_type_list(self):
        """刷新类型列表"""
        self.type_listbox.delete(0, tk.END)
        
        items_by_type = self.db.get_items_by_type()
        for clothing_type in sorted(items_by_type.keys()):
            count = len(items_by_type[clothing_type])
            self.type_listbox.insert(tk.END, f"{clothing_type} ({count})")
            
    def on_type_select(self, event):
        """类型选择事件"""
        selection = self.type_listbox.curselection()
        if not selection:
            return
            
        type_text = self.type_listbox.get(selection[0])
        clothing_type = type_text.split(' (')[0]
        
        # 刷新素材列表
        self.item_tree.delete(*self.item_tree.get_children())
        
        items = self.db.get_all_items(clothing_type)
        for item in items:
            self.item_tree.insert('', tk.END, values=(
                item['md5_hash'],
                item['custom_name'] or '-',
                item['clothing_type'],
                '是' if item['custom_name'] else '否',
                '是' if item['has_animation'] else '否'
            ))
            
    def refresh_manage_list(self):
        """刷新管理列表"""
        self.refresh_type_list()
        self.item_tree.delete(*self.item_tree.get_children())
        
    def toggle_label_mode(self):
        """切换打标模式（服装/动画）"""
        current = self.label_mode_var.get()
        if current == "clothing":
            self.label_mode_var.set("animation")
        else:
            self.label_mode_var.set("clothing")
        self.refresh_label_view()
    
    def refresh_label_view(self):
        """刷新打标视图"""
        mode = self.label_mode_var.get()
        
        # 清空列表
        self.label_type_tree.delete(0, tk.END)
        self.label_folder_tree.delete(0, tk.END)
        
        if mode == "clothing":
            # 加载服装类型
            items_by_type = self.db.get_items_by_type()
            for clothing_type in sorted(items_by_type.keys()):
                if clothing_type != 'Action':
                    count = len(items_by_type[clothing_type])
                    labeled = sum(1 for item in items_by_type[clothing_type] if item['custom_name'])
                    display = f"{clothing_type} ({labeled}/{count})"
                    self.label_type_tree.insert(tk.END, display)
                    # 未完全打标的标红
                    if labeled < count:
                        self.label_type_tree.itemconfig(tk.END, foreground='red')
        else:
            # 加载动画
            animations = self.db.get_all_animations()
            self.label_type_tree.insert(tk.END, f"动画 ({len(animations)})")
    
    def on_label_type_select(self, event):
        """类型选择事件"""
        selection = self.label_type_tree.curselection()
        if not selection:
            return
        
        type_text = self.label_type_tree.get(selection[0])
        
        # 清空文件夹列表
        self.label_folder_tree.delete(0, tk.END)
        # 清空MD5映射
        self.folder_md5_map = {}
        
        mode = self.label_mode_var.get()
        
        if mode == "clothing":
            clothing_type = type_text.split(' (')[0]
            items = self.db.get_all_items(clothing_type)
            
            for idx, item in enumerate(items):
                md5_hash = item['md5_hash']
                
                # 尝试多个可能的路径
                original_path = Path(item['source_path'])
                possible_paths = [
                    original_path,
                    Path('D:/WEB5/数据v1.0版本') / md5_hash,
                    Path('D:/WEB5/数据v2.0版本') / md5_hash,
                ]
                
                found_path = None
                meta_data = {}
                for test_path in possible_paths:
                    if test_path and test_path.exists():
                        # 检查是否有 meta.json
                        meta_path = test_path / 'meta.json'
                        if meta_path.exists():
                            try:
                                with open(meta_path, 'r', encoding='utf-8') as f:
                                    meta_data = json.load(f)
                            except:
                                pass
                        found_path = test_path
                        break
                
                if found_path:
                    # 优先使用 meta.json 中的名称
                    display_name = meta_data.get('name') or found_path.name
                    is_labeled = bool(meta_data.get('name'))
                    
                    if is_labeled:
                        display = f"✓ {display_name}"
                        self.label_folder_tree.insert(tk.END, display)
                        self.label_folder_tree.itemconfig(tk.END, foreground='green')
                    else:
                        # 显示截断的名字
                        short_name = display_name[:20] + "..." if len(display_name) > 20 else display_name
                        display = f"  {short_name}"
                        self.label_folder_tree.insert(tk.END, display)
                        self.label_folder_tree.itemconfig(tk.END, foreground='black')
                    
                    # 保存MD5映射和实际路径
                    self.folder_md5_map[idx] = md5_hash
                    # 更新item的source_path为找到的路径，并合并meta数据
                    item['source_path'] = str(found_path)
                    item['meta_data'] = meta_data
                    item['custom_name'] = meta_data.get('name')
                    item['description'] = meta_data.get('description')
        else:
            # 动画模式
            print(f"[DEBUG] 加载动画模式...")
            animations = self.db.get_all_animations()
            print(f"[DEBUG] 获取到 {len(animations)} 个动画")
            
            for idx, anim in enumerate(animations):
                md5_hash = anim['md5_hash']
                md5_name = md5_hash  # 用于构建路径
                
                # 尝试多个可能的路径
                folder_path = Path(anim['source_path'])
                possible_paths = [
                    folder_path,
                    Path(str(folder_path).replace('数据v1.0版本', '数据v1.1版本')),
                    Path('D:/WEB5/数据v1.1版本') / md5_name,
                    Path('D:/WEB5/数据v1.0版本') / md5_name,
                    Path('D:/WEB5/数据v1.0.0版本') / md5_name,
                    Path('D:/WEB5/v1.0.0') / md5_name,
                ]
                
                found_path = None
                meta_data = {}
                for test_path in possible_paths:
                    if test_path.exists():
                        # 检查是否有 meta.json
                        meta_path = test_path / 'meta.json'
                        if meta_path.exists():
                            try:
                                with open(meta_path, 'r', encoding='utf-8') as f:
                                    meta_data = json.load(f)
                            except:
                                pass
                        found_path = test_path
                        break
                
                if found_path:
                    # 优先使用 meta.json 中的名称
                    display_name = meta_data.get('name') or anim.get('action_name', '') or found_path.name
                    is_labeled = bool(meta_data.get('name'))
                    
                    if is_labeled or anim.get('action_name'):
                        display = f"✓ {display_name}"
                        self.label_folder_tree.insert(tk.END, display)
                        self.label_folder_tree.itemconfig(tk.END, foreground='green')
                    else:
                        short_name = display_name[:20] + "..." if len(display_name) > 20 else display_name
                        display = f"  {short_name}"
                        self.label_folder_tree.insert(tk.END, display)
                    
                    # 保存MD5映射和实际路径
                    self.folder_md5_map[idx] = md5_hash
                    # 更新anim的source_path为找到的路径，并合并meta数据
                    anim['source_path'] = str(found_path)
                    anim['meta_data'] = meta_data
                    anim['action_name'] = meta_data.get('name') or anim.get('action_name')
                    anim['description'] = meta_data.get('description') or anim.get('description')
                    print(f"[DEBUG] 已添加到列表: {display}")
                else:
                    print(f"[DEBUG] 所有路径都不存在，跳过")
    
    def on_label_folder_select(self, event):
        """文件夹选择事件"""
        print(f"\n[DEBUG] ========== 文件夹选择事件 ==========")
        selection = self.label_folder_tree.curselection()
        if not selection:
            print("[DEBUG] 未选择任何文件夹")
            return
        
        idx = selection[0]
        print(f"[DEBUG] 选择的索引: {idx}")
        
        # 使用MD5映射查找
        if not hasattr(self, 'folder_md5_map') or idx not in self.folder_md5_map:
            print(f"[ERROR] 找不到MD5映射 for idx={idx}")
            return
        
        md5_hash = self.folder_md5_map[idx]
        print(f"[DEBUG] 对应的MD5: {md5_hash}")
        
        mode = self.label_mode_var.get()
        print(f"[DEBUG] 当前模式: {mode}")
        
        # 查找对应的数据库记录
        if mode == "clothing":
            print("[DEBUG] 开始查找服装...")
            item = self.db.get_item_by_md5(md5_hash)
            
            if item:
                print(f"[DEBUG] ✓ 找到匹配!")
                folder_path = Path(item['source_path'])
                self.current_label_item = item
                self.label_md5_db.config(text=item['md5_hash'])
                self.label_folder_name.config(text=folder_path.name)
                self.label_type_name.config(text=item['clothing_type'])
                self.entry_new_name.delete(0, tk.END)
                custom_name = item.get('custom_name') or ''
                self.entry_new_name.insert(0, custom_name)
                self.entry_label_desc.delete(0, tk.END)
                description = item.get('description') or ''
                self.entry_label_desc.insert(0, description)
                
                # 显示文件夹内所有图片
                print(f"[DEBUG] 调用 show_folder_preview: {folder_path}")
                self.show_folder_preview(folder_path)
            else:
                print(f"[ERROR] 未找到匹配的服装: {md5_hash}")
        else:
            # 动画模式
            print("[DEBUG] 开始查找动画...")
            animations = self.db.get_all_animations()
            
            for anim in animations:
                if anim['md5_hash'] == md5_hash:
                    print(f"[DEBUG] ✓ 找到匹配的动画!")
                    folder_path = Path(anim['source_path'])
                    self.current_label_item = anim
                    self.label_md5_db.config(text=anim['md5_hash'])
                    self.label_folder_name.config(text=folder_path.name)
                    self.label_type_name.config(text="动画")
                    self.entry_new_name.delete(0, tk.END)
                    action_name = anim.get('action_name') or ''
                    self.entry_new_name.insert(0, action_name)
                    self.entry_label_desc.delete(0, tk.END)
                    description = anim.get('description') or ''
                    self.entry_label_desc.insert(0, description)
                    
                    self.show_folder_preview(folder_path)
                    break
    
    def show_folder_preview(self, folder_path):
        """显示文件夹内所有图片预览 - 响应式布局"""
        print(f"[DEBUG] 开始显示文件夹预览: {folder_path}")
        
        # 清除旧图片
        for widget in self.preview_inner_frame.winfo_children():
            widget.destroy()
        self.preview_images.clear()
        
        # 检查文件夹是否存在
        if not folder_path.exists():
            ttk.Label(self.preview_inner_frame, text=f"文件夹不存在:\n{folder_path}").pack(pady=20)
            return
        
        # 查找所有图片
        png_files = sorted(folder_path.glob("*.png"))
        print(f"[DEBUG] 找到 {len(png_files)} 个PNG文件")
        
        if not png_files:
            ttk.Label(self.preview_inner_frame, text=f"文件夹内没有图片\n{folder_path}").pack(pady=20)
            return
        
        # 配置网格权重，使列可以均匀分布
        self.preview_inner_frame.columnconfigure(0, weight=1)
        self.preview_inner_frame.columnconfigure(1, weight=1)
        self.preview_inner_frame.columnconfigure(2, weight=1)
        self.preview_inner_frame.columnconfigure(3, weight=1)
        self.preview_inner_frame.columnconfigure(4, weight=1)
        self.preview_inner_frame.columnconfigure(5, weight=1)
        
        # 保存图片路径和加载状态
        self.preview_png_files = png_files
        self.preview_folder_path = folder_path
        self.preview_thumb_size = 100
        
        # 加载图片
        self.load_preview_images()
        
        # 绑定窗口大小变化事件
        self.preview_canvas.bind('<Configure>', self.on_preview_resize)
    
    def load_preview_images(self, cols=4):
        """加载预览图片到网格"""
        # 清除现有图片（保留框架结构）
        for widget in self.preview_inner_frame.winfo_children():
            widget.destroy()
        self.preview_images.clear()
        
        png_files = self.preview_png_files
        thumb_size = self.preview_thumb_size
        loaded_count = 0
        
        for idx, img_path in enumerate(png_files):
            try:
                from PIL import Image, ImageTk
                
                # 创建图片框架
                frame = ttk.Frame(self.preview_inner_frame, relief=tk.GROOVE, padding=2)
                row = idx // cols
                col = idx % cols
                frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
                
                # 加载并缩放图片
                img = Image.open(img_path)
                img.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.preview_images.append(photo)
                
                # 图片标签
                label = ttk.Label(frame, image=photo)
                label.pack()
                
                # 文件名标签
                name_label = ttk.Label(frame, text=img_path.name[:12], 
                                      wraplength=thumb_size, font=('Arial', 7))
                name_label.pack()
                
                loaded_count += 1
                
            except Exception as e:
                print(f"[ERROR] 无法加载图片 {img_path}: {e}")
        
        print(f"[DEBUG] 成功加载 {loaded_count}/{len(png_files)} 张图片，列数: {cols}")
        
        # 更新滚动区域
        self.preview_inner_frame.update_idletasks()
        bbox = self.preview_canvas.bbox("all")
        if bbox:
            self.preview_canvas.configure(scrollregion=bbox)
    
    def on_preview_resize(self, event):
        """预览区域大小变化时重新计算列数"""
        # 获取Canvas宽度
        canvas_width = event.width
        
        # 计算每行可以显示的图片数（每个图片约110px宽 + 间距）
        item_width = 120  # 图片宽度 + 间距
        cols = max(2, canvas_width // item_width)  # 至少2列
        cols = min(6, cols)  # 最多6列
        
        # 如果列数变化，重新加载
        if not hasattr(self, '_last_cols') or self._last_cols != cols:
            self._last_cols = cols
            if hasattr(self, 'preview_png_files') and self.preview_png_files:
                self.load_preview_images(cols)
                print(f"[DEBUG] 响应式重排: 宽度={canvas_width}, 列数={cols}")
    
    def save_label(self):
        """保存标签 - 只生成 meta.json，不重命名文件夹"""
        if not self.current_label_item:
            messagebox.showwarning("警告", "请先选择文件夹")
            return
        
        new_name = self.entry_new_name.get().strip()
        if not new_name:
            messagebox.showwarning("警告", "请输入新名称")
            return
        
        desc = self.entry_label_desc.get().strip()
        
        try:
            folder_path = Path(self.current_label_item['source_path'])
            
            mode = self.label_mode_var.get()
            
            # 创建 meta.json 文件
            meta_data = {
                'name': new_name,
                'description': desc,
                'md5': self.current_label_item['md5_hash'],
                'type': self.current_label_item.get('clothing_type') if mode == 'clothing' else 'Action',
                'labeled_at': str(datetime.now())
            }
            
            # 保存 meta.json 到文件夹
            meta_path = folder_path / 'meta.json'
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=2, ensure_ascii=False)
            
            # 更新数据库中的标签信息
            if mode == "clothing":
                self.db.update_clothing_label(
                    self.current_label_item['md5_hash'],
                    new_name,
                    desc,
                    None
                )
            else:
                self.db.add_animation(
                    self.current_label_item['md5_hash'],
                    folder_path.name,  # 保持原文件夹名(MD5)
                    new_name,  # 使用打标的名字
                    desc,
                    str(folder_path)  # 保持原路径
                )
            
            messagebox.showinfo("成功", f"已保存标签: {new_name}\n真实文件夹名保持: {folder_path.name}")
            self.refresh_label_view()
            
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 保留旧方法以兼容
    def refresh_unlabeled(self):
        """兼容旧方法"""
        self.refresh_label_view()
    
    def on_unlabeled_select(self, event):
        """兼容旧方法"""
        pass
    
    def show_preview(self, image_path):
        """兼容旧方法"""
        pass
    
    def select_thumbnail(self):
        """兼容旧方法"""
        pass
    

        
    def load_build_selections(self):
        """加载合成选择控件 - 三栏布局"""
        # 清除旧控件
        for widget in self.build_frame.winfo_children():
            widget.destroy()
            
        self.build_combos = {}
        
        # 获取所有类型
        items_by_type = self.db.get_items_by_type()
        
        # 如果没有素材，显示提示
        if not items_by_type or all(len(items) == 0 for items in items_by_type.values()):
            ttk.Label(self.build_frame, text="暂无素材，请先导入素材", 
                     font=('Arial', 12), foreground='red').pack(pady=20)
            ttk.Button(self.build_frame, text="📥 导入素材", 
                      command=self.show_import_dialog).pack(pady=10)
            return
        
        # 过滤掉Action类型
        clothing_types = [t for t in sorted(items_by_type.keys()) if t != 'Action']
        
        # 三栏布局：每行3个类型
        items_per_row = 3
        row = 0
        
        for i, clothing_type in enumerate(clothing_types):
            col = i % items_per_row
            
            # 创建框架容纳标签和下拉框
            frame = ttk.Frame(self.build_frame)
            frame.grid(row=row, column=col, sticky=tk.W, padx=10, pady=5)
            
            # 类型标签
            ttk.Label(frame, text=f"{clothing_type}:", width=12).pack(side=tk.LEFT)
            
            # 下拉框
            combo = ttk.Combobox(frame, width=25, state="readonly")
            combo.pack(side=tk.LEFT, padx=5)
            
            # 准备选项
            items = items_by_type[clothing_type]
            options = ["不选择"]
            for item in items:
                name = item['custom_name'] or item['md5_hash'][:16]
                options.append(f"{name} ({item['md5_hash'][:8]})")
                
            combo['values'] = options
            combo.set("不选择")
            
            # 如果是 HandOrnament 类型，禁用下拉菜单
            if clothing_type == "HandOrnament":
                combo.config(state="disabled")
                combo.set("暂不支持")
            
            self.build_combos[clothing_type] = combo
            
            # 每3个换一行
            if col == items_per_row - 1:
                row += 1
        
        # 如果最后一行不满3个，也换行
        if len(clothing_types) % items_per_row != 0:
            row += 1
            
    def browse_role(self):
        """浏览 role.json"""
        file = filedialog.askopenfilename(
            title="选择 role.json",
            filetypes=[("JSON files", "*.json")]
        )
        if file:
            self.role_path_var.set(file)
            
    def browse_animation(self):
        """浏览动画文件"""
        file = filedialog.askopenfilename(
            title="选择 action.json",
            filetypes=[("JSON files", "*.json")]
        )
        if file:
            self.anim_path_var.set(file)
            
    def build_character(self):
        """构建角色"""
        # 检查参数
        role_path = self.role_path_var.get()
        if not role_path:
            messagebox.showwarning("警告", "请选择 role.json")
            return
            
        char_name = self.char_name_var.get().strip()
        if not char_name:
            messagebox.showwarning("警告", "请输入角色名称")
            return
            
        # 收集选中的素材
        selected_items = {}
        for clothing_type, combo in self.build_combos.items():
            value = combo.get()
            if value != "不选择":
                # 提取MD5
                md5_short = value.split('(')[-1].rstrip(')')
                
                # 查找完整MD5
                items_by_type = self.db.get_items_by_type()
                for item in items_by_type.get(clothing_type, []):
                    if item['md5_hash'].startswith(md5_short):
                        selected_items[item['md5_hash']] = {
                            'type': clothing_type,
                            'path': item['source_path']
                        }
                        break
                        
        if not selected_items:
            messagebox.showwarning("警告", "请至少选择一种服装")
            return
            
        # 输出目录
        output_dir = Path("output") / char_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 执行合成
        self.status_label.config(text="正在合成...")
        self.root.update()
        
        try:
            result = self.builder.build_character(
                role_path,
                selected_items,
                output_dir,
                self.include_anim_var.get(),
                self.anim_path_var.get() if self.include_anim_var.get() else None
            )
            
            message = f"合成完成！\n\nJSON: {result['json_path']}\n图片: {result['total_images']} 张\n骨骼: {result['bones_count']}\n插槽: {result['slots_count']}\n附件: {result['attachments_count']}"
            messagebox.showinfo("成功", message)
            
            # 打开输出目录
            if messagebox.askyesno("打开文件夹", "是否打开输出文件夹？"):
                os.startfile(output_dir)
                
        except Exception as e:
            messagebox.showerror("错误", f"合成失败: {e}")
            import traceback
            traceback.print_exc()
            
        self.status_label.config(text="合成完成")
        
    def refresh_statistics(self):
        """刷新统计信息"""
        stats = self.db.get_statistics()
        
        text = "=" * 50 + "\n"
        text += "📊 服装素材统计\n"
        text += "=" * 50 + "\n\n"
        
        text += f"总素材数: {stats['total_items']}\n"
        text += f"动画数: {stats['total_animations']}\n\n"
        
        text += "按类型分布:\n"
        text += "-" * 50 + "\n"
        
        for stat in stats['type_stats']:
            labeled = stat['labeled_count'] or 0
            total = stat['count'] or 0
            text += f"{stat['clothing_type']}: {total} 个 (已打标: {labeled})\n"
            
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, text)

def main():
    root = tk.Tk()
    app = ClothingManagerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

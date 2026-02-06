#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
素材处理模块 - 分类和分离动画
"""

import json
import shutil
from pathlib import Path
from PIL import Image, ImageTk
import tkinter as tk

class AssetProcessor:
    def __init__(self, source_dir, db, progress_callback=None):
        self.source_dir = Path(source_dir)
        self.db = db
        self.progress_callback = progress_callback
        
    def process_folder(self, folder_path):
        """处理单个文件夹 - 读取 meta.json"""
        folder_path = Path(folder_path)
        md5_hash = folder_path.name
        
        # 检查是否已存在（服装表或动画表）
        if self.db.check_md5_exists(md5_hash) or self.db.check_animation_exists(md5_hash):
            return {'status': 'skipped', 'reason': '已存在', 'md5': md5_hash}
        
        # 读取 meta.json（如果存在）
        meta_data = {}
        meta_path = folder_path / 'meta.json'
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
                print(f"[DEBUG] 读取到 meta.json: {meta_data.get('name', '未命名')}")
            except Exception as e:
                print(f"[WARN] 无法读取 meta.json: {e}")
        
        # 检查是否有动画文件（优先处理动画）
        action_files = list(folder_path.glob("action*.json"))
        if action_files:
            # 这是动画文件夹
            try:
                # 优先使用 meta.json 中的名称
                action_name = meta_data.get('name')
                
                # 如果没有 meta，尝试读取 action.json
                if not action_name:
                    for action_file in action_files:
                        try:
                            with open(action_file, 'r', encoding='utf-8') as f:
                                action_data = json.load(f)
                                anims = action_data.get('animations', {})
                                if anims:
                                    action_name = list(anims.keys())[0]
                                break
                        except:
                            pass
                
                # 添加到动画表
                result = self.db.add_animation(
                    md5_hash=md5_hash,
                    folder_name=meta_data.get('name', md5_hash),
                    action_name=action_name,
                    description=meta_data.get('description'),
                    source_path=str(folder_path)
                )
                
                if result:
                    return {
                        'status': 'success',
                        'md5': md5_hash,
                        'type': 'Action',
                        'action_name': action_name,
                        'labeled': bool(meta_data)
                    }
                else:
                    return {'status': 'failed', 'reason': '动画添加失败', 'md5': md5_hash}
                    
            except Exception as e:
                return {'status': 'error', 'reason': str(e), 'md5': md5_hash}
        
        # 检查是否有 dress.json（服装）
        dress_path = folder_path / "dress.json"
        if not dress_path.exists():
            return {'status': 'skipped', 'reason': '无dress.json或action.json', 'md5': md5_hash}
        
        try:
            # 读取 dress.json
            with open(dress_path, 'r', encoding='utf-8') as f:
                dress_data = json.load(f)
            
            clothing_type = dress_data.get('type', 'Unknown')
            
            # 检查是否有动画（同时有dress和action的情况）
            has_animation = any(folder_path.glob("action*"))
            
            # 添加到数据库（使用 meta.json 中的打标信息）
            result = self.db.add_clothing_item(
                md5_hash=md5_hash,
                folder_name=meta_data.get('name', md5_hash),
                clothing_type=clothing_type,
                custom_name=meta_data.get('name'),
                description=meta_data.get('description'),
                source_path=str(folder_path),
                has_animation=has_animation
            )
            
            if result:
                return {
                    'status': 'success',
                    'md5': md5_hash,
                    'type': clothing_type,
                    'has_animation': has_animation
                }
            else:
                return {'status': 'failed', 'reason': '数据库添加失败', 'md5': md5_hash}
                
        except Exception as e:
            return {'status': 'error', 'reason': str(e), 'md5': md5_hash}
    
    def scan_and_import(self):
        """扫描并导入所有素材"""
        if not self.source_dir.exists():
            return {'error': f'源目录不存在: {self.source_dir}'}
        
        results = {
            'total': 0,
            'success': 0,
            'skipped': 0,
            'failed': 0,
            'details': []
        }
        
        # 遍历所有文件夹
        for folder in self.source_dir.iterdir():
            if not folder.is_dir():
                continue
            if len(folder.name) != 32:  # MD5长度
                continue
            
            results['total'] += 1
            
            # 处理文件夹
            result = self.process_folder(folder)
            results['details'].append(result)
            
            if result['status'] == 'success':
                results['success'] += 1
            elif result['status'] == 'skipped':
                results['skipped'] += 1
            else:
                results['failed'] += 1
            
            # 更新进度
            if self.progress_callback:
                self.progress_callback(results['total'], results)
        
        return results
    
    def separate_animations(self, target_dir):
        """分离动画到指定目录"""
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        animations = self.db.get_all_animations()
        moved_count = 0
        
        for anim in animations:
            md5_hash = anim['md5_hash']
            source_folder = Path(anim['source_path'])
            
            if not source_folder.exists():
                continue
            
            target_folder = target_dir / md5_hash
            
            # 如果目标已存在，先删除
            if target_folder.exists():
                shutil.rmtree(target_folder)
            
            # 移动文件夹
            shutil.move(str(source_folder), str(target_folder))
            moved_count += 1
        
        return moved_count
    
    def generate_thumbnail(self, folder_path, output_path, size=(128, 128)):
        """生成缩略图"""
        folder_path = Path(folder_path)
        output_path = Path(output_path)
        
        # 查找第一个 PNG 图片
        png_files = list(folder_path.glob("*.png"))
        if not png_files:
            return None
        
        try:
            # 打开并缩放图片
            img = Image.open(png_files[0])
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 保存
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path)
            
            return str(output_path)
        except Exception as e:
            print(f"生成缩略图失败: {e}")
            return None
    
    def get_clothing_types(self):
        """获取所有服装类型"""
        return self.db.get_items_by_type()
    
    def get_statistics(self):
        """获取统计信息"""
        return self.db.get_statistics()

if __name__ == "__main__":
    from database import ClothingDatabase
    
    db = ClothingDatabase()
    processor = AssetProcessor("../data/v1.0", db)
    
    # 测试扫描
    results = processor.scan_and_import()
    print(f"扫描结果: {results}")

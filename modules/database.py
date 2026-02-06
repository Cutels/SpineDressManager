#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模块 - 管理服装素材的MD5和标签信息
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

class ClothingDatabase:
    def __init__(self, db_path="database/clothing.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 服装素材表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clothing_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                md5_hash TEXT UNIQUE NOT NULL,
                folder_name TEXT NOT NULL,
                clothing_type TEXT NOT NULL,
                custom_name TEXT,
                description TEXT,
                thumbnail_path TEXT,
                has_animation BOOLEAN DEFAULT 0,
                source_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 动画表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS animations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                md5_hash TEXT UNIQUE NOT NULL,
                folder_name TEXT NOT NULL,
                action_name TEXT,
                description TEXT,
                source_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 导入历史表 - 防止重复导入
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                md5_hash TEXT UNIQUE NOT NULL,
                import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_folder TEXT,
                status TEXT DEFAULT 'success'
            )
        ''')
        
        # 分类统计视图
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS clothing_stats AS
            SELECT 
                clothing_type,
                COUNT(*) as count,
                SUM(CASE WHEN custom_name IS NOT NULL THEN 1 ELSE 0 END) as labeled_count
            FROM clothing_items
            GROUP BY clothing_type
        ''')
        
        conn.commit()
        conn.close()
        print("数据库初始化完成")
    
    def check_md5_exists(self, md5_hash):
        """检查MD5是否已存在于服装表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clothing_items WHERE md5_hash = ?", (md5_hash,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def check_animation_exists(self, md5_hash):
        """检查MD5是否已存在于动画表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM animations WHERE md5_hash = ?", (md5_hash,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def add_clothing_item(self, md5_hash, folder_name, clothing_type, 
                         custom_name=None, description=None, 
                         thumbnail_path=None, has_animation=False, source_path=None):
        """添加服装素材"""
        if self.check_md5_exists(md5_hash):
            print(f"MD5 {md5_hash} 已存在，跳过")
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO clothing_items 
                (md5_hash, folder_name, clothing_type, custom_name, description, 
                 thumbnail_path, has_animation, source_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (md5_hash, folder_name, clothing_type, custom_name, 
                  description, thumbnail_path, has_animation, source_path))
            
            # 记录导入历史
            cursor.execute('''
                INSERT OR REPLACE INTO import_history (md5_hash, source_folder)
                VALUES (?, ?)
            ''', (md5_hash, source_path))
            
            conn.commit()
            print(f"添加服装: {md5_hash} -> {clothing_type}")
            return True
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return False
        finally:
            conn.close()
    
    def update_clothing_label(self, md5_hash, custom_name, description=None, thumbnail_path=None):
        """更新服装标签"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE clothing_items 
            SET custom_name = ?, description = ?, thumbnail_path = ?, updated_at = ?
            WHERE md5_hash = ?
        ''', (custom_name, description, thumbnail_path, datetime.now(), md5_hash))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def get_all_items(self, clothing_type=None):
        """获取所有服装素材"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if clothing_type:
            cursor.execute('''
                SELECT * FROM clothing_items 
                WHERE clothing_type = ?
                ORDER BY created_at DESC
            ''', (clothing_type,))
        else:
            cursor.execute('SELECT * FROM clothing_items ORDER BY created_at DESC')
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_items_by_type(self):
        """按类型分组获取服装"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT clothing_type FROM clothing_items ORDER BY clothing_type')
        types = [row[0] for row in cursor.fetchall()]
        
        result = {}
        for t in types:
            cursor.execute('''
                SELECT * FROM clothing_items 
                WHERE clothing_type = ?
                ORDER BY custom_name IS NULL, custom_name, md5_hash
            ''', (t,))
            result[t] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return result
    
    def get_item_by_md5(self, md5_hash):
        """通过MD5获取服装信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clothing_items WHERE md5_hash = ?', (md5_hash,))
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None
    
    def add_animation(self, md5_hash, folder_name, action_name=None, description=None, source_path=None):
        """添加动画"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO animations 
                (md5_hash, folder_name, action_name, description, source_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (md5_hash, folder_name, action_name, description, source_path))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return False
        finally:
            conn.close()
    
    def get_all_animations(self):
        """获取所有动画"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM animations ORDER BY created_at DESC')
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_statistics(self):
        """获取统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM clothing_stats')
        stats = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('SELECT COUNT(*) FROM clothing_items')
        total_items = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM animations')
        total_animations = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_items': total_items,
            'total_animations': total_animations,
            'type_stats': stats
        }
    
    def delete_item(self, md5_hash):
        """删除服装素材"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM clothing_items WHERE md5_hash = ?', (md5_hash,))
        cursor.execute('DELETE FROM import_history WHERE md5_hash = ?', (md5_hash,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

# 测试代码
if __name__ == "__main__":
    db = ClothingDatabase()
    
    # 测试添加
    db.add_clothing_item(
        md5_hash="test123456",
        folder_name="test123456",
        clothing_type="TopSuit",
        custom_name="测试上衣",
        description="这是一个测试"
    )
    
    # 测试查询
    stats = db.get_statistics()
    print(f"统计: {stats}")

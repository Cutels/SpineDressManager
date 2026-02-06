#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空数据库脚本
"""

import sqlite3
from pathlib import Path

def reset_database():
    db_path = Path("database/clothing.db")
    
    if not db_path.exists():
        print("数据库不存在")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 清空所有表
    tables = ['clothing_items', 'animations', 'import_history']
    
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"已清空表: {table}")
        except Exception as e:
            print(f"清空表 {table} 失败: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n数据库已重置完成！")
    print("请重新运行 main.py 并导入素材")

if __name__ == "__main__":
    reset_database()

#!/usr/bin/env python3
"""
数据库模块 - 素材元数据管理与空间索引
"""

import sqlite3
import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class MaterialDatabase:
    """素材数据库管理类"""
    
    def __init__(self, db_path: str = "materials.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.enable_load_extension(True)
        
        # 尝试加载空间索引扩展（如果可用）
        try:
            self.conn.enable_load_extension(True)
        except:
            pass
        
        self.cursor = self.conn.cursor()
        return self
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def initialize(self):
        """初始化数据库表结构"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                filepath TEXT NOT NULL,
                label TEXT,
                lon_min REAL NOT NULL,
                lat_min REAL NOT NULL,
                lon_max REAL NOT NULL,
                lat_max REAL NOT NULL,
                width INTEGER,
                height INTEGER,
                file_size INTEGER,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建空间索引
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_lon_min ON materials(lon_min)
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_lat_min ON materials(lat_min)
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_lon_max ON materials(lon_max)
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_lat_max ON materials(lat_max)
        ''')
        
        self.conn.commit()
        return self
    
    def parse_filename(self, filename: str) -> Optional[Dict]:
        """
        解析文件名提取经纬度信息
        格式：L{label}_{lon_min}x{lat_max}_{lon_max}x{lat_min}.png
        例如：L100_113.66768x22.73578_113.66862x22.73456.png
        """
        pattern = r'^L(\d+)_(\d+\.?\d*)x(\d+\.?\d*)_(\d+\.?\d*)x(\d+\.?\d*)\.png$'
        match = re.match(pattern, filename)
        
        if not match:
            return None
        
        return {
            'label': match.group(1),
            'lon_min': float(match.group(2)),
            'lat_max': float(match.group(3)),
            'lon_max': float(match.group(4)),
            'lat_min': float(match.group(5))
        }
    
    def sync_materials(self, material_dir: str) -> int:
        """
        同步素材目录到数据库
        返回新增的文件数量
        """
        material_path = Path(material_dir)
        if not material_path.exists():
            raise FileNotFoundError(f"素材目录不存在：{material_dir}")
        
        count = 0
        for png_file in material_path.glob("*.png"):
            filename = png_file.name
            filepath = str(png_file.absolute())
            
            # 解析文件名
            parsed = self.parse_filename(filename)
            if not parsed:
                print(f"跳过无法解析的文件：{filename}")
                continue
            
            # 检查是否已存在
            self.cursor.execute(
                "SELECT id FROM materials WHERE filename = ?",
                (filename,)
            )
            if self.cursor.fetchone():
                continue
            
            # 获取文件信息
            stat = png_file.stat()
            
            # 插入数据库
            self.cursor.execute('''
                INSERT INTO materials 
                (filename, filepath, label, lon_min, lat_min, lon_max, lat_max, 
                 width, height, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename,
                filepath,
                parsed['label'],
                parsed['lon_min'],
                parsed['lat_min'],
                parsed['lon_max'],
                parsed['lat_max'],
                0,  # width - 待更新
                0,  # height - 待更新
                stat.st_size
            ))
            count += 1
        
        self.conn.commit()
        return count
    
    def get_all_materials(self) -> List[Dict]:
        """获取所有素材记录"""
        self.cursor.execute(
            "SELECT * FROM materials ORDER BY label"
        )
        columns = [desc[0] for desc in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
    
    def get_materials_in_bounds(self, lon_min: float, lat_min: float, 
                                 lon_max: float, lat_max: float) -> List[Dict]:
        """获取指定范围内的素材"""
        self.cursor.execute('''
            SELECT * FROM materials 
            WHERE lon_min <= ? AND lon_max >= ?
              AND lat_min <= ? AND lat_max >= ?
            ORDER BY lon_min, lat_min
        ''', (lon_max, lon_min, lat_max, lat_min))
        
        columns = [desc[0] for desc in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
    
    def get_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """获取所有素材的总边界"""
        self.cursor.execute('''
            SELECT MIN(lon_min), MIN(lat_min), MAX(lon_max), MAX(lat_max)
            FROM materials
        ''')
        row = self.cursor.fetchone()
        if row[0] is None:
            return None
        return (row[0], row[1], row[2], row[3])
    
    def count(self) -> int:
        """获取素材总数"""
        self.cursor.execute("SELECT COUNT(*) FROM materials")
        return self.cursor.fetchone()[0]


def init_database(db_path: str = "materials.db", 
                  material_dir: str = "/home/map") -> MaterialDatabase:
    """
    初始化数据库并同步素材
    """
    db = MaterialDatabase(db_path)
    db.connect()
    db.initialize()
    
    count = db.sync_materials(material_dir)
    total = db.count()
    
    print(f"数据库初始化完成")
    print(f"  - 新增素材：{count} 个")
    print(f"  - 素材总数：{total} 个")
    
    bounds = db.get_bounds()
    if bounds:
        print(f"  - 覆盖范围：{bounds[0]:.6f}~{bounds[2]:.6f}°E, "
              f"{bounds[1]:.6f}~{bounds[3]:.6f}°N")
    
    return db


if __name__ == "__main__":
    # 测试
    db = init_database()
    materials = db.get_all_materials()
    print(f"\n前 5 个素材:")
    for m in materials[:5]:
        print(f"  L{m['label']}: {m['filename']}")
    db.close()

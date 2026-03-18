#!/usr/bin/env python3
"""
图像拼接模块 - 将散乱 PNG 无缝拼接为大幅影像
"""

import numpy as np
from PIL import Image
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import math

from .database import MaterialDatabase


class ImageStitcher:
    """图像拼接类"""
    
    def __init__(self, db: MaterialDatabase):
        self.db = db
    
    def lonlat_to_pixel(self, lon: float, lat: float, 
                        bounds: Tuple[float, float, float, float],
                        resolution: float) -> Tuple[int, int]:
        """
        将经纬度转换为像素坐标
        resolution: 每度对应的像素数
        """
        lon_min, lat_min, lon_max, lat_max = bounds
        x = int((lon - lon_min) * resolution)
        y = int((lat_max - lat) * resolution)  # Y 轴翻转
        return (x, y)
    
    def calculate_canvas_size(self, bounds: Tuple[float, float, float, float],
                              target_resolution: float = 1000) -> Tuple[int, int, float]:
        """
        计算画布大小
        target_resolution: 目标每度像素数
        """
        lon_min, lat_min, lon_max, lat_max = bounds
        
        # 计算经纬度跨度
        lon_span = lon_max - lon_min
        lat_span = lat_max - lat_min
        
        # 使用较高分辨率确保质量
        resolution = target_resolution
        
        width = int(lon_span * resolution)
        height = int(lat_span * resolution)
        
        # 确保最小尺寸
        width = max(width, 1000)
        height = max(height, 1000)
        
        return (width, height, resolution)
    
    def stitch(self, output_path: str = "output/stitched.png") -> str:
        """
        执行图像拼接
        """
        print("开始图像拼接...")
        
        # 获取所有素材和边界
        materials = self.db.get_all_materials()
        bounds = self.db.get_bounds()
        
        if not bounds:
            raise ValueError("没有可用的素材")
        
        print(f"  素材数量：{len(materials)}")
        print(f"  覆盖范围：{bounds[0]:.6f}~{bounds[2]:.6f}°E, "
              f"{bounds[1]:.6f}~{bounds[3]:.6f}°N")
        
        # 计算画布大小
        width, height, resolution = self.calculate_canvas_size(bounds)
        print(f"  画布尺寸：{width} x {height} 像素")
        print(f"  分辨率：{resolution:.1f} 像素/度")
        
        # 创建画布（白色背景）
        canvas = Image.new('RGBA', (width, height), (255, 255, 255, 255))
        
        # 逐个粘贴素材
        for i, material in enumerate(materials):
            if i % 20 == 0:
                print(f"  处理进度：{i}/{len(materials)}")
            
            try:
                img = Image.open(material['filepath']).convert('RGBA')
                
                # 计算素材在画布上的位置
                x1, y1 = self.lonlat_to_pixel(
                    material['lon_min'], material['lat_max'],
                    bounds, resolution
                )
                x2, y2 = self.lonlat_to_pixel(
                    material['lon_max'], material['lat_min'],
                    bounds, resolution
                )
                
                # 调整素材大小以匹配目标位置
                target_width = x2 - x1
                target_height = y2 - y1
                
                if target_width > 0 and target_height > 0:
                    # 兼容旧版本 PIL
                    try:
                        resample = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample = Image.ANTIALIAS
                    img_resized = img.resize((target_width, target_height), resample)
                    canvas.paste(img_resized, (x1, y1), img_resized)
                    
            except Exception as e:
                print(f"  警告：处理 {material['filename']} 时出错：{e}")
        
        # 保存结果
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_file, 'PNG')
        
        print(f"拼接完成：{output_path}")
        print(f"  输出尺寸：{width} x {height}")
        
        return output_path


def stitch_images(db: MaterialDatabase, output_path: str = "output/stitched.png") -> str:
    """
    执行图像拼接
    """
    stitcher = ImageStitcher(db)
    return stitcher.stitch(output_path)


if __name__ == "__main__":
    from .database import init_database
    
    db = init_database()
    stitch_images(db)
    db.close()

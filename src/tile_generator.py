#!/usr/bin/env python3
"""
瓦片生成模块 - 生成 XYZ 瓦片 (z=18, 19, 20)
基于 Web 墨卡托投影 (EPSG:3857)
"""

import math
import os
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional

# 地球半径（米）
EARTH_RADIUS = 6378137.0

# 瓦片大小（像素）
TILE_SIZE = 256


def lonlat_to_mercator(lon: float, lat: float) -> Tuple[float, float]:
    """
    将经纬度转换为 Web 墨卡托坐标（米）
    """
    x = lon * math.pi / 180.0 * EARTH_RADIUS
    
    # 限制纬度范围，避免数学错误（墨卡托投影在两极发散）
    lat = max(-85.0511287798, min(85.0511287798, lat))
    
    # 正确的墨卡托 Y 公式：ln(tan(π/4 + φ*π/360))
    y = math.log(math.tan(math.pi/4 + lat * math.pi / 360.0)) * EARTH_RADIUS
    return (x, y)


def mercator_to_lonlat(x: float, y: float) -> Tuple[float, float]:
    """
    将 Web 墨卡托坐标转换为经纬度
    """
    lon = x / EARTH_RADIUS * 180.0 / math.pi
    lat = 180.0 / math.pi * (2 * math.atan(math.exp(y * math.pi / EARTH_RADIUS)) 
                              - math.pi / 2.0)
    # 限制纬度范围
    lat = max(-85.0511287798, min(85.0511287798, lat))
    return (lon, lat)


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> Tuple[int, int]:
    """
    将经纬度转换为 XYZ 瓦片坐标
    返回：(x, y)
    """
    n = 2 ** zoom
    
    # 标准 XYZ 瓦片坐标公式
    tile_x = int((lon + 180.0) / 360.0 * n)
    
    # 纬度到瓦片 Y 坐标
    lat_rad = math.radians(lat)
    tile_y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    
    return (tile_x, tile_y)


class TileGenerator:
    """瓦片生成器 - 简化版本，直接基于图像生成瓦片"""
    
    def __init__(self, stitched_image_path: str, output_dir: str = "tiles"):
        self.image_path = stitched_image_path
        self.output_dir = Path(output_dir)
        self.image = None
        self.bounds = None  # (lon_min, lat_min, lon_max, lat_max)
    
    def load_image(self, bounds: Tuple[float, float, float, float]):
        """加载拼接图像并设置边界"""
        self.image = Image.open(self.image_path)
        self.bounds = bounds
        print(f"加载图像：{self.image.width} x {self.image.height}")
        print(f"图像边界：{bounds}")
    
    def generate_simple_tiles(self, zoom: int) -> int:
        """
        简化瓦片生成：将整个图像作为一个瓦片源
        根据缩放级别计算需要生成的瓦片
        """
        print(f"\n生成 z={zoom} 瓦片...")
        
        # 计算图像四个角对应的瓦片坐标
        lon_min, lat_min, lon_max, lat_max = self.bounds
        
        tile_x_min, tile_y_min = lonlat_to_tile(lon_min, lat_max, zoom)
        tile_x_max, tile_y_max = lonlat_to_tile(lon_max, lat_min, zoom)
        
        # 确保顺序正确
        if tile_x_min > tile_x_max:
            tile_x_min, tile_x_max = tile_x_max, tile_x_min
        if tile_y_min > tile_y_max:
            tile_y_min, tile_y_max = tile_y_max, tile_y_min
        
        print(f"  瓦片范围：x[{tile_x_min}~{tile_x_max}], y[{tile_y_min}~{tile_y_max}]")
        
        count = 0
        
        # 对于小区域，可能只覆盖 1 个或几个瓦片
        for tx in range(tile_x_min, tile_x_max + 1):
            for ty in range(tile_y_min, tile_y_max + 1):
                # 计算该瓦片覆盖的图像区域
                tile_bounds = self._get_tile_image_bounds(tx, ty, zoom)
                
                if tile_bounds is None:
                    continue
                
                x1, y1, x2, y2 = tile_bounds
                
                if x2 <= x1 or y2 <= y1:
                    continue
                
                # 裁剪并保存
                tile = self.image.crop((x1, y1, x2, y2))
                
                # 如果需要，缩放到标准瓦片大小
                if tile.size != (TILE_SIZE, TILE_SIZE):
                    try:
                        resample = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample = Image.ANTIALIAS
                    tile = tile.resize((TILE_SIZE, TILE_SIZE), resample)
                
                # 保存
                tile_dir = self.output_dir / str(zoom) / str(tx)
                tile_dir.mkdir(parents=True, exist_ok=True)
                
                tile_path = tile_dir / f"{ty}.png"
                tile.save(tile_path, 'PNG')
                count += 1
        
        print(f"  生成瓦片：{count} 个")
        return count
    
    def _get_tile_image_bounds(self, tile_x: int, tile_y: int, zoom: int) -> Optional[Tuple[int, int, int, int]]:
        """
        计算瓦片在图像中的像素边界
        """
        lon_min, lat_min, lon_max, lat_max = self.bounds
        img_width, img_height = self.image.size
        
        # 计算瓦片的经纬度边界
        tile_lon_min, tile_lat_max = self._tile_to_lonlat(tile_x, tile_y, zoom)
        tile_lon_max, tile_lat_min = self._tile_to_lonlat(tile_x + 1, tile_y + 1, zoom)
        
        # 检查重叠
        if (tile_lon_max < lon_min or tile_lon_min > lon_max or
            tile_lat_min > lat_max or tile_lat_max < lat_min):
            return None
        
        # 转换为图像像素坐标
        # 经度 -> X 像素
        x1 = int((max(tile_lon_min, lon_min) - lon_min) / (lon_max - lon_min) * img_width)
        x2 = int((min(tile_lon_max, lon_max) - lon_min) / (lon_max - lon_min) * img_width)
        
        # 纬度 -> Y 像素（Y 轴翻转）
        y1 = int((lat_max - max(tile_lat_max, lat_min)) / (lat_max - lat_min) * img_height)
        y2 = int((lat_max - min(tile_lat_min, lat_max)) / (lat_max - lat_min) * img_height)
        
        # 限制在图像范围内
        x1 = max(0, min(x1, img_width))
        y1 = max(0, min(y1, img_height))
        x2 = max(0, min(x2, img_width))
        y2 = max(0, min(y2, img_height))
        
        if x1 >= x2 or y1 >= y2:
            return None
        
        return (x1, y1, x2, y2)
    
    def _tile_to_lonlat(self, tile_x: int, tile_y: int, zoom: int) -> Tuple[float, float]:
        """
        将瓦片坐标转换为左上角经纬度
        """
        n = 2 ** zoom
        
        # 标准 XYZ 瓦片到经纬度公式
        lon_deg = tile_x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n)))
        lat_deg = math.degrees(lat_rad)
        
        return (lon_deg, lat_deg)
    
    def generate_all(self, zoom_levels: list = [18, 19, 20]) -> dict:
        """生成所有缩放级别的瓦片"""
        results = {}
        
        for zoom in zoom_levels:
            count = self.generate_simple_tiles(zoom)
            results[zoom] = count
        
        return results


def generate_tiles(stitched_image_path: str, 
                   bounds: Tuple[float, float, float, float],
                   output_dir: str = "tiles",
                   zoom_levels: list = [18, 19, 20]) -> dict:
    """
    生成 XYZ 瓦片
    """
    generator = TileGenerator(stitched_image_path, output_dir)
    generator.load_image(bounds)
    
    print(f"\n开始生成瓦片 (z={zoom_levels})...")
    results = generator.generate_all(zoom_levels)
    
    print("\n瓦片生成完成:")
    for zoom, count in results.items():
        print(f"  z={zoom}: {count} 个瓦片")
    
    return results


if __name__ == "__main__":
    from .database import init_database
    from .stitcher import stitch_images
    
    # 初始化
    db = init_database()
    bounds = db.get_bounds()
    
    # 拼接
    stitched_path = stitch_images(db)
    
    # 生成瓦片
    generate_tiles(stitched_path, bounds)
    
    db.close()

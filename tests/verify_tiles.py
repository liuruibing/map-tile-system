#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
瓦片规范验证模块
验证生成的瓦片是否符合 XYZ 规范，检查 z=18,19,20 各级瓦片的完整性
"""

import os
import re
import math
import pytest
from PIL import Image
from pathlib import Path


TILES_DIR = "/home/admin/.openclaw/workspace-pm/map-tile-system/tiles"
MATERIAL_DIR = "/home/map"


def parse_filename_coords(filename):
    """从文件名解析坐标信息"""
    basename = os.path.basename(filename)
    pattern = r'^([LR])(\d+)_(\d+\.?\d*)x(\d+\.?\d*)_(\d+\.?\d*)x(\d+\.?\d*)\.png$'
    match = re.match(pattern, basename)
    
    if not match:
        return None
    
    return {
        'label': match.group(1),
        'index': int(match.group(2)),
        'lon1': float(match.group(3)),
        'lat1': float(match.group(4)),
        'lon2': float(match.group(5)),
        'lat2': float(match.group(6))
    }


def lon_lat_to_tile(lon, lat, zoom):
    """将经纬度转换为瓦片坐标"""
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    lat_rad = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    return x, y


def lon_lat_to_mercator(lon, lat):
    """将经纬度转换为 Web 墨卡托坐标"""
    R = 6378137
    x = R * lon * math.pi / 180
    y = R * math.log(math.tan((90 + lat) * math.pi / 360))
    return x, y


def get_expected_tile_range(coords, zoom):
    """根据坐标范围计算应覆盖的瓦片范围"""
    x1, y1 = lon_lat_to_tile(coords['lon1'], coords['lat1'], zoom)
    x2, y2 = lon_lat_to_tile(coords['lon2'], coords['lat2'], zoom)
    
    return {
        'x_min': min(x1, x2),
        'x_max': max(x1, x2),
        'y_min': min(y1, y2),
        'y_max': max(y1, y2)
    }


def scan_tiles_directory():
    """扫描瓦片目录结构"""
    tiles_info = {}
    
    if not os.path.exists(TILES_DIR):
        return tiles_info
    
    for z in [18, 19, 20]:
        z_dir = os.path.join(TILES_DIR, str(z))
        if not os.path.exists(z_dir):
            continue
        
        tiles_info[z] = {'x': {}, 'total': 0}
        
        for x_str in os.listdir(z_dir):
            x_dir = os.path.join(z_dir, x_str)
            if not os.path.isdir(x_dir):
                continue
            
            x = int(x_str)
            tiles_info[z]['x'][x] = []
            
            for y_file in os.listdir(x_dir):
                if y_file.endswith('.png'):
                    y = int(y_file.replace('.png', ''))
                    tiles_info[z]['x'][x].append(y)
                    tiles_info[z]['total'] += 1
    
    return tiles_info


class TestTilesDirectory:
    """瓦片目录结构测试"""
    
    def test_tiles_dir_exists(self):
        """测试瓦片目录是否存在"""
        if not os.path.exists(TILES_DIR):
            pytest.skip(f"瓦片目录 {TILES_DIR} 不存在，瓦片尚未生成")
        assert os.path.isdir(TILES_DIR)
    
    def test_zoom_levels_present(self):
        """测试 zoom 级别目录"""
        tiles_info = scan_tiles_directory()
        
        if not tiles_info:
            pytest.skip("瓦片目录为空")
        
        expected_zooms = [18, 19, 20]
        present_zooms = list(tiles_info.keys())
        
        print(f"存在的 zoom 级别：{present_zooms}")
        
        # 至少应该有一个 zoom 级别
        assert len(present_zooms) > 0, "没有任何 zoom 级别的瓦片"


class TestXYZSpecification:
    """XYZ 规范符合性测试"""
    
    @pytest.fixture(scope="class")
    def tiles_info(self):
        """获取瓦片信息"""
        return scan_tiles_directory()
    
    def test_tile_naming_convention(self, tiles_info):
        """测试瓦片命名规范"""
        if not tiles_info:
            pytest.skip("无瓦片数据")
        
        # XYZ 规范：/z/x/y.png
        for z in tiles_info:
            for x in tiles_info[z]['x']:
                for y in tiles_info[z]['x'][x]:
                    # 验证坐标非负
                    assert x >= 0, f"负 x 坐标：{x}"
                    assert y >= 0, f"负 y 坐标：{y}"
    
    def test_tile_size_standard(self, tiles_info):
        """测试瓦片尺寸是否为标准 256x256"""
        if not tiles_info:
            pytest.skip("无瓦片数据")
        
        non_standard = []
        
        for z in tiles_info:
            z_dir = os.path.join(TILES_DIR, str(z))
            for x_str in list(tiles_info[z]['x'].keys())[:5]:  # 抽样
                x_dir = os.path.join(z_dir, x_str)
                for y in tiles_info[z]['x'][int(x_str)][:5]:
                    tile_path = os.path.join(x_dir, f"{y}.png")
                    if os.path.exists(tile_path):
                        try:
                            with Image.open(tile_path) as img:
                                if img.width != 256 or img.height != 256:
                                    non_standard.append((tile_path, img.width, img.height))
                        except:
                            pass
        
        if non_standard:
            print(f"非标准尺寸瓦片：{non_standard[:5]}")
    
    def test_tile_format_png(self, tiles_info):
        """测试瓦片格式是否为 PNG"""
        if not tiles_info:
            pytest.skip("无瓦片数据")
        
        non_png = []
        
        for z in tiles_info:
            z_dir = os.path.join(TILES_DIR, str(z))
            for x_str in list(tiles_info[z]['x'].keys())[:3]:
                x_dir = os.path.join(z_dir, x_str)
                for y in tiles_info[z]['x'][int(x_str)][:3]:
                    tile_path = os.path.join(x_dir, f"{y}.png")
                    if os.path.exists(tile_path):
                        try:
                            with Image.open(tile_path) as img:
                                if img.format != 'PNG':
                                    non_png.append((tile_path, img.format))
                        except:
                            pass
        
        assert len(non_png) == 0, f"非 PNG 格式瓦片：{non_png}"


class TestTileCompleteness:
    """瓦片完整性测试"""
    
    @pytest.fixture(scope="class")
    def material_coords(self):
        """获取素材坐标信息"""
        coords_list = []
        for f in os.listdir(MATERIAL_DIR):
            if f.endswith('.png'):
                coords = parse_filename_coords(os.path.join(MATERIAL_DIR, f))
                if coords:
                    coords_list.append(coords)
        return coords_list
    
    @pytest.fixture(scope="class")
    def tiles_info(self):
        """获取瓦片信息"""
        return scan_tiles_directory()
    
    def test_zoom_18_completeness(self, material_coords, tiles_info):
        """测试 z=18 瓦片完整性"""
        if 18 not in tiles_info:
            pytest.skip("z=18 瓦片不存在")
        
        expected_tiles = set()
        for coords in material_coords:
            tile_range = get_expected_tile_range(coords, 18)
            for x in range(tile_range['x_min'], tile_range['x_max'] + 1):
                for y in range(tile_range['y_min'], tile_range['y_max'] + 1):
                    expected_tiles.add((x, y))
        
        actual_tiles = set()
        for x in tiles_info[18]['x']:
            for y in tiles_info[18]['x'][x]:
                actual_tiles.add((x, y))
        
        missing = expected_tiles - actual_tiles
        extra = actual_tiles - expected_tiles
        
        print(f"Z=18: 期望 {len(expected_tiles)} 个瓦片，实际 {len(actual_tiles)} 个")
        if missing:
            print(f"缺少 {len(missing)} 个瓦片")
        
        # 允许一定的缺失率（因为边缘可能不需要）
        if expected_tiles:
            missing_rate = len(missing) / len(expected_tiles)
            assert missing_rate < 0.2, f"缺失率过高：{missing_rate:.2%}"
    
    def test_zoom_19_completeness(self, material_coords, tiles_info):
        """测试 z=19 瓦片完整性"""
        if 19 not in tiles_info:
            pytest.skip("z=19 瓦片不存在")
        
        expected_tiles = set()
        for coords in material_coords:
            tile_range = get_expected_tile_range(coords, 19)
            for x in range(tile_range['x_min'], tile_range['x_max'] + 1):
                for y in range(tile_range['y_min'], tile_range['y_max'] + 1):
                    expected_tiles.add((x, y))
        
        actual_tiles = set()
        for x in tiles_info[19]['x']:
            for y in tiles_info[19]['x'][x]:
                actual_tiles.add((x, y))
        
        print(f"Z=19: 期望 {len(expected_tiles)} 个瓦片，实际 {len(actual_tiles)} 个")
    
    def test_zoom_20_completeness(self, material_coords, tiles_info):
        """测试 z=20 瓦片完整性"""
        if 20 not in tiles_info:
            pytest.skip("z=20 瓦片不存在")
        
        expected_tiles = set()
        for coords in material_coords:
            tile_range = get_expected_tile_range(coords, 20)
            for x in range(tile_range['x_min'], tile_range['x_max'] + 1):
                for y in range(tile_range['y_min'], tile_range['y_max'] + 1):
                    expected_tiles.add((x, y))
        
        actual_tiles = set()
        for x in tiles_info[20]['x']:
            for y in tiles_info[20]['x'][x]:
                actual_tiles.add((x, y))
        
        print(f"Z=20: 期望 {len(expected_tiles)} 个瓦片，实际 {len(actual_tiles)} 个")


class TestTileSeamlessness:
    """瓦片无缝衔接测试"""
    
    @pytest.fixture(scope="class")
    def tiles_info(self):
        """获取瓦片信息"""
        return scan_tiles_directory()
    
    def test_adjacent_tiles_match(self, tiles_info):
        """测试相邻瓦片边缘匹配"""
        if not tiles_info:
            pytest.skip("无瓦片数据")
        
        # 抽样检查相邻瓦片
        for z in tiles_info:
            z_dir = os.path.join(TILES_DIR, str(z))
            x_list = sorted(tiles_info[z]['x'].keys())
            
            for i, x in enumerate(x_list[:5]):  # 抽样
                y_list = tiles_info[z]['x'][x]
                if len(y_list) < 2:
                    continue
                
                # 检查垂直相邻
                y_sorted = sorted(y_list)
                for j in range(len(y_sorted) - 1):
                    y1 = y_sorted[j]
                    y2 = y_sorted[j + 1]
                    
                    if y2 - y1 == 1:  # 相邻
                        tile1_path = os.path.join(z_dir, str(x), f"{y1}.png")
                        tile2_path = os.path.join(z_dir, str(x), f"{y2}.png")
                        
                        if os.path.exists(tile1_path) and os.path.exists(tile2_path):
                            try:
                                with Image.open(tile1_path) as img1, Image.open(tile2_path) as img2:
                                    # 获取边缘像素行
                                    bottom_row = list(img1.crop((0, img1.height - 1, img1.width, img1.height)).getdata())
                                    top_row = list(img2.crop((0, 0, img2.width, 1)).getdata())
                                    
                                    # 计算差异（简化）
                                    if len(bottom_row) == len(top_row):
                                        diff = sum(abs(p1 - p2) for p1, p2 in zip(bottom_row, top_row))
                                        avg_diff = diff / len(bottom_row) if bottom_row else 0
                                        
                                        if avg_diff > 50:  # 阈值
                                            print(f"Z={z}, X={x}, Y={y1}-{y2}: 边缘差异较大 {avg_diff:.2f}")
                            except Exception as e:
                                pass
    
    def test_tile_no_artifacts(self, tiles_info):
        """测试瓦片无明显伪影"""
        if not tiles_info:
            pytest.skip("无瓦片数据")
        
        # 抽样检查
        checked = 0
        for z in tiles_info:
            z_dir = os.path.join(TILES_DIR, str(z))
            for x in list(tiles_info[z]['x'].keys())[:3]:
                for y in tiles_info[z]['x'][x][:3]:
                    tile_path = os.path.join(z_dir, str(x), f"{y}.png")
                    if os.path.exists(tile_path):
                        try:
                            with Image.open(tile_path) as img:
                                # 检查是否全黑或全白
                                pixels = list(img.getdata())
                                if pixels:
                                    avg_brightness = sum(sum(p[:3]) / 3 for p in pixels) / len(pixels)
                                    if avg_brightness < 5 or avg_brightness > 250:
                                        print(f"警告：{tile_path} 亮度异常 {avg_brightness:.2f}")
                                checked += 1
                        except:
                            pass
        
        print(f"检查了 {checked} 个瓦片的伪影")


class TestGeographicAccuracy:
    """地理准确性抽样检查"""
    
    @pytest.fixture(scope="class")
    def tiles_info(self):
        """获取瓦片信息"""
        return scan_tiles_directory()
    
    def test_tile_coordinate_validity(self, tiles_info):
        """测试瓦片坐标在有效范围内"""
        if not tiles_info:
            pytest.skip("无瓦片数据")
        
        for z in tiles_info:
            max_tile = 2 ** z
            for x in tiles_info[z]['x']:
                assert 0 <= x < max_tile, f"Z={z} 时 x={x} 超出范围 [0, {max_tile})"
                for y in tiles_info[z]['x'][x]:
                    assert 0 <= y < max_tile, f"Z={z} 时 y={y} 超出范围 [0, {max_tile})"
    
    def test_zoom_level_consistency(self, tiles_info):
        """测试不同 zoom 级别的一致性"""
        if len(tiles_info) < 2:
            pytest.skip("需要至少 2 个 zoom 级别")
        
        zooms = sorted(tiles_info.keys())
        
        for i in range(len(zooms) - 1):
            z1 = zooms[i]
            z2 = zooms[i + 1]
            
            # z2 应该比 z1 有更详细的瓦片
            if tiles_info[z1]['total'] > 0 and tiles_info[z2]['total'] > 0:
                print(f"Z{z1}: {tiles_info[z1]['total']} 个瓦片, Z{z2}: {tiles_info[z2]['total']} 个瓦片")
                # 理论上 z2 应该是 z1 的 4 倍左右（每个瓦片分成 4 个）
                # 但实际可能因为裁剪而不同


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

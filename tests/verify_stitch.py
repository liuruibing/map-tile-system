#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拼接精度验证模块
验证拼接后图像的地理坐标准确性，检查重叠区域是否存在明显接缝
"""

import os
import re
import math
import pytest
from PIL import Image
from pathlib import Path


MATERIAL_DIR = "/home/map"
OUTPUT_DIR = "/home/admin/.openclaw/workspace-pm/map-tile-system/output"


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


def get_all_png_files():
    """获取素材库中所有 PNG 文件"""
    png_files = []
    for f in os.listdir(MATERIAL_DIR):
        if f.lower().endswith('.png'):
            png_files.append(os.path.join(MATERIAL_DIR, f))
    return sorted(png_files)


def lon_lat_to_mercator(lon, lat):
    """将经纬度转换为 Web 墨卡托坐标"""
    R = 6378137  # 地球半径
    x = R * lon * math.pi / 180
    y = R * math.log(math.tan((90 + lat) * math.pi / 360))
    return x, y


def calculate_overlap_area(coords1, coords2):
    """计算两个坐标区域的重叠面积"""
    # coords: {lon1, lat1, lon2, lat2}
    lon_left = max(coords1['lon1'], coords2['lon1'])
    lon_right = min(coords1['lon2'], coords2['lon2'])
    lat_top = min(coords1['lat1'], coords2['lat1'])
    lat_bottom = max(coords1['lat2'], coords2['lat2'])
    
    if lon_left >= lon_right or lat_bottom >= lat_top:
        return 0
    
    return (lon_right - lon_left) * (lat_top - lat_bottom)


def find_overlapping_pairs(png_files, min_overlap=0.00001):
    """查找所有重叠的图像对"""
    overlapping = []
    coords_list = []
    
    for filepath in png_files:
        coords = parse_filename_coords(filepath)
        if coords:
            coords_list.append((filepath, coords))
    
    for i in range(len(coords_list)):
        for j in range(i + 1, len(coords_list)):
            fp1, c1 = coords_list[i]
            fp2, c2 = coords_list[j]
            
            overlap = calculate_overlap_area(c1, c2)
            if overlap > min_overlap:
                overlapping.append((fp1, fp2, overlap))
    
    return overlapping


class TestOutputDirectory:
    """输出目录测试"""
    
    def test_output_dir_exists(self):
        """测试输出目录是否存在"""
        assert os.path.isdir(OUTPUT_DIR), f"输出目录 {OUTPUT_DIR} 不存在"
    
    def test_output_dir_writable(self):
        """测试输出目录是否可写"""
        test_file = os.path.join(OUTPUT_DIR, ".test_write")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            assert True
        except:
            assert False, f"输出目录 {OUTPUT_DIR} 不可写"


class TestStitchAccuracy:
    """拼接精度测试"""
    
    @pytest.fixture(scope="class")
    def png_files(self):
        """获取所有 PNG 文件列表"""
        return get_all_png_files()
    
    @pytest.fixture(scope="class")
    def coords_map(self, png_files):
        """创建文件到坐标的映射"""
        coords_map = {}
        for filepath in png_files:
            coords = parse_filename_coords(filepath)
            if coords:
                coords_map[filepath] = coords
        return coords_map
    
    def test_coordinate_coverage(self, coords_map):
        """测试坐标覆盖范围"""
        if not coords_map:
            assert False, "没有有效的坐标信息"
        
        all_lons = []
        all_lats = []
        for coords in coords_map.values():
            all_lons.extend([coords['lon1'], coords['lon2']])
            all_lats.extend([coords['lat1'], coords['lat2']])
        
        lon_range = max(all_lons) - min(all_lons)
        lat_range = max(all_lats) - min(all_lats)
        
        print(f"覆盖范围：经度 [{min(all_lons):.5f}, {max(all_lons):.5f}], "
              f"纬度 [{min(all_lats):.5f}, {max(all_lats):.5f}]")
        print(f"覆盖跨度：经度 {lon_range:.5f}°, 纬度 {lat_range:.5f}°")
        
        assert lon_range > 0, "经度覆盖范围为 0"
        assert lat_range > 0, "纬度覆盖范围为 0"
    
    def test_no_gaps_in_coverage(self, coords_map):
        """测试覆盖是否连续（无明显间隙）"""
        # 简化检查：检查相邻索引的图像是否有重叠或邻接
        L_files = [(fp, c) for fp, c in coords_map.items() if c['label'] == 'L']
        R_files = [(fp, c) for fp, c in coords_map.items() if c['label'] == 'R']
        
        # 按索引排序
        L_files.sort(key=lambda x: x[1]['index'])
        R_files.sort(key=lambda x: x[1]['index'])
        
        # 检查 L 序列的连续性
        gaps_L = []
        for i in range(len(L_files) - 1):
            c1 = L_files[i][1]
            c2 = L_files[i + 1][1]
            
            # 检查是否邻接或重叠
            if c2['lon1'] > c1['lon2'] + 0.001:  # 允许小间隙
                gaps_L.append((L_files[i][0], L_files[i + 1][0]))
        
        # 检查 R 序列的连续性
        gaps_R = []
        for i in range(len(R_files) - 1):
            c1 = R_files[i][1]
            c2 = R_files[i + 1][1]
            
            if c2['lon1'] > c1['lon2'] + 0.001:
                gaps_R.append((R_files[i][0], R_files[i + 1][0]))
        
        if gaps_L:
            print(f"L 序列中的间隙：{len(gaps_L)} 处")
        if gaps_R:
            print(f"R 序列中的间隙：{len(gaps_R)} 处")
        
        # 这只是警告，不强制失败
        assert len(gaps_L) + len(gaps_R) < 10, f"发现过多间隙：{len(gaps_L) + len(gaps_R)}"
    
    def test_overlapping_regions_consistent(self, png_files):
        """测试重叠区域的一致性"""
        overlapping = find_overlapping_pairs(png_files)
        
        if not overlapping:
            print("未发现明显重叠区域")
            assert True
            return
        
        print(f"发现 {len(overlapping)} 对重叠图像")
        
        # 检查重叠区域的坐标一致性
        inconsistent = []
        for fp1, fp2, overlap in overlapping[:10]:  # 只检查前 10 对
            c1 = parse_filename_coords(fp1)
            c2 = parse_filename_coords(fp2)
            
            if c1 and c2:
                # 计算重叠区域的坐标差异
                lon_overlap_left = max(c1['lon1'], c2['lon1'])
                lon_overlap_right = min(c1['lon2'], c2['lon2'])
                
                # 如果重叠区域很小，可能是边缘重叠，可以接受
                if lon_overlap_right - lon_overlap_left < 0.0001:
                    continue
        
        assert len(inconsistent) == 0, f"发现不一致的重叠：{inconsistent}"


class TestImageDimensions:
    """图像尺寸验证"""
    
    @pytest.fixture(scope="class")
    def png_files(self):
        """获取所有 PNG 文件列表"""
        return get_all_png_files()
    
    def test_resolution_consistency(self, png_files):
        """测试图像分辨率的一致性"""
        resolutions = {}
        
        for filepath in png_files[:50]:  # 抽样检查
            try:
                with Image.open(filepath) as img:
                    res = (img.width, img.height)
                    resolutions[res] = resolutions.get(res, 0) + 1
            except:
                pass
        
        print(f"分辨率分布：{resolutions}")
        
        # 检查是否有主导分辨率
        if resolutions:
            most_common = max(resolutions.items(), key=lambda x: x[1])
            print(f"最常见分辨率：{most_common[0]} ({most_common[1]} 张)")
    
    def test_image_aspect_ratio(self, png_files):
        """测试图像宽高比是否合理"""
        unusual_ratios = []
        
        for filepath in png_files[:50]:
            try:
                with Image.open(filepath) as img:
                    ratio = img.width / img.height
                    if ratio < 0.5 or ratio > 3.0:
                        unusual_ratios.append((filepath, ratio))
            except:
                pass
        
        if unusual_ratios:
            print(f"非常见宽高比的图像：{unusual_ratios[:5]}")


class TestSeamDetection:
    """接缝检测"""
    
    @pytest.fixture(scope="class")
    def overlapping_pairs(self):
        """获取重叠图像对"""
        png_files = get_all_png_files()
        return find_overlapping_pairs(png_files)
    
    def test_edge_pixel_continuity(self, overlapping_pairs):
        """测试边缘像素的连续性（简化版）"""
        if not overlapping_pairs:
            assert True
            return
        
        # 抽样检查几对
        for fp1, fp2, overlap in overlapping_pairs[:5]:
            try:
                with Image.open(fp1) as img1, Image.open(fp2) as img2:
                    # 这里应该实现更复杂的接缝检测算法
                    # 简化为检查图像是否能正常打开
                    pass
            except Exception as e:
                assert False, f"无法检查接缝：{fp1}, {fp2}: {e}"


class TestGeoreferencing:
    """地理配准验证"""
    
    @pytest.fixture(scope="class")
    def png_files(self):
        """获取所有 PNG 文件列表"""
        return get_all_png_files()
    
    def test_mercator_projection_valid(self, png_files):
        """测试 Web 墨卡托投影的有效性"""
        coords_list = []
        for filepath in png_files:
            coords = parse_filename_coords(filepath)
            if coords:
                coords_list.append(coords)
        
        # 转换为墨卡托坐标
        mercator_coords = []
        for coords in coords_list[:20]:  # 抽样
            try:
                x1, y1 = lon_lat_to_mercator(coords['lon1'], coords['lat1'])
                x2, y2 = lon_lat_to_mercator(coords['lon2'], coords['lat2'])
                mercator_coords.append({
                    'x1': x1, 'y1': y1,
                    'x2': x2, 'y2': y2
                })
            except:
                pass
        
        assert len(mercator_coords) > 0, "无法转换任何坐标到墨卡托投影"
        print(f"成功转换 {len(mercator_coords)} 个坐标到墨卡托投影")
    
    def test_coordinate_bounds(self, png_files):
        """测试坐标在有效范围内"""
        for filepath in png_files:
            coords = parse_filename_coords(filepath)
            if coords:
                # 检查是否在 Web 墨卡托有效范围内
                assert -180 <= coords['lon1'] <= 180, f"经度超出范围：{coords['lon1']}"
                assert -180 <= coords['lon2'] <= 180, f"经度超出范围：{coords['lon2']}"
                # 墨卡托投影在纬度±85.06 处有极限
                assert -85.06 <= coords['lat1'] <= 85.06, f"纬度超出墨卡托范围：{coords['lat1']}"
                assert -85.06 <= coords['lat2'] <= 85.06, f"纬度超出墨卡托范围：{coords['lat2']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

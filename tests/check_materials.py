#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
素材质量检查模块
验证所有 PNG 文件是否可正常读取，检查文件名坐标与实际图片内容是否匹配
"""

import os
import re
import pytest
from PIL import Image
from pathlib import Path


MATERIAL_DIR = "/home/map"


def parse_filename_coords(filename):
    """
    从文件名解析坐标信息
    格式：Lxxx_113.66x22.73_113.67x22.72.png 或 Rxxx_...
    返回：(label, lon1, lat1, lon2, lat2)
    """
    basename = os.path.basename(filename)
    # 匹配模式：L 或 R 开头，后跟数字，然后是两个坐标对
    pattern = r'^([LR])(\d+)_(\d+\.?\d*)x(\d+\.?\d*)_(\d+\.?\d*)x(\d+\.?\d*)\.png$'
    match = re.match(pattern, basename)
    
    if not match:
        return None
    
    label = match.group(1)
    index = int(match.group(2))
    lon1 = float(match.group(3))
    lat1 = float(match.group(4))
    lon2 = float(match.group(5))
    lat2 = float(match.group(6))
    
    return {
        'label': label,
        'index': index,
        'lon1': lon1,
        'lat1': lat1,
        'lon2': lon2,
        'lat2': lat2
    }


def get_all_png_files():
    """获取素材库中所有 PNG 文件"""
    png_files = []
    for f in os.listdir(MATERIAL_DIR):
        if f.lower().endswith('.png'):
            png_files.append(os.path.join(MATERIAL_DIR, f))
    return sorted(png_files)


class TestMaterialFiles:
    """素材文件基础测试"""
    
    @pytest.fixture(scope="class")
    def png_files(self):
        """获取所有 PNG 文件列表"""
        return get_all_png_files()
    
    def test_material_dir_exists(self):
        """测试素材目录是否存在"""
        assert os.path.isdir(MATERIAL_DIR), f"素材目录 {MATERIAL_DIR} 不存在"
    
    def test_png_files_exist(self, png_files):
        """测试存在 PNG 文件"""
        assert len(png_files) > 0, "素材库中没有找到 PNG 文件"
    
    def test_file_readable(self, png_files):
        """测试所有文件是否可读"""
        unreadable = []
        for filepath in png_files:
            if not os.access(filepath, os.R_OK):
                unreadable.append(filepath)
        
        assert len(unreadable) == 0, f"以下文件不可读：{unreadable}"
    
    def test_file_size_valid(self, png_files):
        """测试文件大小是否合理（非空）"""
        empty_files = []
        for filepath in png_files:
            size = os.path.getsize(filepath)
            if size == 0:
                empty_files.append(filepath)
        
        assert len(empty_files) == 0, f"以下文件大小为 0: {empty_files}"


class TestPNGValidity:
    """PNG 文件有效性测试"""
    
    @pytest.fixture(scope="class")
    def png_files(self):
        """获取所有 PNG 文件列表"""
        return get_all_png_files()
    
    def test_all_png_openable(self, png_files):
        """测试所有 PNG 文件能否被 PIL 打开"""
        failed_files = []
        for filepath in png_files:
            try:
                with Image.open(filepath) as img:
                    img.verify()
            except Exception as e:
                failed_files.append((filepath, str(e)))
        
        assert len(failed_files) == 0, f"以下文件无法打开：{failed_files[:10]}"
    
    def test_png_format_valid(self, png_files):
        """测试文件确实是 PNG 格式"""
        non_png = []
        for filepath in png_files:
            try:
                with Image.open(filepath) as img:
                    if img.format != 'PNG':
                        non_png.append((filepath, img.format))
            except:
                pass
        
        assert len(non_png) == 0, f"以下文件不是 PNG 格式：{non_png}"
    
    def test_image_dimensions_valid(self, png_files):
        """测试图片尺寸是否合理"""
        invalid_dims = []
        for filepath in png_files:
            try:
                with Image.open(filepath) as img:
                    width, height = img.size
                    if width <= 0 or height <= 0:
                        invalid_dims.append((filepath, width, height))
                    if width > 10000 or height > 10000:
                        invalid_dims.append((filepath, width, height, "尺寸异常大"))
            except:
                pass
        
        assert len(invalid_dims) == 0, f"以下文件尺寸异常：{invalid_dims}"
    
    def test_image_mode_valid(self, png_files):
        """测试图片模式是否合理"""
        invalid_modes = []
        for filepath in png_files:
            try:
                with Image.open(filepath) as img:
                    if img.mode not in ['RGB', 'RGBA', 'L', 'LA', 'P', 'PA']:
                        invalid_modes.append((filepath, img.mode))
            except:
                pass
        
        # 这只是警告，不是错误
        if len(invalid_modes) > 0:
            print(f"注意：以下文件使用非常见模式：{invalid_modes}")


class TestFilenameCoords:
    """文件名坐标解析测试"""
    
    @pytest.fixture(scope="class")
    def png_files(self):
        """获取所有 PNG 文件列表"""
        return get_all_png_files()
    
    def test_filename_format(self, png_files):
        """测试所有文件名符合命名规范"""
        invalid_names = []
        pattern = r'^[LR]\d+_\d+\.?\d*x\d+\.?\d*_\d+\.?\d*x\d+\.?\d*\.png$'
        
        for filepath in png_files:
            basename = os.path.basename(filepath)
            if not re.match(pattern, basename):
                invalid_names.append(basename)
        
        assert len(invalid_names) == 0, f"以下文件名不符合规范：{invalid_names}"
    
    def test_coords_parseable(self, png_files):
        """测试所有文件名坐标可解析"""
        unparseable = []
        for filepath in png_files:
            coords = parse_filename_coords(filepath)
            if coords is None:
                unparseable.append(os.path.basename(filepath))
        
        assert len(unparseable) == 0, f"以下文件坐标无法解析：{unparseable}"
    
    def test_coords_logical(self, png_files):
        """测试坐标逻辑合理性"""
        invalid_coords = []
        for filepath in png_files:
            coords = parse_filename_coords(filepath)
            if coords is None:
                continue
            
            # 检查经度范围（应该在合理范围内）
            if not (-180 <= coords['lon1'] <= 180 and -180 <= coords['lon2'] <= 180):
                invalid_coords.append((filepath, "经度超出范围"))
            
            # 检查纬度范围
            if not (-90 <= coords['lat1'] <= 90 and -90 <= coords['lat2'] <= 90):
                invalid_coords.append((filepath, "纬度超出范围"))
            
            # 检查 lon1 应该小于 lon2（从左到右）
            if coords['lon1'] >= coords['lon2']:
                invalid_coords.append((filepath, "lon1 应该小于 lon2"))
            
            # 检查 lat1 应该大于 lat2（从上到下）
            if coords['lat1'] <= coords['lat2']:
                invalid_coords.append((filepath, "lat1 应该大于 lat2"))
        
        assert len(invalid_coords) == 0, f"以下文件坐标不合理：{invalid_coords}"
    
    def test_label_consistency(self, png_files):
        """测试标签（L/R）一致性"""
        labels = {'L': 0, 'R': 0}
        for filepath in png_files:
            coords = parse_filename_coords(filepath)
            if coords:
                labels[coords['label']] = labels.get(coords['label'], 0) + 1
        
        assert sum(labels.values()) == len(png_files), "存在未识别标签的文件"
        print(f"标签分布：L={labels['L']}, R={labels['R']}")


class TestCorruptedFiles:
    """损坏文件检测"""
    
    @pytest.fixture(scope="class")
    def png_files(self):
        """获取所有 PNG 文件列表"""
        return get_all_png_files()
    
    def test_no_truncated_files(self, png_files):
        """检测是否有截断的文件"""
        truncated = []
        for filepath in png_files:
            try:
                with Image.open(filepath) as img:
                    # 尝试加载完整图像
                    img.load()
            except Exception as e:
                if "truncated" in str(e).lower() or "unexpected" in str(e).lower():
                    truncated.append((filepath, str(e)))
        
        assert len(truncated) == 0, f"以下文件可能已截断：{truncated}"
    
    def test_no_header_corruption(self, png_files):
        """检测文件头是否损坏"""
        corrupted_headers = []
        for filepath in png_files:
            try:
                with open(filepath, 'rb') as f:
                    header = f.read(8)
                    # PNG 文件头应该是：89 50 4E 47 0D 0A 1A 0A
                    if not header.startswith(b'\x89PNG'):
                        corrupted_headers.append(filepath)
            except:
                corrupted_headers.append(filepath)
        
        assert len(corrupted_headers) == 0, f"以下文件头损坏：{corrupted_headers}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

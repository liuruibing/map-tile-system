#!/usr/bin/env python3
"""
主程序 - 瓦片拼接与生成系统入口
"""

import argparse
import sys
from pathlib import Path

from .database import init_database, MaterialDatabase
from .stitcher import stitch_images
from .tile_generator import generate_tiles


def main():
    parser = argparse.ArgumentParser(
        description='瓦片拼接与生成系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python -m src.main --init                    # 初始化数据库
  python -m src.main --stitch                  # 执行图像拼接
  python -m src.main --tiles                   # 生成瓦片
  python -m src.main --all                     # 执行全部流程
        '''
    )
    
    parser.add_argument('--init', action='store_true',
                        help='初始化数据库并同步素材')
    parser.add_argument('--stitch', action='store_true',
                        help='执行图像拼接')
    parser.add_argument('--tiles', action='store_true',
                        help='生成 XYZ 瓦片')
    parser.add_argument('--all', action='store_true',
                        help='执行全部流程')
    
    parser.add_argument('--db', default='materials.db',
                        help='数据库路径 (默认：materials.db)')
    parser.add_argument('--material-dir', default='/home/map',
                        help='素材目录 (默认：/home/map)')
    parser.add_argument('--output', default='output',
                        help='输出目录 (默认：output)')
    parser.add_argument('--tiles-dir', default='tiles',
                        help='瓦片输出目录 (默认：tiles)')
    parser.add_argument('--zoom', nargs='+', type=int, default=[18, 19, 20],
                        help='缩放级别 (默认：18 19 20)')
    
    args = parser.parse_args()
    
    # 如果没有指定任何操作，显示帮助
    if not any([args.init, args.stitch, args.tiles, args.all]):
        parser.print_help()
        return
    
    db = None
    stitched_path = None
    bounds = None
    
    try:
        # 初始化数据库
        if args.init or args.all:
            print("=" * 60)
            print("步骤 1: 初始化数据库")
            print("=" * 60)
            db = init_database(args.db, args.material_dir)
            bounds = db.get_bounds()
        
        # 图像拼接
        if args.stitch or args.all:
            print("\n" + "=" * 60)
            print("步骤 2: 图像拼接")
            print("=" * 60)
            
            if db is None:
                db = MaterialDatabase(args.db)
                db.connect()
                if not db.get_bounds():
                    db.initialize()
                    db.sync_materials(args.material_dir)
                bounds = db.get_bounds()
            
            stitched_path = Path(args.output) / "stitched.png"
            stitch_images(db, str(stitched_path))
        
        # 生成瓦片
        if args.tiles or args.all:
            print("\n" + "=" * 60)
            print("步骤 3: 生成瓦片")
            print("=" * 60)
            
            if stitched_path is None:
                stitched_path = Path(args.output) / "stitched.png"
            
            if not stitched_path.exists():
                print(f"错误：拼接图像不存在：{stitched_path}")
                print("请先执行 --stitch 或 --all")
                return
            
            if bounds is None:
                if db is None:
                    db = MaterialDatabase(args.db)
                    db.connect()
                bounds = db.get_bounds()
            
            generate_tiles(
                str(stitched_path),
                bounds,
                args.tiles_dir,
                args.zoom
            )
        
        print("\n" + "=" * 60)
        print("✅ 全部任务完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()

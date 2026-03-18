# GitHub 仓库创建指南

## 自动创建（推荐）

```bash
cd /home/admin/.openclaw/workspace-pm/map-tile-system/

# 方法 1: 使用 gh CLI（需要登录）
gh auth login
gh repo create map-tile-system --public --source=. --remote=origin --push

# 方法 2: 使用 GitHub Token
export GITHUB_TOKEN=your_token_here
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
     -d '{"name":"map-tile-system","public":true,"description":"瓦片拼接与生成系统 - XYZ Tile Generator"}' \
     https://api.github.com/user/repos
git remote add origin https://github.com/YOUR_USERNAME/map-tile-system.git
git push -u origin master
```

## 手动创建

1. 访问 https://github.com/new
2. 仓库名：`map-tile-system`
3. 描述：`瓦片拼接与生成系统 - XYZ Tile Generator for Map Images`
4. 选择 Public
5. 点击 "Create repository"
6. 按页面提示执行：

```bash
git remote add origin https://github.com/YOUR_USERNAME/map-tile-system.git
git branch -M master
git push -u origin master
```

## 项目结构

```
map-tile-system/
├── src/                    # 源代码
│   ├── __init__.py
│   ├── database.py        # 数据库模块
│   ├── stitcher.py        # 图像拼接模块
│   ├── tile_generator.py  # 瓦片生成模块
│   └── main.py            # 主程序入口
├── tests/                  # 测试脚本
├── output/                 # 输出目录
├── tiles/                  # 瓦片输出
├── materials.db            # SQLite 数据库
├── .gitignore
└── README.md
```

## 使用方法

```bash
# 完整流程
python3 -m src.main --all

# 分步执行
python3 -m src.main --init      # 初始化数据库
python3 -m src.main --stitch    # 图像拼接
python3 -m src.main --tiles     # 生成瓦片

# 自定义参数
python3 -m src.main --all \
    --material-dir /path/to/images \
    --zoom 18 19 20
```

## 瓦片结构

生成的瓦片遵循标准 XYZ 结构：

```
tiles/
├── 18/          # Zoom level 18
│   ├── 213837/
│   │   ├── 114059.png
│   │   └── ...
│   └── ...
├── 19/          # Zoom level 19
└── 20/          # Zoom level 20
```

## 统计信息

- 素材总数：232 个（L 标签）
- 覆盖范围：113.661190~113.676750°E, 22.726880~22.741430°N
- 拼接图像：1000x1000 像素
- 生成瓦片：
  - z=18: 144 个
  - z=19: 552 个
  - z=20: 2162 个
- 总计：2858 个瓦片

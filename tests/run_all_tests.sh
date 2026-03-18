#!/bin/bash
# 运行所有测试并生成报告

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "🧪 瓦片拼接与生成系统 - 完整测试套件"
echo "========================================"
echo ""

cd "$PROJECT_DIR"

echo "📁 项目目录：$PROJECT_DIR"
echo "📂 测试目录：$SCRIPT_DIR"
echo ""

# 运行所有测试
echo "========================================"
echo "🏃 开始运行测试..."
echo "========================================"
echo ""

python3 -m pytest tests/ -v --tb=short --html=tests/report.html --self-contained-html

echo ""
echo "========================================"
echo "✅ 测试完成!"
echo "========================================"
echo ""
echo "📊 HTML 报告：$SCRIPT_DIR/report.html"
echo ""

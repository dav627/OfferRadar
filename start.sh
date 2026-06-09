#!/bin/bash
# OfferRadar 一键启动脚本（macOS / Linux）
# 自动检查依赖 → 初始化 → 启动仪表盘

set -e
cd "$(dirname "$0")"

echo "==============================="
echo "  OfferRadar 一键启动"
echo "==============================="
echo ""

# 1. 检查 Python
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "[ERROR] 未找到 Python，请先安装 Python 3.9+"
    echo "  macOS: brew install python3"
    echo "  Ubuntu: sudo apt install python3"
    exit 1
fi
echo "[OK] Python: $($PY --version)"

# 2. 安装依赖
$PY -c "import openpyxl, yaml" 2>/dev/null || {
    echo "[INFO] 安装依赖..."
    $PY -m pip install openpyxl pyyaml -q
}
echo "[OK] 依赖已就绪"

# 3. 配置文件
if [ ! -f config.yaml ]; then
    cp config.yaml.example config.yaml
    echo "[INFO] 已创建 config.yaml，请编辑后重新运行"
    echo "  vim config.yaml"
    exit 0
fi
echo "[OK] config.yaml 已存在"

# 4. 初始化
$PY -W ignore launcher.py init 2>/dev/null

# 5. 启动仪表盘
echo ""
echo "[OK] 启动仪表盘..."
echo "  浏览器打开: http://127.0.0.1:8686"
echo "  按 Ctrl+C 停止"
echo ""
$PY -W ignore launcher.py dashboard

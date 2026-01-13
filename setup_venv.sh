#!/bin/bash
# 创建并配置venv虚拟环境（Linux/macOS）

echo "========================================"
echo "知识库助手 - 虚拟环境设置"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请先安装Python 3.8或更高版本"
    exit 1
fi

echo "[1/4] 检查Python版本..."
python3 --version

# 检查Python版本是否>=3.8
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
    echo "[错误] Python版本过低，需要3.8或更高版本"
    exit 1
fi

echo "[2/4] 创建虚拟环境..."
if [ -d "venv" ]; then
    echo "[警告] venv目录已存在，是否删除并重新创建？(y/n)"
    read -r choice
    if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
        rm -rf venv
    else
        echo "[信息] 跳过创建，使用现有venv"
        source venv/bin/activate
    fi
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 创建虚拟环境失败"
        exit 1
    fi
fi

echo "[3/4] 激活虚拟环境并升级pip..."
source venv/bin/activate
python -m pip install --upgrade pip

echo "[4/4] 安装项目依赖..."
if [ ! -f "requirements.txt" ]; then
    echo "[错误] 未找到requirements.txt文件"
    exit 1
fi

python -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[错误] 依赖安装失败，请检查网络连接或requirements.txt文件"
    exit 1
fi

echo ""
echo "========================================"
echo "虚拟环境设置完成！"
echo "========================================"
echo ""
echo "使用说明："
echo "  1. 激活虚拟环境: source activate.sh"
echo "  2. 运行应用: ./run.sh"
echo "  3. 退出虚拟环境: deactivate"
echo ""


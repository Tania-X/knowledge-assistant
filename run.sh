#!/bin/bash
# 在venv中运行应用（Linux/macOS）

# 检查venv是否存在
if [ ! -d "venv" ]; then
    echo "[错误] 虚拟环境不存在，请先运行 ./setup_venv.sh"
    exit 1
fi

# 检查是否已激活venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "[信息] 激活虚拟环境..."
    source venv/bin/activate
fi

# 检查run.py是否存在
if [ ! -f "run.py" ]; then
    echo "[错误] 未找到run.py文件"
    exit 1
fi

echo "[信息] 启动知识库助手..."
echo ""

# 运行应用
python run.py

# 检查退出状态
if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 应用运行出错"
    exit 1
fi


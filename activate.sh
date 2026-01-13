#!/bin/bash
# 激活venv虚拟环境（Linux/macOS）

if [ ! -d "venv" ]; then
    echo "[错误] 虚拟环境不存在，请先运行 ./setup_venv.sh"
    exit 1
fi

echo "[信息] 激活虚拟环境..."
source venv/bin/activate

echo "[信息] 虚拟环境已激活"
echo "[提示] 运行 'deactivate' 退出虚拟环境"
echo "[提示] 运行 'python run.py' 启动应用"
echo ""

# 启动新的shell会话以保持激活状态
exec $SHELL


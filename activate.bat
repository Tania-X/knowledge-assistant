@echo off
REM 激活venv虚拟环境（Windows）

if not exist venv (
    echo [错误] 虚拟环境不存在，请先运行 setup_venv.bat
    pause
    exit /b 1
)

echo [信息] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [信息] 虚拟环境已激活
echo [提示] 运行 'deactivate' 退出虚拟环境
echo [提示] 运行 'python run.py' 启动应用
echo.

REM 保持命令行窗口打开
cmd /k


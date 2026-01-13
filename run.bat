@echo off
REM 在venv中运行应用（Windows）

REM 检查venv是否存在
if not exist venv (
    echo [错误] 虚拟环境不存在，请先运行 setup_venv.bat
    pause
    exit /b 1
)

REM 检查是否已激活venv
echo %VIRTUAL_ENV% | findstr /i "venv" >nul
if errorlevel 1 (
    echo [信息] 激活虚拟环境...
    call venv\Scripts\activate.bat
)

REM 检查run.py是否存在
if not exist run.py (
    echo [错误] 未找到run.py文件
    pause
    exit /b 1
)

echo [信息] 启动知识库助手...
echo.

REM 运行应用
python run.py

REM 如果应用退出，保持窗口打开
if errorlevel 1 (
    echo.
    echo [错误] 应用运行出错
    pause
)


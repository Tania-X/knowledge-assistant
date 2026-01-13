@echo off
REM 创建并配置venv虚拟环境（Windows）

echo ========================================
echo 知识库助手 - 虚拟环境设置
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 检查Python版本...
python --version

REM 检查Python版本是否>=3.8
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
for /f "tokens=1 delims=." %%i in ("%PYTHON_VERSION%") do set MAJOR=%%i
for /f "tokens=2 delims=." %%i in ("%PYTHON_VERSION%") do set MINOR=%%i

if %MAJOR% LSS 3 (
    echo [错误] Python版本过低，需要3.8或更高版本
    pause
    exit /b 1
)

if %MAJOR% EQU 3 (
    if "%MINOR%"=="" (
        echo [错误] 无法解析Python次版本号
        pause
        exit /b 1
    )
    if %MINOR% LSS 8 (
        echo [错误] Python版本过低，需要3.8或更高版本
        pause
        exit /b 1
    )
)

echo [2/4] 创建虚拟环境...
if exist venv (
    echo [信息] venv目录已存在，删除并重新创建...
    rmdir /s /q venv
    if errorlevel 1 (
        echo [错误] 删除现有venv目录失败
        pause
        exit /b 1
    )
)

python -m venv venv
if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
)

echo [3/4] 激活虚拟环境并升级pip...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b 1
)
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [错误] 升级pip失败
    pause
    exit /b 1
)

echo [4/4] 安装项目依赖...
if not exist requirements.txt (
    echo [错误] 未找到requirements.txt文件
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络连接或requirements.txt文件
    pause
    exit /b 1
)

echo.
echo ========================================
echo 虚拟环境设置完成！
echo ========================================
echo.
echo 使用说明：
echo   1. 激活虚拟环境: activate.bat
echo   2. 运行应用: run.bat
echo   3. 退出虚拟环境: deactivate
echo.
pause


@echo off
REM OfferRadar 一键启动脚本（Windows）
REM 自动检查依赖 - 初始化 - 启动仪表盘

cd /d "%~dp0"

echo ===============================
echo   OfferRadar 一键启动
echo ===============================
echo.

REM 1. 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.9+
    echo   下载: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python 已找到

REM 2. 安装依赖
python -c "import openpyxl, yaml" 2>nul || (
    echo [INFO] 安装依赖...
    python -m pip install openpyxl pyyaml -q
)
echo [OK] 依赖已就绪

REM 3. 配置文件
if not exist config.yaml (
    copy config.yaml.example config.yaml >nul
    echo [INFO] 已创建 config.yaml，请编辑后重新运行
    echo   notepad config.yaml
    pause
    exit /b 0
)
echo [OK] config.yaml 已存在

REM 4. 初始化
python launcher.py init 2>nul

REM 5. 启动仪表盘
echo.
echo [OK] 启动仪表盘...
echo   浏览器打开: http://127.0.0.1:8686
echo   按 Ctrl+C 停止
echo.
python launcher.py dashboard
pause

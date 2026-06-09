@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ===============================
echo   OfferRadar
echo ===============================
echo.

REM === 检查 Python ===
where python >nul 2>&1
if errorlevel 1 (
    where python3 >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] 未找到 Python
        echo   请安装 Python 3.9+: https://www.python.org/downloads/
        echo   安装时务必勾选 "Add Python to PATH"
        echo.
        pause
        exit /b 1
    )
    set PY=python3
) else (
    set PY=python
)
echo [OK] Python 已就绪

REM === 安装依赖 ===
%PY% -c "import openpyxl; import yaml" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 首次运行，正在安装依赖...
    %PY% -m pip install openpyxl pyyaml
    echo.
)

REM === 启动 ===
echo.
echo   正在启动仪表盘...
echo   浏览器将打开: http://127.0.0.1:8686
echo   关闭此窗口可停止服务
echo.
%PY% -c "import sys; sys.path.insert(0,'.'); from core.dashboard import _ensure_init, serve; _ensure_init(); serve()"
echo.
echo [INFO] 仪表盘已停止
if errorlevel 1 (
    echo.
    echo [ERROR] 启动失败，请检查上方错误信息
)
pause

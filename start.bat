@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ===============================
echo   OfferRadar 一键启动
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

%PY% --version
echo [OK] Python 已找到
echo.

REM === 安装依赖 ===
echo [INFO] 检查依赖...
%PY% -c "import openpyxl; import yaml" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 正在安装依赖...
    %PY% -m pip install openpyxl pyyaml
    echo.
)
echo [OK] 依赖已就绪
echo.

REM === 配置文件 ===
if not exist config.yaml (
    if exist config.yaml.example (
        copy config.yaml.example config.yaml >nul
        echo [INFO] 已创建 config.yaml
        echo [INFO] 请先编辑 config.yaml 填写你的配置，然后重新运行本脚本
        echo.
        echo   用记事本打开: notepad config.yaml
        echo.
        pause
        exit /b 0
    ) else (
        echo [ERROR] 未找到 config.yaml.example，请确认项目完整
        pause
        exit /b 1
    )
)
echo [OK] config.yaml 已存在
echo.

REM === 初始化 ===
echo [INFO] 初始化项目...
%PY% launcher.py init
echo.

REM === 启动仪表盘 ===
echo ===============================
echo   仪表盘启动中...
echo   浏览器打开: http://127.0.0.1:8686
echo   关闭此窗口可停止服务
echo ===============================
echo.
%PY% launcher.py dashboard

echo.
echo 仪表盘已停止
pause

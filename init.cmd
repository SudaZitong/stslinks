@echo off
cd /d "%~dp0"
echo 安装依赖（需要 Python 3）
py -3 -m pip install -r requirements.txt
if errorlevel 1 "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
echo 若提示找不到 Python，请安装 https://www.python.org/downloads/ 并勾选 Add to PATH
pause

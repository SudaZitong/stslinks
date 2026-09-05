@echo off
cd /d "%~dp0"
echo 打开浏览器 http://127.0.0.1:8765
py -3 webapp.py
if errorlevel 1 "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" webapp.py
pause

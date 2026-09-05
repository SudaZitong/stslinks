@echo off
cd /d "%~dp0"
py -3 cli.py
if errorlevel 1 "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" cli.py
pause

@echo off
title Interview Assistant — Proxy Bot
cd /d "%~dp0"

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://python.org
    pause & exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing / verifying dependencies...
pip install -q -r requirements.txt

echo.
echo ======================================================
echo   Interview Assistant starting...
echo   Ctrl+Shift+Space  — toggle show/hide
echo   Window is HIDDEN from screen-share by default
echo ======================================================
echo.

python main.py
pause

@echo off
title ABA on Demand Automator
cd /d "%~dp0"

pythonw main.py
if errorlevel 1 (
    echo.
    echo [ERROR] pythonw failed, trying python...
    python main.py
    pause
)

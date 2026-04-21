@echo off
title ABA on Demand Automator - Setup

echo.
echo ============================================
echo   ABA on Demand Automator - Setup
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/3] Python found.
echo.

echo [2/3] Installing Playwright...
pip install playwright --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install Playwright.
    pause
    exit /b 1
)
echo Playwright installed.
echo.

echo [3/3] Downloading Chromium browser...
python -m playwright install chromium
if errorlevel 1 (
    echo [ERROR] Failed to download Chromium.
    pause
    exit /b 1
)
echo Chromium installed.
echo.

echo ============================================
echo   Setup complete! Double-click run.bat
echo ============================================
echo.
pause

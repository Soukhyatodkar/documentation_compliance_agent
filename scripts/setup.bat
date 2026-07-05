@echo off
REM ============================================================================
REM Documentation Compliance Agent - Setup Script (Windows)
REM ============================================================================
REM This script automates the initial setup of the project.
REM Usage: scripts\setup.bat
REM ============================================================================

setlocal enabledelayedexpansion

echo ==========================================
echo Documentation Compliance Agent - Setup
echo ==========================================
echo.

REM Check Python version
echo [1/6] Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.11+
    exit /b 1
)
echo Found Python:
python --version
echo [OK] Python version OK
echo.

REM Create virtual environment
echo [2/6] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists
) else (
    python -m venv venv
    echo [OK] Virtual environment created
)
echo.

REM Activate virtual environment
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated
echo.

REM Install dependencies
echo [4/6] Installing dependencies...
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
echo [OK] Dependencies installed
echo.

REM Install Playwright browsers
echo [5/6] Installing Playwright browsers...
playwright install chromium
echo [OK] Playwright browsers installed
echo.

REM Set up environment file
echo [6/6] Setting up environment configuration...
if exist .env (
    echo .env file already exists
) else (
    copy .env.example .env
    echo [OK] Created .env file (update with your values)
)
echo.

echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Edit .env with your API keys and settings
echo 2. Start Qdrant: docker run -p 6333:6333 qdrant/qdrant:latest
echo 3. Run validation: python src/main.py validate-config
echo 4. Run tests: pytest
echo.
echo For more info, see README.md
echo.

endlocal

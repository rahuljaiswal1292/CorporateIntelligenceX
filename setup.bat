@echo off
REM Setup script for UAE Corporate Intelligence Hub (Windows)

echo.
echo 🚀 Setting up UAE Corporate Intelligence Hub...
echo.

REM Create project-specific virtual environment
set VENV_NAME=intelligence-hub-env

echo 📦 Creating virtual environment: %VENV_NAME%
python -m venv %VENV_NAME%

if errorlevel 1 (
    echo ❌ Failed to create virtual environment
    exit /b 1
)

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call %VENV_NAME%\Scripts\activate.bat

if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    exit /b 1
)

REM Upgrade pip
echo ⬆️ Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install dependencies
    exit /b 1
)

REM Initialize database
echo 🗄️ Initializing database...
python scripts/init_db.py

echo.
echo ✅ Setup complete!
echo.
echo To run the application:
echo   %VENV_NAME%\Scripts\activate && python main.py
echo.
pause

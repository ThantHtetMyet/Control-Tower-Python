@echo off
echo Installing Python requirements for Server PM Report PDF Generator...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo Python found. Installing requirements...
echo.

REM Install requirements
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo Error: Failed to install some requirements
    echo Please check the error messages above
    pause
    exit /b 1
)

echo.
echo All requirements installed successfully!
echo.
echo To run the PDF generator service:
echo python main.py
echo.
pause
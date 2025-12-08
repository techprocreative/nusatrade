@echo off
echo ========================================
echo   ForexAI Connector Build Script
echo   Windows VPS Build Automation
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak terinstall!
    echo Download dari: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Membuat virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo [INFO] Mengaktifkan virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Memperbarui pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo [INFO] Menginstall dependencies...
pip install -r requirements.txt --quiet

REM Ensure PyInstaller is installed
echo [INFO] Menginstall PyInstaller...
pip install pyinstaller --quiet

REM Create resources folder if not exists
if not exist "resources" mkdir resources

REM Build executable
echo.
echo [INFO] Memulai build...
echo ========================================
python build.py

REM Check if build was successful
if exist "dist\ForexAI-Connector.exe" (
    echo.
    echo ========================================
    echo   BUILD BERHASIL!
    echo ========================================
    echo.
    echo   File executable:
    echo   dist\ForexAI-Connector.exe
    echo.
    echo   Size:
    for %%A in (dist\ForexAI-Connector.exe) do echo   %%~zA bytes
    echo.
) else (
    echo.
    echo ========================================
    echo   BUILD GAGAL!
    echo ========================================
    echo   Periksa error di atas.
    echo.
)

pause

@echo off
echo ========================================
echo   Fix Virtual Environment
echo   Menghapus venv lama dan membuat baru
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

echo [INFO] Python version:
python --version
echo.

REM Remove old venv if exists
if exist "venv" (
    echo [INFO] Menghapus virtual environment lama...
    rmdir /s /q venv
    echo [INFO] Virtual environment lama telah dihapus.
) else (
    echo [INFO] Tidak ada virtual environment lama.
)

REM Create new venv
echo [INFO] Membuat virtual environment baru...
python -m venv venv

if exist "venv" (
    echo [SUCCESS] Virtual environment baru berhasil dibuat!
    echo.
    echo Sekarang Anda bisa menjalankan build_windows.bat
) else (
    echo [ERROR] Gagal membuat virtual environment!
)

echo.
pause

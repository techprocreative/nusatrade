@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   NusaTrade Connector Build Script
echo   Windows VPS Build Automation
echo ========================================
echo.

REM Check if Python is installed
echo [STEP 1/7] Memeriksa Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak terinstall!
    echo Download dari: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo [OK] Python ditemukan!
echo.

REM Check if virtual environment exists
echo [STEP 2/7] Memeriksa virtual environment...
if not exist "venv" (
    echo [INFO] Membuat virtual environment baru...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Gagal membuat virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment berhasil dibuat!
) else (
    echo [OK] Virtual environment sudah ada!
)
echo.

REM Activate virtual environment
echo [STEP 3/7] Mengaktifkan virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Gagal mengaktifkan virtual environment!
    echo Coba hapus folder venv dan jalankan ulang script.
    pause
    exit /b 1
)
echo [OK] Virtual environment aktif!
echo.

REM Upgrade pip
echo [STEP 4/7] Memperbarui pip...
python -m pip install --upgrade pip --no-warn-script-location 2>nul
if errorlevel 1 (
    echo [WARNING] Gagal update pip, melanjutkan dengan versi saat ini...
) else (
    echo [OK] Pip berhasil diperbarui!
)
echo.

REM Install dependencies
echo [STEP 5/7] Menginstall dependencies...
echo [INFO] Ini mungkin memakan waktu beberapa menit...
pip install -r requirements.txt --no-warn-script-location
if errorlevel 1 (
    echo [ERROR] Gagal menginstall dependencies!
    echo [INFO] Mencoba install satu per satu...
    
    REM Try installing one by one
    for /f "tokens=*" %%i in (requirements.txt) do (
        echo Installing %%i...
        pip install %%i --no-warn-script-location
    )
)
echo [OK] Dependencies berhasil diinstall!
echo.

REM Ensure PyInstaller is installed
echo [STEP 6/7] Memastikan PyInstaller terinstall...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] Menginstall PyInstaller...
    pip install pyinstaller --no-warn-script-location
    if errorlevel 1 (
        echo [ERROR] Gagal menginstall PyInstaller!
        pause
        exit /b 1
    )
)
echo [OK] PyInstaller siap!
echo.

REM Create resources folder if not exists
if not exist "resources" (
    echo [INFO] Membuat folder resources...
    mkdir resources
)

REM Build executable
echo [STEP 7/7] Memulai build executable...
echo ========================================
echo [INFO] Proses build dimulai...
echo [INFO] Ini akan memakan waktu 1-3 menit...
echo.

python build.py
set BUILD_EXIT_CODE=%errorlevel%

echo.
echo ========================================

REM Check if build was successful
if exist "dist\NusaTrade-Connector.exe" (
    echo.
    echo ========================================
    echo   BUILD BERHASIL!
    echo ========================================
    echo.
    echo   File executable:
    echo   dist\NusaTrade-Connector.exe
    echo.
    echo   Size:
    for %%A in (dist\NusaTrade-Connector.exe) do (
        set size=%%~zA
        set /a size_mb=!size! / 1048576
        echo   !size! bytes (~!size_mb! MB^)
    )
    echo.
    echo [INFO] Build selesai dengan sukses!
    echo [INFO] Anda bisa menjalankan: dist\NusaTrade-Connector.exe
    echo.
) else (
    echo.
    echo ========================================
    echo   BUILD GAGAL!
    echo ========================================
    echo.
    if %BUILD_EXIT_CODE% neq 0 (
        echo [ERROR] Build script keluar dengan error code: %BUILD_EXIT_CODE%
    )
    echo [INFO] Periksa error di atas untuk detail.
    echo [INFO] Jika masalah berlanjut, coba:
    echo   1. Hapus folder venv: rmdir /s /q venv
    echo   2. Jalankan ulang script ini
    echo.
)

pause
endlocal

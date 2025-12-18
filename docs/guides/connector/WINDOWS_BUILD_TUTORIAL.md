# 🖥️ Tutorial Build ForexAI Connector di Windows VPS

Tutorial lengkap untuk membangun (build) aplikasi ForexAI Connector menjadi file `.exe` di Windows VPS.

---

## 📋 Prasyarat

| Requirement | Keterangan |
|-------------|------------|
| Windows 10/11 atau Windows Server 2019+ | VPS Anda sudah memenuhi ini |
| Python 3.10 - 3.12 | Disarankan 3.11 untuk stabilitas |
| MetaTrader 5 | Harus terinstall untuk library MT5 |
| Git | Untuk clone repository |

---

## 🚀 Langkah-Langkah Build

### Step 1: Install Python

1. Download Python dari https://www.python.org/downloads/
2. Jalankan installer dengan **opsi berikut dicentang**:
   - ✅ **Add Python to PATH** (PENTING!)
   - ✅ Install pip
3. Pilih "Install Now" atau "Customize Installation"

**Verifikasi:**
```powershell
python --version
# Output: Python 3.11.x

pip --version
# Output: pip 24.x.x
```

---

### Step 2: Install Git

1. Download Git dari https://git-scm.com/download/win
2. Install dengan pengaturan default
3. Verifikasi:

```powershell
git --version
# Output: git version 2.x.x
```

---

### Step 3: Install MetaTrader 5

> [!IMPORTANT]
> MetaTrader 5 **WAJIB** terinstall karena library `MetaTrader5` Python memerlukan file-file MT5.

1. Download dari broker Anda atau https://www.metatrader5.com/
2. Install dengan lokasi default (`C:\Program Files\MetaTrader 5\`)
3. Login ke akun demo/live (opsional untuk build, tapi diperlukan untuk testing)

---

### Step 4: Clone Repository

Buka **PowerShell** atau **Command Prompt**:

```powershell
# Masuk ke folder yang diinginkan
cd C:\Users\Administrator\Documents

# Clone repository
git clone https://github.com/YOUR_USERNAME/forex-ai.git

# Masuk ke folder connector
cd forex-ai\connector
```

> [!NOTE]
> Ganti `YOUR_USERNAME/forex-ai` dengan URL repository Anda yang sebenarnya.
> Jika project sudah ada di VPS, skip step ini.

---

### Step 5: Setup Virtual Environment (Direkomendasikan)

```powershell
# Buat virtual environment
python -m venv venv

# Aktifkan virtual environment
.\venv\Scripts\activate

# Pastikan pip ter-update
python -m pip install --upgrade pip
```

Setelah aktif, prompt akan berubah menjadi:
```
(venv) C:\Users\Administrator\Documents\forex-ai\connector>
```

---

### Step 6: Install Dependencies

```powershell
# Install semua dependencies
pip install -r requirements.txt
```

**Dependencies yang akan diinstall:**
- `PyQt6` - GUI Framework
- `MetaTrader5` - MT5 API  
- `websockets` - WebSocket client
- `pydantic` - Data validation
- `requests` - HTTP client
- `tenacity` - Retry logic
- `cryptography` - Enkripsi
- `PyInstaller` - Build tool

---

### Step 7: (Opsional) Tambahkan Icon

Buat folder `resources` dan tambahkan icon:

```powershell
# Buat folder jika belum ada
mkdir resources -Force

# Copy icon Anda ke folder resources
# File harus bernama icon.ico
copy C:\path\ke\icon.ico resources\icon.ico
```

> [!TIP]
> Jika tidak ada icon, build akan tetap berjalan tanpa icon khusus.

---

### Step 8: Build Executable

```powershell
# Pastikan masih di folder connector dan venv aktif
# Jalankan build script
python build.py
```

**Output yang diharapkan:**
```
Building ForexAI Connector for Windows...
Running: python -m PyInstaller --name=ForexAI-Connector --onefile --windowed ...

✅ Build successful!
Executable: C:\...\connector\dist\ForexAI-Connector.exe
```

---

## 🎯 Hasil Akhir

Setelah build berhasil, Anda akan mendapatkan:
- File executable: `dist/ForexAI-Connector.exe`
- Ukuran: ~15-20 MB (sudah termasuk Python runtime)
- Siap didistribusikan tanpa perlu install Python

## 🔧 Troubleshooting

### Error: "did not find executable at Python314"

**Penyebab**: Virtual environment dibuat dengan versi Python yang berbeda dari yang terinstall sekarang.

**Solusi**:
1. Jalankan script fix:
   ```batch
   fix_venv.bat
   ```
   
2. Atau hapus manual folder `venv`:
   ```batch
   rmdir /s /q venv
   ```
   
3. Kemudian jalankan ulang `build_windows.bat`

Script akan otomatis membuat virtual environment baru dengan Python version yang benar.

### Error: Python tidak ditemukan

**Solusi**: 
- Pastikan Python sudah terinstall
- Tambahkan Python ke PATH saat instalasi
- Restart Command Prompt setelah install Python

### Build gagal dengan error lain

**Solusi**:
1. Pastikan semua dependencies terinstall: `pip install -r requirements.txt`
2. Update PyInstaller: `pip install --upgrade pyinstaller`
3. Periksa log error untuk detail lebih lanjut

## 📝 Catatan Penting

## 🧹 Membersihkan Build Artifacts

Jika ingin build ulang dari awal:

```powershell
python build.py clean
```

Ini akan menghapus folder `build/`, `dist/`, dan file `.spec`.

---

## 🔧 Troubleshooting

### ❌ Error: Python not found
**Solusi:** Pastikan Python sudah ditambahkan ke PATH saat instalasi. Jika belum, reinstall Python dengan opsi "Add to PATH".

### ❌ Error: pip not recognized
**Solusi:**
```powershell
python -m ensurepip --upgrade
```

### ❌ Error: MetaTrader5 library failed
**Solusi:** Pastikan MetaTrader 5 terinstall. Library ini membutuhkan file DLL dari instalasi MT5.

### ❌ Error: PyInstaller failed - Visual C++ required
**Solusi:** Install Visual C++ Build Tools:
1. Download dari https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Install "Desktop development with C++"

### ❌ Error: DLL load failed
**Solusi:** Install Microsoft Visual C++ Redistributable:
- Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

### ❌ Build berhasil tapi .exe tidak jalan
**Kemungkinan penyebab:**
1. MetaTrader 5 tidak terinstall di komputer target
2. Versi Windows tidak kompatibel
3. Antivirus memblokir file

---

## 📦 Distribusi ke User

Setelah build berhasil, Anda bisa:

1. **Upload ke cloud storage** (Google Drive, OneDrive, dll)
2. **Buat installer** menggunakan NSIS atau Inno Setup
3. **Hosting di GitHub Releases**

### Checklist untuk User:
- [ ] Windows 10/11 (64-bit)
- [ ] MetaTrader 5 terinstall
- [ ] Microsoft Visual C++ Redistributable terinstall

---

## 📝 Script Otomatis (Opsional)

Buat file `build_all.bat` untuk automasi:

```batch
@echo off
echo ========================================
echo   ForexAI Connector Build Script
echo ========================================
echo.

REM Aktifkan virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies
pip install -r requirements.txt

REM Build
python build.py

echo.
echo ========================================
echo   Build Complete!
echo   Check dist\ForexAI-Connector.exe
echo ========================================
pause
```

**Cara pakai:**
```powershell
.\build_all.bat
```

---

## ✅ Ringkasan Perintah

```powershell
# One-liner untuk build cepat (setelah setup awal)
cd C:\path\to\forex-ai\connector && .\venv\Scripts\activate && python build.py
```

---

## 📞 Support

Jika mengalami masalah, periksa:
1. Log error di terminal
2. File `build.log` (jika ada)
3. Pastikan semua prasyarat terpenuhi

---

*Tutorial ini dibuat untuk ForexAI Connector v1.0*

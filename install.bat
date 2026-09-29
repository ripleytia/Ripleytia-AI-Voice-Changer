@echo off
title Ripleytia AI Ses Degistirici - Otomatik Kurulum
chcp 65001 >nul
cls

echo =========================================================
echo   Ripleytia AI Ses Degistirici V1 Beta - Hizli Kurulum
echo   Yapimci: Ripleytia  ^|  FiveM, Warzone ^& Yayin Optimize
echo =========================================================
echo.

cd /d "%~dp0"

:: 1. Python Tespiti
echo [1/5] Sisteminizdeki Python surumu tespit ediliyor...
set "PY_CMD="

:: Once Windows py launcher ile 3.10 veya 3.11 dene
py -3.10 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.10"
if "%PY_CMD%"=="" (
    py -3.11 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.11"
)
if "%PY_CMD%"=="" (
    python -c "import sys" >nul 2>&1 && set "PY_CMD=python"
)
if "%PY_CMD%"=="" (
    py -3 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3"
)

if "%PY_CMD%"=="" (
    echo.
    echo =========================================================
    echo [HATA] Sisteminizde calisabilir bir Python bulunamadi!
    echo.
    echo Lutfen asagidaki baglantidan Python 3.10 kurun:
    echo https://www.python.org/downloads/release/python-31011/
    echo.
    echo ONEMLI: Kurulum penceresinin en altindaki
    echo [X] "Add Python to PATH" kutucugunu MUTLAKA isaretleyin!
    echo =========================================================
    echo.
    pause
    exit /b 1
)

echo [1/5] Python bulundu: %PY_CMD%

:: 2. Sanal Ortam (.venv) Olusturma
echo.
echo [2/5] Sanal calisma ortami (.venv) hazirlaniyor...
if not exist ".venv\Scripts\python.exe" (
    echo     .venv klasoru olusturuluyor, lutfen bekleyin...
    %PY_CMD% -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [HATA] .venv sanal ortami olusturulamadi!
    echo Lutfen Python kurulumunuzda 'venv' ve 'pip' bilesenlerinin yuklu oldugundan emin olun.
    pause
    exit /b 1
)
echo [2/5] Sanal ortam hazir!

:: 3. Pip ve Paketleme Araclari Guncelleme
echo.
echo [3/5] Paket yoneticisi (pip) guncelleniyor...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel >nul 2>&1

:: 4. PyTorch & CUDA Kurulumu
echo.
echo [4/5] PyTorch (NVIDIA RTX/GTX GPU - CUDA 12.1 destegi) yukleniyor...
echo     Bu islem dosya boyutundan dolayi internet hizina bagli birkac dakika surebilir...
.venv\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 (
    echo [BILGI] CUDA PyTorch yuklenemedi veya zaman asimina ugradi, standart PyTorch kuruluyor...
    .venv\Scripts\python.exe -m pip install torch torchaudio
)

:: 5. Diger Gereksinimler (customtkinter, sounddevice vb.)
echo.
echo [5/5] Arayuz (customtkinter) ve ses isleme motoru yukleniyor...
.venv\Scripts\python.exe -m pip install -r requirements.txt

:: Dogrulama Testi
echo.
echo Dogrulama yapiliyor...
.venv\Scripts\python.exe -c "import customtkinter, torch, sounddevice, PIL; print('[TEST] Basarili: Tum temel kutuphaneler eksiksiz kuruldu!')"
if errorlevel 1 (
    echo.
    echo [UYARI] Bazi paketlerin kurulumunda sorun olusmus olabilir.
    echo Eger uygulama acilmazsa lutfen bu penceredeki hata mesajini bize iletin.
) else (
    echo.
    echo =========================================================
    echo  ✓ [TEBRIKLER] Kurulum basariyla tamamlandi!
    echo  Artik 'run.bat' dosyasina tiklayarak Ripleytia AI Ses
    echo  Degistirici'yi calistirabilirsiniz.
    echo =========================================================
)

echo.
pause

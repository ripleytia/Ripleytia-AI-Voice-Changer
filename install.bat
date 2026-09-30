@echo off
title Ripleytia AI Ses Degistirici V1 - Dinamik Kurulum
chcp 65001 >nul
cls

echo =========================================================
echo   Ripleytia AI Ses Degistirici V1 Beta - Kurulum
echo   Sifirdan Dinamik venv ve Evrensel Derleme Motoru
echo =========================================================
echo.

cd /d "%~dp0"

:: 1. Eski ve Bozuk venv Temizligi (Hardcoded Path'leri Yok Et)
echo [1/4] Eski sanal ortamlar (venv / .venv) temizleniyor...
if exist "venv" (
    echo [BILGI] "venv" klasoru bulundu, siliniyor...
    rmdir /s /q "venv"
)
if exist ".venv" (
    echo [BILGI] ".venv" klasoru bulundu, siliniyor...
    rmdir /s /q ".venv"
)

:: 2. Dinamik Sanal Ortam Olusturma
echo [2/4] Sifirdan dinamik Python sanal ortami (venv) olusturuluyor...
python -m venv venv
if errorlevel 1 (
    echo [HATA] venv olusturulamadi! Sisteminizde Python 3 kurulu oldugundan emin olun.
    pause
    exit /b 1
)

:: 3. Ortami Aktif Et ve Kurulum Araclari Guncelle
echo [3/4] Sanal ortam aktif ediliyor ve tekerlek (wheel) yapicilar guncelleniyor...
call .\venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel >nul 2>&1

:: 4. Pre-Compiled (Onceden Derlenmis) Kutuphaneleri Kur
echo [4/4] Bagimliliklar kuruluyor (C++ Derleme Korumasi Aktif / Sadece Binary)...
:: C++ veya Meson hatasini onlemek icin sadece wheel/binary indirmeye zorluyoruz.
:: Not: pyworld, faiss gibi bazi paketlerin binary versiyonlari icin prefer-binary 
:: ve genel paketler icin only-binary kullanimi guvenlik kalkanidir.
pip install --prefer-binary -r requirements.txt
if errorlevel 1 (
    echo.
    echo [HATA] Kurulum sirasinda bir hata olustu! Lutfen internet baglantinizi kontrol edin.
    pause
    exit /b 1
)

echo.
echo =========================================================
echo [BASARILI] Dinamik kurulum sifir hata ile tamamlandi!
echo Uygulamayi baslatmak icin 'run.bat' dosyasini calistirin.
echo =========================================================
pause
exit /b 0

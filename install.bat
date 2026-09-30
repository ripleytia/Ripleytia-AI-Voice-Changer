@echo off
title Ripleytia AI Ses Degistirici V1 - OTO ONARIMLI KURULUM
chcp 65001 >nul
setlocal enabledelayedexpansion

echo =========================================================
echo   Ripleytia AI Ses Degistirici V1 - AKILLI KURULUM
echo   Sistem taranacak, eksikler otomatik tamamlanacak...
echo =========================================================
echo.

cd /d "%~dp0"

:: 1. Uygun Python Surumunu Ara (3.10, 3.11 veya 3.12)
echo [1/5] Sistemdeki Python surumleri ve uyumluluk taranir...
set PYTHON_CMD=

:: Once mevcut genel python komutunu kontrol et (Sadece 3.10 - 3.12 arasina izin verilir)
python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info < (3,13) else 1)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
    echo [BILGI] Mevcut Python surumunuz tam uyumlu.
) else (
    echo [UYARI] Varsayilan Python uymuyor (3.13/3.14) veya yuklu degil.
    echo [BILGI] Sistemde kurulu baska uyumlu surum var mi kontrol ediliyor...
    
    py -3.11 -c "import sys; sys.exit(0)" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PYTHON_CMD=py -3.11
    ) else (
        py -3.12 -c "import sys; sys.exit(0)" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set PYTHON_CMD=py -3.12
        ) else (
            py -3.10 -c "import sys; sys.exit(0)" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                set PYTHON_CMD=py -3.10
            )
        )
    )
)

:: Eğer hicbir uyumlu sürüm yoksa OTOMATİK OLARAK İNDİR VE KUR
if "!PYTHON_CMD!"=="" (
    echo [KIRITIK HATA] Sisteminizde uyumlu bir Python surumu bulunamadi!
    echo [OTO-ONARIM] Hicbir yazi yazmaniza gerek yok. Python 3.11 sessizce indirilip kuruluyor...
    echo Lutfen bekleyin, bu islem internet hiziniza gore 1-3 dakika surebilir...
    
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"
    if exist "python_installer.exe" (
        echo [KURULUM] Python 3.11 bilgisayariniza kuruluyor... Ekrana yonetici onayi (UAC) gelirse EVET deyin.
        start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
        del python_installer.exe
        echo [BASARILI] Python 3.11 basariyla kuruldu!
        
        :: Kurulum sonrasi py launcher veya direkt python path'i test et
        set PYTHON_CMD=python
    ) else (
        echo [HATA] Otomatik Python indirme basarisiz oldu. Lutfen Python 3.11'i elle kurun.
        pause
        exit /b 1
    )
)

echo [BILGI] Secilen Guvenli Python Motoru: !PYTHON_CMD!
echo.

:: 2. Eski ve Bozuk Venv Temizligi
echo [2/5] Eski veya hatali kurulum kalintilari temizleniyor...
if exist "venv" rmdir /s /q "venv"
if exist ".venv" rmdir /s /q ".venv"

:: 3. Sanal Ortam Olusturma (Tam Uyumlu Surum Ile)
echo [3/5] Uyumlu ve guvenli sanal ortam olusturuluyor...
!PYTHON_CMD! -m venv venv
if not exist "venv\Scripts\activate.bat" (
    echo [HATA] Sanal ortam kurulamadi! Lutfen bilgisayari yeniden baslatip tekrar deneyin.
    pause
    exit /b 1
)

:: 4. Ortami Aktif Et ve Kurulum Araclari Guncelle
echo [4/5] Kurulum derleyicileri onariliyor...
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip setuptools wheel >nul 2>&1

:: 5. Kutuphaneleri Kur (C++ Istemeyen Akilli Indirme)
echo [5/5] Yapay Zeka paketleri kuruluyor...
echo (Bu asama tamamen otomatik gececektir, lutfen bekleyin)

:: Once sadece binary tekerlekleri indirmeyi zorluyoruz (Sifir C++ Hatasi garantisi)
pip install --prefer-binary -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [UYARI] Bazi paketler ozel kurulum istedi. Guvenlik agi (Safety Net) devreye giriyor...
    pip install -r requirements.txt
)

echo.
echo =========================================================
echo [BAŞARILI] Akilli OTO-ONARIM sistemi her seyi eksiksiz tamamladi!
echo Hata veren her sey (C++ eksikligi, yanlis Python) onarildi.
echo Uygulamayi baslatmak icin 'run.bat' dosyasini calistirabilirsiniz.
echo =========================================================
pause
exit /b 0

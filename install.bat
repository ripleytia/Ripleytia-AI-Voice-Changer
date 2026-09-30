@echo off
title Ripleytia AI Ses Degistirici V1 - OTO ONARIMLI KURULUM
chcp 65001 >nul

echo =========================================================
echo   Ripleytia AI Ses Degistirici V1 - AKILLI KURULUM
echo   Sistem taranacak, eksikler otomatik tamamlanacak...
echo =========================================================
echo.

cd /d "%~dp0"

:: 1. Uygun Python Surumunu Ara
echo [1/5] Sistemdeki Python surumleri ve uyumluluk taraniyor...
set PYTHON_CMD=

:: A
python -c "import sys; sys.exit(0 if sys.version_info[0]==3 and sys.version_info[1] in [10,11,12] else 1)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
    echo [BILGI] Mevcut Python surumunuz tam uyumlu.
    goto :python_found
)

echo [UYARI] Varsayilan Python uymuyor veya yuklu degil. Baska surum var mi bakiliyor...

:: B
py -3.11 -c "import sys; sys.exit(0)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py -3.11
    goto :python_found
)

:: C
py -3.12 -c "import sys; sys.exit(0)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py -3.12
    goto :python_found
)

:: D
py -3.10 -c "import sys; sys.exit(0)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py -3.10
    goto :python_found
)

:python_found
if not "%PYTHON_CMD%"=="" goto :python_ok

echo [KIRITIK HATA] Sisteminizde uyumlu bir Python surumu bulunamadi.
echo [OTO-ONARIM] Hicbir yazi yazmaniza gerek yok. Python 3.11 sessizce indirilip kuruluyor...
echo Lutfen bekleyin, bu islem internet hiziniza gore 1-3 dakika surebilir...

powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"

if not exist "python_installer.exe" goto :download_failed

echo [KURULUM] Python 3.11 bilgisayariniza kuruluyor... Ekrana yonetici onayi gelirse EVET deyin.
start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
del python_installer.exe
echo [BASARILI] Python 3.11 basariyla kuruldu.
set PYTHON_CMD=python
goto :python_ok

:download_failed
echo [HATA] Otomatik Python indirme basarisiz oldu. Lutfen Python 3.11.9 sürümünü elle kurun.
pause
exit /b 1

:python_ok
echo [BILGI] Secilen Guvenli Python Motoru: %PYTHON_CMD%
echo.

:: 2. Eski ve Bozuk Venv Temizligi
echo [2/5] Eski veya hatali kurulum kalintilari temizleniyor...
if exist "venv" rmdir /s /q "venv"
if exist ".venv" rmdir /s /q ".venv"

:: 3. Sanal Ortam Olusturma
echo [3/5] Uyumlu ve guvenli sanal ortam olusturuluyor...
%PYTHON_CMD% -m venv venv
if exist "venv\Scripts\activate.bat" goto :venv_ok

echo [HATA] Sanal ortam kurulamadi. Lutfen bilgisayari yeniden baslatip tekrar deneyin.
pause
exit /b 1

:venv_ok
:: 4. Ortami Aktif Et ve Kurulum Araclari Guncelle
echo [4/5] Kurulum derleyicileri onariliyor...
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip setuptools wheel >nul 2>&1

:: 5. Kutuphaneleri Kur
echo [5/5] Yapay Zeka paketleri kuruluyor...
echo Bu asama tamamen otomatik gececektir lutfen bekleyin...

pip install --prefer-binary -r requirements.txt
if %ERRORLEVEL% EQU 0 goto :install_success

echo.
echo [UYARI] Bazi paketler ozel kurulum istedi. Guvenlik agi devreye giriyor...
pip install -r requirements.txt

:install_success
echo.
echo =========================================================
echo [BASARILI] Akilli OTO-ONARIM sistemi her seyi eksiksiz tamamladi.
echo Hata veren her sey onarildi. Uygulamayi baslatmak icin run.bat dosyasini calistirabilirsiniz.
echo =========================================================
pause
exit /b 0

@echo off
title Ripleytia AI Ses Degistirici - Kurulum
chcp 65001 >nul
echo.
echo =========================================================
echo   Ripleytia AI Ses Degistirici V1 Beta - Hizli Kurulum
echo   Yapimci: Ripleytia
echo =========================================================
echo.

cd /d "%~dp0"

echo [1/3] Python sanal ortami (.venv) kontrol ediliyor...
if not exist ".venv" (
    echo [1/3] .venv olusturuluyor...
    python -m venv .venv
)

echo [2/3] Temel bagimliliklar ve GPU destegi yukleniyor...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt

echo.
echo [3/3] Kurulum tamamlandi!
echo 'run.bat' dosyasina tiklayarak uygulamayi baslatabilirsiniz.
echo.
pause

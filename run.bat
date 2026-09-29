@echo off
title Ripleytia AI Ses Degistirici V1 Beta
chcp 65001 >nul
cls

echo =========================================================
echo   Ripleytia AI Ses Degistirici V1 Beta
echo   Yapimci: Ripleytia  ^|  FiveM, Warzone ^& Yayin Optimize
echo =========================================================
echo.

cd /d "%~dp0"

:: 1. Sanal Ortam (.venv) Kontrolu
if not exist ".venv\Scripts\python.exe" (
    echo [BILGI] Ilk calistirma tespit edildi. Gerekli ortam bulunamadi.
    echo [BILGI] Otomatik kurulum baslatiliyor... Lutfen bekleyin...
    echo.
    call install.bat
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo [HATA] Kurulum tamamlanamadi! Lutfen once 'install.bat' dosyasini calistirin.
        pause
        exit /b 1
    )
)

:: 2. Temel Modul Kontrolu (customtkinter vb.)
.venv\Scripts\python.exe -c "import customtkinter, torch" >nul 2>&1
if errorlevel 1 (
    echo [UYARI] Gerekli Python kutuphaneleri (customtkinter vb.) eksik tespit edildi!
    echo [BILGI] Otomatik yukleme baslatiliyor...
    echo.
    call install.bat
)

:: 3. Uygulamayi Baslat
echo [BASLATILIYOR] Ripleytia AI Ses Degistirici baslatiliyor...
echo.
.venv\Scripts\python.exe app.py
if errorlevel 1 (
    echo.
    echo =========================================================
    echo [HATA] Uygulama bir hata nedeniyle kapandi.
    echo Eger bir kutuphane eksikse 'install.bat' dosyasini tekrar
    echo calistirarak eksikleri giderebilirsiniz.
    echo =========================================================
    pause
)

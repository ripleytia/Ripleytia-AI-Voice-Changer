@echo off
title Ripleytia AI Ses Degistirici V1 Beta
chcp 65001 >nul
cls

echo =========================================================
echo   Ripleytia AI Ses Degistirici V1 Beta
echo   Yapimci: Ripleytia  ^|  Evrensel Calistirma Motoru
echo =========================================================
echo.

cd /d "%~dp0"

:: 1. Dinamik Sanal Ortam Kontrolu
if not exist ".\venv\Scripts\python.exe" (
    echo [BILGI] Gerekli dinamik sanal ortam bulunamadi!
    echo [BILGI] Kurulum baslatiliyor... Lutfen bekleyin...
    echo.
    call install.bat
    if not exist ".\venv\Scripts\python.exe" (
        echo.
        echo [HATA] Kurulum tamamlanamadi! Lutfen once 'install.bat' dosyasini yonetici olarak calistirmayi deneyin.
        pause
        exit /b 1
    )
)

:: 2. Uygulamayi Baslat
echo [BASLATILIYOR] Uygulama aciliyor, lutfen bekleyin...
echo.
.\venv\Scripts\python.exe app.py
if errorlevel 1 (
    echo.
    echo =========================================================
    echo [HATA] Uygulama bir hata nedeniyle kapandi.
    echo Eger bir kutuphane eksikse 'install.bat' dosyasini tekrar
    echo calistirarak eksikleri giderebilirsiniz.
    echo =========================================================
    pause
)

@echo off
title Ripleytia AI Ses Degistirici V1 Beta
chcp 65001 >nul
echo.
echo =========================================================
echo   Ripleytia AI Ses Degistirici V1 Beta
echo   Yapimci: Ripleytia  ^|  FiveM, Warzone ^& Yayin Optimize
echo =========================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else if exist "..\..\.gemini\antigravity\scratch\rvc_voice_changer\.venv\Scripts\python.exe" (
    set PYTHON=..\..\.gemini\antigravity\scratch\rvc_voice_changer\.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

%PYTHON% app.py
if errorlevel 1 (
    echo.
    echo [HATA] Uygulama beklenmeyen bir sekilde kapandi.
    pause
)

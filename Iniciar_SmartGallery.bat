@echo off
title Smart Gallery AI - Pro Edition
color 0B
echo ======================================================================
echo             SMART GALLERY AI - ORGANIZADOR INTELIGENTE
echo ======================================================================
echo.
echo [*] Iniciando servidor de fototeca en segundo plano...
echo [*] URL de acceso: http://127.0.0.1:5000
echo.

start "" http://127.0.0.1:5000

py app.py
if %ERRORLEVEL% NEQ 0 (
    python app.py
)

pause
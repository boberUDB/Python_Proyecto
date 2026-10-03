@echo off
chcp 65001 >nul
title Paisaje de Tecleo - Modo Demo
cd /d "%~dp0"
echo Iniciando Paisaje de Tecleo en Modo Demostracion...
"C:\Users\rober\AppData\Local\Programs\Python\Python312\python.exe" main.py --demo
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un error al ejecutar la aplicacion.
    pause
)

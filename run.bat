@echo off
REM Простой запуск MaxFlash - просто дважды кликните!

title MaxFlash Dashboard
color 0A

cd /d %~dp0

python run.py

if errorlevel 1 (
    echo.
    echo [ERROR] Не удалось запустить приложение
    echo.
    pause
)


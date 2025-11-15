@echo off
chcp 65001 >nul
title MaxFlash - Торговая Система
color 0A
echo.
echo ╔═══════════════════════════════════════════════════════╗
echo ║     MAXFLASH - ТОРГОВАЯ СИСТЕМА                       ║
echo ║     Универсальный запуск                              ║
echo ╚═══════════════════════════════════════════════════════╝
echo.
echo 🔄 Проверка зависимостей...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.10+
    pause
    exit /b 1
)

echo ✅ Python найден
echo.
echo 📦 Установка зависимостей (если нужно)...
python -m pip install --quiet --upgrade pip >nul 2>&1
python -m pip install --quiet dash dash-bootstrap-components plotly pandas numpy ccxt python-telegram-bot >nul 2>&1

echo.
echo 🚀 Запуск системы...
echo.
echo ════════════════════════════════════════════════════════
echo   Интерфейс будет доступен: http://localhost:8050
echo   Telegram бот: t.me/MaxFlash_bot
echo   Нажмите Ctrl+C для остановки
echo ════════════════════════════════════════════════════════
echo.

cd /d %~dp0
python run.py

pause


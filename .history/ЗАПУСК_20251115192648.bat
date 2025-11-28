@echo off
chcp 65001 >nul
title MaxFlash Trading System

echo.
echo ============================================================
echo   🚀 MAXFLASH - ТОРГОВАЯ СИСТЕМА
echo ============================================================
echo.
echo   🌐 Веб-интерфейс: http://localhost:8050
echo   🤖 Telegram бот: t.me/MaxFlash_bot
echo.
echo   ⏹️  Нажмите Ctrl+C для остановки
echo ============================================================
echo.

cd /d "%~dp0"

python start.py

pause

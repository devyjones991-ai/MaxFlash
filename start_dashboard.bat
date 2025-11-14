@echo off
title MaxFlash Dashboard Server
color 0A
echo.
echo ========================================
echo   MAXFLASH TRADING DASHBOARD
echo ========================================
echo.
cd /d %~dp0web_interface
echo Запускаю сервер на http://localhost:8050
echo.
python app_simple.py
pause

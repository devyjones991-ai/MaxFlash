@echo off
REM ПРОСТОЙ ЗАПУСК - ДВАЖДЫ КЛИКНИ И ВСЁ РАБОТАЕТ!
title MaxFlash Dashboard
color 0A
echo.
echo ========================================
echo   MAXFLASH TRADING DASHBOARD
echo ========================================
echo.
echo Запускаю сервер...
echo.
cd /d %~dp0web_interface
python app.py
pause


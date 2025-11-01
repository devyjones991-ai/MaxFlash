@echo off
REM СУПЕР ПРОСТОЙ ЗАПУСК - Просто дважды кликните!

title MaxFlash Dashboard
color 0A

echo.
echo ========================================
echo    MAXFLASH TRADING DASHBOARD
echo ========================================
echo.

cd web_interface

echo [1/3] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [ERROR] Python не установлен!
    echo.
    echo Установите Python 3.9+ с python.org
    pause
    exit
)

echo [OK] Python найден
echo.

echo [2/3] Установка зависимостей (если нужно)...
pip install --quiet --upgrade pip dash dash-bootstrap-components dash-table requests 2>nul
echo [OK] Готово
echo.

echo [3/3] Запуск Dashboard...
echo.
color 0B
echo ========================================
echo   ДАШБОРД ЗАПУЩЕН!
echo ========================================
echo.
echo   Откройте в браузере:
echo   http://localhost:8050
echo.
echo   Нажмите Ctrl+C для остановки
echo ========================================
echo.

python app_simple.py

pause

@echo off
REM Запуск современного интерфейса MaxFlash Dashboard

echo ========================================
echo ⚡ MaxFlash Trading Dashboard - Modern
echo ========================================
echo.
echo 🎨 Современный интерфейс в стиле топовых криптосайтов
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не установлен!
    pause
    exit /b 1
)

echo [1/2] Установка зависимостей...
pip install dash dash-bootstrap-components plotly pandas numpy --quiet 2>nul

echo [2/2] Запуск dashboard...
echo.
echo ========================================
echo 🌐 Dashboard: http://localhost:8050
echo ⏹️  Нажмите Ctrl+C для остановки
echo ========================================
echo.

cd /d %~dp0
python app_modern.py

pause


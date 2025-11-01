@echo off
REM Автоматическая установка и запуск

echo Установка зависимостей MaxFlash Dashboard...
pip install dash dash-bootstrap-components dash-table requests --quiet

if errorlevel 1 (
    echo Ошибка установки. Используйте: pip install dash dash-bootstrap-components dash-table requests
    pause
    exit /b 1
)

echo.
echo Запуск dashboard...
echo Откройте http://localhost:8050 в браузере
echo.

python app.py


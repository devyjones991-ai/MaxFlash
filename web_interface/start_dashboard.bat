@echo off
REM Простой запуск MaxFlash Dashboard для Windows

echo ========================================
echo MaxFlash Trading Dashboard
echo ========================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не установлен!
    echo Установите Python 3.9+ и попробуйте снова
    pause
    exit /b 1
)

echo [1/3] Проверка зависимостей...
python -c "import dash" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Установка зависимостей...
    pip install dash dash-bootstrap-components dash-table requests --quiet
    if errorlevel 1 (
        echo [ERROR] Не удалось установить зависимости!
        pause
        exit /b 1
    )
    echo [OK] Зависимости установлены
) else (
    echo [OK] Зависимости уже установлены
)

echo.
echo [2/3] Запуск dashboard...
echo.
echo ========================================
echo Dashboard будет доступен по адресу:
echo http://localhost:8050
echo ========================================
echo.
echo Нажмите Ctrl+C для остановки
echo.

cd /d %~dp0

REM Пробуем запустить основной app.py, если не получается - упрощенную версию
python app.py 2>nul
if errorlevel 1 (
    echo [INFO] Запуск упрощенной версии...
    python app_simple.py
) else (
    REM app.py запустился успешно
)

pause


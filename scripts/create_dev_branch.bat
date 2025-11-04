@echo off
REM Скрипт для создания dev ветки и настройки workflow (Windows)

setlocal enabledelayedexpansion

color 0A

echo.
echo ========================================
echo    СОЗДАНИЕ DEV ВЕТКИ
echo ========================================
echo.

REM Проверяем что мы в git репозитории
git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Не найдена git директория
    pause
    exit /b 1
)

REM Получаем текущую ветку
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
echo [INFO] Текущая ветка: !CURRENT_BRANCH!
echo.

REM Переключаемся на main если нужно
if not "!CURRENT_BRANCH!"=="main" if not "!CURRENT_BRANCH!"=="master" (
    echo [INFO] Переключение на main...
    git checkout main 2>nul
    if errorlevel 1 (
        git checkout master 2>nul
        if errorlevel 1 (
            echo [ERROR] Не удалось переключиться на main/master
            pause
            exit /b 1
        )
    )
)

REM Обновляем main
echo [INFO] Обновление main...
git pull origin main 2>nul
if errorlevel 1 (
    git pull origin master 2>nul
    if errorlevel 1 (
        echo [WARNING] Не удалось обновить main
    )
)

REM Проверяем существует ли dev ветка
git show-ref --verify --quiet refs/heads/dev
if errorlevel 1 (
    REM Создаем dev ветку
    echo [INFO] Создание dev ветки...
    git checkout -b dev
    
    REM Пушим dev ветку
    echo [INFO] Отправка dev ветки...
    git push -u origin dev
    if errorlevel 1 (
        echo [ERROR] Не удалось отправить dev ветку
        pause
        exit /b 1
    )
    
    echo.
    echo ========================================
    echo    DEV ВЕТКА СОЗДАНА И ОТПРАВЛЕНА
    echo ========================================
) else (
    echo [INFO] Ветка dev уже существует
    echo [INFO] Переключение на dev...
    git checkout dev
    git pull origin dev 2>nul
    if errorlevel 1 (
        echo [WARNING] Не удалось обновить dev
    )
    echo.
    echo ========================================
    echo    ПЕРЕКЛЮЧИЛИСЬ НА DEV ВЕТКУ
    echo ========================================
)

echo.
echo Теперь вы можете:
echo   - Работать в dev ветке для разработки
echo   - Использовать main для стабильных релизов
echo   - Использовать scripts\auto_commit_push.bat для коммитов
echo.
pause


@echo off
REM Скрипт для загрузки проекта на GitHub
REM ЗАМЕНИТЕ yourusername на ваш GitHub username!

echo ========================================
echo Загрузка проекта MaxFlash на GitHub
echo ========================================
echo.

REM Проверка наличия remote
git remote -v | findstr origin >nul
if %errorlevel% neq 0 (
    echo.
    echo ВНИМАНИЕ: Remote не настроен!
    echo.
    echo Выполните команды:
    echo   git remote add origin https://github.com/YOUR_USERNAME/MaxFlash.git
    echo   Замените YOUR_USERNAME на ваш GitHub username
    echo.
    echo Или используйте SSH:
    echo   git remote add origin git@github.com:YOUR_USERNAME/MaxFlash.git
    echo.
    pause
    exit /b 1
)

echo Текущий remote:
git remote -v
echo.

echo Текущая ветка:
git branch --show-current
echo.

echo Загрузка на GitHub...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo ✅ УСПЕШНО! Проект загружен на GitHub!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ❌ ОШИБКА при загрузке!
    echo ========================================
    echo.
    echo Возможные причины:
    echo 1. Репозиторий не создан на GitHub
    echo 2. Неправильный URL remote
    echo 3. Нет прав доступа
    echo.
    echo Проверьте инструкции в GITHUB_SETUP.md
)

pause


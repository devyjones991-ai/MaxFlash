@echo off
echo ========================================
echo Загрузка MaxFlash на GitHub
echo https://github.com/devyjones991-ai/MaxFlash
echo ========================================
echo.
echo Убедитесь, что репозиторий создан на GitHub!
echo Если репозитория нет, создайте его:
echo   1. Перейдите на https://github.com/devyjones991-ai
echo   2. Нажмите "New repository"
echo   3. Название: MaxFlash
echo   4. НЕ добавляйте README/.gitignore (они уже есть)
echo   5. Нажмите "Create repository"
echo.
pause
echo.
echo Загрузка на GitHub...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo ✅ УСПЕШНО! Проект загружен!
    echo ========================================
    echo.
    echo Откройте: https://github.com/devyjones991-ai/MaxFlash
) else (
    echo.
    echo ========================================
    echo ❌ ОШИБКА!
    echo ========================================
    echo.
    echo Возможные причины:
    echo 1. Репозиторий не создан на GitHub
    echo 2. Проблемы с аутентификацией
    echo.
    echo Решение:
    echo - Создайте репозиторий на GitHub
    echo - Используйте GitHub CLI: gh auth login
    echo - Или используйте Personal Access Token
)

pause


@echo off
REM Скрипт для автоматического коммита и пуша изменений (Windows)
REM Использование: scripts\auto_commit_push.bat [message]

setlocal enabledelayedexpansion

color 0A

REM Получаем сообщение коммита
set "COMMIT_MESSAGE=%~1"
if "!COMMIT_MESSAGE!"=="" (
    for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
    set "COMMIT_MESSAGE=Auto commit: !datetime:~0,4!-!datetime:~4,2!-!datetime:~6,2! !datetime:~8,2!:!datetime:~10,2!:!datetime:~12,2!"
)

echo.
echo ========================================
echo    АВТОМАТИЧЕСКИЙ КОММИТ И ПУШ
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

REM Синхронизируем версию
echo [1/5] Синхронизация версии...
python scripts\sync_version.py
echo.

REM Проверяем статус
echo [2/5] Проверка статуса...
git status --short
echo.

REM Проверяем есть ли изменения
git diff --quiet >nul 2>&1
set HAS_CHANGES=%errorlevel%

git diff --cached --quiet >nul 2>&1
set HAS_STAGED=%errorlevel%

if %HAS_CHANGES%==0 if %HAS_STAGED%==0 (
    echo [WARNING] Нет изменений для коммита
    pause
    exit /b 0
)

REM Добавляем все изменения
echo [3/5] Добавление изменений...
git add .
echo.

REM Проверяем линтер (если установлен)
where ruff >nul 2>&1
if %errorlevel%==0 (
    echo [4/5] Проверка линтера...
    ruff check . --fix || echo [WARNING] Найдены проблемы линтера
    echo.
) else (
    echo [4/5] Линтер не установлен, пропускаем...
    echo.
)

REM Коммитим
echo [5/5] Создание коммита и пуша...
git commit -m "!COMMIT_MESSAGE!"
if errorlevel 1 (
    echo [ERROR] Ошибка при создании коммита
    pause
    exit /b 1
)

REM Пушим
git push origin !CURRENT_BRANCH!
if errorlevel 1 (
    echo [ERROR] Ошибка при отправке на удаленный репозиторий
    pause
    exit /b 1
)

echo.
echo ========================================
echo    УСПЕШНО! КОММИТ И ПУШ ВЫПОЛНЕНЫ
echo ========================================
echo.
pause


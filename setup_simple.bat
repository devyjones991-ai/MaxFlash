@echo off
chcp 65001 >nul
echo ========================================
echo   НАСТРОЙКА MAXFLASH TRADING SYSTEM
echo ========================================
echo.

REM Создание виртуального окружения
if not exist "venv" (
    echo [1/5] Создание виртуального окружения...
    python -m venv venv
    echo ✓ Готово
) else (
    echo [1/5] Виртуальное окружение уже существует
)

call venv\Scripts\activate.bat

REM Установка зависимостей
echo [2/5] Установка зависимостей Python...
pip install --upgrade pip
pip install -r requirements.txt
echo ✓ Готово

REM Создание .env
echo [3/5] Настройка переменных окружения...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo ✓ Создан .env файл
    ) else (
        REM Создаём минимальный .env если шаблона нет
        (
            echo DATABASE_URL=postgresql+asyncpg://maxflash:maxflash_dev@localhost:5432/maxflash
            echo REDIS_URL=redis://localhost:6379/0
            echo DEBUG=true
            echo SECRET_KEY=dev-secret-key-change-in-production
        ) > .env
        echo ✓ Создан минимальный .env файл
    )
    echo.
    echo [ИНФО] .env файл создан с настройками по умолчанию
    echo.
    echo ════════════════════════════════════════════════════════
    echo   ВАЖНО: Настройте API ключи перед запуском!
    echo ════════════════════════════════════════════════════════
    echo.
    echo Откройте файл НАСТРОЙКА_API.txt для инструкций
    echo или README_SETUP.md для подробной информации
    echo.
    echo Для торговли укажите в .env:
    echo   - BINANCE_API_KEY и BINANCE_API_SECRET
    echo   - TELEGRAM_BOT_TOKEN (опционально)
    echo.
    echo Без API ключей система работает в безопасном
    echo режиме paper trading (только тестирование)
    echo.
) else (
    echo ✓ .env файл уже существует
)

REM Создание директорий
echo [4/5] Создание необходимых директорий...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "ml\artifacts" mkdir ml\artifacts
echo ✓ Готово

REM Проверка Docker
echo [5/5] Проверка Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Docker не установлен!
    echo Установите Docker Desktop для запуска БД
) else (
    echo ✓ Docker установлен
)

echo.
echo ========================================
echo   НАСТРОЙКА ЗАВЕРШЕНА!
echo ========================================
echo.
echo Следующие шаги:
echo 1. Отредактируйте .env файл (опционально)
echo 2. Запустите: START.bat
echo.
pause


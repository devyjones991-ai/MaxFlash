#!/bin/bash
# Скрипт для исправления и запуска бота на сервере

cd ~/MaxFlash

# Остановка старых процессов
echo "Остановка старых процессов..."
pkill -f "run_bot.py" || true
sleep 2

# Активируем venv и проверяем установку
source venv/bin/activate

# Устанавливаем библиотеку если нужно
pip install python-telegram-bot --quiet

# Проверяем импорт
echo "Проверка импорта..."
python -c "from bots.telegram.bot import TelegramBot; print('✅ Импорт OK')" || exit 1

# Запускаем бота в фоне
echo "Запуск бота..."
nohup python run_bot.py > logs/telegram_bot.log 2>&1 &
sleep 2

# Проверяем что запустился
if ps aux | grep -v grep | grep "run_bot.py" > /dev/null; then
    echo "✅ Бот запущен!"
    ps aux | grep -v grep | grep "run_bot.py"
    echo ""
    echo "Последние логи:"
    tail -20 logs/telegram_bot.log
else
    echo "❌ Бот не запустился. Логи:"
    tail -30 logs/telegram_bot.log
    exit 1
fi


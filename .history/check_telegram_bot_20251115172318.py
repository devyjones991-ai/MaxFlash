"""
Проверка и диагностика Telegram бота
"""
import os
import sys
import asyncio
from pathlib import Path

# Настройка путей - важно добавить корень ПЕРВЫМ
root = Path(__file__).parent.absolute()
# Меняем рабочую директорию на корень проекта
os.chdir(root)

# Добавляем корень проекта в начало sys.path для импорта api
# ВАЖНО: корень должен быть ПЕРВЫМ, иначе Python будет искать api в web_interface
project_root_str = str(root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

# Также добавляем web_interface (но после корня)
web_interface_str = str(root / "web_interface")
if web_interface_str not in sys.path:
    sys.path.insert(1, web_interface_str)  # Вставляем на позицию 1, не 0

print("="*60)
print("  ДИАГНОСТИКА TELEGRAM БОТА")
print("="*60)

# 1. Проверка библиотеки
print("\n1. Проверка библиотеки python-telegram-bot...")
try:
    import telegram
    from telegram import Bot
    print(f"   ✅ Установлена версия: {telegram.__version__}")
except ImportError as e:
    print(f"   ❌ НЕ установлена: {e}")
    print("   Установи: pip install python-telegram-bot")
    sys.exit(1)

# 2. Проверка токена
print("\n2. Проверка токена...")
token = "8274253718:AAGa8juUeXf1jXP7BUZ3o_t-fpK-3BADxew"
if not token or len(token) < 10:
    print("   ❌ Токен неверный или пустой")
    sys.exit(1)
print(f"   ✅ Токен: {token[:10]}...{token[-5:]}")

# 3. Проверка подключения к Telegram API
print("\n3. Проверка подключения к Telegram API...")
try:
    bot = Bot(token=token)

    # get_me() - это async функция, нужно использовать asyncio.run()
    async def check_bot():
        bot_info = await bot.get_me()
        return bot_info

    bot_info = asyncio.run(check_bot())
    print("   ✅ Подключение успешно!")
    print(f"   ✅ Имя бота: {bot_info.first_name}")
    print(f"   ✅ Username: @{bot_info.username}")
    print(f"   ✅ ID: {bot_info.id}")
except Exception as e:
    print(f"   ❌ Ошибка подключения: {e}")
    print("   Возможные причины:")
    print("   - Неверный токен")
    print("   - Нет интернета")
    print("   - Telegram API недоступен")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Проверка импорта модулей
print("\n4. Проверка импорта модулей...")
try:
    # Сначала проверяем, что api.models доступен
    try:
        from api.models import SignalModel  # noqa: F401
        print("   ✅ api.models импортирован")
    except ImportError as e:
        print(f"   ❌ Ошибка импорта api.models: {e}")
        print(f"   Текущий sys.path: {sys.path[:3]}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Теперь импортируем остальные модули
    from utils.telegram_bot import get_telegram_bot
    from utils.signal_generator import SignalGenerator
    from utils.profit_tracker import ProfitTracker
    from utils.market_data_manager import MarketDataManager
    print("   ✅ Все модули импортированы")
except Exception as e:
    print(f"   ❌ Ошибка импорта: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. Создание бота
print("\n5. Создание экземпляра бота...")
try:
    data_manager = MarketDataManager()
    signal_generator = SignalGenerator(data_manager=data_manager)
    profit_tracker = ProfitTracker(data_manager=data_manager)

    telegram_bot = get_telegram_bot(
        token=token,
        data_manager=data_manager,
        signal_generator=signal_generator,
        profit_tracker=profit_tracker
    )

    if telegram_bot:
        print("   ✅ Бот создан")
        print(f"   ✅ is_running: {telegram_bot.is_running}")
    else:
        print("   ❌ Бот не создан (вернул None)")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Ошибка создания: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 6. Запуск бота
print("\n6. Запуск бота...")
try:
    telegram_bot.start()
    import time
    time.sleep(3)  # Ждем запуск

    if telegram_bot.is_running:
        print("   ✅ Бот запущен успешно!")
        print(f"   ✅ Статус: is_running = {telegram_bot.is_running}")
        print("\n" + "="*60)
        print("  ✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
        print("="*60)
        # bot_info уже определен выше
        try:
            bot_username = (
                bot_info.username if 'bot_info' in locals()
                else "MaxFlash_bot"
            )
            print(
                f"\nБот работает! Отправь /start в Telegram: @{bot_username}"
            )
        except Exception:
            print(
                "\nБот работает! Отправь /start в Telegram: t.me/MaxFlash_bot"
            )
        print("\nНажми Ctrl+C для остановки...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nОстановка бота...")
            telegram_bot.stop()
            print("✅ Бот остановлен")
    else:
        print("   ⚠️  Бот не запустился (is_running=False)")
        print("   Проверь логи для подробностей")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Ошибка запуска: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

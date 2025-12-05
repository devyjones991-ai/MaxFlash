"""
MaxFlash Telegram Bot
Минималистичный но информативный бот для трейдинга.

Команды:
/start - Приветствие и меню
/price [symbol] - Текущая цена (по умолчанию BTC/USDT)
/signal [symbol] - Получить торговый сигнал
/top - Топ-5 монет по изменению за 24ч
/alerts - Управление алертами
/status - Статус системы
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Добавляем путь к родительской директории
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.market_data_manager import MarketDataManager
from utils.signal_scanner import SignalScanner
from utils.logger_config import setup_logging

logger = setup_logging()

# Bot token
BOT_TOKEN = "7865140777:AAEyYsYcqjey_6_cBOQOAq2I2kQxGRt5kek"

# Инициализация менеджеров
data_manager = MarketDataManager()
signal_scanner = SignalScanner(data_manager=data_manager)  # Независимый сканер

# Популярные пары
POPULAR_PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT"]

# Хранилище алертов пользователей
user_alerts = {}  # {user_id: [{symbol, price_above, price_below}]}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение с главным меню."""
    keyboard = [
        [
            InlineKeyboardButton("📊 BTC", callback_data="price_BTC/USDT"),
            InlineKeyboardButton("📊 ETH", callback_data="price_ETH/USDT"),
            InlineKeyboardButton("📊 SOL", callback_data="price_SOL/USDT"),
        ],
        [
            InlineKeyboardButton("🎯 Сигнал BTC", callback_data="signal_BTC/USDT"),
            InlineKeyboardButton("🎯 Сигнал ETH", callback_data="signal_ETH/USDT"),
        ],
        [
            InlineKeyboardButton("🔍 СКАН ВСЕХ 50", callback_data="scan_all"),
        ],
        [
            InlineKeyboardButton("🔝 Топ-5", callback_data="top5"),
            InlineKeyboardButton("📈 Статус", callback_data="status"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🚀 *MaxFlash Trading Bot*

Добро пожаловать! Я сканирую топ-50 криптовалют.

*Команды:*
/price `BTC` - Текущая цена
/signal `ETH` - Торговый сигнал
/scan - 🔍 *Сканировать все 50 монет*
/top - Топ монет за 24ч
/alert `BTC 100000` - Установить алерт

Или используй кнопки ниже 👇
"""
    await update.message.reply_text(
        welcome_text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить текущую цену."""
    # Определяем символ
    if context.args:
        symbol = context.args[0].upper()
        if "/" not in symbol:
            symbol = f"{symbol}/USDT"
    else:
        symbol = "BTC/USDT"
    
    await _send_price(update.message, symbol)


async def _send_price(message, symbol: str, is_callback=False):
    """Отправляет цену для указанного символа."""
    try:
        # Получаем тикер
        ticker = data_manager.get_ticker(symbol, exchange_id='binance')
        
        if ticker is None:
            await message.reply_text(f"❌ Не удалось получить данные для {symbol}")
            return
        
        price = ticker.get('last', 0)
        change_24h = ticker.get('percentage', 0) or 0
        high_24h = ticker.get('high', 0) or 0
        low_24h = ticker.get('low', 0) or 0
        volume = ticker.get('quoteVolume', 0) or 0
        
        # Определяем эмодзи
        if change_24h > 0:
            change_emoji = "🟢"
            arrow = "▲"
        elif change_24h < 0:
            change_emoji = "🔴"
            arrow = "▼"
        else:
            change_emoji = "⚪"
            arrow = "■"
        
        # Форматируем объем
        if volume >= 1_000_000_000:
            vol_str = f"{volume/1_000_000_000:.2f}B"
        elif volume >= 1_000_000:
            vol_str = f"{volume/1_000_000:.2f}M"
        else:
            vol_str = f"{volume:,.0f}"
        
        text = f"""
{change_emoji} *{symbol}*

💰 Цена: `${price:,.2f}`
{arrow} 24ч: `{change_24h:+.2f}%`
📈 High: `${high_24h:,.2f}`
📉 Low: `${low_24h:,.2f}`
📊 Volume: `${vol_str}`

🕐 {datetime.now().strftime('%H:%M:%S')}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Обновить", callback_data=f"price_{symbol}"),
                InlineKeyboardButton("🎯 Сигнал", callback_data=f"signal_{symbol}"),
            ],
            [
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if is_callback:
            await message.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка получения цены {symbol}: {e}")
        await message.reply_text(f"❌ Ошибка: {str(e)}")


async def get_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить торговый сигнал."""
    if context.args:
        symbol = context.args[0].upper()
        if "/" not in symbol:
            symbol = f"{symbol}/USDT"
    else:
        symbol = "BTC/USDT"
    
    await _send_signal(update.message, symbol)


async def _send_signal(message, symbol: str, is_callback=False):
    """Отправляет сигнал для указанного символа (независимый сканер!)."""
    try:
        # Отправляем сообщение о генерации
        if is_callback:
            status_msg = message  # Уже сообщение для редактирования
            await status_msg.edit_text(f"⏳ Анализирую {symbol}...")
        else:
            status_msg = await message.reply_text(f"⏳ Анализирую {symbol}...")
        
        # Используем независимый сканер
        signal = signal_scanner.scan_single(symbol)
        
        if signal:
            if signal.signal_type == "LONG":
                emoji = "🟢"
                direction = "LONG (Покупка)"
            else:
                emoji = "🔴"
                direction = "SHORT (Продажа)"
            
            # Risk/Reward
            rr_ratio = signal.risk_reward
            
            text = f"""
{emoji} *СИГНАЛ {direction}*

📍 *{symbol}* ({signal.timeframe})

🎯 Entry: `${signal.entry_price:,.4f}`
✅ Take Profit: `${signal.take_profit:,.4f}`
🛑 Stop Loss: `${signal.stop_loss:,.4f}`

📊 Confidence: `{signal.confidence:.0%}`
⚖️ Risk/Reward: `1:{rr_ratio:.1f}`

📋 *Индикаторы:*
✓ {' • '.join(signal.indicators[:4])}

⚠️ _Это не финансовый совет. Торгуйте ответственно._
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Обновить", callback_data=f"signal_{symbol}"),
                    InlineKeyboardButton("📊 Цена", callback_data=f"price_{symbol}"),
                ],
                [
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            text = f"""
⏸️ *Нет сигнала*

📍 {symbol}

В данный момент нет чётких торговых сигналов. 
Условия не соответствуют критериям входа.

💡 _Попробуйте /scan для поиска сигналов по всем монетам._
"""
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Обновить", callback_data=f"signal_{symbol}"),
                    InlineKeyboardButton("🔍 Скан всех", callback_data="scan_all"),
                ],
                [
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Ошибка генерации сигнала {symbol}: {e}")
        await message.reply_text(f"❌ Ошибка: {str(e)}")


async def get_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Топ-5 монет по изменению за 24 часа."""
    await _send_top(update.message)


async def _send_top(message, is_callback=False):
    """Отправляет топ монет."""
    try:
        if not is_callback:
            status_msg = await message.reply_text("⏳ Загружаю данные...")
        else:
            status_msg = message  # Уже сообщение для редактирования
        
        results = []
        for symbol in POPULAR_PAIRS:
            ticker = data_manager.get_ticker(symbol, exchange_id='binance')
            if ticker:
                results.append({
                    'symbol': symbol,
                    'price': ticker.get('last', 0),
                    'change': ticker.get('percentage', 0) or 0
                })
        
        # Сортируем по изменению
        results.sort(key=lambda x: x['change'], reverse=True)
        
        text = "🔝 *Топ монет за 24ч*\n\n"
        
        for i, item in enumerate(results, 1):
            if item['change'] > 0:
                emoji = "🟢"
                arrow = "▲"
            elif item['change'] < 0:
                emoji = "🔴"
                arrow = "▼"
            else:
                emoji = "⚪"
                arrow = "■"
            
            symbol_short = item['symbol'].replace('/USDT', '')
            text += f"{i}. {emoji} *{symbol_short}*: `${item['price']:,.2f}` {arrow}`{item['change']:+.2f}%`\n"
        
        text += f"\n🕐 {datetime.now().strftime('%H:%M:%S')}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="top5")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка получения топа: {e}")
        if not is_callback:
            await message.reply_text(f"❌ Ошибка: {str(e)}")
        else:
            await message.edit_text(f"❌ Ошибка: {str(e)}")


async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить ценовой алерт."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📢 *Установка алерта*\n\n"
            "Использование:\n"
            "`/alert BTC 100000` - алерт при цене выше $100k\n"
            "`/alert ETH <3000` - алерт при цене ниже $3k\n",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    if "/" not in symbol:
        symbol = f"{symbol}/USDT"
    
    price_str = context.args[1]
    
    try:
        if price_str.startswith('<'):
            price = float(price_str[1:])
            alert_type = "below"
            direction = "ниже"
        else:
            price = float(price_str.replace('>', ''))
            alert_type = "above"
            direction = "выше"
        
        user_id = update.effective_user.id
        if user_id not in user_alerts:
            user_alerts[user_id] = []
        
        user_alerts[user_id].append({
            'symbol': symbol,
            'price': price,
            'type': alert_type
        })
        
        await update.message.reply_text(
            f"✅ Алерт установлен!\n\n"
            f"📍 {symbol}\n"
            f"💰 Цена {direction} `${price:,.2f}`",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат цены")


async def scan_all_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сканирование всех 50 монет для поиска сигналов."""
    await _send_scan_results(update.message)


async def _send_scan_results(message, is_callback=False):
    """Сканирует все монеты и отправляет результаты."""
    try:
        if is_callback:
            status_msg = message  # Уже сообщение для редактирования
        else:
            status_msg = await message.reply_text("🔍 Сканирую 50 монет... Это займёт ~30 сек.")
        
        # Сканируем все монеты
        signals = signal_scanner.scan_all()
        
        if signals:
            # Топ-10 сигналов
            top_signals = signals[:10]
            
            text = f"🔍 *Найдено {len(signals)} сигналов*\n\n"
            
            for i, s in enumerate(top_signals, 1):
                emoji = "🟢" if s.signal_type == "LONG" else "🔴"
                symbol_short = s.symbol.replace('/USDT', '')
                text += f"{i}. {emoji} *{symbol_short}* `${s.entry_price:,.4f}` ({s.confidence:.0%})\n"
                text += f"   TP: `${s.take_profit:,.4f}` | SL: `${s.stop_loss:,.4f}`\n"
            
            if len(signals) > 10:
                text += f"\n_...и ещё {len(signals) - 10} сигналов_"
            
            text += "\n\n💡 Для деталей: /signal `SYMBOL`"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="scan_all")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="scan_all")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await status_msg.edit_text(
                "⏸️ *Нет сигналов*\n\n"
                "В данный момент нет чётких торговых сигналов по топ-50 монетам.\n"
                "Рынок в состоянии неопределённости.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка сканирования: {e}")
        await message.reply_text(f"❌ Ошибка: {str(e)}")


async def get_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статус системы."""
    await _send_status(update.message)


async def _send_status(message, is_callback=False):
    """Отправляет статус системы."""
    try:
        # Проверяем подключение к биржам
        exchanges_status = []
        for exchange in ['binance', 'bybit']:
            try:
                ticker = data_manager.get_ticker('BTC/USDT', exchange_id=exchange)
                if ticker:
                    exchanges_status.append(f"✅ {exchange.upper()}")
                else:
                    exchanges_status.append(f"⚠️ {exchange.upper()}")
            except:
                exchanges_status.append(f"❌ {exchange.upper()}")
        
        text = f"""
📈 *Статус MaxFlash*

*Биржи:*
{chr(10).join(exchanges_status)}

*Сигналы:* ✅ Активен

*Активные алерты:* {sum(len(v) for v in user_alerts.values())}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="status")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if is_callback:
            await message.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка статуса: {e}")
        if is_callback:
            await message.edit_text(f"❌ Ошибка: {str(e)}")
        else:
            await message.reply_text(f"❌ Ошибка: {str(e)}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на inline кнопки."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("price_"):
        symbol = data.replace("price_", "")
        await _send_price(query.message, symbol, is_callback=True)
        
    elif data.startswith("signal_"):
        symbol = data.replace("signal_", "")
        # Используем правильный метод через сканер
        await _send_signal(query.message, symbol, is_callback=True)
        
    elif data == "top5":
        await query.message.edit_text("⏳ Загружаю...")
        await _send_top(query.message, is_callback=True)
        
    elif data == "status":
        await query.message.edit_text("⏳ Загружаю статус...")
        await _send_status(query.message, is_callback=True)
    
    elif data == "scan_all":
        await query.message.edit_text("🔍 Сканирую 50 монет... Это займёт ~30 сек.")
        await _send_scan_results(query.message, is_callback=True)
    
    elif data == "main_menu":
        # Возврат в главное меню
        keyboard = [
            [
                InlineKeyboardButton("📊 BTC", callback_data="price_BTC/USDT"),
                InlineKeyboardButton("📊 ETH", callback_data="price_ETH/USDT"),
                InlineKeyboardButton("📊 SOL", callback_data="price_SOL/USDT"),
            ],
            [
                InlineKeyboardButton("🎯 Сигнал BTC", callback_data="signal_BTC/USDT"),
                InlineKeyboardButton("🎯 Сигнал ETH", callback_data="signal_ETH/USDT"),
            ],
            [
                InlineKeyboardButton("🔍 СКАН ВСЕХ 50", callback_data="scan_all"),
            ],
            [
                InlineKeyboardButton("🔝 Топ-5", callback_data="top5"),
                InlineKeyboardButton("📈 Статус", callback_data="status"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = """
🚀 *MaxFlash Trading Bot*

Добро пожаловать! Я сканирую топ-50 криптовалют.

*Команды:*
/price `BTC` - Текущая цена
/signal `ETH` - Торговый сигнал
/scan - 🔍 *Сканировать все 50 монет*
/top - Топ монет за 24ч
/alert `BTC 100000` - Установить алерт

Или используй кнопки ниже 👇
"""
        await query.message.edit_text(
            welcome_text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений (быстрые запросы цены)."""
    text = update.message.text.upper().strip()
    
    # Если это просто название монеты, показываем цену
    if len(text) <= 10 and text.isalpha():
        symbol = f"{text}/USDT"
        await _send_price(update.message, symbol)


async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Периодическая проверка алертов."""
    for user_id, alerts in list(user_alerts.items()):
        alerts_to_remove = []
        
        for alert in alerts:
            try:
                ticker = data_manager.get_ticker(alert['symbol'], exchange_id='binance')
                if not ticker:
                    continue
                
                price = ticker.get('last', 0)
                triggered = False
                
                if alert['type'] == 'above' and price >= alert['price']:
                    triggered = True
                    msg = f"🔔 *АЛЕРТ!*\n\n{alert['symbol']} выше ${alert['price']:,.2f}\nТекущая цена: `${price:,.2f}`"
                elif alert['type'] == 'below' and price <= alert['price']:
                    triggered = True
                    msg = f"🔔 *АЛЕРТ!*\n\n{alert['symbol']} ниже ${alert['price']:,.2f}\nТекущая цена: `${price:,.2f}`"
                
                if triggered:
                    await context.bot.send_message(user_id, msg, parse_mode='Markdown')
                    alerts_to_remove.append(alert)
                    
            except Exception as e:
                logger.error(f"Ошибка проверки алерта: {e}")
        
        # Удаляем сработавшие алерты
        for alert in alerts_to_remove:
            alerts.remove(alert)


def main():
    """Запуск бота."""
    print("🤖 Starting MaxFlash Telegram Bot...")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", get_price))
    application.add_handler(CommandHandler("p", get_price))  # Короткая версия
    application.add_handler(CommandHandler("signal", get_signal))
    application.add_handler(CommandHandler("s", get_signal))  # Короткая версия
    application.add_handler(CommandHandler("top", get_top))
    application.add_handler(CommandHandler("scan", scan_all_coins))  # Сканирование всех монет
    application.add_handler(CommandHandler("alert", set_alert))
    application.add_handler(CommandHandler("status", get_status))
    
    # Обработчик callback кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений (для быстрых запросов)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Периодическая проверка алертов (каждые 30 секунд)
    application.job_queue.run_repeating(check_alerts, interval=30, first=10)
    
    print("✅ Bot is running!")
    print("📱 Open Telegram and message the bot")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


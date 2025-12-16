"""
MaxFlash Telegram Bot v2.0
Улучшенный интерфейс с выбором монет.
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
signal_scanner = SignalScanner(data_manager=data_manager)

# ======================== КАТЕГОРИИ МОНЕТ ========================
COINS_TOP = ["BTC", "ETH", "BNB", "SOL", "XRP"]
COINS_LAYER1 = ["ADA", "AVAX", "DOT", "ATOM", "NEAR", "APT", "SUI"]
COINS_DEFI = ["UNI", "AAVE", "LINK", "MKR", "CRV", "LDO", "SNX"]
COINS_MEME = ["DOGE", "WIF", "PEPE", "SHIB", "FLOKI", "BONK"]
COINS_AI = ["FET", "RENDER", "AGIX", "OCEAN", "TAO"]
COINS_GAMING = ["AXS", "SAND", "MANA", "IMX", "GALA", "ENJ"]
COINS_OTHER = ["LTC", "TRX", "XLM", "ALGO", "FIL", "ARB", "OP"]

ALL_COINS = COINS_TOP + COINS_LAYER1 + COINS_DEFI + COINS_MEME + COINS_AI + COINS_GAMING + COINS_OTHER

# Хранилище состояний пользователей
user_states = {}  # {user_id: {'last_action': ..., 'page': ...}}


# ======================== КЛАВИАТУРЫ ========================

def get_main_menu_keyboard():
    """Главное меню."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Цена", callback_data="menu_price"),
            InlineKeyboardButton("🎯 Сигнал", callback_data="menu_signal"),
        ],
        [
            InlineKeyboardButton("🔍 СКАН 50 МОНЕТ", callback_data="scan_all"),
        ],
        [
            InlineKeyboardButton("🔝 Топ-5 24ч", callback_data="top5"),
            InlineKeyboardButton("📈 Статус", callback_data="status"),
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
        ]
    ])


def get_coin_categories_keyboard(action: str):
    """Выбор категории монет."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ ТОП-5", callback_data=f"cat_{action}_top"),
            InlineKeyboardButton("🔷 Layer-1", callback_data=f"cat_{action}_l1"),
        ],
        [
            InlineKeyboardButton("💎 DeFi", callback_data=f"cat_{action}_defi"),
            InlineKeyboardButton("🐕 Meme", callback_data=f"cat_{action}_meme"),
        ],
        [
            InlineKeyboardButton("🤖 AI", callback_data=f"cat_{action}_ai"),
            InlineKeyboardButton("🎮 Gaming", callback_data=f"cat_{action}_gaming"),
        ],
        [
            InlineKeyboardButton("📋 Другие", callback_data=f"cat_{action}_other"),
            InlineKeyboardButton("🔤 Все A-Z", callback_data=f"cat_{action}_all"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
        ]
    ])


def get_coins_keyboard(coins: list, action: str, category: str):
    """Генерирует клавиатуру с монетами (по 3 в ряд)."""
    keyboard = []
    row = []
    for coin in coins:
        emoji = "💰" if action == "price" else "🎯"
        row.append(InlineKeyboardButton(f"{emoji} {coin}", callback_data=f"{action}_{coin}/USDT"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton("◀️ Категории", callback_data=f"menu_{action}"),
        InlineKeyboardButton("🏠 Меню", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(extra_buttons=None):
    """Клавиатура с кнопкой назад."""
    keyboard = extra_buttons or []
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


# ======================== КОМАНДЫ ========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение."""
    welcome_text = """
🚀 *MaxFlash Trading Bot*

Добро пожаловать! Я анализирую *50 криптовалют* и генерирую торговые сигналы на основе AI.

*Быстрые команды:*
• `/p btc` - цена BTC
• `/s eth` - сигнал ETH  
• `/scan` - скан всех монет

Выбери действие 👇
"""
    await update.message.reply_text(
        welcome_text, 
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )


async def quick_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрая команда /p для цены."""
    if context.args:
        symbol = context.args[0].upper()
        if "/" not in symbol:
            symbol = f"{symbol}/USDT"
        await send_price(update.message, symbol)
    else:
        await update.message.reply_text(
            "💰 *Цена*\n\nИспользование: `/p btc` или `/p sol`",
            parse_mode='Markdown',
            reply_markup=get_coin_categories_keyboard("price")
        )


async def quick_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрая команда /s для сигнала."""
    if context.args:
        symbol = context.args[0].upper()
        if "/" not in symbol:
            symbol = f"{symbol}/USDT"
        await send_signal(update.message, symbol)
    else:
        await update.message.reply_text(
            "🎯 *Сигнал*\n\nИспользование: `/s btc` или `/s eth`",
            parse_mode='Markdown',
            reply_markup=get_coin_categories_keyboard("signal")
        )


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /scan."""
    await send_scan_results(update.message)


# ======================== ОТПРАВКА ДАННЫХ ========================

async def send_price(message, symbol: str, edit=False):
    """Отправляет цену монеты."""
    try:
        if not edit:
            status_msg = await message.reply_text("⏳ Загружаю...")
        else:
            status_msg = message
            await status_msg.edit_text("⏳ Загружаю...")
        
        ticker = data_manager.get_ticker(symbol, exchange_id='binance')
        
        if ticker:
            price = ticker.get('last', 0)
            change = ticker.get('percentage', 0) or 0
            high = ticker.get('high', 0)
            low = ticker.get('low', 0)
            volume = ticker.get('quoteVolume', 0) or ticker.get('baseVolume', 0) * price
            
            if change > 0:
                emoji, arrow = "🟢", "▲"
            elif change < 0:
                emoji, arrow = "🔴", "▼"
            else:
                emoji, arrow = "⚪", "■"
            
            coin = symbol.replace('/USDT', '')
            
            text = f"""
{emoji} *{coin}* / USDT

💰 Цена: `${price:,.4f}`
📊 24ч: {arrow} `{change:+.2f}%`

📈 High: `${high:,.4f}`
📉 Low: `${low:,.4f}`
💎 Volume: `${volume/1e6:,.1f}M`

🕐 {datetime.now().strftime('%H:%M:%S')}
"""
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Обновить", callback_data=f"price_{symbol}"),
                    InlineKeyboardButton("🎯 Сигнал", callback_data=f"signal_{symbol}"),
                ],
                [
                    InlineKeyboardButton("💰 Другая монета", callback_data="menu_price"),
                    InlineKeyboardButton("🏠 Меню", callback_data="main_menu"),
                ]
            ]
            await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await status_msg.edit_text(f"❌ Не удалось получить данные для {symbol}")
            
    except Exception as e:
        logger.error(f"Ошибка цены {symbol}: {e}")
        if edit:
            await message.edit_text(f"❌ Ошибка: {str(e)}")
        else:
            await message.reply_text(f"❌ Ошибка: {str(e)}")


async def send_signal(message, symbol: str, edit=False):
    """Отправляет сигнал для монеты."""
    try:
        if not edit:
            status_msg = await message.reply_text("🔍 Анализирую...")
        else:
            status_msg = message
            await status_msg.edit_text("🔍 Анализирую...")
        
        signal = signal_scanner.scan_single(symbol)
        coin = symbol.replace('/USDT', '')
        
        if signal:
            if signal.signal_type == "LONG":
                emoji = "🟢"
                direction = "LONG (Покупка)"
            else:
                emoji = "🔴"
                direction = "SHORT (Продажа)"
            
            rr_ratio = signal.risk_reward
            
            text = f"""
{emoji} *СИГНАЛ {direction}*

📍 *{coin}/USDT* ({signal.timeframe})

🎯 Entry: `${signal.entry_price:,.4f}`
✅ Take Profit: `${signal.take_profit:,.4f}`
🛑 Stop Loss: `${signal.stop_loss:,.4f}`

📊 Confidence: `{signal.confidence:.0%}`
⚖️ Risk/Reward: `1:{rr_ratio:.1f}`

📋 *Индикаторы:*
• {chr(10).join(['✓ ' + ind for ind in signal.indicators[:4]])}

⚠️ _Это не финансовый совет_
"""
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Обновить", callback_data=f"signal_{symbol}"),
                    InlineKeyboardButton("💰 Цена", callback_data=f"price_{symbol}"),
                ],
                [
                    InlineKeyboardButton("🎯 Другая монета", callback_data="menu_signal"),
                    InlineKeyboardButton("🏠 Меню", callback_data="main_menu"),
                ]
            ]
        else:
            text = f"""
⏸️ *Нет сигнала для {coin}*

Условия не соответствуют критериям входа.

💡 Попробуй:
• 🔍 Скан всех монет
• 🎯 Сигнал для другой монеты
"""
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Обновить", callback_data=f"signal_{symbol}"),
                    InlineKeyboardButton("🔍 Скан всех", callback_data="scan_all"),
                ],
                [
                    InlineKeyboardButton("🎯 Другая монета", callback_data="menu_signal"),
                    InlineKeyboardButton("🏠 Меню", callback_data="main_menu"),
                ]
            ]
        
        await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            
    except Exception as e:
        logger.error(f"Ошибка сигнала {symbol}: {e}")
        if edit:
            await message.edit_text(f"❌ Ошибка: {str(e)}")
        else:
            await message.reply_text(f"❌ Ошибка: {str(e)}")


async def send_scan_results(message, edit=False):
    """Сканирует все монеты."""
    try:
        if not edit:
            status_msg = await message.reply_text("🔍 Сканирую 50 монет... ~30 сек")
        else:
            status_msg = message
            await status_msg.edit_text("🔍 Сканирую 50 монет... ~30 сек")
        
        signals = signal_scanner.scan_all()
        
        if signals:
            text = f"🔍 *Найдено сигналов: {len(signals)}*\n\n"
            
            # Топ-10 сигналов
            for i, sig in enumerate(signals[:10], 1):
                emoji = "🟢" if sig.signal_type == "LONG" else "🔴"
                coin = sig.symbol.replace('/USDT', '')
                text += f"{i}. {emoji} *{coin}* - {sig.signal_type} ({sig.confidence:.0%})\n"
            
            if len(signals) > 10:
                text += f"\n_...и ещё {len(signals) - 10} сигналов_"
            
            text += f"\n\n🕐 {datetime.now().strftime('%H:%M:%S')}"
            
            # Кнопки для топ-5 сигналов
            keyboard = []
            row = []
            for sig in signals[:6]:
                coin = sig.symbol.replace('/USDT', '')
                emoji = "🟢" if sig.signal_type == "LONG" else "🔴"
                row.append(InlineKeyboardButton(f"{emoji}{coin}", callback_data=f"signal_{sig.symbol}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
                
            keyboard.append([
                InlineKeyboardButton("🔄 Обновить", callback_data="scan_all"),
                InlineKeyboardButton("🏠 Меню", callback_data="main_menu"),
            ])
        else:
            text = """
⏸️ *Сигналов не найдено*

В данный момент нет чётких торговых возможностей.
Попробуйте позже или проверьте конкретную монету.
"""
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="scan_all")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
            ]
        
        await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Ошибка сканирования: {e}")
        if edit:
            await message.edit_text(f"❌ Ошибка: {str(e)}")


async def send_top5(message, edit=False):
    """Топ-5 монет за 24ч."""
    try:
        if not edit:
            status_msg = await message.reply_text("⏳ Загружаю...")
        else:
            status_msg = message
            await status_msg.edit_text("⏳ Загружаю...")
        
        results = []
        for coin in COINS_TOP + COINS_LAYER1[:5]:
            symbol = f"{coin}/USDT"
            ticker = data_manager.get_ticker(symbol, exchange_id='binance')
            if ticker:
                results.append({
                    'coin': coin,
                    'price': ticker.get('last', 0),
                    'change': ticker.get('percentage', 0) or 0
                })
        
        results.sort(key=lambda x: x['change'], reverse=True)
        
        text = "🔝 *Топ монет за 24ч*\n\n"
        
        for i, item in enumerate(results[:10], 1):
            if item['change'] > 0:
                emoji, arrow = "🟢", "▲"
            elif item['change'] < 0:
                emoji, arrow = "🔴", "▼"
            else:
                emoji, arrow = "⚪", "■"
            
            text += f"{i}. {emoji} *{item['coin']}*: `${item['price']:,.2f}` {arrow}`{item['change']:+.2f}%`\n"
        
        text += f"\n🕐 {datetime.now().strftime('%H:%M:%S')}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="top5")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        ]
        
        await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Ошибка топа: {e}")


async def send_status(message, edit=False):
    """Статус системы."""
    try:
        if not edit:
            status_msg = await message.reply_text("⏳ Проверяю...")
        else:
            status_msg = message
        
        # Проверяем подключения
        btc_ticker = data_manager.get_ticker("BTC/USDT", exchange_id='binance')
        
        text = f"""
📈 *Статус MaxFlash*

🟢 Бот: *Онлайн*
🟢 Binance: *{'Подключен' if btc_ticker else 'Ошибка'}*
🟢 AI Модель: *Активна*

📊 Отслеживается: *50 монет*
⏱️ Таймфрейм: *15m*

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="status")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        ]
        
        await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Ошибка статуса: {e}")


# ======================== ОБРАБОТЧИК CALLBACK ========================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на inline кнопки."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    message = query.message
    
    logger.info(f"Callback: {data}")
    
    # Главное меню
    if data == "main_menu":
        text = """
🚀 *MaxFlash Trading Bot*

Выбери действие 👇
"""
        await message.edit_text(text, parse_mode='Markdown', reply_markup=get_main_menu_keyboard())
    
    # Меню выбора монеты для цены
    elif data == "menu_price":
        text = "💰 *Выбери категорию монет:*"
        await message.edit_text(text, parse_mode='Markdown', reply_markup=get_coin_categories_keyboard("price"))
    
    # Меню выбора монеты для сигнала
    elif data == "menu_signal":
        text = "🎯 *Выбери категорию монет:*"
        await message.edit_text(text, parse_mode='Markdown', reply_markup=get_coin_categories_keyboard("signal"))
    
    # Категории монет
    elif data.startswith("cat_"):
        parts = data.split("_")
        action = parts[1]  # price или signal
        category = parts[2]  # top, l1, defi, etc.
        
        coins_map = {
            "top": COINS_TOP,
            "l1": COINS_LAYER1,
            "defi": COINS_DEFI,
            "meme": COINS_MEME,
            "ai": COINS_AI,
            "gaming": COINS_GAMING,
            "other": COINS_OTHER,
            "all": sorted(ALL_COINS),
        }
        
        category_names = {
            "top": "⭐ ТОП-5",
            "l1": "🔷 Layer-1",
            "defi": "💎 DeFi",
            "meme": "🐕 Meme",
            "ai": "🤖 AI",
            "gaming": "🎮 Gaming",
            "other": "📋 Другие",
            "all": "🔤 Все монеты",
        }
        
        coins = coins_map.get(category, COINS_TOP)
        action_text = "💰 Цена" if action == "price" else "🎯 Сигнал"
        text = f"{action_text} - {category_names.get(category, category)}\n\nВыбери монету:"
        
        await message.edit_text(text, parse_mode='Markdown', reply_markup=get_coins_keyboard(coins, action, category))
    
    # Цена конкретной монеты
    elif data.startswith("price_"):
        symbol = data.replace("price_", "")
        await send_price(message, symbol, edit=True)
    
    # Сигнал конкретной монеты
    elif data.startswith("signal_"):
        symbol = data.replace("signal_", "")
        await send_signal(message, symbol, edit=True)
    
    # Сканирование всех
    elif data == "scan_all":
        await send_scan_results(message, edit=True)
    
    # Топ-5
    elif data == "top5":
        await send_top5(message, edit=True)
    
    # Статус
    elif data == "status":
        await send_status(message, edit=True)
    
    # Настройки
    elif data == "settings":
        text = """
⚙️ *Настройки*

Пока доступны только базовые команды.

В будущих версиях:
• Выбор биржи
• Настройка алертов
• Персональный портфель
"""
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        await message.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


# ======================== ОБРАБОТЧИК ТЕКСТА ========================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения как запросы монет."""
    text = update.message.text.upper().strip()
    
    # Если это похоже на тикер монеты
    if len(text) <= 10 and text.isalpha():
        symbol = f"{text}/USDT"
        # Проверяем, существует ли такая монета
        if text in ALL_COINS or text in ["BTC", "ETH"]:
            await send_price(update.message, symbol)
        else:
            await update.message.reply_text(
                f"❓ Монета *{text}* не найдена\n\nИспользуй /start для списка доступных монет",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            "❓ Не понял команду\n\nИспользуй /start для меню",
            parse_mode='Markdown'
        )


# ======================== MAIN ========================

def main():
    """Запуск бота."""
    logger.info("Starting MaxFlash Telegram Bot v2.0...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("p", quick_price))
    application.add_handler(CommandHandler("price", quick_price))
    application.add_handler(CommandHandler("s", quick_signal))
    application.add_handler(CommandHandler("signal", quick_signal))
    application.add_handler(CommandHandler("scan", scan_command))
    
    # Callback для кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Текстовые сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("Bot is running!")
    logger.info("Open Telegram and message the bot")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

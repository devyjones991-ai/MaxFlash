"""
MaxFlash Telegram Bot v2.0 - User-Friendly Edition
Senior-level signal bot with quick actions, top pairs, and beautiful formatting.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from typing import Optional, List, Dict
import structlog
import asyncio
from datetime import datetime
import ccxt

from app.config import settings
from app.database import AsyncSessionLocal

# Import new signal modules
from trading.signal_direction import SignalDirection
from trading.signal_validator import SignalQualityChecker
from trading.signal_logger import get_signal_logger
from trading.trading_config import get_coin_tier, get_confidence_threshold, requires_triple_confirmation, ALL_PAIRS

logger = structlog.get_logger()

# TOP 55 Trading Pairs (synced with dashboard + hot coins)
TOP_PAIRS = [
    # TIER 1 - Mega
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "SOL/USDT",
    # TIER 2 - Large
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
    "SHIB/USDT", "TRX/USDT", "LTC/USDT", "LINK/USDT", "NEAR/USDT",
    "UNI/USDT", "APT/USDT", "SUI/USDT", "BCH/USDT", "ETC/USDT",
    # TIER 3 - Mid + Hot
    "ATOM/USDT", "ALGO/USDT", "FTM/USDT", "AAVE/USDT", "ARB/USDT",
    "OP/USDT", "INJ/USDT", "ICP/USDT", "GALA/USDT", "CHZ/USDT",
    "LDO/USDT", "CRV/USDT", "SNX/USDT", "COMP/USDT", "MKR/USDT",
    "PEPE/USDT", "WIF/USDT", "BONK/USDT", "SAND/USDT", "MANA/USDT",
    "AXS/USDT", "EOS/USDT", "XLM/USDT", "HBAR/USDT", "FIL/USDT",
    # Extra hot coins
    "GUN/USDT", "FLOKI/USDT", "WLD/USDT", "RENDER/USDT", "THETA/USDT",
    "IMX/USDT", "RUNE/USDT", "EGLD/USDT", "FLOW/USDT", "XTZ/USDT",
    "VET/USDT", "GRT/USDT",
]

# Quick access pairs (top 10)
QUICK_PAIRS = TOP_PAIRS[:10]

# Risk management defaults (same as dashboard)
RISK_CONFIG = {
    'default_risk_pct': 1.0,    # 1% риска на сделку
    'tp1_multiplier': 1.5,      # TP1 = 1.5R
    'tp2_multiplier': 2.5,      # TP2 = 2.5R  
    'tp3_multiplier': 4.0,      # TP3 = 4R
    'default_leverage': 5,      # Плечо по умолчанию
}

# Exchange fee (Binance default)
EXCHANGE_FEE = 0.001  # 0.1%

# Supported exchanges (same as dashboard)
EXCHANGES = {
    'binance': {'name': 'Binance', 'icon': '🟡', 'fee': 0.1},
    'bybit': {'name': 'Bybit', 'icon': '🟠', 'fee': 0.1},
    'okx': {'name': 'OKX', 'icon': '⚪', 'fee': 0.08},
    'kraken': {'name': 'Kraken', 'icon': '🟣', 'fee': 0.16},
}


def fmt_price(price: float) -> str:
    """Smart price formatting - more decimals for smaller prices."""
    if price is None or price == 0:
        return "$0"
    elif price >= 1000:
        return f"${price:,.0f}"
    elif price >= 100:
        return f"${price:,.1f}"
    elif price >= 1:
        return f"${price:,.2f}"
    elif price >= 0.01:
        return f"${price:.4f}"
    elif price >= 0.0001:
        return f"${price:.6f}"
    else:
        return f"${price:.8f}"  # PEPE, BONK, SHIB etc.

class MaxFlashBotV2:
    """Enhanced Telegram Bot with user-friendly interface."""

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        if not self.token:
            logger.warning("Telegram bot token not configured")
            return

        self.application = Application.builder().token(self.token).build()
        self.exchange = ccxt.binance({'enableRateLimit': True})
        # Initialize exchanges for checking availability
        self.exchanges = {
            'binance': ccxt.binance({'enableRateLimit': True}),
            'bybit': ccxt.bybit({'enableRateLimit': True}),
            'okx': ccxt.okx({'enableRateLimit': True}),
            'kraken': ccxt.kraken({'enableRateLimit': True}),
        }
        # Store top signals for quick access
        self.cached_top_signals = []
        
        # Initialize ML model
        self.ml_model = None
        try:
            from ml.lightgbm_model import LightGBMSignalGenerator
            import os
            model_path = os.path.join(os.path.dirname(__file__), '../../models/lightgbm_quick.pkl')
            if os.path.exists(model_path):
                self.ml_model = LightGBMSignalGenerator(model_path=model_path)
                logger.info("ML model loaded successfully")
            else:
                # Try absolute path
                model_path = 'models/lightgbm_quick.pkl'
                if os.path.exists(model_path):
                    self.ml_model = LightGBMSignalGenerator(model_path=model_path)
                    logger.info("ML model loaded successfully")
                else:
                    logger.warning("ML model not found, running without ML")
        except Exception as e:
            logger.warning(f"Failed to load ML model: {e}")
        
        # Initialize signal validator and logger
        self.signal_validator = SignalQualityChecker()
        self.signal_logger = get_signal_logger()
        
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup all command handlers."""
        # Main commands
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("top", self.cmd_top_signals))
        self.application.add_handler(CommandHandler("hot", self.cmd_hot_pairs))
        self.application.add_handler(CommandHandler("scan", self.cmd_scan_market))
        self.application.add_handler(CommandHandler("price", self.cmd_price))
        self.application.add_handler(CommandHandler("signal", self.cmd_signal))
        self.application.add_handler(CommandHandler("health", self.cmd_health))
        
        # Callback handlers for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Text message handler for symbol input
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

    # ==================== COMMANDS ====================

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message with main menu."""
        user = update.effective_user
        
        welcome_text = f"""
🚀 *Добро пожаловать в MaxFlash, {user.first_name}!*

Я помогу найти лучшие торговые сигналы на крипторынке.

⚡ *Быстрые действия:*
• /top - 🏆 Топ сигналы прямо сейчас
• /hot - 🔥 Горячие пары (высокая волатильность)
• /scan - 📡 Сканировать рынок
• /price BTC - 💰 Цена монеты

📊 *Анализ:*
• /signal BTC - Полный анализ пары
• /health - Состояние системы

👇 *Или выберите пару для быстрого анализа:*
"""
        
        # Inline keyboard for pair selection
        inline_keyboard = self._create_quick_pairs_keyboard()
        # Reply keyboard for main menu (permanent buttons)
        reply_keyboard = self._create_main_menu_keyboard()
        
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=reply_keyboard
        )
        
        # Send inline keyboard separately
        await update.message.reply_text(
            "👇 *Выберите пару для анализа:*",
            parse_mode="Markdown",
            reply_markup=inline_keyboard
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help message."""
        help_text = """
📚 *MaxFlash Bot - Справка*

*Основные команды:*
/start - Главное меню
/top - Топ-10 сигналов сейчас
/hot - Горячие пары (волатильность)
/scan - Полное сканирование рынка

*Анализ пар:*
/signal BTC - Анализ BTC/USDT
/signal ETH - Анализ ETH/USDT
/price SOL - Текущая цена SOL

*Система:*
/health - Состояние системы
/help - Эта справка

*Быстрые кнопки:*
Используйте кнопки под сообщениями для мгновенного анализа популярных пар.

💡 *Совет:* Отправьте просто название монеты (BTC, ETH, SOL) для быстрого анализа!
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def cmd_top_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show top signals across TOP 50 pairs."""
        msg = await update.message.reply_text("🔍 *Сканирую ТОП 50 монет...*\n⏳ Это займёт ~30 сек", parse_mode="Markdown")
        
        # Analyze all 50 pairs
        signals = await self._analyze_multiple_pairs(TOP_PAIRS)
        
        # Cache signals for quick access
        self.cached_top_signals = signals
        
        # Separate by signal type
        buy_signals = [s for s in signals if s['signal'] == 'BUY']
        sell_signals = [s for s in signals if s['signal'] == 'SELL']
        
        # Sort by confidence
        buy_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        sell_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        text = "🏆 *ТОП СИГНАЛЫ ИЗ 50 МОНЕТ*\n\n"
        
        if buy_signals:
            text += "🟢 *ЛУЧШИЕ ДЛЯ ПОКУПКИ:*\n"
            for i, sig in enumerate(buy_signals[:5], 1):
                sym = sig['symbol'].replace('/USDT', '')
                conf = sig['confidence'] * 100
                change = sig.get('change_24h', 0)
                text += f"{i}. *{sym}* - {conf:.0f}% ({change:+.1f}%)\n"
            text += "\n"
        
        if sell_signals:
            text += "🔴 *СИГНАЛЫ НА ПРОДАЖУ:*\n"
            for i, sig in enumerate(sell_signals[:5], 1):
                sym = sig['symbol'].replace('/USDT', '')
                conf = sig['confidence'] * 100
                change = sig.get('change_24h', 0)
                text += f"{i}. *{sym}* - {conf:.0f}% ({change:+.1f}%)\n"
            text += "\n"
        
        neutral_count = len(signals) - len(buy_signals) - len(sell_signals)
        text += f"⚪ *Нейтральных:* {neutral_count} монет\n"
        text += f"\n_Всего проанализировано: {len(signals)} монет_\n"
        text += "\n💡 *Нажмите на кнопку с монетой для детального анализа*"
        
        # Create inline buttons for top signals (clickable)
        buttons = []
        top_signals = (buy_signals + sell_signals)[:8]  # Top 8 signals
        
        # Create 2 rows of 4 buttons each
        for i in range(0, len(top_signals), 4):
            row = []
            for sig in top_signals[i:i+4]:
                sym = sig['symbol'].replace('/USDT', '')
                emoji = "🟢" if sig['signal'] == 'BUY' else "🔴"
                row.append(InlineKeyboardButton(f"{emoji}{sym}", callback_data=f"signal_{sym}"))
            buttons.append(row)
        
        # Add action buttons
        buttons.append([
            InlineKeyboardButton("🔄 Обновить", callback_data="refresh_top"),
            InlineKeyboardButton("🔥 Горячие", callback_data="hot_pairs")
        ])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        # Set reply keyboard
        reply_keyboard = self._create_main_menu_keyboard()
        
        if hasattr(msg, 'edit_text'):
            await msg.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await msg.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
        
        # Update reply keyboard
        if update.message:
            await update.message.reply_text(
                "📱 *Используйте кнопки ниже для навигации*",
                parse_mode="Markdown",
                reply_markup=reply_keyboard
            )

    async def cmd_hot_pairs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pairs with high volatility/volume - all coins clickable."""
        await update.message.reply_text("🔥 *Ищу горячие пары...*", parse_mode="Markdown")
        
        hot_pairs = await self._get_hot_pairs()
        
        text = "🔥 *ГОРЯЧИЕ ПАРЫ*\n_(высокая волатильность)_\n\n"
        
        for i, pair in enumerate(hot_pairs[:10], 1):
            vol_emoji = "🟢" if pair['volume_ratio'] > 2 else "🟡"
            text += f"{vol_emoji} *{pair['symbol'].replace('/USDT', '')}*"
            text += f" ${pair['price']:,.4f} | {pair['change']:+.1f}%\n"
        
        text += "\n👇 *Выбери монету для сигнала:*"
        
        # Create buttons for ALL top pairs (rows of 4)
        buttons = []
        row = []
        for i, pair in enumerate(hot_pairs[:20]):
            sym = pair['symbol'].replace('/USDT', '')
            row.append(InlineKeyboardButton(f"{sym}", callback_data=f"signal_{sym}"))
            if len(row) == 4:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

    async def cmd_scan_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Full market scan."""
        msg = await update.message.reply_text(
            "📡 *СКАНИРОВАНИЕ РЫНКА*\n\n"
            "⏳ Анализирую 10 пар...",
            parse_mode="Markdown"
        )
        
        signals = await self._analyze_multiple_pairs(TOP_PAIRS)
        
        # Categorize signals
        buy_signals = [s for s in signals if s['signal'] == 'BUY']
        sell_signals = [s for s in signals if s['signal'] == 'SELL']
        neutral = [s for s in signals if s['signal'] == 'HOLD']
        
        text = "📡 *РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ*\n\n"
        
        if buy_signals:
            text += "🟢 *ПОКУПКА:*\n"
            for s in buy_signals:
                text += f"  • {s['symbol']} ({s['confidence']*100:.0f}%)\n"
            text += "\n"
        
        if sell_signals:
            text += "🔴 *ПРОДАЖА:*\n"
            for s in sell_signals:
                text += f"  • {s['symbol']} ({s['confidence']*100:.0f}%)\n"
            text += "\n"
        
        text += f"⚪ *Нейтрально:* {len(neutral)} пар\n\n"
        text += f"_Обновлено: {datetime.now().strftime('%H:%M:%S')}_"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Обновить скан", callback_data="full_scan")]
        ])
        
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

    async def cmd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get price for a symbol."""
        if not context.args:
            await update.message.reply_text("❌ Укажите монету: /price BTC")
            return
        
        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol = f"{symbol}/USDT"
        else:
            symbol = symbol.replace('USDT', '/USDT')
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            
            change = ticker.get('percentage', 0) or 0
            change_emoji = "📈" if change > 0 else "📉"
            
            text = f"""
💰 *{symbol}*

💵 Цена: *${ticker['last']:,.2f}*
{change_emoji} 24h: *{change:+.2f}%*
📊 Объем: ${ticker.get('quoteVolume', 0):,.0f}
📈 High: ${ticker.get('high', 0):,.2f}
📉 Low: ${ticker.get('low', 0):,.2f}
"""
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📊 Анализ {symbol.replace('/USDT', '')}", 
                                     callback_data=f"signal_{symbol.replace('/USDT', '')}")]
            ])
            
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Не удалось получить цену: {e}")

    async def cmd_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Full signal analysis for a pair."""
        if not context.args:
            # Show quick pairs keyboard
            keyboard = self._create_quick_pairs_keyboard()
            await update.message.reply_text(
                "📊 *Выберите пару для анализа:*",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return
        
        symbol = context.args[0].upper()
        await self._send_signal_analysis(update.message, symbol)

    async def cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """System health check."""
        try:
            from services.monitoring.health_monitor import get_health_monitor
            monitor = get_health_monitor()
            report = monitor.format_health_report()
            await update.message.reply_text(report, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка мониторинга: {e}")

    # ==================== CALLBACKS ====================

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("signal_"):
            symbol = data.replace("signal_", "")
            await self._send_signal_analysis(query.message, symbol, edit=True)
        
        elif data == "refresh_top":
            await query.answer("🔄 Обновляю топ сигналы...")
            await query.message.edit_text("🔍 *Обновляю топ сигналы...*", parse_mode="Markdown")
            
            # Analyze and cache
            signals = await self._analyze_multiple_pairs(TOP_PAIRS)
            self.cached_top_signals = signals
            
            # Separate by signal type
            buy_signals = [s for s in signals if s['signal'] == 'BUY']
            sell_signals = [s for s in signals if s['signal'] == 'SELL']
            
            buy_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            sell_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            text = "🏆 *ТОП СИГНАЛЫ ИЗ 50 МОНЕТ*\n\n"
            
            if buy_signals:
                text += "🟢 *ЛУЧШИЕ ДЛЯ ПОКУПКИ:*\n"
                for i, sig in enumerate(buy_signals[:5], 1):
                    sym = sig['symbol'].replace('/USDT', '')
                    conf = sig['confidence'] * 100
                    change = sig.get('change_24h', 0)
                    text += f"{i}. *{sym}* - {conf:.0f}% ({change:+.1f}%)\n"
                text += "\n"
            
            if sell_signals:
                text += "🔴 *СИГНАЛЫ НА ПРОДАЖУ:*\n"
                for i, sig in enumerate(sell_signals[:5], 1):
                    sym = sig['symbol'].replace('/USDT', '')
                    conf = sig['confidence'] * 100
                    change = sig.get('change_24h', 0)
                    text += f"{i}. *{sym}* - {conf:.0f}% ({change:+.1f}%)\n"
                text += "\n"
            
            text += f"_Обновлено: {datetime.now().strftime('%H:%M:%S')}_\n"
            text += "\n💡 *Нажмите на кнопку с монетой для детального анализа*"
            
            # Create inline buttons
            buttons = []
            top_signals = (buy_signals + sell_signals)[:8]
            for i in range(0, len(top_signals), 4):
                row = []
                for sig in top_signals[i:i+4]:
                    sym = sig['symbol'].replace('/USDT', '')
                    emoji = "🟢" if sig['signal'] == 'BUY' else "🔴"
                    row.append(InlineKeyboardButton(f"{emoji}{sym}", callback_data=f"signal_{sym}"))
                buttons.append(row)
            
            buttons.append([
                InlineKeyboardButton("🔄 Обновить", callback_data="refresh_top"),
                InlineKeyboardButton("🏠 Меню", callback_data="back_menu")
            ])
            
            keyboard = InlineKeyboardMarkup(buttons)
            await query.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
        
        elif data == "hot_pairs":
            await query.answer("🔥 Загружаю горячие пары...")
            await query.message.edit_text("🔥 *Ищу горячие пары...*", parse_mode="Markdown")
            
            hot_pairs = await self._get_hot_pairs()
            
            text = "🔥 *ГОРЯЧИЕ ПАРЫ*\n_(высокая волатильность/объем)_\n\n"
            
            for i, pair in enumerate(hot_pairs[:8], 1):
                vol_emoji = "🟢" if pair['volume_ratio'] > 2 else "🟡"
                text += f"{vol_emoji} *{pair['symbol']}*\n"
                text += f"   💰 ${pair['price']:,.2f} | 📊 Vol: {pair['volume_ratio']:.1f}x\n"
                text += f"   📈 24h: {pair['change']:+.2f}%\n\n"
            
            buttons = []
            for i in range(0, len(hot_pairs[:8]), 4):
                row = []
                for pair in hot_pairs[i:i+4]:
                    sym = pair['symbol'].replace('/USDT', '')
                    row.append(InlineKeyboardButton(f"📊 {sym}", callback_data=f"signal_{sym}"))
                buttons.append(row)
            
            buttons.append([
                InlineKeyboardButton("🔄 Обновить", callback_data="hot_pairs"),
                InlineKeyboardButton("🏠 Меню", callback_data="back_menu")
            ])
            
            keyboard = InlineKeyboardMarkup(buttons)
            await query.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
        
        elif data == "full_scan":
            await query.answer("📡 Сканирую рынок...")
            await query.message.edit_text("📡 *Сканирую рынок...*", parse_mode="Markdown")
            # Trigger full scan
            signals = await self._analyze_multiple_pairs(TOP_PAIRS)
            buy = [s for s in signals if s['signal'] == 'BUY']
            sell = [s for s in signals if s['signal'] == 'SELL']
            
            text = f"📡 *СКАН ЗАВЕРШЕН*\n\n🟢 Покупка: {len(buy)}\n🔴 Продажа: {len(sell)}\n"
            text += f"\n_Обновлено: {datetime.now().strftime('%H:%M:%S')}_"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Меню", callback_data="back_menu")]
            ])
            await query.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
        
        elif data == "back_menu":
            await query.message.reply_text(
                "🏠 *Возвращаемся в главное меню...*",
                parse_mode="Markdown",
                reply_markup=self._create_main_menu_keyboard()
            )
            await self.cmd_start(update, context)

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages - buttons and symbols."""
        text = update.message.text.strip()
        text_upper = text.upper()
        
        # Handle menu buttons
        if text == "🏆 Топ сигналы" or text == "Топ сигналы":
            await self.cmd_top_signals(update, context)
            return
        elif text == "🔥 Горячие пары" or text == "Горячие пары":
            await self.cmd_hot_pairs(update, context)
            return
        elif text == "📡 Сканировать" or text == "Сканировать":
            await self.cmd_scan_market(update, context)
            return
        elif text == "🏠 Главное меню" or text == "Главное меню" or text == "Назад":
            await self.cmd_start(update, context)
            return
        
        # Handle numbered signals (e.g., "1", "2" for top signals)
        # But skip if it's a menu button command
        if text.isdigit() and self.cached_top_signals and text not in ["1", "2", "3", "4"]:
            idx = int(text) - 1
            # Filter only BUY and SELL signals (not HOLD)
            active_signals = [s for s in self.cached_top_signals if s['signal'] in ['BUY', 'SELL']]
            if 0 <= idx < len(active_signals):
                signal = active_signals[idx]
                symbol = signal['symbol'].replace('/USDT', '')
                await self._send_signal_analysis(update.message, symbol)
                return
        
        # Check if it looks like a symbol
        if len(text_upper) <= 10 and text_upper.isalpha():
            await self._send_signal_analysis(update.message, text_upper)
        else:
            await update.message.reply_text(
                "❓ Не понял. Отправьте название монеты (BTC, ETH, SOL) или используйте кнопки меню",
                reply_markup=self._create_main_menu_keyboard()
            )

    # ==================== HELPERS ====================

    def _create_main_menu_keyboard(self) -> ReplyKeyboardMarkup:
        """Create main menu keyboard (permanent buttons at bottom)."""
        keyboard = [
            ["🏆 Топ сигналы", "🔥 Горячие пары"],
            ["📡 Сканировать", "🏠 Главное меню"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def _create_quick_pairs_keyboard(self) -> InlineKeyboardMarkup:
        """Create keyboard with quick pair buttons."""
        buttons = []
        row = []
        for pair in TOP_PAIRS[:8]:
            sym = pair.replace('/USDT', '')
            row.append(InlineKeyboardButton(sym, callback_data=f"signal_{sym}"))
            if len(row) == 4:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        buttons.append([
            InlineKeyboardButton("🔄 Обновить", callback_data="refresh_top"),
            InlineKeyboardButton("🏠 Меню", callback_data="back_menu")
        ])
        
        return InlineKeyboardMarkup(buttons)

    def _get_signal_emoji(self, signal: str) -> str:
        """Get emoji for signal type."""
        return {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(signal, "⚪")

    async def _analyze_multiple_pairs(self, pairs: List[str]) -> List[Dict]:
        """Analyze multiple pairs and return signals."""
        results = []
        
        for pair in pairs:
            try:
                signal = await self._get_signal_for_pair(pair)
                if signal:
                    results.append(signal)
            except Exception as e:
                logger.error(f"Error analyzing {pair}: {e}")
        
        return results

    async def _get_signal_for_pair(self, symbol: str) -> Optional[Dict]:
        """Get signal for a single pair. SYNCED WITH DASHBOARD LOGIC."""
        try:
            if not symbol.endswith('/USDT'):
                symbol = f"{symbol}/USDT"
            
            # Get ticker data
            ticker = self.exchange.fetch_ticker(symbol)
            
            # Get OHLCV for analysis
            ohlcv = self.exchange.fetch_ohlcv(symbol, '15m', limit=100)
            
            if not ohlcv:
                return None
            
            import pandas as pd
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            close = df['close']
            
            # === SIGNAL SCORING (SAME AS DASHBOARD) ===
            buy_score = 0
            sell_score = 0
            reasons = []
            
            # 1. Price change (24h)
            change_24h = ticker.get('percentage', 0) or 0
            
            if change_24h <= -5:
                sell_score += 30
                reasons.append(f"📉 {change_24h:.1f}%")
            elif change_24h <= -2:
                sell_score += 20
                reasons.append(f"📉 {change_24h:.1f}%")
            elif change_24h <= -0.5:
                sell_score += 10
            elif change_24h >= 5:
                buy_score += 30
                reasons.append(f"📈 {change_24h:+.1f}%")
            elif change_24h >= 2:
                buy_score += 20
                reasons.append(f"📈 {change_24h:+.1f}%")
            elif change_24h >= 0.5:
                buy_score += 10
            
            # 2. RSI
            if len(df) >= 14:
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / (loss + 1e-10)
                rsi_series = 100 - (100 / (1 + rs))
                current_rsi = rsi_series.iloc[-1]
                rsi_prev = rsi_series.iloc[-2] if len(rsi_series) > 1 else current_rsi
                rsi_trend = current_rsi - rsi_prev
                
                if current_rsi < 30:
                    buy_score += 25
                    reasons.append(f"RSI {current_rsi:.0f}")
                elif current_rsi < 40:
                    buy_score += 15
                    reasons.append(f"RSI {current_rsi:.0f}↓")
                elif current_rsi > 70:
                    sell_score += 25
                    reasons.append(f"RSI {current_rsi:.0f}")
                elif current_rsi > 60:
                    sell_score += 15
                    reasons.append(f"RSI {current_rsi:.0f}↑")
                elif current_rsi < 45 and rsi_trend < 0:
                    sell_score += 10
                    reasons.append(f"RSI {current_rsi:.0f}⬇")
                elif current_rsi > 55 and rsi_trend > 0:
                    buy_score += 10
                    reasons.append(f"RSI {current_rsi:.0f}⬆")
            else:
                current_rsi = 50
            
            # 3. MACD (8-17-9)
            ema_fast = close.ewm(span=8, adjust=False).mean()
            ema_slow = close.ewm(span=17, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            
            macd = macd_line.iloc[-1]
            macd_prev = macd_line.iloc[-2] if len(macd_line) > 1 else macd
            signal = signal_line.iloc[-1]
            signal_prev = signal_line.iloc[-2] if len(signal_line) > 1 else signal
            
            macd_bullish = macd_prev < signal_prev and macd > signal
            macd_bearish = macd_prev > signal_prev and macd < signal
            
            if macd_bullish:
                buy_score += 25
                reasons.append("MACD⬆")
            elif macd_bearish:
                sell_score += 25
                reasons.append("MACD⬇")
            elif macd > signal:
                buy_score += 10
                reasons.append("MACD+")
            elif macd < signal:
                sell_score += 10
                reasons.append("MACD-")
            
            # 4. Price vs MA
            price = close.iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else ma20
            
            if price > ma20 > ma50:
                buy_score += 15
                reasons.append("Тренд⬆")
            elif price < ma20 < ma50:
                sell_score += 15
                reasons.append("Тренд⬇")
            elif price < ma20:
                sell_score += 5
            elif price > ma20:
                buy_score += 5
            
            # === 5. ML MODEL PREDICTION (HYBRID) ===
            ml_signal = None
            ml_conf = 0
            if self.ml_model:
                try:
                    ml_pred = self.ml_model.predict(df)
                    ml_signal = ml_pred.get('action', 'HOLD')
                    ml_conf = ml_pred.get('confidence', 0.5)
                    
                    # ML score boost based on agreement
                    score_direction = "BUY" if buy_score > sell_score else ("SELL" if sell_score > buy_score else "HOLD")
                    
                    if ml_signal == "BUY" and ml_conf > 0.55:
                        if score_direction == "BUY":
                            # Agreement - strong boost
                            buy_score += 25
                            reasons.append(f"🤖ML:{ml_conf:.0%}")
                        else:
                            # ML alone - moderate boost
                            buy_score += 15
                            reasons.append(f"🤖ML BUY")
                    elif ml_signal == "SELL" and ml_conf > 0.55:
                        if score_direction == "SELL":
                            # Agreement - strong boost
                            sell_score += 25
                            reasons.append(f"🤖ML:{ml_conf:.0%}")
                        else:
                            # ML alone - moderate boost
                            sell_score += 15
                            reasons.append(f"🤖ML SELL")
                except Exception as e:
                    logger.debug(f"ML prediction failed: {e}")
            
            # === CALCULATE CONFIDENCE ===
            max_score = max(buy_score, sell_score)
            
            if max_score >= 60:
                confidence = 0.85
            elif max_score >= 45:
                confidence = 0.75
            elif max_score >= 30:
                confidence = 0.60
            elif max_score >= 20:
                confidence = 0.50
            else:
                confidence = 0.40
            
            # === DETERMINE SIGNAL (SAME AS DASHBOARD) ===
            diff = buy_score - sell_score
            
            if diff >= 20:
                signal_type = "BUY"
            elif diff <= -20:
                signal_type = "SELL"
            elif diff >= 10:
                signal_type = "BUY"
                confidence = min(confidence, 0.55)
            elif diff <= -10:
                signal_type = "SELL"
                confidence = min(confidence, 0.55)
            elif diff > 0:
                signal_type = "BUY"
                confidence = min(confidence, 0.45)
            elif diff < 0:
                signal_type = "SELL"
                confidence = min(confidence, 0.45)
            else:
                signal_type = "HOLD"
                confidence = 0.50
            
            # === 6. USE SignalDirection FOR CORRECT BUY/SELL ===
            # Override signal based on RSI rules (RSI < 30 = BUY, RSI > 70 = SELL)
            macd_histogram = macd - signal
            price_trend = "uptrend" if price > ma20 else ("downtrend" if price < ma20 else "neutral")
            
            direction, confidence_adj, direction_reason = SignalDirection.determine_direction(
                rsi=current_rsi,
                macd_histogram=macd_histogram,
                macd_line=macd,
                signal_line=signal,
                price_trend=price_trend,
                confidence=confidence * 100
            )
            
            # Apply direction result
            if direction != "NEUTRAL":
                signal_type = direction
                confidence = min(1.0, confidence + (confidence_adj / 100))
                if direction_reason not in reasons:
                    reasons.insert(0, direction_reason.split("=")[0].strip())
            
            # === 7. VALIDATE SIGNAL FOR CONTRADICTIONS ===
            volume_ratio = ticker.get('quoteVolume', 0) / 1_000_000  # Simplified ratio
            
            validation = self.signal_validator.validate_and_fix(
                symbol=symbol,
                signal_direction=signal_type,
                confidence=confidence * 100,
                rsi=current_rsi,
                macd_histogram=macd_histogram,
                price_change_24h=change_24h,
                volume_ratio=min(2.0, volume_ratio / 100) if volume_ratio > 0 else 1.0
            )
            
            # Apply validation result
            if validation['was_inverted']:
                signal_type = validation['final_signal']
                reasons.insert(0, "🔄 INVERTED")
            
            confidence = validation['final_confidence'] / 100
            
            # === 8. GET TIER (for info only, don't override signal) ===
            tier = get_coin_tier(symbol)
            # NOTE: We don't apply threshold here - let users see all signals
            # Threshold filtering was too aggressive and didn't match dashboard
            
            # Log the signal
            try:
                self.signal_logger.log_signal(
                    symbol=symbol,
                    tier=tier,
                    signal_direction=signal_type,
                    confidence=confidence * 100,
                    rsi=current_rsi,
                    macd=macd_histogram,
                    price_change_24h=change_24h,
                    volume_ratio=volume_ratio,
                    validation_result=validation
                )
            except Exception as log_err:
                logger.debug(f"Logging failed: {log_err}")
            
            return {
                'symbol': symbol,
                'signal': signal_type,
                'confidence': confidence,
                'price': ticker['last'],
                'change_24h': change_24h,
                'rsi': current_rsi,
                'volume': ticker.get('quoteVolume', 0),
                'reasons': reasons,
                'macd_bullish': macd > signal,
                'ma_trend': 'up' if price > ma20 else 'down',
                'buy_score': buy_score,
                'sell_score': sell_score,
                'tier': tier,
                'was_inverted': validation['was_inverted'],
                'issues': validation.get('issues', []),
            }
            
        except Exception as e:
            logger.error(f"Error getting signal for {symbol}: {e}")
            return None

    async def _get_hot_pairs(self) -> List[Dict]:
        """Get pairs with high volatility/volume."""
        try:
            tickers = self.exchange.fetch_tickers()
            
            hot = []
            for symbol, ticker in tickers.items():
                if not symbol.endswith('/USDT'):
                    continue
                if ticker.get('quoteVolume', 0) < 1000000:  # Min $1M volume
                    continue
                
                # Calculate volume ratio (current vs average)
                volume_ratio = 1.0
                if ticker.get('quoteVolume'):
                    # Simplified: just use percentage change as proxy
                    change = abs(ticker.get('percentage', 0) or 0)
                    volume_ratio = 1 + (change / 10)
                
                hot.append({
                    'symbol': symbol,
                    'price': ticker.get('last', 0),
                    'change': ticker.get('percentage', 0) or 0,
                    'volume': ticker.get('quoteVolume', 0),
                    'volume_ratio': volume_ratio,
                })
            
            # Sort by volume_ratio
            hot.sort(key=lambda x: x['volume_ratio'], reverse=True)
            return hot[:10]
            
        except Exception as e:
            logger.error(f"Error getting hot pairs: {e}")
            return []

    def _calculate_full_signal(self, symbol: str, price: float, signal: str, signal_score: float,
                               change: float, volume: float, reasons: list,
                               deposit: float = 1000, risk_pct: float = 1.0,
                               exchange_fee: float = EXCHANGE_FEE) -> dict:
        """
        Calculate full trading signal with entry, TP levels, SL, position size.
        Same logic as dashboard calculate_full_signal.
        """
        if signal == 'HOLD':
            return None
        
        # ATR approximation based on 24h change
        atr_estimate = price * abs(change) / 100 * 0.5  # Half of daily range
        if atr_estimate < price * 0.005:
            atr_estimate = price * 0.005  # Minimum 0.5% ATR
        
        if signal == 'BUY':
            entry = price
            sl = price - (atr_estimate * 1.5)  # 1.5 ATR stop loss
            sl_distance = entry - sl
            
            tp1 = entry + (sl_distance * RISK_CONFIG['tp1_multiplier'])
            tp2 = entry + (sl_distance * RISK_CONFIG['tp2_multiplier'])
            tp3 = entry + (sl_distance * RISK_CONFIG['tp3_multiplier'])
            
        else:  # SELL
            entry = price
            sl = price + (atr_estimate * 1.5)
            sl_distance = sl - entry
            
            tp1 = entry - (sl_distance * RISK_CONFIG['tp1_multiplier'])
            tp2 = entry - (sl_distance * RISK_CONFIG['tp2_multiplier'])
            tp3 = entry - (sl_distance * RISK_CONFIG['tp3_multiplier'])
        
        # Risk/Reward calculation
        risk_reward = RISK_CONFIG['tp2_multiplier']  # Based on TP2
        
        # Position sizing
        risk_amount = deposit * (risk_pct / 100)
        position_size_usd = risk_amount / (abs(entry - sl) / entry)
        position_size_usd = min(position_size_usd, deposit * 0.3)  # Max 30% of deposit
        
        # Quantity
        quantity = position_size_usd / entry
        
        # Расчет комиссий
        commission_entry = position_size_usd * exchange_fee
        # Комиссия на выходе (примерно на TP2)
        expected_profit_pct = (tp2 - entry) / entry if signal == 'BUY' else (entry - tp2) / entry
        position_value_exit = position_size_usd * (1 + expected_profit_pct)
        commission_exit = position_value_exit * exchange_fee
        total_commission = commission_entry + commission_exit
        
        return {
            'symbol': symbol,
            'signal': signal,
            'confidence': signal_score,
            'entry': entry,
            'sl': sl,
            'sl_pct': abs(entry - sl) / entry * 100,
            'tp1': tp1,
            'tp1_pct': abs(tp1 - entry) / entry * 100,
            'tp2': tp2,
            'tp2_pct': abs(tp2 - entry) / entry * 100,
            'tp3': tp3,
            'tp3_pct': abs(tp3 - entry) / entry * 100,
            'risk_reward': risk_reward,
            'position_size_usd': position_size_usd,
            'quantity': quantity,
            'change_24h': change,
            'volume': volume,
            'reasons': reasons,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            # Комиссии
            'exchange_fee_pct': exchange_fee * 100,
            'commission_entry': commission_entry,
            'commission_exit': commission_exit,
            'total_commission': total_commission,
        }

    async def _get_available_exchanges(self, symbol: str) -> List[str]:
        """Check which exchanges have this trading pair available."""
        available = []
        
        for ex_id, exchange_obj in self.exchanges.items():
            try:
                # Try to fetch ticker to check if pair exists
                ticker = exchange_obj.fetch_ticker(symbol)
                if ticker and ticker.get('last'):
                    available.append(ex_id)
            except (ccxt.ExchangeError, ccxt.NetworkError, ccxt.BaseError):
                # Pair not available on this exchange, skip
                continue
            except Exception:
                # Other errors, skip
                continue
        
        return available if available else ['binance']  # Default to Binance if none found

    async def _send_signal_analysis(self, message, symbol: str, edit: bool = False):
        """Send detailed signal analysis."""
        if not symbol.endswith('/USDT'):
            full_symbol = f"{symbol}/USDT"
        else:
            full_symbol = symbol
            symbol = symbol.replace('/USDT', '')
        
        loading_text = f"🔍 *Анализирую {symbol}...*"
        
        if edit:
            await message.edit_text(loading_text, parse_mode="Markdown")
        else:
            message = await message.reply_text(loading_text, parse_mode="Markdown")
        
        signal = await self._get_signal_for_pair(full_symbol)
        
        if not signal:
            error_text = f"❌ Не удалось получить данные для {symbol}"
            if edit:
                await message.edit_text(error_text)
            return
        
        # Calculate full signal with TP/SL levels
        full_signal = self._calculate_full_signal(
            symbol=full_symbol,
            price=signal['price'],
            signal=signal['signal'],
            signal_score=signal['confidence'],
            change=signal.get('change_24h', 0),
            volume=signal.get('volume', 0),
            reasons=signal.get('reasons', []),
            deposit=1000,  # Default deposit
            risk_pct=1.0,  # Default 1% risk
            exchange_fee=EXCHANGE_FEE
        )
        
        # Build beautiful analysis message
        emoji = self._get_signal_emoji(signal['signal'])
        conf = signal['confidence'] * 100
        change = signal.get('change_24h', 0)
        change_emoji = "📈" if change > 0 else "📉"
        
        # Signal strength bar
        bar_filled = int(conf / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        
        # Get available exchanges for this pair
        available_exchanges = await self._get_available_exchanges(full_symbol)
        exchanges_list = []
        for ex_id in available_exchanges:
            ex_info = EXCHANGES.get(ex_id, {'name': ex_id.capitalize(), 'icon': '🔷'})
            exchanges_list.append(f"{ex_info['icon']} {ex_info['name']}")
        exchanges_str = ", ".join(exchanges_list) if exchanges_list else "🟡 Binance"
        
        text = f"""
{emoji} *{full_symbol}*

📊 *СИГНАЛ: {signal['signal']}*
├ Уверенность: [{bar}] {conf:.0f}%
├ RSI: {signal.get('rsi', 0):.1f}
└ Причины: {', '.join(signal.get('reasons', [])) if signal.get('reasons') else 'Технические'}

🏢 *БИРЖИ:* {exchanges_str}

💰 *ЦЕНА*
├ Текущая: ${signal['price']:,.2f}
└ {change_emoji} 24h: {change:+.2f}%
"""
        
        # Display full signal details if available
        if full_signal and signal['signal'] != 'HOLD':
            entry = full_signal['entry']
            sl = full_signal['sl']
            sl_pct = full_signal['sl_pct']
            tp1 = full_signal['tp1']
            tp1_pct = full_signal['tp1_pct']
            tp2 = full_signal['tp2']
            tp2_pct = full_signal['tp2_pct']
            tp3 = full_signal['tp3']
            tp3_pct = full_signal['tp3_pct']
            rr = full_signal['risk_reward']
            pos_size = full_signal['position_size_usd']
            qty = full_signal['quantity']
            commission = full_signal['total_commission']
            
            text += f"""
📈 *ТОРГОВЫЕ УРОВНИ*

💰 *Entry:* ${entry:,.2f}

🎯 *Take Profit:*
├ TP1: ${tp1:,.2f} (+{tp1_pct:.1f}%) [1.5R]
├ TP2: ${tp2:,.2f} (+{tp2_pct:.1f}%) [2.5R] ⭐
└ TP3: ${tp3:,.2f} (+{tp3_pct:.1f}%) [4.0R]

🛑 *Stop Loss:*
└ SL: ${sl:,.2f} (-{sl_pct:.1f}%)

📊 *ПОЗИЦИЯ* (Депозит: $1000, Риск: 1%)
├ Размер: ${pos_size:,.2f}
├ Количество: {qty:.6f} {symbol}
├ R:R = 1:{rr:.1f}
└ Комиссия: ${commission:.2f} ({full_signal['exchange_fee_pct']:.2f}%)
"""
        elif signal['signal'] == 'HOLD':
            text += "\n⚪ *Ожидайте более четкого сигнала*\n"
        
        text += f"\n_Обновлено: {datetime.now().strftime('%H:%M:%S')}_"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Обновить", callback_data=f"signal_{symbol}"),
                InlineKeyboardButton("🏠 Меню", callback_data="back_menu")
            ]
        ])
        
        if edit:
            await message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

    def start(self):
        """Start the bot."""
        if not self.token:
            logger.error("Bot token not configured!")
            return
        logger.info("Starting MaxFlash Bot v2.0")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Run the bot."""
    bot = MaxFlashBotV2()
    bot.start()


if __name__ == "__main__":
    main()


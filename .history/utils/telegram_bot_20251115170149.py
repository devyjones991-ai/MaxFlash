"""
Telegram бот для MaxFlash Trading System.
Отправляет уведомления о ценах, рыночных событиях и позволяет управлять watchlist.
"""
import logging
import asyncio
import threading
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
import json

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        filters,
        ContextTypes
    )
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    logging.warning("python-telegram-bot не установлен. Установите: pip install python-telegram-bot")

from utils.logger_config import setup_logging
from utils.market_data_manager import MarketDataManager
from utils.market_alerts import MarketAlerts
from utils.signal_generator import SignalGenerator
from utils.profit_tracker import ProfitTracker

logger = setup_logging()


class TelegramBot:
    """
    Telegram бот для уведомлений и управления watchlist.
    """

    def __init__(
        self,
        token: str,
        data_manager: Optional[MarketDataManager] = None,
        alerts: Optional[MarketAlerts] = None,
        allowed_chat_ids: Optional[List[int]] = None,
        signal_generator: Optional[SignalGenerator] = None,
        profit_tracker: Optional[ProfitTracker] = None
    ):
        """
        Инициализация Telegram бота.

        Args:
            token: Токен Telegram бота
            data_manager: Менеджер данных рынка
            alerts: Система алертов
            allowed_chat_ids: Список разрешенных chat_id (None для всех)
            signal_generator: Генератор сигналов
            profit_tracker: Трекер профитов
        """
        if not HAS_TELEGRAM:
            raise ImportError("python-telegram-bot не установлен. Установите: pip install python-telegram-bot")

        self.token = token
        self.data_manager = data_manager or MarketDataManager()
        self.alerts = alerts
        self.allowed_chat_ids = set(allowed_chat_ids) if allowed_chat_ids else None
        self.watchlist: Dict[int, Set[str]] = {}  # chat_id -> set of symbols
        self.price_alerts: Dict[int, List[Dict[str, Any]]] = {}  # chat_id -> list of alerts
        
        # Система сигналов и профитов
        self.signal_generator = signal_generator or SignalGenerator(data_manager=self.data_manager)
        self.profit_tracker = profit_tracker or ProfitTracker(data_manager=self.data_manager)
        
        # Настройки для автоотправки сигналов
        self.auto_send_signals = True
        self.subscribed_chats: Set[int] = set()  # Чат-ы, подписанные на сигналы
        
        self.application = None
        self.is_running = False
        self.bot_thread = None

    def _is_authorized(self, chat_id: int) -> bool:
        """Проверить, авторизован ли пользователь."""
        if self.allowed_chat_ids is None:
            return True
        return chat_id in self.allowed_chat_ids

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы для использования этого бота.")
            return

        welcome_text = """
🤖 **MaxFlash Trading Bot**

Добро пожаловать! Я помогу вам отслеживать криптовалютный рынок.

**Основные команды:**
/help - Показать все команды
/watchlist - Управление отслеживаемыми монетами
/alerts - Управление уведомлениями о ценах
/price <SYMBOL> - Получить текущую цену монеты
/search <QUERY> - Найти монеты по запросу
/stats - Статистика рынка

**Примеры:**
/price BTC/USDT
/search BTC
/watchlist add BTC/USDT
/alerts add BTC/USDT 50000 above
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы.")
            return

        help_text = """
📚 **Список команд:**

**Торговые сигналы:**
/signals - Показать активные сигналы
/signals <SYMBOL> - Генерировать сигналы для пары
/profits - Показать профиты по активным сигналам
/stats - Статистика по сигналам
/subscribe - Подписаться на автоматические сигналы
/unsubscribe - Отписаться от сигналов

**Управление Watchlist:**
/watchlist - Показать отслеживаемые монеты
/watchlist add <SYMBOL> - Добавить монету
/watchlist remove <SYMBOL> - Удалить монету
/watchlist clear - Очистить весь список

**Уведомления о ценах:**
/alerts - Показать активные уведомления
/alerts add <SYMBOL> <PRICE> <above/below> - Добавить уведомление
/alerts remove <ID> - Удалить уведомление

**Информация:**
/price <SYMBOL> - Текущая цена монеты
/search <QUERY> - Поиск монет
/top - Топ-10 монет по объему

**Примеры:**
/signals BTC/USDT
/profits
/stats
/price BTC/USDT
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получить текущую цену монеты."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы.")
            return

        if not context.args:
            await update.message.reply_text("❌ Укажите символ. Пример: /price BTC/USDT")
            return

        symbol = context.args[0].upper()
        if '/' not in symbol:
            symbol = f"{symbol}/USDT"

        try:
            ticker = self.data_manager.get_ticker(symbol, 'binance')
            if not ticker:
                await update.message.reply_text(f"❌ Не удалось получить данные для {symbol}")
                return

            price = ticker.get('last', 0)
            change_24h = ticker.get('percentage', 0)
            volume_24h = ticker.get('quoteVolume', 0)
            high_24h = ticker.get('high', 0)
            low_24h = ticker.get('low', 0)

            change_icon = "📈" if change_24h >= 0 else "📉"
            change_color = "🟢" if change_24h >= 0 else "🔴"

            message = f"""
💰 **{symbol}**

**Цена:** ${price:,.2f}
**Изменение 24ч:** {change_icon} {change_24h:+.2f}% {change_color}
**Объем 24ч:** ${volume_24h:,.0f}
**Макс 24ч:** ${high_24h:,.2f}
**Мин 24ч:** ${low_24h:,.2f}
            """
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка получения цены для {symbol}: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    async def watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Управление watchlist."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы.")
            return

        if chat_id not in self.watchlist:
            self.watchlist[chat_id] = set()

        if not context.args:
            # Показать текущий watchlist
            symbols = list(self.watchlist[chat_id])
            if not symbols:
                await update.message.reply_text("📋 Ваш watchlist пуст. Используйте /watchlist add <SYMBOL>")
                return

            message = "⭐ **Ваш Watchlist:**\n\n"
            tickers = self.data_manager.get_tickers('binance', symbols)
            
            for symbol in symbols:
                ticker = tickers.get(symbol)
                if ticker:
                    price = ticker.get('last', 0)
                    change_24h = ticker.get('percentage', 0)
                    change_icon = "📈" if change_24h >= 0 else "📉"
                    message += f"{change_icon} **{symbol}** ${price:,.2f} ({change_24h:+.2f}%)\n"
                else:
                    message += f"❓ **{symbol}** (данные недоступны)\n"

            keyboard = [
                [InlineKeyboardButton("➕ Добавить", callback_data="watchlist_add"),
                 InlineKeyboardButton("🗑️ Очистить", callback_data="watchlist_clear")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            return

        action = context.args[0].lower()
        
        if action == "add" and len(context.args) > 1:
            symbol = context.args[1].upper()
            if '/' not in symbol:
                symbol = f"{symbol}/USDT"
            
            self.watchlist[chat_id].add(symbol)
            await update.message.reply_text(f"✅ {symbol} добавлен в watchlist")
        
        elif action == "remove" and len(context.args) > 1:
            symbol = context.args[1].upper()
            if '/' not in symbol:
                symbol = f"{symbol}/USDT"
            
            if symbol in self.watchlist[chat_id]:
                self.watchlist[chat_id].remove(symbol)
                await update.message.reply_text(f"✅ {symbol} удален из watchlist")
            else:
                await update.message.reply_text(f"❌ {symbol} не найден в watchlist")
        
        elif action == "clear":
            self.watchlist[chat_id].clear()
            await update.message.reply_text("✅ Watchlist очищен")

    async def alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Управление уведомлениями о ценах."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы.")
            return

        if chat_id not in self.price_alerts:
            self.price_alerts[chat_id] = []

        if not context.args:
            # Показать активные уведомления
            alerts = self.price_alerts[chat_id]
            if not alerts:
                await update.message.reply_text("🔔 Нет активных уведомлений. Используйте /alerts add <SYMBOL> <PRICE> <above/below>")
                return

            message = "🔔 **Активные уведомления:**\n\n"
            for idx, alert in enumerate(alerts):
                message += f"{idx + 1}. {alert['symbol']} ${alert['price']:,.2f} ({alert['type']})\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            return

        action = context.args[0].lower()
        
        if action == "add" and len(context.args) >= 4:
            symbol = context.args[1].upper()
            if '/' not in symbol:
                symbol = f"{symbol}/USDT"
            
            try:
                price = float(context.args[2])
                alert_type = context.args[3].lower()
                
                if alert_type not in ['above', 'below']:
                    await update.message.reply_text("❌ Тип должен быть 'above' или 'below'")
                    return

                alert = {
                    'symbol': symbol,
                    'price': price,
                    'type': alert_type,
                    'triggered': False
                }
                self.price_alerts[chat_id].append(alert)
                await update.message.reply_text(f"✅ Уведомление добавлено: {symbol} ${price:,.2f} ({alert_type})")
            except ValueError:
                await update.message.reply_text("❌ Неверный формат цены")
        
        elif action == "remove" and len(context.args) > 1:
            try:
                idx = int(context.args[1]) - 1
                if 0 <= idx < len(self.price_alerts[chat_id]):
                    removed = self.price_alerts[chat_id].pop(idx)
                    await update.message.reply_text(f"✅ Уведомление удалено: {removed['symbol']}")
                else:
                    await update.message.reply_text("❌ Неверный номер уведомления")
            except ValueError:
                await update.message.reply_text("❌ Неверный формат номера")

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск монет."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы.")
            return

        if not context.args:
            await update.message.reply_text("❌ Укажите запрос. Пример: /search BTC")
            return

        query = context.args[0].upper()
        
        try:
            all_pairs = self.data_manager.get_all_pairs('binance')
            matches = [p for p in all_pairs if query in p.upper()][:10]
            
            if not matches:
                await update.message.reply_text(f"❌ Ничего не найдено для '{query}'")
                return

            message = f"🔍 **Найдено для '{query}':**\n\n"
            for pair in matches:
                message += f"• {pair}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка поиска: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    async def signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать или сгенерировать сигналы."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы.")
            return

        try:
            # Если указан символ, генерируем сигналы
            if context.args:
                symbol = context.args[0].upper()
                if '/' not in symbol:
                    symbol = f"{symbol}/USDT"
                
                await update.message.reply_text(f"🔍 Генерирую сигналы для {symbol}...")
                
                signals = self.signal_generator.generate_signals(symbol)
                
                if not signals:
                    await update.message.reply_text(f"❌ Сигналы не найдены для {symbol}")
                    return
                
                # Добавляем сигналы в трекер
                for signal in signals:
                    signal_id = self.profit_tracker.add_signal(signal)
                    self.signal_generator.add_active_signal(signal)
                
                # Отправляем сигналы
                for signal in signals:
                    message = self._format_signal_message(signal)
                    await update.message.reply_text(message, parse_mode='Markdown')
            else:
                # Показываем активные сигналы
                active_signals = self.profit_tracker.get_active_signals()
                
                if not active_signals:
                    await update.message.reply_text("📊 Нет активных сигналов")
                    return
                
                message = "📊 **Активные сигналы:**\n\n"
                for signal in active_signals[:10]:  # Показываем первые 10
                    message += self._format_signal_status(signal) + "\n\n"
                
                await update.message.reply_text(message, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Ошибка работы с сигналами: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def profits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать профиты по активным сигналам."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы.")
            return

        try:
            # Обновляем цены
            self.profit_tracker.update_all_prices()
            
            active_signals = self.profit_tracker.get_active_signals()
            
            if not active_signals:
                await update.message.reply_text("💰 Нет активных сигналов для отслеживания")
                return
            
            message = "💰 **Профиты по активным сигналам:**\n\n"
            total_pnl = 0.0
            
            for signal in active_signals:
                pnl = signal.get('pnl_percent', 0)
                total_pnl += pnl
                
                symbol = signal['symbol']
                signal_type = signal['type']
                entry = signal['entry_price']
                current = signal.get('current_price', entry)
                pnl_icon = "🟢" if pnl >= 0 else "🔴"
                
                message += f"""
{pnl_icon} **{symbol}** {signal_type}
Entry: ${entry:,.2f} → Current: ${current:,.2f}
P&L: {pnl:+.2f}%
Confluence: {signal.get('confluence', 0)}/5
"""
            
            message += f"\n**Общий P&L:** {total_pnl:+.2f}%"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка получения профитов: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика по сигналам или рынку."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы.")
            return

        try:
            # Статистика по сигналам
            stats = self.profit_tracker.get_statistics()
            
            message = f"""
📊 **Статистика сигналов**

**Всего сигналов:** {stats.get('total_signals', 0)}
**Активных:** {stats.get('active_signals', 0)}
**Закрытых:** {stats.get('closed_signals', 0)}

**Результаты:**
Победных: {stats.get('winning_signals', 0)}
Проигрышных: {stats.get('losing_signals', 0)}
Win Rate: {stats.get('win_rate', 0):.2f}%

**Профиты:**
Общий профит: ${stats.get('total_profit', 0):,.2f}
Общий убыток: ${stats.get('total_loss', 0):,.2f}
Чистый профит: ${stats.get('net_profit', 0):,.2f}

**Средние:**
Средний профит: ${stats.get('avg_profit', 0):,.2f}
Средний убыток: ${stats.get('avg_loss', 0):,.2f}
Profit Factor: {stats.get('profit_factor', 0):.2f}
"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подписаться на автоматические сигналы."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы.")
            return
        
        self.subscribed_chats.add(chat_id)
        await update.message.reply_text(
            "✅ Вы подписаны на автоматические сигналы!\n"
            "Новые сигналы будут приходить автоматически."
        )
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отписаться от автоматических сигналов."""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы.")
            return
        
        self.subscribed_chats.discard(chat_id)
        await update.message.reply_text("❌ Вы отписаны от автоматических сигналов.")
    
    def _format_signal_message(self, signal) -> str:
        """Форматирует сообщение о сигнале."""
        signal_icon = "🟢" if signal.type == "LONG" else "🔴"
        tp_text = f"${signal.take_profit:,.2f}" if signal.take_profit else "N/A"
        sl_text = f"${signal.stop_loss:,.2f}" if signal.stop_loss else "N/A"
        
        message = f"""
{signal_icon} **Новый сигнал: {signal.symbol}**

**Тип:** {signal.type}
**Entry:** ${signal.entry_price:,.2f}
**Stop Loss:** {sl_text}
**Take Profit:** {tp_text}

**Confluence:** {signal.confluence}/5
**Confidence:** {signal.confidence*100:.0f}%
**Timeframe:** {signal.timeframe}

**Индикаторы:**
{', '.join(signal.indicators)}

⏰ {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
        return message
    
    def _format_signal_status(self, signal: dict) -> str:
        """Форматирует статус сигнала."""
        signal_type = signal['type']
        signal_icon = "🟢" if signal_type == "LONG" else "🔴"
        pnl = signal.get('pnl_percent', 0)
        pnl_icon = "📈" if pnl >= 0 else "📉"
        
        return f"""
{signal_icon} **{signal['symbol']}** {signal_type}
Entry: ${signal['entry_price']:,.2f}
Current: ${signal.get('current_price', signal['entry_price']):,.2f}
{pnl_icon} P&L: {pnl:+.2f}%
Confluence: {signal.get('confluence', 0)}/5
"""

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок."""
        query = update.callback_query
        await query.answer()
        
        chat_id = query.message.chat_id
        
        if not self._is_authorized(chat_id):
            await query.message.reply_text("❌ Вы не авторизованы.")
            return

        data = query.data
        
        if data == "watchlist_add":
            await query.message.reply_text("Введите: /watchlist add <SYMBOL>")
        elif data == "watchlist_clear":
            if chat_id in self.watchlist:
                self.watchlist[chat_id].clear()
                await query.message.reply_text("✅ Watchlist очищен")

    def send_notification(self, chat_id: int, message: str, parse_mode: str = 'Markdown'):
        """Отправить уведомление пользователю."""
        if not self.is_running or not self.application:
            logger.warning(f"Бот не запущен, не могу отправить сообщение в chat_id {chat_id}")
            return

        async def _send():
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode
                )
                logger.debug(f"Сообщение отправлено в chat_id {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения в Telegram (chat_id {chat_id}): {str(e)}", exc_info=True)

        try:
            # Получаем event loop из application
            if hasattr(self.application, 'bot') and hasattr(self.application.bot, '_loop'):
                loop = self.application.bot._loop
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(_send(), loop)
                else:
                    logger.warning("Event loop не запущен, не могу отправить сообщение")
            else:
                logger.warning("Application.bot._loop недоступен")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}", exc_info=True)

    def check_price_alerts(self):
        """Проверить и отправить уведомления о ценах."""
        if not self.is_running:
            return

        for chat_id, alerts in self.price_alerts.items():
            if not self._is_authorized(chat_id):
                continue

            for alert in alerts:
                if alert.get('triggered', False):
                    continue

                symbol = alert['symbol']
                target_price = alert['price']
                alert_type = alert['type']

                try:
                    ticker = self.data_manager.get_ticker(symbol, 'binance')
                    if not ticker:
                        continue

                    current_price = ticker.get('last', 0)
                    should_trigger = False

                    if alert_type == 'above' and current_price >= target_price:
                        should_trigger = True
                    elif alert_type == 'below' and current_price <= target_price:
                        should_trigger = True

                    if should_trigger:
                        alert['triggered'] = True
                        message = f"""
🔔 **Уведомление о цене**

**{symbol}** достиг ${target_price:,.2f}
**Текущая цена:** ${current_price:,.2f}
**Тип:** {alert_type}
                        """
                        self.send_notification(chat_id, message)
                except Exception as e:
                    logger.error(f"Ошибка проверки уведомления для {symbol}: {str(e)}")

    def send_price_alert(self, symbol: str, price: float, change_24h: float, message_type: str = "update"):
        """Отправить уведомление о цене для всех пользователей в watchlist."""
        if not self.is_running:
            return

        for chat_id, symbols in self.watchlist.items():
            if symbol in symbols:
                change_icon = "📈" if change_24h >= 0 else "📉"
                message = f"""
{change_icon} **{symbol}**

**Цена:** ${price:,.2f}
**Изменение 24ч:** {change_24h:+.2f}%
                """
                self.send_notification(chat_id, message)

    def send_market_alert(self, message: str):
        """Отправить рыночное уведомление всем авторизованным пользователям."""
        if not self.is_running:
            return

        if self.allowed_chat_ids:
            for chat_id in self.allowed_chat_ids:
                self.send_notification(chat_id, message)
        else:
            # Отправляем всем пользователям, которые использовали бота
            all_chat_ids = set(self.watchlist.keys()) | set(self.price_alerts.keys())
            for chat_id in all_chat_ids:
                self.send_notification(chat_id, message)

    def _check_alerts_loop(self):
        """Периодическая проверка уведомлений о ценах."""
        import time
        while self.is_running:
            try:
                self.check_price_alerts()
                time.sleep(10)  # Проверяем каждые 10 секунд
            except Exception as e:
                logger.error(f"Ошибка проверки уведомлений: {str(e)}")
                time.sleep(10)
    
    def _signals_monitoring_loop(self):
        """Периодический мониторинг сигналов и обновление цен."""
        import time
        from config.market_config import POPULAR_PAIRS
        
        while self.is_running:
            try:
                # Обновляем цены для активных сигналов каждые 10 секунд
                try:
                    self.profit_tracker.update_all_prices()
                    logger.debug("Цены обновлены для активных сигналов")
                except Exception as e:
                    logger.error(f"Ошибка обновления цен: {e}", exc_info=True)
                
                # Генерируем сигналы для популярных пар (если включена автоотправка)
                if self.auto_send_signals and self.subscribed_chats:
                    for symbol in POPULAR_PAIRS[:10]:  # Топ-10 пар
                        try:
                            signals = self.signal_generator.generate_signals(symbol)
                            
                            # Проверяем, не были ли эти сигналы уже отправлены
                            for signal in signals:
                                signal_id = f"{signal.symbol}_{signal.type}_{int(signal.timestamp.timestamp())}"
                                
                                # Проверяем, есть ли уже такой сигнал
                                existing = self.profit_tracker.get_signal(signal_id)
                                if not existing:
                                    # Добавляем в трекер
                                    self.profit_tracker.add_signal(signal)
                                    self.signal_generator.add_active_signal(signal)
                                    
                                    # Отправляем подписчикам
                                    message = self._format_signal_message(signal)
                                    for chat_id in self.subscribed_chats:
                                        self.send_notification(chat_id, message)
                                    
                                    logger.info(f"Отправлен новый сигнал: {signal.symbol} {signal.type}")
                        except Exception as e:
                            logger.error(f"Ошибка генерации сигналов для {symbol}: {e}", exc_info=True)
                
                time.sleep(10)  # Обновляем каждые 10 секунд (было 60)
            except Exception as e:
                logger.error(f"Ошибка мониторинга сигналов: {str(e)}", exc_info=True)
                time.sleep(10)

    def _run_bot(self):
        """Запустить бота в отдельном потоке."""
        async def post_init(app: Application):
            """Инициализация после запуска."""
            logger.info("Telegram бот запущен и готов к работе")
            # Запускаем поток для проверки уведомлений
            alerts_thread = threading.Thread(
                target=self._check_alerts_loop,
                daemon=True,
                name="TelegramBotAlerts"
            )
            alerts_thread.start()

        def run():
            try:
                import asyncio
                # Создаем новый event loop для потока
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Проверяем токен перед созданием Application
                if not self.token or len(self.token) < 10:
                    raise ValueError(f"Неверный токен Telegram бота: {self.token[:10] if self.token else 'None'}...")
                
                logger.info(f"Создание Application с токеном: {self.token[:10]}...")
                try:
                    self.application = Application.builder().token(self.token).post_init(post_init).build()
                    logger.info("Application создан успешно")
                except Exception as e:
                    logger.error(f"Ошибка создания Application: {e}", exc_info=True)
                    raise
                
                # Регистрация обработчиков
                logger.info("Регистрация обработчиков команд...")
                self.application.add_handler(CommandHandler("start", self.start_command))
                self.application.add_handler(CommandHandler("help", self.help_command))
                self.application.add_handler(CommandHandler("price", self.price_command))
                self.application.add_handler(CommandHandler("watchlist", self.watchlist_command))
                self.application.add_handler(CommandHandler("alerts", self.alerts_command))
                self.application.add_handler(CommandHandler("search", self.search_command))
                self.application.add_handler(CommandHandler("signals", self.signals_command))
                self.application.add_handler(CommandHandler("profits", self.profits_command))
                self.application.add_handler(CommandHandler("stats", self.stats_command))
                self.application.add_handler(CommandHandler("subscribe", self.subscribe_command))
                self.application.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
                self.application.add_handler(CallbackQueryHandler(self.callback_handler))
                
                # Запускаем поток для обновления цен и отправки сигналов
                signals_thread = threading.Thread(
                    target=self._signals_monitoring_loop,
                    daemon=True,
                    name="TelegramBotSignals"
                )
                signals_thread.start()

                # Запуск бота
                self.is_running = True
                logger.info("Запуск polling для Telegram бота...")
                print("🔄 Запуск Telegram бота...")
                
                # Проверяем, что Application создан
                if not self.application:
                    raise RuntimeError("Application не создан")
                
                try:
                    self.application.run_polling(
                        allowed_updates=Update.ALL_TYPES,
                        drop_pending_updates=True,
                        close_loop=False
                    )
                    logger.info("Telegram бот успешно запущен и работает")
                except Exception as e:
                    logger.error(f"Ошибка при run_polling: {e}", exc_info=True)
                    raise
            except Exception as e:
                logger.error(f"Ошибка запуска Telegram бота: {str(e)}", exc_info=True)
                print(f"❌ Ошибка запуска бота: {e}")
                self.is_running = False
                import traceback
                traceback.print_exc()

        self.bot_thread = threading.Thread(target=run, daemon=True, name="TelegramBot")
        self.bot_thread.start()

    def start(self):
        """Запустить бота."""
        if self.is_running:
            logger.warning("Telegram бот уже запущен")
            return

        if not HAS_TELEGRAM:
            logger.error("python-telegram-bot не установлен")
            print("❌ python-telegram-bot не установлен. Установи: pip install python-telegram-bot")
            return

        if not self.token:
            logger.error("Токен Telegram бота не указан")
            print("❌ Токен Telegram бота не указан")
            return

        logger.info("Запуск Telegram бота...")
        try:
            self._run_bot()
            # Даем время на запуск потока
            import time
            time.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
            print(f"❌ Ошибка запуска бота: {e}")

    def stop(self):
        """Остановить бота."""
        if not self.is_running:
            return

        self.is_running = False
        if self.application:
            asyncio.run_coroutine_threadsafe(
                self.application.stop(),
                self.application.bot._loop
            )
        logger.info("Telegram бот остановлен")


# Глобальный экземпляр бота
_telegram_bot_instance: Optional[TelegramBot] = None


def get_telegram_bot(
    token: Optional[str] = None,
    data_manager: Optional[MarketDataManager] = None,
    alerts: Optional[MarketAlerts] = None,
    allowed_chat_ids: Optional[List[int]] = None,
    signal_generator: Optional[SignalGenerator] = None,
    profit_tracker: Optional[ProfitTracker] = None
) -> Optional[TelegramBot]:
    """
    Получить или создать экземпляр Telegram бота (singleton).

    Args:
        token: Токен бота
        data_manager: Менеджер данных
        alerts: Система алертов
        allowed_chat_ids: Разрешенные chat_id

    Returns:
        Экземпляр TelegramBot или None
    """
    global _telegram_bot_instance

    if not HAS_TELEGRAM:
        logger.warning("python-telegram-bot не установлен")
        return None

    if _telegram_bot_instance is None and token:
        try:
            _telegram_bot_instance = TelegramBot(
                token=token,
                data_manager=data_manager,
                alerts=alerts,
                allowed_chat_ids=allowed_chat_ids,
                signal_generator=signal_generator,
                profit_tracker=profit_tracker
            )
        except Exception as e:
            logger.error(f"Ошибка создания Telegram бота: {str(e)}")
            return None

    return _telegram_bot_instance


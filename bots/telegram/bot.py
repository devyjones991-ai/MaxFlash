from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from typing import Optional
import structlog

from app.config import settings
from app.database import AsyncSession
from app.models.user import User, UserRole, Subscription, SubscriptionStatus
from app.models.signal import Signal, SignalRating
from app.repositories.signal_repository import SignalRepository
from sqlalchemy import select
# from services.llm_engine import llm_engine

logger = structlog.get_logger()

# Состояния диалога
MENU, ANALYZE_WAITING = range(2)


class TelegramBot:
    """Telegram бот для сигналов."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.token = settings.TELEGRAM_BOT_TOKEN
        if not self.token:
            logger.warning("Telegram bot token not configured")
            return

        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """Настроить обработчики команд."""
        # Основной диалог
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start_command)],
            states={
                MENU: [
                    MessageHandler(filters.Regex("^(📊 Сигналы)$"), self.signals_command),
                    MessageHandler(filters.Regex("^(🤖 Анализ рынка)$"), self.analyze_start),
                    MessageHandler(filters.Regex("^(👤 Мой статус)$"), self.status_command),
                    MessageHandler(filters.Regex("^(❓ Помощь)$"), self.help_command),
                ],
                ANALYZE_WAITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.analyze_process)],
            },
            fallbacks=[CommandHandler("start", self.start_command)],
        )

        self.application.add_handler(conv_handler)
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        # Fallback для неизвестных команд вне диалога
        self.application.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))

    async def start_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start и главное меню."""
        if not update.effective_user:
            return MENU

        user = update.effective_user
        await self._get_or_create_user(user.id, user.username)

        keyboard = [
            ["📊 Сигналы", "🤖 Анализ рынка"],
            ["👤 Мой статус", "❓ Помощь"],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        if update.message:
            await update.message.reply_text(
                f"Привет, {user.first_name}! 👋\nВыберите действие в меню:",
                reply_markup=reply_markup,
            )
        return MENU

    async def help_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки Помощь."""
        help_text = (
            "📚 **Помощь по боту MaxFlash**\n\n"
            "🤖 **Анализ рынка**: Нажмите кнопку, введите пару (например BTC/USDT), и AI проведет анализ.\n"
            "📊 **Сигналы**: Показывает последние активные сигналы.\n"
            "👤 **Статус**: Ваша подписка и роль.\n\n"
            "Рейтинги:\n"
            "• FREE - базовые сигналы\n"
            "• PRO - качественные сигналы\n"
            "• ALPHA - премиум сигналы\n\n"
            "Поддержка: @MaxFlashSupport"
        )
        if update.message:
            await update.message.reply_text(help_text, parse_mode="Markdown")
        return MENU

    async def signals_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки Сигналы."""
        if not update.effective_user:
            return MENU

        user_id = update.effective_user.id
        user = await self._get_user(user_id)

        if not user:
            if update.message:
                await update.message.reply_text("Пользователь не найден. Нажмите /start")
            return MENU

        allowed_ratings = self._get_allowed_ratings(user.role)
        signal_repo = SignalRepository(self.db)
        signals = await signal_repo.get_active_signals(limit=10)
        filtered_signals = [s for s in signals if s.rating in allowed_ratings]

        if not filtered_signals:
            if update.message:
                await update.message.reply_text("📊 Активных сигналов нет.")
            return MENU

        for signal in filtered_signals[:5]:
            signal_text = self._format_signal(signal)
            if update.message:
                await update.message.reply_text(signal_text, parse_mode="HTML")

        if len(filtered_signals) > 5 and update.message:
            await update.message.reply_text("Показано 5 сигналов. Подпишитесь для большего.")

        return MENU

    async def analyze_start(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """Начало анализа: запрос символа."""
        if update.message:
            await update.message.reply_text(
                "Введите торговую пару для анализа (например: BTC/USDT):", reply_markup=ReplyKeyboardRemove()
            )
        return ANALYZE_WAITING

    async def analyze_process(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода символа и запуск анализа."""
        if not update.message or not update.message.text:
            return ANALYZE_WAITING

        symbol = update.message.text.upper().strip()

        # Простая валидация
        if len(symbol) < 3 or len(symbol) > 10:
            if update.message:
                await update.message.reply_text(
                    "❌ Некорректный формат. Попробуйте снова (например: ETH/USDT) или /start для выхода."
                )
            return ANALYZE_WAITING

        if update.message:
            await update.message.reply_text(f"🤖 Анализирую рынок для {symbol}...\nЭто может занять несколько секунд.")

        try:
            from trading.signals_service import signal_service

            # Use SignalService for comprehensive analysis
            result = await signal_service.analyze_symbol(symbol)

            # Format response
            emoji = "⚪"
            if result.signal_type == "BUY":
                emoji = "🟢"
            elif result.signal_type == "SELL":
                emoji = "🔴"

            response = (
                f"{emoji} **Анализ {result.symbol}**\n\n"
                f"Сигнал: **{result.signal_type.value}**\n"
                f"Уверенность: {result.confidence * 100:.1f}%\n"
                f"Цена: ${result.price:.2f}\n\n"
            )

            if result.stop_loss:
                response += f"SL: ${result.stop_loss:.2f}\n"
            if result.take_profit:
                response += f"TP: ${result.take_profit:.2f}\n\n"

            if result.reasoning:
                response += f"📝 **Обоснование**:\n{result.reasoning[0]}\n"

            if update.message:
                await update.message.reply_text(response, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            if update.message:
                await update.message.reply_text("❌ Ошибка анализа. Попробуйте позже.")

        # Возвращаем меню
        keyboard = [
            ["📊 Сигналы", "🤖 Анализ рынка"],
            ["👤 Мой статус", "❓ Помощь"],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        if update.message:
            await update.message.reply_text("Готово! Что дальше?", reply_markup=reply_markup)
        return MENU

    async def status_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки Статус."""
        if not update.effective_user:
            return MENU

        user_id = update.effective_user.id
        user = await self._get_user(user_id)

        if not user:
            return MENU

        # Получаем активные подписки
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user.id, Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        subscriptions = result.scalars().all()

        text = f"👤 **Ваш профиль**\n\nРоль: {user.role.value}\n"

        if subscriptions:
            text += "Активные подписки:\n"
            for sub in subscriptions:
                expires_at = sub.expires_at.strftime("%d.%m.%Y %H:%M")
                text += f"• {sub.rating.value.upper()} до {expires_at}\n"

        keyboard = [
            [
                InlineKeyboardButton("Pro ($29)", callback_data="subscribe_pro"),
                InlineKeyboardButton("Alpha ($99)", callback_data="subscribe_alpha"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        return MENU

    async def button_callback(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """Обработчик инлайн кнопок (подписка)."""
        if not update.callback_query:
            return

        query = update.callback_query
        await query.answer()

        if query.data and query.data.startswith("subscribe_"):
            rating = query.data.replace("subscribe_", "")
            await query.edit_message_text(f"Подписка {rating} в разработке. Пишите @MaxFlashSupport")

    async def unknown_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text("Неизвестная команда. Введите /start для меню.")

    def _format_signal(self, signal: Signal) -> str:
        """Форматировать сигнал для отправки."""
        rating_emoji = {
            SignalRating.FREE: "🆓",
            SignalRating.PRO: "⭐",
            SignalRating.ALPHA: "💎",
        }
        emoji = rating_emoji.get(signal.rating, "📊")

        text = f"{emoji} <b>{signal.symbol} {signal.signal_type.value.upper()}</b>\nВход: ${signal.entry_price:.8f}\n"
        if signal.stop_loss:
            text += f"SL: ${signal.stop_loss:.8f}\n"
        if signal.take_profit:
            text += f"TP: ${signal.take_profit:.8f}\n"

        return text

    def _get_allowed_ratings(self, user_role: UserRole) -> list[SignalRating]:
        if user_role == UserRole.ALPHA:
            return [SignalRating.FREE, SignalRating.PRO, SignalRating.ALPHA]
        elif user_role == UserRole.PRO:
            return [SignalRating.FREE, SignalRating.PRO]
        return [SignalRating.FREE]

    async def _get_or_create_user(self, telegram_id: int, username: Optional[str]) -> User:
        result = await self.db.execute(select(User).where(User.telegram_id == str(telegram_id)))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=str(telegram_id), telegram_username=username, role=UserRole.FREE)
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def _get_user(self, telegram_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.telegram_id == str(telegram_id)))
        return result.scalar_one_or_none()

    async def send_signal(self, signal: Signal, user: User):
        if not self.token or not user.notifications_enabled:
            return
        try:
            text = self._format_signal(signal)
            await self.application.bot.send_message(chat_id=user.telegram_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error sending signal: {e}")

    def start(self):
        if not self.token:
            return
        logger.info("Starting Telegram bot")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def stop(self):
        if self.application:
            await self.application.stop()
            await self.application.shutdown()

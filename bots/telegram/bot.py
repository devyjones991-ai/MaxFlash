"""
Telegram бот для доставки сигналов и управления подписками.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from typing import Optional, List
import structlog
from datetime import datetime

from app.config import settings
from app.database import AsyncSession
from app.models.user import User, UserRole, Subscription, SubscriptionStatus
from app.models.signal import Signal, SignalRating
from app.repositories.signal_repository import SignalRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from services.llm_engine import llm_engine

logger = structlog.get_logger()


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
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("signals", self.signals_command))
        self.application.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("analyze", self.analyze_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start."""
        user = update.effective_user

        # Регистрируем или обновляем пользователя
        await self._get_or_create_user(user.id, user.username)

        welcome_text = (
            f"Привет, {user.first_name}! 👋\n\n"
            "Я MaxFlash Trading Bot - твой помощник в криптотрейдинге.\n\n"
            "Доступные команды:\n"
            "/signals - получить торговые сигналы\n"
            "/subscribe - подписаться на платные сигналы\n"
            "/status - статус подписки\n"
            "/help - помощь\n\n"
            "Начни с команды /signals чтобы увидеть бесплатные сигналы!"
        )

        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help."""
        help_text = (
            "📚 Помощь по боту MaxFlash\n\n"
            "Команды:\n"
            "• /start - начать работу с ботом\n"
            "• /signals - получить торговые сигналы\n"
            "• /subscribe - подписаться на Pro/Alpha сигналы\n"
            "• /status - проверить статус подписки\n"
            "• /help - показать эту справку\n\n"
            "Рейтинги сигналов:\n"
            "• FREE - бесплатные сигналы (базовый уровень)\n"
            "• PRO - платные сигналы (высокое качество)\n"
            "• ALPHA - премиум сигналы (максимальный потенциал)\n\n"
            "Для вопросов: @MaxFlashSupport"
        )

        await update.message.reply_text(help_text)

    async def signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /signals."""
        user_id = update.effective_user.id

        # Получаем пользователя
        user = await self._get_user(user_id)
        if not user:
            await update.message.reply_text("Ошибка: пользователь не найден. Используйте /start")
            return

        # Определяем доступные рейтинги
        allowed_ratings = self._get_allowed_ratings(user.role)

        # Получаем сигналы
        signal_repo = SignalRepository(self.db)
        signals = await signal_repo.get_active_signals(limit=10)

        # Фильтруем по доступным рейтингам
        filtered_signals = [s for s in signals if s.rating in allowed_ratings]

        if not filtered_signals:
            text = "📊 Активных сигналов нет.\n\nПопробуйте позже или подпишитесь на платные сигналы: /subscribe"
            await update.message.reply_text(text)
            return

        # Отправляем сигналы
        for signal in filtered_signals[:5]:  # Максимум 5 сигналов
            signal_text = self._format_signal(signal, user.role)
            await update.message.reply_text(signal_text, parse_mode="HTML")

        if len(filtered_signals) > 5:
            await update.message.reply_text(
                f"Показано 5 из {len(filtered_signals)} сигналов. Подпишитесь на Pro/Alpha для большего: /subscribe"
            )

    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /subscribe."""
        user_id = update.effective_user.id
        user = await self._get_user(user_id)

        if not user:
            await update.message.reply_text("Ошибка: пользователь не найден. Используйте /start")
            return

        keyboard = [
            [
                InlineKeyboardButton("Pro ($29/мес)", callback_data="subscribe_pro"),
                InlineKeyboardButton("Alpha ($99/мес)", callback_data="subscribe_alpha"),
            ],
            [InlineKeyboardButton("Отмена", callback_data="cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "💳 Выберите подписку:\n\n"
            "• <b>Pro</b> - платные сигналы высокого качества\n"
            "  Цена: $29/месяц\n\n"
            "• <b>Alpha</b> - премиум сигналы максимального потенциала\n"
            "  Цена: $99/месяц\n\n"
            "Текущая роль: " + user.role.value
        )

        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status."""
        user_id = update.effective_user.id
        user = await self._get_user(user_id)

        if not user:
            await update.message.reply_text("Ошибка: пользователь не найден. Используйте /start")
            return

        # Получаем активные подписки
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user.id, Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        subscriptions = result.scalars().all()

        text = f"👤 Ваш статус:\n\nРоль: {user.role.value}\n\n"

        if subscriptions:
            text += "Активные подписки:\n"
            for sub in subscriptions:
                expires_at = sub.expires_at.strftime("%d.%m.%Y %H:%M")
                text += f"• {sub.rating.value.upper()} до {expires_at}\n"
        else:
            text += "Нет активных подписок.\nПодпишитесь: /subscribe"

        await update.message.reply_text(text)

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /analyze."""
        if not context.args:
            await update.message.reply_text("⚠️ Пожалуйста, укажите символ. Пример: /analyze BTC/USDT")
            return

        symbol = context.args[0].upper()
        await update.message.reply_text(f"🤖 Анализирую рынок для {symbol}...")

        try:
            # Используем LLM для анализа
            analysis = await llm_engine.analyze_market(symbol)
            await update.message.reply_text(analysis, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            await update.message.reply_text("❌ Произошла ошибка при анализе. Попробуйте позже.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки."""
        query = update.callback_query
        await query.answer()

        if query.data == "cancel":
            await query.edit_message_text("Отменено.")
            return

        if query.data.startswith("subscribe_"):
            rating = query.data.replace("subscribe_", "")
            await query.edit_message_text(
                f"Подписка {rating} - функция в разработке. Свяжитесь с поддержкой: @MaxFlashSupport"
            )

    def _format_signal(self, signal: Signal, user_role: UserRole) -> str:
        """Форматировать сигнал для отправки."""
        rating_emoji = {
            SignalRating.FREE: "🆓",
            SignalRating.PRO: "⭐",
            SignalRating.ALPHA: "💎",
        }

        type_emoji = {
            "long": "📈",
            "short": "📉",
        }

        emoji = rating_emoji.get(signal.rating, "📊")
        type_emoji_str = type_emoji.get(signal.signal_type.value, "📊")

        text = (
            f"{emoji} <b>{signal.symbol} {signal.signal_type.value.upper()}</b> "
            f"({signal.rating.value.upper()})\n\n"
            f"Вход: ${signal.entry_price:.8f}\n"
        )

        if signal.stop_loss:
            text += f"Stop Loss: ${signal.stop_loss:.8f}\n"
        if signal.take_profit:
            text += f"Take Profit: ${signal.take_profit:.8f}\n"

        text += f"\nScore: {float(signal.signal_score):.2%}\n"

        if signal.description:
            text += f"\n{signal.description}"

        # Для Pro/Alpha показываем полное описание
        if user_role in [UserRole.PRO, UserRole.ALPHA] and signal.full_description:
            text += f"\n\n{signal.full_description}"

        return text

    def _get_allowed_ratings(self, user_role: UserRole) -> List[SignalRating]:
        """Получить список разрешённых рейтингов для роли."""
        if user_role == UserRole.ALPHA:
            return [SignalRating.FREE, SignalRating.PRO, SignalRating.ALPHA]
        elif user_role == UserRole.PRO:
            return [SignalRating.FREE, SignalRating.PRO]
        else:
            return [SignalRating.FREE]

    async def _get_or_create_user(self, telegram_id: int, username: Optional[str]) -> User:
        """Получить или создать пользователя."""
        result = await self.db.execute(select(User).where(User.telegram_id == str(telegram_id)))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=str(telegram_id),
                telegram_username=username,
                role=UserRole.FREE,
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info("User created", telegram_id=telegram_id)
        else:
            # Обновляем username если изменился
            if user.telegram_username != username:
                user.telegram_username = username
                await self.db.commit()

        return user

    async def _get_user(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя."""
        result = await self.db.execute(select(User).where(User.telegram_id == str(telegram_id)))
        return result.scalar_one_or_none()

    async def send_signal(self, signal: Signal, user: User):
        """Отправить сигнал пользователю."""
        if not self.token:
            return

        # Проверяем доступ
        allowed_ratings = self._get_allowed_ratings(user.role)
        if signal.rating not in allowed_ratings:
            return

        if not user.notifications_enabled:
            return

        try:
            signal_text = self._format_signal(signal, user.role)
            await self.application.bot.send_message(chat_id=user.telegram_id, text=signal_text, parse_mode="HTML")

            logger.info("Signal sent", signal_id=signal.id, user_id=user.id)
        except Exception as e:
            logger.error("Error sending signal", signal_id=signal.id, error=str(e))

    def start(self):
        """Запустить бота."""
        if not self.token:
            logger.warning("Telegram bot token not configured, skipping bot start")
            return

        logger.info("Starting Telegram bot")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def stop(self):
        """Остановить бота."""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()

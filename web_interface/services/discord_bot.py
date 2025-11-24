"""
Discord Bot для алертов и уведомлений.
Интеграция из Crypto Price Monitoring System.
"""

import logging
import os
from datetime import datetime
from typing import Optional

try:
    import discord
    from discord.ext import commands

    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    logging.warning("discord.py не установлен. Discord bot недоступен.")

logger = logging.getLogger(__name__)


class TradingAlertBot:
    """
    Discord бот для отправки торговых алертов и уведомлений.
    """

    def __init__(self, token: Optional[str] = None, channel_id: Optional[int] = None, prefix: str = "!"):
        """
        Инициализация Discord бота.

        Args:
            token: Discord Bot Token (из .env или параметр)
            channel_id: ID канала для отправки алертов
            prefix: Префикс для команд
        """
        if not DISCORD_AVAILABLE:
            raise ImportError("discord.py не установлен. Установите: pip install discord.py")

        self.token = token or os.getenv("DISCORD_BOT_TOKEN")
        self.channel_id = channel_id or int(os.getenv("DISCORD_CHANNEL_ID", "0"))
        self.prefix = prefix

        if not self.token:
            raise ValueError("Discord Bot Token не указан. Установите DISCORD_BOT_TOKEN в .env")

        # Инициализация бота
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix=prefix, intents=intents)
        self.channel: Optional[discord.TextChannel] = None
        self.is_running = False

        # История алертов
        self.alert_history: list[dict] = []
        self.max_history = 100

        # Настройка команд
        self._setup_commands()

    def _setup_commands(self):
        """Настройка команд бота."""

        @self.bot.event
        async def on_ready():
            logger.info(f"Discord бот подключен как {self.bot.user}")
            if self.channel_id:
                self.channel = self.bot.get_channel(self.channel_id)
                if self.channel:
                    logger.info(f"Канал для алертов: {self.channel.name}")
                else:
                    logger.warning(f"Канал с ID {self.channel_id} не найден")
            self.is_running = True

        @self.bot.command(name="status")
        async def status(ctx):
            """Проверка статуса системы."""
            embed = discord.Embed(
                title="📊 MaxFlash Trading System Status",
                description="Статус торговой системы",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="Статус", value="🟢 Online", inline=False)
            embed.add_field(name="Бот", value=f"{self.bot.user.name}", inline=True)
            embed.add_field(name="Алертов отправлено", value=str(len(self.alert_history)), inline=True)
            await ctx.send(embed=embed)

        @self.bot.command(name="help")
        async def help_command(ctx):
            """Показать доступные команды."""
            embed = discord.Embed(
                title="🤖 Доступные команды", description=f"Префикс: `{self.prefix}`", color=discord.Color.blue()
            )
            commands_list = [
                ("status", "Проверить статус системы"),
                ("alerts", "Показать последние алерты"),
                ("help", "Показать эту справку"),
            ]
            for cmd, desc in commands_list:
                embed.add_field(name=f"`{self.prefix}{cmd}`", value=desc, inline=False)
            await ctx.send(embed=embed)

        @self.bot.command(name="alerts")
        async def alerts(ctx, limit: int = 10):
            """Показать последние алерты."""
            if not self.alert_history:
                await ctx.send("📭 Нет отправленных алертов")
                return

            recent_alerts = self.alert_history[-limit:]
            embed = discord.Embed(title=f"📢 Последние {len(recent_alerts)} алертов", color=discord.Color.orange())

            for i, alert in enumerate(reversed(recent_alerts), 1):
                alert_text = alert.get("message", "N/A")[:100]
                timestamp = alert.get("timestamp", "N/A")
                embed.add_field(
                    name=f"Алерт #{len(recent_alerts) - i + 1}", value=f"{alert_text}\n`{timestamp}`", inline=False
                )

            await ctx.send(embed=embed)

    async def start(self):
        """Запуск бота."""
        if not self.token:
            raise ValueError("Discord Bot Token не указан")

        try:
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Ошибка запуска Discord бота: {e}")
            raise

    def run(self):
        """Запуск бота (синхронная версия)."""
        if not self.token:
            raise ValueError("Discord Bot Token не указан")

        try:
            self.bot.run(self.token)
        except Exception as e:
            logger.error(f"Ошибка запуска Discord бота: {e}")
            raise

    async def send_alert(self, message: str, embed: Optional[discord.Embed] = None):
        """
        Отправить алерт в Discord канал.

        Args:
            message: Текст сообщения
            embed: Опциональный embed объект
        """
        if not self.channel:
            logger.warning("Discord канал не установлен")
            return

        try:
            if embed:
                await self.channel.send(content=message, embed=embed)
            else:
                await self.channel.send(message)

            # Сохраняем в историю
            self.alert_history.append({"message": message, "timestamp": datetime.now().isoformat()})

            # Ограничиваем размер истории
            if len(self.alert_history) > self.max_history:
                self.alert_history.pop(0)

            logger.info(f"Discord алерт отправлен: {message[:50]}...")

        except Exception as e:
            logger.error(f"Ошибка отправки Discord алерта: {e}")

    async def send_signal_alert(self, signal: dict):
        """
        Отправить алерт о торговом сигнале.

        Args:
            signal: Словарь с информацией о сигнале
        """
        symbol = signal.get("symbol", "N/A")
        signal_type = signal.get("type", "N/A")
        confluence = signal.get("confluence", 0)
        entry_price = signal.get("entry_price", 0)

        # Создаем embed
        color = discord.Color.green() if signal_type.lower() == "long" else discord.Color.red()

        embed = discord.Embed(
            title=f"🚀 Новый торговый сигнал: {symbol}",
            description=f"Тип: **{signal_type.upper()}**",
            color=color,
            timestamp=datetime.now(),
        )

        embed.add_field(name="Торговая пара", value=symbol, inline=True)
        embed.add_field(name="Тип сигнала", value=signal_type.upper(), inline=True)
        embed.add_field(name="Confluence", value=f"{confluence} сигналов", inline=True)
        embed.add_field(name="Цена входа", value=f"${entry_price:,.2f}", inline=True)

        if "indicators" in signal:
            indicators_text = ", ".join(signal["indicators"][:5])
            embed.add_field(name="Индикаторы", value=indicators_text, inline=False)

        await self.send_alert(f"🎯 Сигнал {signal_type.upper()} для {symbol}", embed=embed)

    async def send_anomaly_alert(self, anomaly: dict):
        """
        Отправить алерт об аномалии.

        Args:
            anomaly: Словарь с информацией об аномалии
        """
        anomaly_type = anomaly.get("type", "unknown")
        severity = anomaly.get("severity", "medium")
        message = anomaly.get("message", "Аномалия обнаружена")

        # Цвет по серьезности
        color = discord.Color.red() if severity == "high" else discord.Color.orange()
        emoji = "🔥" if severity == "high" else "⚠️"

        embed = discord.Embed(
            title=f"{emoji} Обнаружена аномалия", description=message, color=color, timestamp=datetime.now()
        )

        embed.add_field(name="Тип", value=anomaly_type, inline=True)
        embed.add_field(name="Серьезность", value=severity.upper(), inline=True)

        if "price" in anomaly:
            embed.add_field(name="Цена", value=f"${anomaly['price']:,.2f}", inline=True)

        await self.send_alert(f"{emoji} Аномалия: {anomaly_type}", embed=embed)


def create_discord_bot(token: Optional[str] = None, channel_id: Optional[int] = None) -> Optional[TradingAlertBot]:
    """
    Создать и вернуть Discord бота если доступен.

    Returns:
        TradingAlertBot или None если не настроен
    """
    if not DISCORD_AVAILABLE:
        logger.warning("discord.py не установлен. Discord бот недоступен.")
        return None

    try:
        bot = TradingAlertBot(token=token, channel_id=channel_id)
        return bot
    except Exception as e:
        logger.error(f"Не удалось создать Discord бота: {e}")
        return None

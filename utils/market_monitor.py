"""
Фоновый мониторинг рынка для автоматического отслеживания алертов.
Запускается в отдельном потоке и периодически проверяет рынок на события.
Поддерживает WebSocket для real-time обновлений.
"""
import threading
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from utils.logger_config import setup_logging
from utils.market_data_manager import MarketDataManager
from utils.market_alerts import MarketAlerts
from config.market_config import POPULAR_PAIRS

try:
    from utils.websocket_manager import get_websocket_manager
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False
    get_websocket_manager = None

logger = setup_logging()


class MarketMonitor:
    """
    Фоновый мониторинг рынка для автоматического отслеживания событий.
    """

    def __init__(
        self,
        data_manager: Optional[MarketDataManager] = None,
        alerts: Optional[MarketAlerts] = None,
        monitoring_interval: int = 30,
        symbols: Optional[List[str]] = None,
        use_websocket: bool = True
    ):
        """
        Инициализация монитора рынка.

        Args:
            data_manager: Менеджер данных рынка
            alerts: Система алертов
            monitoring_interval: Интервал мониторинга в секундах (используется только при polling)
            symbols: Список символов для мониторинга (None для популярных)
            use_websocket: Использовать WebSocket для real-time обновлений
        """
        self.data_manager = data_manager or MarketDataManager()
        self.alerts = alerts or MarketAlerts(self.data_manager)
        self.monitoring_interval = monitoring_interval
        self.symbols = symbols or POPULAR_PAIRS[:50]  # Мониторим топ-50 пар
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.price_history: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[float]] = {}
        self.last_check_time: Dict[str, datetime] = {}
        self.telegram_bot = None  # Будет установлен из app.py
        
        # WebSocket для real-time обновлений
        self.use_websocket = use_websocket and HAS_WEBSOCKET
        self.ws_manager = None
        if self.use_websocket:
            try:
                self.ws_manager = get_websocket_manager('binance')
                if not self.ws_manager.is_available:
                    self.use_websocket = False
                    logger.info("WebSocket недоступен, используем polling")
            except Exception as e:
                logger.warning("Не удалось инициализировать WebSocket: %s", str(e))
                self.use_websocket = False

    def start(self):
        """Запустить мониторинг в фоновом потоке."""
        if self.is_running:
            logger.warning("Мониторинг уже запущен")
            return

        self.is_running = True

        # Если используем WebSocket, подписываемся на обновления
        if self.use_websocket and self.ws_manager:
            try:
                self.ws_manager.start()
                for symbol in self.symbols:
                    self.ws_manager.subscribe(symbol, self._websocket_price_callback)
                logger.info(
                    "Мониторинг рынка запущен через WebSocket для %s пар",
                    len(self.symbols)
                )
                # Запускаем polling как fallback
                self.monitor_thread = threading.Thread(
                    target=self._monitor_loop,
                    daemon=True,
                    name="MarketMonitor"
                )
                self.monitor_thread.start()
                return
            except Exception as e:
                logger.warning("Ошибка запуска WebSocket: %s, используем polling", str(e))
                self.use_websocket = False

        # Fallback на polling
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="MarketMonitor"
        )
        self.monitor_thread.start()
        logger.info(
            "Мониторинг рынка запущен (polling) для %s пар с интервалом %s сек",
            len(self.symbols),
            self.monitoring_interval
        )

    def stop(self):
        """Остановить мониторинг."""
        self.is_running = False
        if self.ws_manager:
            try:
                self.ws_manager.stop()
            except Exception as e:
                logger.warning("Ошибка остановки WebSocket: %s", str(e))
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Мониторинг рынка остановлен")

    def _websocket_price_callback(self, price_data: Dict[str, Any]):
        """
        Callback для обработки обновлений цен через WebSocket.

        Args:
            price_data: Данные о цене
        """
        try:
            symbol = price_data.get('symbol')
            if not symbol:
                return

            current_price = price_data.get('price', 0)
            current_volume = price_data.get('volume', 0)

            if current_price == 0:
                return

            # Проверяем изменение цены
            if symbol in self.price_history and self.price_history[symbol]:
                previous_price = self.price_history[symbol][-1]
                spike_detected = self.alerts.check_price_spike(symbol, current_price, previous_price)
                # Отправляем уведомление в Telegram если есть бот
                if spike_detected and self.telegram_bot:
                    change_pct = ((current_price - previous_price) / previous_price * 100) if previous_price > 0 else 0
                    self.telegram_bot.send_price_alert(symbol, current_price, change_pct, "spike")

            # Обновляем историю цен
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            self.price_history[symbol].append(current_price)
            if len(self.price_history[symbol]) > 10:
                self.price_history[symbol] = self.price_history[symbol][-10:]

            # Проверяем всплеск объема
            if symbol in self.volume_history and self.volume_history[symbol]:
                avg_volume = sum(self.volume_history[symbol]) / len(self.volume_history[symbol])
                self.alerts.check_volume_surge(symbol, current_volume, avg_volume)

            # Обновляем историю объемов
            if symbol not in self.volume_history:
                self.volume_history[symbol] = []
            self.volume_history[symbol].append(current_volume)
            if len(self.volume_history[symbol]) > 20:
                self.volume_history[symbol] = self.volume_history[symbol][-20:]

            # Проверяем прорывы уровней
            if symbol in self.price_history and len(self.price_history[symbol]) >= 5:
                prices = self.price_history[symbol]
                resistance = max(prices)
                support = min(prices)
                self.alerts.check_breakout(symbol, current_price, resistance, support)

            self.last_check_time[symbol] = datetime.now()

        except Exception as e:
            logger.warning("Ошибка обработки WebSocket callback: %s", str(e))

    def _monitor_loop(self):
        """Основной цикл мониторинга."""
        while self.is_running:
            try:
                self._check_market_events()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error("Ошибка в цикле мониторинга: %s", str(e))
                time.sleep(self.monitoring_interval)

    def _check_market_events(self):
        """Проверить события на рынке."""
        logger.debug("Проверка рыночных событий для %s пар", len(self.symbols))

        for symbol in self.symbols:
            try:
                # Получаем текущий тикер
                ticker = self.data_manager.get_ticker(symbol, 'binance')
                if not ticker:
                    continue

                current_price = ticker.get('last', 0)
                current_volume = ticker.get('quoteVolume', 0)

                if current_price == 0:
                    continue

                # Проверяем изменение цены
                if symbol in self.price_history:
                    previous_price = self.price_history[symbol][-1] if self.price_history[symbol] else current_price
                    spike_detected = self.alerts.check_price_spike(symbol, current_price, previous_price)
                    # Отправляем уведомление в Telegram если есть бот
                    if spike_detected and self.telegram_bot:
                        change_pct = ((current_price - previous_price) / previous_price * 100) if previous_price > 0 else 0
                        self.telegram_bot.send_price_alert(symbol, current_price, change_pct, "spike")
                else:
                    self.price_history[symbol] = []

                # Обновляем историю цен (храним последние 10 значений)
                self.price_history[symbol].append(current_price)
                if len(self.price_history[symbol]) > 10:
                    self.price_history[symbol] = self.price_history[symbol][-10:]

                # Проверяем всплеск объема
                if symbol in self.volume_history:
                    avg_volume = sum(self.volume_history[symbol]) / len(self.volume_history[symbol]) if self.volume_history[symbol] else current_volume
                    self.alerts.check_volume_surge(symbol, current_volume, avg_volume)
                else:
                    self.volume_history[symbol] = []

                # Обновляем историю объемов
                self.volume_history[symbol].append(current_volume)
                if len(self.volume_history[symbol]) > 20:
                    self.volume_history[symbol] = self.volume_history[symbol][-20:]

                # Проверяем прорывы уровней (упрощенная версия)
                if symbol in self.price_history and len(self.price_history[symbol]) >= 5:
                    prices = self.price_history[symbol]
                    resistance = max(prices)
                    support = min(prices)
                    self.alerts.check_breakout(symbol, current_price, resistance, support)

                self.last_check_time[symbol] = datetime.now()

            except Exception as e:
                logger.warning(
                    "Ошибка проверки событий для %s: %s",
                    symbol, str(e)
                )
                continue

        logger.debug("Проверка событий завершена")

    def add_symbol(self, symbol: str):
        """Добавить символ для мониторинга."""
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            logger.info("Добавлен символ для мониторинга: %s", symbol)

    def remove_symbol(self, symbol: str):
        """Удалить символ из мониторинга."""
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            self.price_history.pop(symbol, None)
            self.volume_history.pop(symbol, None)
            self.last_check_time.pop(symbol, None)
            logger.info("Удален символ из мониторинга: %s", symbol)

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Получить статистику мониторинга."""
        return {
            'is_running': self.is_running,
            'symbols_count': len(self.symbols),
            'monitoring_interval': self.monitoring_interval,
            'last_check_times': {
                symbol: time.isoformat()
                for symbol, time in self.last_check_time.items()
            }
        }


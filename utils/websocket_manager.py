"""
Менеджер WebSocket для интеграции real-time обновлений в dashboard.
Управляет WebSocket соединениями и обновляет данные в реальном времени.
"""

import threading
from collections import defaultdict
from typing import Any, Callable, Optional

from utils.logger_config import setup_logging

try:
    from web_interface.services.websocket_stream import WebSocketPriceStream

    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False
    WebSocketPriceStream = None

logger = setup_logging()


class WebSocketManager:
    """
    Менеджер WebSocket для real-time обновлений в dashboard.
    """

    def __init__(self, exchange_name: str = "binance"):
        """
        Инициализация менеджера WebSocket.

        Args:
            exchange_name: Имя биржи (binance, bybit, okx)
        """
        if not HAS_WEBSOCKET:
            logger.warning("WebSocket модуль не найден. Real-time обновления недоступны.")
            self.stream = None
            self.is_available = False
            return

        self.exchange_name = exchange_name
        self.stream = WebSocketPriceStream(exchange_name=exchange_name)
        self.is_available = True
        self.subscribers: dict[str, list[Callable]] = defaultdict(list)
        self.price_cache: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def start(self):
        """Запустить WebSocket stream."""
        if not self.is_available or not self.stream:
            logger.warning("WebSocket недоступен")
            return

        try:
            self.stream.start()
            logger.info("WebSocket менеджер запущен для %s", self.exchange_name)
        except Exception as e:
            logger.error("Ошибка запуска WebSocket: %s", str(e))

    def stop(self):
        """Остановить WebSocket stream."""
        if self.stream:
            try:
                self.stream.stop()
                logger.info("WebSocket менеджер остановлен")
            except Exception as e:
                logger.error("Ошибка остановки WebSocket: %s", str(e))

    def subscribe(self, symbol: str, callback: Callable[[dict[str, Any]], None]):
        """
        Подписаться на обновления цены для символа.

        Args:
            symbol: Торговая пара (например, 'BTC/USDT')
            callback: Функция для обработки обновлений
        """
        if not self.is_available or not self.stream:
            logger.warning("WebSocket недоступен для подписки на %s", symbol)
            return

        def price_update_handler(price_data: dict[str, Any]):
            """Обработчик обновлений цены."""
            try:
                # Обновляем кэш
                with self.lock:
                    self.price_cache[symbol] = price_data

                # Вызываем все callbacks для этого символа
                if symbol in self.subscribers:
                    for cb in self.subscribers[symbol]:
                        try:
                            cb(price_data)
                        except Exception as e:
                            logger.error("Ошибка в callback для %s: %s", symbol, str(e))
            except Exception as e:
                logger.error("Ошибка обработки обновления цены: %s", str(e))

        # Подписываемся через WebSocket stream
        self.stream.subscribe(symbol, price_update_handler)
        self.subscribers[symbol].append(callback)
        logger.debug("Подписка на %s добавлена", symbol)

    def unsubscribe(self, symbol: str, callback: Optional[Callable] = None):
        """
        Отписаться от обновлений для символа.

        Args:
            symbol: Торговая пара
            callback: Конкретный callback для удаления (None для всех)
        """
        if symbol in self.subscribers:
            if callback:
                if callback in self.subscribers[symbol]:
                    self.subscribers[symbol].remove(callback)
            else:
                self.subscribers[symbol].clear()

        logger.debug("Отписка от %s", symbol)

    def get_latest_price(self, symbol: str) -> Optional[dict[str, Any]]:
        """
        Получить последнюю цену из кэша.

        Args:
            symbol: Торговая пара

        Returns:
            Данные о цене или None
        """
        with self.lock:
            return self.price_cache.get(symbol)

    def get_all_prices(self) -> dict[str, dict[str, Any]]:
        """
        Получить все кэшированные цены.

        Returns:
            Словарь {symbol: price_data}
        """
        with self.lock:
            return self.price_cache.copy()

    def is_connected(self) -> bool:
        """Проверить, подключен ли WebSocket."""
        if not self.is_available or not self.stream:
            return False
        return self.stream.is_connected if hasattr(self.stream, "is_connected") else False


# Глобальный экземпляр менеджера
_global_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager(exchange_name: str = "binance") -> WebSocketManager:
    """
    Получить глобальный экземпляр WebSocket менеджера.

    Args:
        exchange_name: Имя биржи

    Returns:
        WebSocketManager экземпляр
    """
    global _global_ws_manager
    if _global_ws_manager is None:
        _global_ws_manager = WebSocketManager(exchange_name=exchange_name)
    return _global_ws_manager

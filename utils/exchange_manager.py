"""
Универсальный менеджер бирж для работы со всеми биржами через CCXT.
Автоматическое обнаружение доступных бирж, кэширование и управление rate limits.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

try:
    import ccxt

    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False
    ccxt = None

from utils.logger_config import setup_logging

logger = setup_logging()


class ExchangeManager:
    """
    Менеджер для работы со всеми биржами через CCXT.
    Управляет подключениями, кэшированием и rate limits.
    """

    def __init__(self):
        """Инициализация менеджера бирж."""
        if not HAS_CCXT:
            logger.warning("CCXT не установлен. Установите: pip install ccxt")
            self.exchanges: dict[str, Any] = {}
            self.markets_cache: dict[str, dict] = {}
            self.markets_cache_time: dict[str, datetime] = {}
            self.cache_ttl = timedelta(minutes=30)
            return

        self.exchanges: dict[str, Any] = {}
        self.markets_cache: dict[str, dict] = {}
        self.markets_cache_time: dict[str, datetime] = {}
        self.cache_ttl = timedelta(minutes=30)
        self.rate_limits: dict[str, float] = {}

        # Популярные биржи для быстрого доступа
        self.priority_exchanges = ["binance", "okx", "bybit", "gate", "kraken", "bitget", "bingx", "htx", "bitmart"]

    def get_all_exchanges(self) -> list[str]:
        """
        Получить список всех доступных бирж через CCXT.

        Returns:
            Список идентификаторов бирж
        """
        if not HAS_CCXT:
            return []

        try:
            # Получаем все биржи из CCXT
            all_exchanges = ccxt.exchanges
            logger.info("Найдено %s бирж в CCXT", len(all_exchanges))
            return sorted(all_exchanges)
        except Exception as e:
            logger.error("Ошибка получения списка бирж: %s", str(e))
            return []

    def get_exchange_instance(self, exchange_id: str, enable_rate_limit: bool = True) -> Optional[Any]:
        """
        Получить экземпляр биржи.

        Args:
            exchange_id: Идентификатор биржи (например, 'binance')
            enable_rate_limit: Включить автоматическое управление rate limits

        Returns:
            Экземпляр биржи или None при ошибке
        """
        if not HAS_CCXT:
            return None

        if exchange_id in self.exchanges:
            return self.exchanges[exchange_id]

        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({"enableRateLimit": enable_rate_limit, "options": {"defaultType": "spot"}})
            self.exchanges[exchange_id] = exchange
            logger.info("Создан экземпляр биржи: %s", exchange_id)
            return exchange
        except AttributeError:
            logger.warning("Биржа %s не найдена в CCXT", exchange_id)
            return None
        except Exception as e:
            logger.error("Ошибка создания экземпляра биржи %s: %s", exchange_id, str(e))
            return None

    def get_markets(self, exchange_id: str, force_refresh: bool = False) -> dict[str, Any]:
        """
        Получить список всех торговых пар для биржи.

        Args:
            exchange_id: Идентификатор биржи
            force_refresh: Принудительно обновить кэш

        Returns:
            Словарь с информацией о торговых парах
        """
        if not HAS_CCXT:
            return {}

        # Проверяем кэш
        if not force_refresh and exchange_id in self.markets_cache and exchange_id in self.markets_cache_time:
            cache_time = self.markets_cache_time[exchange_id]
            if datetime.now() - cache_time < self.cache_ttl:
                logger.debug("Используем кэш для биржи %s", exchange_id)
                return self.markets_cache[exchange_id]

        exchange = self.get_exchange_instance(exchange_id)
        if not exchange:
            return {}

        try:
            markets = exchange.load_markets()
            self.markets_cache[exchange_id] = markets
            self.markets_cache_time[exchange_id] = datetime.now()
            logger.info("Загружено %s пар для биржи %s", len(markets), exchange_id)
            return markets
        except Exception as e:
            logger.error("Ошибка загрузки рынков для %s: %s", exchange_id, str(e))
            return {}

    def get_all_pairs(self, exchange_id: Optional[str] = None) -> list[str]:
        """
        Получить список всех торговых пар.

        Args:
            exchange_id: Идентификатор биржи (None для всех бирж)

        Returns:
            Список торговых пар в формате 'BASE/QUOTE'
        """
        if not HAS_CCXT:
            return []

        pairs = set()

        if exchange_id:
            markets = self.get_markets(exchange_id)
            pairs.update(markets.keys())
        else:
            # Получаем пары со всех приоритетных бирж
            for ex_id in self.priority_exchanges:
                markets = self.get_markets(ex_id)
                pairs.update(markets.keys())

        return sorted(pairs)

    def fetch_ticker(self, symbol: str, exchange_id: str = "binance") -> Optional[dict[str, Any]]:
        """
        Получить тикер для торговой пары.

        Args:
            symbol: Торговая пара (например, 'BTC/USDT')
            exchange_id: Идентификатор биржи

        Returns:
            Словарь с данными тикера или None
        """
        if not HAS_CCXT:
            return None

        exchange = self.get_exchange_instance(exchange_id)
        if not exchange:
            return None

        try:
            ticker = exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            logger.warning("Ошибка получения тикера %s с %s: %s", symbol, exchange_id, str(e))
            return None

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "15m", limit: int = 200, exchange_id: str = "binance"
    ) -> Optional[list[list]]:
        """
        Получить OHLCV данные для торговой пары.

        Args:
            symbol: Торговая пара
            timeframe: Таймфрейм ('15m', '1h', '4h', '1d')
            limit: Количество свечей
            exchange_id: Идентификатор биржи

        Returns:
            Список OHLCV данных или None
        """
        if not HAS_CCXT:
            return None

        exchange = self.get_exchange_instance(exchange_id)
        if not exchange:
            return None

        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return ohlcv
        except Exception as e:
            logger.warning("Ошибка получения OHLCV %s %s с %s: %s", symbol, timeframe, exchange_id, str(e))
            return None

    def get_exchange_info(self, exchange_id: str) -> dict[str, Any]:
        """
        Получить информацию о бирже.

        Args:
            exchange_id: Идентификатор биржи

        Returns:
            Словарь с информацией о бирже
        """
        exchange = self.get_exchange_instance(exchange_id)
        if not exchange:
            return {}

        try:
            info = {
                "id": exchange.id,
                "name": exchange.name,
                "countries": getattr(exchange, "countries", []),
                "urls": getattr(exchange, "urls", {}),
                "version": getattr(exchange, "version", "unknown"),
                "rateLimit": getattr(exchange, "rateLimit", 0),
                "has": {
                    "fetchMarkets": exchange.has.get("fetchMarkets", False),
                    "fetchTicker": exchange.has.get("fetchTicker", False),
                    "fetchOHLCV": exchange.has.get("fetchOHLCV", False),
                },
            }
            return info
        except Exception as e:
            logger.error("Ошибка получения информации о бирже %s: %s", exchange_id, str(e))
            return {}

    def clear_cache(self, exchange_id: Optional[str] = None):
        """
        Очистить кэш рынков.

        Args:
            exchange_id: Идентификатор биржи (None для всех)
        """
        if exchange_id:
            self.markets_cache.pop(exchange_id, None)
            self.markets_cache_time.pop(exchange_id, None)
        else:
            self.markets_cache.clear()
            self.markets_cache_time.clear()
        logger.info("Кэш очищен для %s", exchange_id or "всех бирж")

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

        # Популярные биржи для быстрого доступа и фоллбека
        self.priority_exchanges = ["binance", "bybit", "okx", "kraken"]

        # Инициализируем основные биржи сразу
        for ex_id in self.priority_exchanges:
            self.get_exchange_instance(ex_id)

    def get_all_exchanges(self) -> list[str]:
        """Получить список всех доступных бирж через CCXT."""
        if not HAS_CCXT:
            return []
        try:
            return sorted(ccxt.exchanges)
        except Exception as e:
            logger.error("Ошибка получения списка бирж: %s", str(e))
            return []

    def get_exchange_instance(self, exchange_id: str, enable_rate_limit: bool = True) -> Optional[Any]:
        """Получить экземпляр биржи."""
        if not HAS_CCXT:
            return None

        if exchange_id in self.exchanges:
            return self.exchanges[exchange_id]

        try:
            exchange_class = getattr(ccxt, exchange_id)
            # Используем настройки для обхода блокировок если нужно
            config = {
                "enableRateLimit": enable_rate_limit,
                "options": {"defaultType": "spot"},
                "timeout": 10000,  # 10 секунд таймаут
            }
            exchange = exchange_class(config)
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
        """Получить список всех торговых пар для биржи."""
        if not HAS_CCXT:
            return {}

        # Проверяем кэш
        if not force_refresh and exchange_id in self.markets_cache and exchange_id in self.markets_cache_time:
            cache_time = self.markets_cache_time[exchange_id]
            if datetime.now() - cache_time < self.cache_ttl:
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

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "15m", limit: int = 200, exchange_id: str = "binance"
    ) -> Optional[list[list]]:
        """
        Получить OHLCV данные с автоматическим фоллбеком.
        """
        if not HAS_CCXT:
            return None

        # Список бирж для попытки: выбранная + остальные приоритетные
        target_exchanges = [exchange_id] + [ex for ex in self.priority_exchanges if ex != exchange_id]

        for ex_id in target_exchanges:
            exchange = self.get_exchange_instance(ex_id)
            if not exchange:
                continue

            try:
                # Проверяем поддерживает ли биржа эту пару
                if not exchange.markets or symbol not in exchange.markets:
                    self.get_markets(ex_id)  # Загружаем рынки если пусто

                # Если рынки не загрузились, пропускаем
                if not exchange.markets:
                    logger.warning(f"Markets not loaded for {ex_id}, skipping.")
                    continue

                # Если символа нет на этой бирже, пропускаем
                if symbol not in exchange.markets:
                    # Попробуем найти похожий символ (например BTC/USDT:USDT для фьючерсов)
                    continue

                logger.info(f"Запрос OHLCV {symbol} {timeframe} через {ex_id}")
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                if ohlcv and len(ohlcv) > 0:
                    return ohlcv

            except Exception as e:
                logger.warning(f"Ошибка получения данных с {ex_id}: {e}")
                continue

        logger.error(f"Не удалось получить данные для {symbol} ни с одной биржи")
        return None

    def fetch_ticker(self, symbol: str, exchange_id: str = "binance") -> Optional[dict[str, Any]]:
        """Получить тикер с фоллбеком."""
        if not HAS_CCXT:
            return None

        target_exchanges = [exchange_id] + [ex for ex in self.priority_exchanges if ex != exchange_id]

        for ex_id in target_exchanges:
            exchange = self.get_exchange_instance(ex_id)
            if not exchange:
                continue

            try:
                ticker = exchange.fetch_ticker(symbol)
                return ticker
            except Exception as e:
                logger.warning(f"Ошибка получения тикера с {ex_id}: {e}")
                continue

        return None

    def get_exchange_info(self, exchange_id: str) -> dict[str, Any]:
        """Получить информацию о бирже."""
        exchange = self.get_exchange_instance(exchange_id)
        if not exchange:
            return {}
        try:
            return {
                "id": exchange.id,
                "name": exchange.name,
                "rateLimit": getattr(exchange, "rateLimit", 0),
                "has": {
                    "fetchOHLCV": exchange.has.get("fetchOHLCV", False),
                    "fetchTicker": exchange.has.get("fetchTicker", False),
                },
            }
        except Exception:
            return {}

    def clear_cache(self, exchange_id: Optional[str] = None):
        if exchange_id:
            self.markets_cache.pop(exchange_id, None)
        else:
            self.markets_cache.clear()

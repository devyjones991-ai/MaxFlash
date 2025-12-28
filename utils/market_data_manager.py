"""
Система управления данными рынка.
Кэширование и управление данными всех торговых пар с TTL.

ОБНОВЛЕНО: Использует MultiSourceDataProvider вместо прямого Binance API
для избежания банов IP.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np
import pandas as pd

from utils.logger_config import setup_logging
from utils.market_cache import MarketCache
from utils.performance import global_profiler

# Новый мульти-источниковый провайдер
try:
    from utils.multi_source_provider import MultiSourceDataProvider, get_data_provider
    HAS_MULTI_SOURCE = True
except ImportError:
    HAS_MULTI_SOURCE = False
    MultiSourceDataProvider = None

# Legacy ExchangeManager как fallback
try:
    from utils.exchange_manager import ExchangeManager
    HAS_EXCHANGE_MANAGER = True
except ImportError:
    HAS_EXCHANGE_MANAGER = False
    ExchangeManager = None

logger = setup_logging()


class MarketDataManager:
    """
    Менеджер для кэширования и управления данными всех торговых пар.
    Поддерживает TTL, batch загрузку и статистику рынка.

    ВАЖНО: Теперь использует MultiSourceDataProvider (KuCoin, Kraken, OKX, CoinGecko)
    вместо Binance для избежания банов IP.
    """

    # Топ криптовалюты для мониторинга
    TOP_CRYPTO_PAIRS = [
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "SOL/USDT",
        "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
        "LINK/USDT", "ATOM/USDT", "LTC/USDT", "UNI/USDT", "XLM/USDT",
        "NEAR/USDT", "APT/USDT", "ARB/USDT", "OP/USDT", "SUI/USDT",
        "INJ/USDT", "FET/USDT", "RENDER/USDT", "TIA/USDT", "SEI/USDT",
        "PEPE/USDT", "WIF/USDT", "BONK/USDT", "FLOKI/USDT", "SHIB/USDT",
    ]

    def __init__(self, cache_ttl_minutes: int = 5, use_multi_source: bool = True):
        """
        Инициализация менеджера данных.

        Args:
            cache_ttl_minutes: Время жизни кэша в минутах
            use_multi_source: Использовать MultiSourceDataProvider (рекомендуется)
        """
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.ohlcv_cache: dict[str, dict[str, Any]] = {}
        self.tickers_cache: dict[str, dict[str, Any]] = {}
        self.cache_times: dict[str, datetime] = {}
        self.lock = threading.Lock()

        # Используем MarketCache для продвинутого кэширования
        self.market_cache = MarketCache(use_redis=False)

        # Инициализируем провайдеры
        self.use_multi_source = use_multi_source and HAS_MULTI_SOURCE
        self.data_provider: Optional[MultiSourceDataProvider] = None
        self.exchange_manager = None

        if self.use_multi_source:
            try:
                coingecko_key = os.getenv("COINGECKO_API_KEY")
                twelve_data_key = os.getenv("TWELVE_DATA_API_KEY")
                self.data_provider = MultiSourceDataProvider(
                    coingecko_api_key=coingecko_key,
                    twelve_data_api_key=twelve_data_key
                )
                logger.info("MarketDataManager: Using MultiSourceDataProvider (KuCoin/Kraken/OKX/CoinGecko)")
            except Exception as e:
                logger.warning(f"Failed to init MultiSourceDataProvider: {e}, falling back to ExchangeManager")
                self.use_multi_source = False

        if not self.use_multi_source and HAS_EXCHANGE_MANAGER:
            self.exchange_manager = ExchangeManager()
            logger.info("MarketDataManager: Using legacy ExchangeManager (may have Binance ban issues)")

    def _get_cache_key(self, symbol: str, exchange_id: str, timeframe: str) -> str:
        """Генерация ключа кэша."""
        return f"{exchange_id}:{symbol}:{timeframe}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Проверка валидности кэша."""
        if cache_key not in self.cache_times:
            return False
        cache_time = self.cache_times[cache_key]
        return datetime.now() - cache_time < self.cache_ttl

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 200,
        exchange_id: str = "auto",  # "auto" для автовыбора источника
        force_refresh: bool = False,
    ) -> Optional[pd.DataFrame]:
        """
        Получить OHLCV данные для торговой пары.

        Args:
            symbol: Торговая пара (например "BTC/USDT")
            timeframe: Таймфрейм ("1h", "4h", "1d" и т.д.)
            limit: Количество свечей
            exchange_id: "auto" для автовыбора или конкретная биржа
            force_refresh: Игнорировать кэш

        Returns:
            DataFrame с OHLCV данными или None
        """
        global_profiler.start("get_ohlcv")

        # Упрощенный кэш ключ
        cache_key = f"multi:{symbol}:{timeframe}"

        # Проверяем локальный кэш (простой TTL)
        if not force_refresh and cache_key in self.ohlcv_cache:
            cache_data = self.ohlcv_cache[cache_key]
            if datetime.now() - cache_data["time"] < self.cache_ttl:
                global_profiler.stop("get_ohlcv")
                return cache_data["df"].copy()

        df = None

        # Используем MultiSourceDataProvider
        if self.use_multi_source and self.data_provider:
            try:
                logger.info(f"Fetching {symbol} {timeframe} via MultiSourceProvider...")
                df = self.data_provider.get_ohlcv(symbol, timeframe, limit, force_refresh)

                if df is not None and not df.empty:
                    # Сохраняем в кэш
                    with self.lock:
                        self.ohlcv_cache[cache_key] = {"df": df.copy(), "time": datetime.now()}

                    elapsed = global_profiler.stop("get_ohlcv")
                    logger.info(
                        f"Loaded {len(df)} candles for {symbol} in {elapsed:.2f}s. Price: {df['close'].iloc[-1]:.2f}"
                    )
                    return df
            except Exception as e:
                logger.warning(f"MultiSourceProvider error for {symbol}: {e}")

        # Fallback на legacy ExchangeManager
        if self.exchange_manager:
            try:
                logger.info(f"Fallback: fetching {symbol} from ExchangeManager...")
                ohlcv_data = self.exchange_manager.fetch_ohlcv(symbol, timeframe, limit, exchange_id)

                if ohlcv_data:
                    df = pd.DataFrame(
                        ohlcv_data,
                        columns=["timestamp", "open", "high", "low", "close", "volume"]
                    )
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    df.set_index("timestamp", inplace=True)
                    df = df.sort_index()
                    df = df[~df.index.duplicated(keep="last")]

                    with self.lock:
                        self.ohlcv_cache[cache_key] = {"df": df.copy(), "time": datetime.now()}

                    elapsed = global_profiler.stop("get_ohlcv")
                    logger.info(f"Loaded {len(df)} candles for {symbol} (fallback) in {elapsed:.2f}s")
                    return df
            except Exception as e:
                logger.error(f"ExchangeManager error for {symbol}: {e}")

        logger.warning(f"Failed to fetch data for {symbol} from any source")
        global_profiler.stop("get_ohlcv")
        return None

    def batch_fetch_ohlcv(
        self,
        symbols: list[str],
        timeframe: str = "1h",
        limit: int = 150,
        exchange_id: str = "auto",
        max_workers: int = 3,  # Уменьшено для избежания rate limits
    ) -> dict[str, Optional[pd.DataFrame]]:
        """
        Batch загрузка OHLCV данных для множества пар с параллельной обработкой.

        Args:
            symbols: Список торговых пар
            timeframe: Таймфрейм
            limit: Количество свечей
            exchange_id: Идентификатор биржи или "auto"
            max_workers: Максимальное количество параллельных запросов

        Returns:
            Словарь {symbol: DataFrame}
        """
        global_profiler.start("batch_fetch_ohlcv")
        results: dict[str, Optional[pd.DataFrame]] = {}

        def fetch_symbol(symbol: str) -> tuple[str, Optional[pd.DataFrame]]:
            """Worker функция для загрузки одного символа."""
            try:
                df = self.get_ohlcv(symbol, timeframe, limit, exchange_id)
                return symbol, df
            except Exception as e:
                logger.warning("Ошибка загрузки данных для %s: %s", symbol, str(e))
                return symbol, None

        # Используем ThreadPoolExecutor для параллельной загрузки
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {executor.submit(fetch_symbol, symbol): symbol for symbol in symbols}

            for future in as_completed(future_to_symbol):
                symbol, df = future.result()
                results[symbol] = df

        elapsed = global_profiler.stop("batch_fetch_ohlcv")
        success_count = len([r for r in results.values() if r is not None])
        logger.info(
            "Загружено %s из %s пар за %.2f сек",
            success_count,
            len(symbols),
            elapsed,
        )
        return results

    def get_ticker(
        self, symbol: str, exchange_id: str = "auto", force_refresh: bool = False
    ) -> Optional[dict[str, Any]]:
        """
        Получить тикер для торговой пары.
        """
        cache_key = f"ticker:{symbol}"

        # Проверяем кэш
        if not force_refresh and cache_key in self.tickers_cache:
            cache_data = self.tickers_cache.get(cache_key)
            if cache_data and self._is_cache_valid(cache_key):
                return cache_data.copy()

        ticker = None

        # MultiSourceDataProvider
        if self.use_multi_source and self.data_provider:
            try:
                ticker = self.data_provider.get_ticker(symbol)
            except Exception as e:
                logger.warning(f"Ticker error from MultiSource for {symbol}: {e}")

        # Fallback
        if not ticker and self.exchange_manager:
            try:
                ticker = self.exchange_manager.fetch_ticker(symbol, exchange_id)
            except Exception as e:
                logger.warning(f"Ticker error from ExchangeManager for {symbol}: {e}")

        if ticker:
            with self.lock:
                self.tickers_cache[cache_key] = ticker.copy()
                self.cache_times[cache_key] = datetime.now()

        return ticker

    def get_all_pairs(self, exchange_id: Optional[str] = None) -> list[str]:
        """
        Получить список всех торговых пар.
        Возвращает предопределённый список топ пар для стабильности.
        """
        return self.TOP_CRYPTO_PAIRS.copy()

    def get_tickers(
        self,
        exchange_id: str = "auto",
        symbols: Optional[list[str]] = None,
        max_workers: int = 3,
    ) -> dict[str, dict[str, Any]]:
        """
        Получить тикеры для множества пар.
        """
        if symbols is None:
            symbols = self.TOP_CRYPTO_PAIRS

        global_profiler.start("get_tickers")
        tickers: dict[str, dict[str, Any]] = {}

        # Пробуем получить все тикеры через MultiSourceDataProvider
        if self.use_multi_source and self.data_provider:
            try:
                tickers = self.data_provider.get_tickers(symbols)
                if tickers:
                    elapsed = global_profiler.stop("get_tickers")
                    logger.info("Loaded %s tickers in %.2f sec", len(tickers), elapsed)
                    return tickers
            except Exception as e:
                logger.warning(f"Batch tickers error: {e}")

        # Fallback: загружаем по одному
        def fetch_ticker(symbol: str) -> tuple[str, Optional[dict[str, Any]]]:
            ticker = self.get_ticker(symbol, exchange_id)
            return symbol, ticker

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {executor.submit(fetch_ticker, symbol): symbol for symbol in symbols}

            for future in as_completed(future_to_symbol):
                symbol, ticker = future.result()
                if ticker:
                    tickers[symbol] = ticker

        elapsed = global_profiler.stop("get_tickers")
        logger.debug("Загружено %s тикеров за %.2f сек", len(tickers), elapsed)
        return tickers

    def get_market_stats(self) -> dict[str, Any]:
        """
        Получить общую статистику рынка.
        """
        try:
            # Через MultiSourceDataProvider
            if self.use_multi_source and self.data_provider:
                overview = self.data_provider.get_market_overview()
                crypto_markets = overview.get("crypto_markets", [])

                if crypto_markets:
                    # Извлекаем статистику из CoinGecko данных
                    total_volume = sum(m.get("total_volume", 0) for m in crypto_markets)
                    btc_data = next((m for m in crypto_markets if m.get("symbol") == "btc"), {})

                    # BTC доминация (приблизительно)
                    btc_market_cap = btc_data.get("market_cap", 0)
                    total_market_cap = sum(m.get("market_cap", 0) for m in crypto_markets)
                    btc_dominance = (btc_market_cap / total_market_cap * 100) if total_market_cap > 0 else 50

                    # Считаем рост/падение
                    up_24h = sum(1 for m in crypto_markets if m.get("price_change_percentage_24h", 0) > 0)
                    down_24h = len(crypto_markets) - up_24h

                    return {
                        "total_pairs": len(crypto_markets),
                        "active_pairs": len(crypto_markets),
                        "total_volume_24h": total_volume,
                        "avg_price": 0,  # Не имеет смысла для разных монет
                        "pairs_up_24h": up_24h,
                        "pairs_down_24h": down_24h,
                        "btc_dominance": min(btc_dominance, 100),
                        "btc_price": btc_data.get("current_price", 0),
                        "eth_price": next((m.get("current_price", 0) for m in crypto_markets if m.get("symbol") == "eth"), 0),
                        "source": "coingecko",
                        "timestamp": datetime.now().isoformat(),
                    }

            # Fallback на legacy метод
            tickers = self.get_tickers()
            if not tickers:
                return {}

            usdt_pairs = {k: v for k, v in tickers.items() if k.endswith("/USDT")}
            if not usdt_pairs:
                return {}

            volumes = [t.get("quoteVolume", 0) for t in usdt_pairs.values()]
            prices = [t.get("last", 0) for t in usdt_pairs.values() if t.get("last")]
            price_changes = [t.get("percentage", 0) for t in usdt_pairs.values()]

            btc_ticker = usdt_pairs.get("BTC/USDT", {})

            return {
                "total_pairs": len(usdt_pairs),
                "active_pairs": sum(1 for t in usdt_pairs.values() if t.get("quoteVolume", 0) > 0),
                "total_volume_24h": sum(volumes),
                "avg_price": np.mean(prices) if prices else 0,
                "pairs_up_24h": sum(1 for p in price_changes if p > 0),
                "pairs_down_24h": sum(1 for p in price_changes if p < 0),
                "btc_dominance": 50,  # Приблизительно
                "btc_price": btc_ticker.get("last", 0),
                "source": "ccxt",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error("Ошибка расчета статистики рынка: %s", str(e))
            return {}

    def get_health_status(self) -> dict[str, Any]:
        """Получить статус здоровья провайдеров данных."""
        if self.use_multi_source and self.data_provider:
            return self.data_provider.get_health_status()
        return {"status": "legacy_mode", "provider": "exchange_manager"}

    def clear_cache(self, symbol: Optional[str] = None):
        """
        Очистить кэш данных.
        """
        with self.lock:
            if symbol:
                keys_to_remove = [k for k in self.ohlcv_cache if symbol in k]
                for k in keys_to_remove:
                    self.ohlcv_cache.pop(k, None)
                    self.cache_times.pop(k, None)
                keys_to_remove = [k for k in self.tickers_cache if symbol in k]
                for k in keys_to_remove:
                    self.tickers_cache.pop(k, None)
            else:
                self.ohlcv_cache.clear()
                self.tickers_cache.clear()
                self.cache_times.clear()

        logger.info("Кэш очищен для %s", symbol or "всех пар")

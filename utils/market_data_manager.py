"""
Система управления данными рынка.
Кэширование и управление данными всех торговых пар с TTL.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np
import pandas as pd

from utils.exchange_manager import ExchangeManager
from utils.logger_config import setup_logging
from utils.market_cache import MarketCache
from utils.performance import global_profiler

logger = setup_logging()


class MarketDataManager:
    """
    Менеджер для кэширования и управления данными всех торговых пар.
    Поддерживает TTL, batch загрузку и статистику рынка.
    """

    def __init__(self, cache_ttl_minutes: int = 5):
        """
        Инициализация менеджера данных.

        Args:
            cache_ttl_minutes: Время жизни кэша в минутах
        """
        self.exchange_manager = ExchangeManager()
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.ohlcv_cache: dict[str, dict[str, Any]] = {}
        self.tickers_cache: dict[str, dict[str, Any]] = {}
        self.cache_times: dict[str, datetime] = {}
        self.lock = threading.Lock()
        # Используем MarketCache для продвинутого кэширования
        self.market_cache = MarketCache(use_redis=False)

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
        timeframe: str = "15m",
        limit: int = 200,
        exchange_id: str = "binance",
        force_refresh: bool = False,
    ) -> Optional[pd.DataFrame]:
        """
        Получить OHLCV данные для торговой пары.
        """
        global_profiler.start("get_ohlcv")

        # Упрощенный кэш ключ
        cache_key = f"{exchange_id}:{symbol}:{timeframe}"

        # Проверяем локальный кэш (простой TTL)
        if not force_refresh and cache_key in self.ohlcv_cache:
            cache_data = self.ohlcv_cache[cache_key]
            if datetime.now() - cache_data["time"] < self.cache_ttl:
                # logger.debug(f"Cache hit for {cache_key}")
                global_profiler.stop("get_ohlcv")
                return cache_data["df"].copy()

        # Загружаем данные через ExchangeManager (который теперь имеет фоллбек)
        logger.info(f"Fetching {symbol} from {exchange_id}...")
        ohlcv_data = self.exchange_manager.fetch_ohlcv(symbol, timeframe, limit, exchange_id)

        if not ohlcv_data:
            logger.warning(f"Failed to fetch data for {symbol} from {exchange_id}")
            global_profiler.stop("get_ohlcv")
            return None

        try:
            # Создаем DataFrame
            df = pd.DataFrame(ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            # Сортируем и убираем дубликаты
            df = df.sort_index()
            df = df[~df.index.duplicated(keep="last")]

            # Сохраняем в кэш
            with self.lock:
                self.ohlcv_cache[cache_key] = {"df": df.copy(), "time": datetime.now()}

            elapsed = global_profiler.stop("get_ohlcv")
            logger.info(
                f"Loaded {len(df)} candles for {symbol} from {exchange_id} in {elapsed:.2f}s. Price: {df['close'].iloc[-1]}"
            )
            return df

        except Exception as e:
            logger.error(f"Error processing data for {symbol}: {e}")
            global_profiler.stop("get_ohlcv")
            return None

    def batch_fetch_ohlcv(
        self,
        symbols: list[str],
        timeframe: str = "15m",
        limit: int = 150,
        exchange_id: str = "binance",  # Уменьшен лимит
        max_workers: int = 5,  # Уменьшено для производительности
    ) -> dict[str, Optional[pd.DataFrame]]:
        """
        Batch загрузка OHLCV данных для множества пар с параллельной обработкой.

        Args:
            symbols: Список торговых пар
            timeframe: Таймфрейм
            limit: Количество свечей
            exchange_id: Идентификатор биржи
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
            # Запускаем все задачи
            future_to_symbol = {executor.submit(fetch_symbol, symbol): symbol for symbol in symbols}

            # Собираем результаты по мере завершения
            for future in as_completed(future_to_symbol):
                symbol, df = future.result()
                results[symbol] = df

        elapsed = global_profiler.stop("batch_fetch_ohlcv")
        logger.info(
            "Загружено %s из %s пар за %.2f сек",
            len([r for r in results.values() if r is not None]),
            len(symbols),
            elapsed,
        )
        return results

    def get_ticker(
        self, symbol: str, exchange_id: str = "binance", force_refresh: bool = False
    ) -> Optional[dict[str, Any]]:
        """
        Получить тикер для торговой пары.

        Args:
            symbol: Торговая пара
            exchange_id: Идентификатор биржи
            force_refresh: Принудительно обновить кэш

        Returns:
            Словарь с данными тикера или None
        """
        cache_key = f"ticker:{exchange_id}:{symbol}"

        # Проверяем кэш
        if not force_refresh and cache_key in self.tickers_cache and self._is_cache_valid(cache_key):
            return self.tickers_cache[cache_key].copy()

        # Загружаем тикер
        ticker = self.exchange_manager.fetch_ticker(symbol, exchange_id)
        if not ticker:
            return None

        # Сохраняем в кэш
        with self.lock:
            self.tickers_cache[cache_key] = ticker.copy()
            self.cache_times[cache_key] = datetime.now()

        return ticker

    def get_all_pairs(self, exchange_id: Optional[str] = None) -> list[str]:
        """
        Получить список всех торговых пар.

        Args:
            exchange_id: Идентификатор биржи (None для всех)

        Returns:
            Список торговых пар
        """
        return self.exchange_manager.get_all_pairs(exchange_id)

    def get_tickers(
        self,
        exchange_id: str = "binance",
        symbols: Optional[list[str]] = None,
        max_workers: int = 5,  # Уменьшено по умолчанию для производительности
    ) -> dict[str, dict[str, Any]]:
        """
        Получить тикеры для множества пар с параллельной загрузкой.

        Args:
            exchange_id: Идентификатор биржи
            symbols: Список пар (None для всех)
            max_workers: Максимальное количество параллельных запросов

        Returns:
            Словарь {symbol: ticker_data}
        """
        if symbols is None:
            symbols = self.get_all_pairs(exchange_id)

        global_profiler.start("get_tickers")
        tickers: dict[str, dict[str, Any]] = {}

        def fetch_ticker(symbol: str) -> tuple[str, Optional[dict[str, Any]]]:
            """Worker функция для загрузки тикера."""
            ticker = self.get_ticker(symbol, exchange_id)
            return symbol, ticker

        # Параллельная загрузка для больших списков
        if len(symbols) > 5:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_symbol = {executor.submit(fetch_ticker, symbol): symbol for symbol in symbols}

                for future in as_completed(future_to_symbol):
                    symbol, ticker = future.result()
                    if ticker:
                        tickers[symbol] = ticker
        else:
            # Последовательная загрузка для малых списков
            for symbol in symbols:
                ticker = self.get_ticker(symbol, exchange_id)
                if ticker:
                    tickers[symbol] = ticker

        elapsed = global_profiler.stop("get_tickers")
        logger.debug("Загружено %s тикеров за %.2f сек", len(tickers), elapsed)
        return tickers

    def get_market_stats(self) -> dict[str, Any]:
        """
        Получить общую статистику рынка.

        Returns:
            Словарь со статистикой рынка
        """
        try:
            # Получаем тикеры с Binance (самая популярная биржа)
            tickers = self.get_tickers("binance")
            if not tickers:
                return {}

            # Фильтруем только USDT пары
            usdt_pairs = {k: v for k, v in tickers.items() if k.endswith("/USDT")}

            if not usdt_pairs:
                return {}

            # Вычисляем статистику
            volumes = [t["quoteVolume"] for t in usdt_pairs.values() if "quoteVolume" in t]
            prices = [t["last"] for t in usdt_pairs.values() if t.get("last")]

            total_volume = sum(volumes) if volumes else 0
            avg_price = np.mean(prices) if prices else 0
            price_change_24h = [t.get("percentage", 0) for t in usdt_pairs.values() if "percentage" in t]

            # Рассчитываем доминирование BTC
            btc_ticker = usdt_pairs.get("BTC/USDT", {})
            btc_market_cap = btc_ticker.get("quoteVolume", 0) * 24  # Примерная оценка
            btc_dominance = (btc_market_cap / total_volume * 24) * 100 if total_volume > 0 else 0

            # Количество активных пар (с объемом > 0)
            active_pairs = sum(1 for t in usdt_pairs.values() if t.get("quoteVolume", 0) > 0)

            stats = {
                "total_pairs": len(usdt_pairs),
                "active_pairs": active_pairs,
                "total_volume_24h": total_volume,
                "avg_price": avg_price,
                "pairs_up_24h": sum(1 for p in price_change_24h if p > 0),
                "pairs_down_24h": sum(1 for p in price_change_24h if p < 0),
                "btc_dominance": min(btc_dominance, 100),  # Ограничиваем до 100%
                "top_volume_pairs": sorted(usdt_pairs.items(), key=lambda x: x[1].get("quoteVolume", 0), reverse=True)[
                    :10
                ],
            }

            return stats
        except Exception as e:
            logger.error("Ошибка расчета статистики рынка: %s", str(e))
            return {}

    def clear_cache(self, symbol: Optional[str] = None):
        """
        Очистить кэш данных.

        Args:
            symbol: Торговая пара (None для всех)
        """
        with self.lock:
            if symbol:
                # Удаляем все записи для символа
                keys_to_remove = [k for k in self.ohlcv_cache if symbol in k]
                for k in keys_to_remove:
                    self.ohlcv_cache.pop(k, None)
                    self.cache_times.pop(k, None)
            else:
                self.ohlcv_cache.clear()
                self.tickers_cache.clear()
                self.cache_times.clear()

        logger.info("Кэш очищен для %s", symbol or "всех пар")

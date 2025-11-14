"""
Асинхронная загрузка данных для производительности.
Использует ThreadPoolExecutor для параллельной загрузки данных с разных бирж.
"""
import threading
from typing import Dict, List, Optional, Any, Callable
from queue import Queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger_config import setup_logging
from utils.market_data_manager import MarketDataManager
from utils.performance import global_profiler

logger = setup_logging()


class AsyncDataLoader:
    """
    Класс для асинхронной загрузки данных с использованием потоков.
    """

    def __init__(self, data_manager: Optional[MarketDataManager] = None):
        """
        Инициализация загрузчика.

        Args:
            data_manager: Менеджер данных рынка
        """
        self.data_manager = data_manager or MarketDataManager()
        self.thread_pool: List[threading.Thread] = []
        self.result_queue: Queue = Queue()

    def _load_ticker_worker(
        self, exchange_id: str, symbol: str, result_dict: Dict
    ):
        """
        Worker функция для загрузки тикера в отдельном потоке.

        Args:
            exchange_id: Идентификатор биржи
            symbol: Торговая пара
            result_dict: Словарь для сохранения результата
        """
        try:
            ticker = self.data_manager.get_ticker(symbol, exchange_id)
            result_dict[symbol] = ticker
        except Exception as e:
            logger.warning(
                "Ошибка загрузки тикера %s с %s: %s",
                symbol, exchange_id, str(e)
            )
            result_dict[symbol] = None

    def load_tickers_async(
        self, symbols: List[str], exchange_id: str = 'binance',
        max_workers: int = 15
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Асинхронная загрузка тикеров для множества пар с использованием ThreadPoolExecutor.

        Args:
            symbols: Список торговых пар
            exchange_id: Идентификатор биржи
            max_workers: Максимальное количество потоков

        Returns:
            Словарь {symbol: ticker_data}
        """
        global_profiler.start('load_tickers_async')
        results: Dict[str, Optional[Dict[str, Any]]] = {}

        def load_ticker(symbol: str) -> tuple[str, Optional[Dict[str, Any]]]:
            """Worker функция для загрузки тикера."""
            try:
                ticker = self.data_manager.get_ticker(symbol, exchange_id)
                return symbol, ticker
            except Exception as e:
                logger.warning(
                    "Ошибка загрузки тикера %s с %s: %s",
                    symbol, exchange_id, str(e)
                )
                return symbol, None

        # Используем ThreadPoolExecutor для лучшей производительности
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(load_ticker, symbol): symbol
                for symbol in symbols
            }
            
            for future in as_completed(future_to_symbol):
                symbol, ticker = future.result()
                results[symbol] = ticker

        elapsed = global_profiler.stop('load_tickers_async')
        logger.info(
            "Асинхронно загружено %s тикеров из %s за %.2f сек",
            len([v for v in results.values() if v]),
            len(symbols),
            elapsed
        )
        return results

    def load_ohlcv_async(
        self, symbols: List[str], timeframe: str = '15m',
        limit: int = 200, exchange_id: str = 'binance',
        max_workers: int = 10
    ) -> Dict[str, Any]:
        """
        Асинхронная загрузка OHLCV данных для множества пар с использованием ThreadPoolExecutor.

        Args:
            symbols: Список торговых пар
            timeframe: Таймфрейм
            limit: Количество свечей
            exchange_id: Идентификатор биржи
            max_workers: Максимальное количество потоков

        Returns:
            Словарь {symbol: dataframe}
        """
        global_profiler.start('load_ohlcv_async')
        results: Dict[str, Any] = {}

        def load_ohlcv(symbol: str) -> tuple[str, Any]:
            """Worker для загрузки OHLCV."""
            try:
                df = self.data_manager.get_ohlcv(
                    symbol, timeframe, limit, exchange_id
                )
                return symbol, df
            except Exception as e:
                logger.warning(
                    "Ошибка загрузки OHLCV %s: %s",
                    symbol, str(e)
                )
                return symbol, None

        # Используем ThreadPoolExecutor для параллельной загрузки
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(load_ohlcv, symbol): symbol
                for symbol in symbols
            }
            
            for future in as_completed(future_to_symbol):
                symbol, df = future.result()
                results[symbol] = df

        elapsed = global_profiler.stop('load_ohlcv_async')
        logger.info(
            "Асинхронно загружено %s OHLCV из %s за %.2f сек",
            len([r for r in results.values() if r is not None]),
            len(symbols),
            elapsed
        )
        return results


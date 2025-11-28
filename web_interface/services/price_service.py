"""
Сервис для получения актуальных цен и рыночных данных.
Обеспечивает real-time обновления цен для веб-интерфейса.
"""
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PriceService:
    """Сервис для работы с ценами в веб-интерфейсе."""

    def __init__(self, data_manager=None):
        """
        Инициализация сервиса цен.

        Args:
            data_manager: Экземпляр MarketDataManager
        """
        self.data_manager = data_manager

    def get_current_price(self, symbol: str, exchange: str = 'binance') -> Optional[float]:
        """
        Получить текущую цену для символа.

        Args:
            symbol: Торговая пара (например, BTC/USDT)
            exchange: Биржа (по умолчанию binance)

        Returns:
            Текущая цена или None
        """
        if not self.data_manager:
            logger.warning("MarketDataManager не инициализирован")
            return None

        try:
            ticker = self.data_manager.get_ticker(symbol, exchange)
            if ticker:
                return ticker.get('last', 0)
            return None
        except Exception as e:
            logger.error("Ошибка получения цены для %s: %s", symbol, str(e), exc_info=True)
            return None

    def get_ticker_data(self, symbol: str, exchange: str = 'binance') -> Dict[str, Any]:
        """
        Получить полные данные тикера для символа.

        Args:
            symbol: Торговая пара
            exchange: Биржа

        Returns:
            Словарь с данными тикера
        """
        if not self.data_manager:
            logger.warning("MarketDataManager не инициализирован")
            return {}

        try:
            ticker = self.data_manager.get_ticker(symbol, exchange)
            if ticker:
                return {
                    'price': ticker.get('last', 0),
                    'change_24h': ticker.get('percentage', 0),
                    'volume_24h': ticker.get('quoteVolume', 0),
                    'high_24h': ticker.get('high', 0),
                    'low_24h': ticker.get('low', 0),
                    'bid': ticker.get('bid', 0),
                    'ask': ticker.get('ask', 0),
                    'timestamp': datetime.now()
                }
            return {}
        except Exception as e:
            logger.error("Ошибка получения тикера для %s: %s", symbol, str(e), exc_info=True)
            return {}

    def get_multiple_prices(self, symbols: list, exchange: str = 'binance') -> Dict[str, float]:
        """
        Получить цены для нескольких символов.

        Args:
            symbols: Список торговых пар
            exchange: Биржа

        Returns:
            Словарь {symbol: price}
        """
        if not self.data_manager:
            return {}

        try:
            tickers = self.data_manager.get_tickers(exchange, symbols)
            prices = {}
            for symbol, ticker in tickers.items():
                if ticker:
                    prices[symbol] = ticker.get('last', 0)
            return prices
        except Exception as e:
            logger.error("Ошибка получения цен для множества символов: %s", str(e), exc_info=True)
            return {}


# Глобальный экземпляр сервиса
_price_service_instance: Optional[PriceService] = None


def get_price_service(data_manager=None) -> PriceService:
    """
    Получить или создать экземпляр PriceService (singleton).

    Args:
        data_manager: Экземпляр MarketDataManager

    Returns:
        Экземпляр PriceService
    """
    global _price_service_instance

    if _price_service_instance is None:
        _price_service_instance = PriceService(data_manager=data_manager)
    else:
        # Обновляем ссылку если передана
        if data_manager:
            _price_service_instance.data_manager = data_manager

    return _price_service_instance


"""
Универсальный адаптер для работы с различными биржами.
Поддерживает Binance, OKX, Bybit через CCXT с async поддержкой.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from enum import Enum

try:
    import ccxt
    import ccxt.async_support as ccxt_async
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False
    logging.warning("CCXT не установлен. Установите: pip install ccxt")

logger = logging.getLogger(__name__)


class ExchangeType(str, Enum):
    """Типы поддерживаемых бирж."""
    BINANCE = "binance"
    OKX = "okx"
    BYBIT = "bybit"


class ExchangeAdapter:
    """
    Универсальный адаптер для работы с биржами через CCXT.
    Поддерживает синхронные и асинхронные операции.
    """

    def __init__(
        self,
        exchange_type: ExchangeType = ExchangeType.BINANCE,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False
    ):
        """
        Инициализация адаптера биржи.

        Args:
            exchange_type: Тип биржи
            api_key: API ключ (опционально)
            api_secret: API секрет (опционально)
            sandbox: Использовать тестовую среду
        """
        if not HAS_CCXT:
            raise ImportError(
                "CCXT не установлен. Установите: pip install ccxt"
            )

        self.exchange_type = exchange_type
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox

        # Создаем синхронный и асинхронный экземпляры
        self._sync_exchange = None
        self._async_exchange = None

    @property
    def sync_exchange(self):
        """Получить синхронный экземпляр биржи."""
        if self._sync_exchange is None:
            exchange_class = getattr(ccxt, self.exchange_type.value)
            config = {
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'sandbox': self.sandbox,
                'enableRateLimit': True,
            }
            self._sync_exchange = exchange_class(config)
        return self._sync_exchange

    @property
    def async_exchange(self):
        """Получить асинхронный экземпляр биржи."""
        if self._async_exchange is None:
            exchange_class = getattr(
                ccxt_async, self.exchange_type.value
            )
            config = {
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'sandbox': self.sandbox,
                'enableRateLimit': True,
            }
            self._async_exchange = exchange_class(config)
        return self._async_exchange

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Получить тикер для символа (async).

        Args:
            symbol: Торговая пара (например, BTC/USDT)

        Returns:
            Словарь с данными тикера
        """
        try:
            ticker = await self.async_exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            logger.error(
                "Ошибка получения тикера %s: %s", symbol, str(e), exc_info=True
            )
            raise

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '15m',
        limit: int = 100
    ) -> List[List]:
        """
        Получить OHLCV данные (async).

        Args:
            symbol: Торговая пара
            timeframe: Таймфрейм (1m, 5m, 15m, 1h, 1d и т.д.)
            limit: Количество свечей

        Returns:
            Список свечей [[timestamp, open, high, low, close, volume], ...]
        """
        try:
            ohlcv = await self.async_exchange.fetch_ohlcv(
                symbol, timeframe, limit=limit
            )
            return ohlcv
        except Exception as e:
            logger.error(
                "Ошибка получения OHLCV для %s: %s",
                symbol, str(e), exc_info=True
            )
            raise

    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float
    ) -> Dict[str, Any]:
        """
        Создать рыночный ордер (async).

        Args:
            symbol: Торговая пара
            side: 'buy' или 'sell'
            amount: Количество

        Returns:
            Информация об ордере
        """
        try:
            order = await self.async_exchange.create_market_order(
                symbol, side, amount
            )
            logger.info(
                "Создан рыночный ордер: %s %s %s",
                symbol, side, amount
            )
            return order
        except Exception as e:
            logger.error(
                "Ошибка создания рыночного ордера: %s", str(e), exc_info=True
            )
            raise

    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float
    ) -> Dict[str, Any]:
        """
        Создать лимитный ордер (async).

        Args:
            symbol: Торговая пара
            side: 'buy' или 'sell'
            amount: Количество
            price: Цена

        Returns:
            Информация об ордере
        """
        try:
            order = await self.async_exchange.create_limit_order(
                symbol, side, amount, price
            )
            logger.info(
                "Создан лимитный ордер: %s %s %s @ %s",
                symbol, side, amount, price
            )
            return order
        except Exception as e:
            logger.error(
                "Ошибка создания лимитного ордера: %s", str(e), exc_info=True
            )
            raise

    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float
    ) -> Dict[str, Any]:
        """
        Создать стоп-лосс ордер (async).

        Args:
            symbol: Торговая пара
            side: 'buy' или 'sell'
            amount: Количество
            stop_price: Цена срабатывания стоп-лосса

        Returns:
            Информация об ордере
        """
        try:
            # Для стоп-лосса используем stop-loss order type
            order = await self.async_exchange.create_order(
                symbol=symbol,
                type='stop',
                side=side,
                amount=amount,
                price=stop_price,
                params={'stopPrice': stop_price}
            )
            logger.info(
                "Создан стоп-лосс ордер: %s %s %s @ %s",
                symbol, side, amount, stop_price
            )
            return order
        except Exception as e:
            logger.error(
                "Ошибка создания стоп-лосс ордера: %s", str(e), exc_info=True
            )
            raise

    async def cancel_order(
        self,
        order_id: str,
        symbol: str
    ) -> Dict[str, Any]:
        """
        Отменить ордер (async).

        Args:
            order_id: ID ордера
            symbol: Торговая пара

        Returns:
            Информация об отмененном ордере
        """
        try:
            result = await self.async_exchange.cancel_order(
                order_id, symbol
            )
            logger.info("Ордер отменен: %s", order_id)
            return result
        except Exception as e:
            logger.error(
                "Ошибка отмены ордера %s: %s", order_id, str(e), exc_info=True
            )
            raise

    async def fetch_balance(self) -> Dict[str, Any]:
        """
        Получить баланс аккаунта (async).

        Returns:
            Словарь с балансами
        """
        try:
            balance = await self.async_exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(
                "Ошибка получения баланса: %s", str(e), exc_info=True
            )
            raise

    async def fetch_open_orders(
        self,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить открытые ордера (async).

        Args:
            symbol: Торговая пара (опционально, если None - все ордера)

        Returns:
            Список открытых ордеров
        """
        try:
            orders = await self.async_exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            logger.error(
                "Ошибка получения открытых ордеров: %s", str(e), exc_info=True
            )
            raise

    async def fetch_positions(
        self,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить открытые позиции (async).

        Args:
            symbol: Торговая пара (опционально)

        Returns:
            Список позиций
        """
        try:
            if hasattr(self.async_exchange, 'fetch_positions'):
                positions = await self.async_exchange.fetch_positions(symbol)
                return positions
            else:
                logger.warning(
                    "Биржа %s не поддерживает fetch_positions",
                    self.exchange_type.value
                )
                return []
        except Exception as e:
            logger.error(
                "Ошибка получения позиций: %s", str(e), exc_info=True
            )
            raise

    async def close(self):
        """Закрыть соединения с биржей."""
        if self._async_exchange:
            await self._async_exchange.close()
        if self._sync_exchange:
            self._sync_exchange.close()

    def __del__(self):
        """Деструктор - закрываем соединения."""
        if self._sync_exchange:
            try:
                self._sync_exchange.close()
            except Exception:
                pass


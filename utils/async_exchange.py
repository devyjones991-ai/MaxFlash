"""
Fully async exchange manager using ccxt.async_support for high-performance trading.
Supports concurrent API calls for multiple symbols/exchanges.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    import ccxt.async_support as ccxt_async

    HAS_CCXT_ASYNC = True
except ImportError:
    HAS_CCXT_ASYNC = False
    ccxt_async = None

from utils.logger_config import setup_logging

logger = setup_logging()


class AsyncExchangeManager:
    """
    Fully async exchange manager for concurrent operations.
    Uses ccxt.async_support for non-blocking exchange API calls.
    """

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
    ):
        """
        Initialize async exchange manager.

        Args:
            exchange_id: Exchange identifier (e.g., 'binance', 'bybit')
            api_key: API key for authenticated requests
            api_secret: API secret for authenticated requests
            testnet: Use testnet/sandbox mode
        """
        if not HAS_CCXT_ASYNC:
            raise ImportError("ccxt.async_support not available. Install with: pip install 'ccxt[async]'")

        self.exchange_id = exchange_id
        self.exchange_class = getattr(ccxt_async, exchange_id)

        # Exchange configuration
        config = {
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }

        if api_key and api_secret:
            config["apiKey"] = api_key
            config["secret"] = api_secret

        if testnet:
            config["sandbox"] = True

        self.exchange = self.exchange_class(config)
        self._is_closed = False

        logger.info(f"AsyncExchangeManager initialized for {exchange_id} (testnet={testnet})")

    async def fetch_ohlcv(
        self, symbol: str, timeframe: str = "15m", limit: int = 200, since: Optional[int] = None
    ) -> Optional[List[List]]:
        """
        Fetch OHLCV data for a single symbol.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles
            since: Timestamp in milliseconds

        Returns:
            List of OHLCV arrays or None on error
        """
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            logger.debug(f"Fetched {len(ohlcv)} candles for {symbol} {timeframe}")
            return ohlcv
        except Exception as e:
            logger.warning(f"Error fetching OHLCV for {symbol}: {str(e)}")
            return None

    async def fetch_ohlcv_multi(
        self, symbols: List[str], timeframe: str = "15m", limit: int = 200
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Fetch OHLCV for multiple symbols concurrently (10-50x faster than sequential).

        Args:
            symbols: List of trading pairs
            timeframe: Timeframe
            limit: Number of candles

        Returns:
            Dictionary {symbol: DataFrame}
        """
        # Create concurrent tasks
        tasks = [self.fetch_ohlcv(symbol, timeframe, limit) for symbol in symbols]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        ohlcv_dict = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.warning(f"Error fetching {symbol}: {str(result)}")
                ohlcv_dict[symbol] = None
            elif result:
                # Convert to DataFrame
                df = pd.DataFrame(result, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                ohlcv_dict[symbol] = df
            else:
                ohlcv_dict[symbol] = None

        logger.info(
            f"Fetched OHLCV for {len([v for v in ohlcv_dict.values() if v is not None])}/{len(symbols)} symbols"
        )
        return ohlcv_dict

    async def fetch_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch ticker data for a symbol.

        Args:
            symbol: Trading pair

        Returns:
            Ticker dictionary or None
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            logger.warning(f"Error fetching ticker for {symbol}: {str(e)}")
            return None

    async def fetch_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fetch tickers for multiple symbols concurrently.

        Args:
            symbols: List of symbols (None for all available)

        Returns:
            Dictionary {symbol: ticker_data}
        """
        try:
            if symbols:
                # Fetch specific symbols concurrently
                tasks = [self.fetch_ticker(symbol) for symbol in symbols]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                tickers = {}
                for symbol, result in zip(symbols, results):
                    if not isinstance(result, Exception) and result:
                        tickers[symbol] = result
                return tickers
            else:
                # Fetch all tickers at once (most exchanges support this)
                tickers = await self.exchange.fetch_tickers()
                return tickers
        except Exception as e:
            logger.error(f"Error fetching tickers: {str(e)}")
            return {}

    async def fetch_balance(self) -> Dict[str, Any]:
        """
        Fetch account balance (requires API credentials).

        Returns:
            Balance dictionary
        """
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance: {str(e)}")
            return {}

    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create an order (requires API credentials).

        Args:
            symbol: Trading pair
            order_type: 'market' or 'limit'
            side: 'buy' or 'sell'
            amount: Order amount
            price: Price for limit orders
            params: Additional parameters

        Returns:
            Order details or None
        """
        try:
            order = await self.exchange.create_order(
                symbol=symbol, type=order_type, side=side, amount=amount, price=price, params=params or {}
            )
            logger.info(f"Order created: {order['id']} ({symbol} {side} {amount})")
            return order
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return None

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            True if successful
        """
        try:
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return False

    async def fetch_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch order status.

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            Order details or None
        """
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            logger.warning(f"Error fetching order {order_id}: {str(e)}")
            return None

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch open orders.

        Args:
            symbol: Trading pair (None for all)

        Returns:
            List of open orders
        """
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            logger.error(f"Error fetching open orders: {str(e)}")
            return []

    async def fetch_markets(self) -> Dict[str, Any]:
        """
        Fetch all available markets/trading pairs.

        Returns:
            Markets dictionary
        """
        try:
            markets = await self.exchange.load_markets()
            return markets
        except Exception as e:
            logger.error(f"Error fetching markets: {str(e)}")
            return {}

    async def close(self):
        """Close exchange connection and cleanup resources."""
        if not self._is_closed:
            await self.exchange.close()
            self._is_closed = True
            logger.info(f"AsyncExchangeManager closed for {self.exchange_id}")

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()


# Singleton instance management
_global_async_exchanges: Dict[str, AsyncExchangeManager] = {}


async def get_async_exchange(
    exchange_id: str = "binance",
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    testnet: bool = False,
) -> AsyncExchangeManager:
    """
    Get or create async exchange manager instance.

    Args:
        exchange_id: Exchange identifier
        api_key: API key (optional)
        api_secret: API secret (optional)
        testnet: Use testnet mode

    Returns:
        AsyncExchangeManager instance
    """
    cache_key = f"{exchange_id}_{testnet}"

    if cache_key not in _global_async_exchanges:
        manager = AsyncExchangeManager(exchange_id=exchange_id, api_key=api_key, api_secret=api_secret, testnet=testnet)
        _global_async_exchanges[cache_key] = manager

    return _global_async_exchanges[cache_key]


async def cleanup_all_exchanges():
    """Cleanup all exchange connections."""
    for manager in _global_async_exchanges.values():
        await manager.close()
    _global_async_exchanges.clear()
    logger.info("All async exchange connections closed")

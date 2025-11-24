"""
Order execution engine for live trading.
Handles order placement, monitoring, and error recovery.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from utils.async_exchange import AsyncExchangeManager, get_async_exchange
from utils.logger_config import setup_logging

logger = setup_logging()


class OrderStatus(Enum):
    """Order status enumeration."""

    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderExecutor:
    """
    Advanced order executor with validation, retries, and monitoring.
    Supports market, limit, and stop-limit orders with automatic SL/TP placement.
    """

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,  # Default to testnet for safety
    ):
        """
        Initialize order executor.

        Args:
            exchange_id: Exchange identifier
            api_key: API key for trading
            api_secret: API secret for trading
            testnet: Use testnet/paper trading mode
        """
        self.exchange_id = exchange_id
        self.testnet = testnet
        self.api_key = api_key
        self.api_secret = api_secret
        self.exchange: Optional[AsyncExchangeManager] = None

        # Order tracking
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        self.order_history: List[Dict[str, Any]] = []

        logger.info(f"OrderExecutor initialized (testnet={testnet})")

    async def initialize(self):
        """Initialize exchange connection."""
        self.exchange = await get_async_exchange(
            exchange_id=self.exchange_id,
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=self.testnet,
        )
        logger.info("Exchange connection established")

    async def validate_balance(self, symbol: str, side: str, amount: float, price: Optional[float] = None) -> bool:
        """
        Validate sufficient balance for order.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Order amount
            price: Order price (for limit orders)

        Returns:
            True if sufficient balance
        """
        try:
            balance = await self.exchange.fetch_balance()

            # Parse symbol
            base, quote = symbol.split("/")

            if side == "buy":
                # Need quote currency
                required = amount * (price if price else 0)
                available = balance.get(quote, {}).get("free", 0)

                if available < required:
                    logger.warning(f"Insufficient {quote} balance: need {required}, have {available}")
                    return False
            else:  # sell
                # Need base currency
                available = balance.get(base, {}).get("free", 0)

                if available < amount:
                    logger.warning(f"Insufficient {base} balance: need {amount}, have {available}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating balance: {str(e)}")
            return False

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = "market",
        amount: float = None,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        validate_balance: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Place an order with optional SL/TP.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', or 'stop_limit'
            amount: Order amount
            price: Price for limit orders
            stop_loss: Stop-loss price (optional)
            take_profit: Take-profit price (optional)
            validate_balance: Check balance before placing

        Returns:
            Order details or None on failure
        """
        if not self.exchange:
            await self.initialize()

        try:
            # Validate balance
            if validate_balance:
                if not await self.validate_balance(symbol, side, amount, price):
                    logger.error("Balance validation failed")
                    return None

            # Place main order
            logger.info(f"Placing {order_type} {side} order: {amount} {symbol} @ {price or 'market'}")

            order = await self.exchange.create_order(
                symbol=symbol, order_type=order_type, side=side, amount=amount, price=price
            )

            if not order:
                logger.error("Order placement failed")
                return None

            order_id = order["id"]
            logger.info(f"Order placed successfully: {order_id}")

            # Track order
            self.active_orders[order_id] = {
                "order": order,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "placed_at": datetime.now(),
                "sl_order_id": None,
                "tp_order_id": None,
            }

            # Place stop-loss order
            if stop_loss:
                sl_order = await self._place_stop_loss(symbol, side, amount, stop_loss)
                if sl_order:
                    self.active_orders[order_id]["sl_order_id"] = sl_order["id"]
                    logger.info(f"Stop-loss placed: {sl_order['id']} @ {stop_loss}")

            # Place take-profit order
            if take_profit:
                tp_order = await self._place_take_profit(symbol, side, amount, take_profit)
                if tp_order:
                    self.active_orders[order_id]["tp_order_id"] = tp_order["id"]
                    logger.info(f"Take-profit placed: {tp_order['id']} @ {take_profit}")

            return order

        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return None

    async def _place_stop_loss(
        self, symbol: str, side: str, amount: float, stop_price: float
    ) -> Optional[Dict[str, Any]]:
        """Place stop-loss order."""
        try:
            # Reverse side for stop-loss
            sl_side = "sell" if side == "buy" else "buy"

            # Use stop-limit order
            order = await self.exchange.create_order(
                symbol=symbol,
                order_type="stop_limit",
                side=sl_side,
                amount=amount,
                price=stop_price * 0.995 if sl_side == "sell" else stop_price * 1.005,  # 0.5% slippage
                params={"stopPrice": stop_price},
            )

            return order

        except Exception as e:
            logger.error(f"Error placing stop-loss: {str(e)}")
            return None

    async def _place_take_profit(
        self, symbol: str, side: str, amount: float, tp_price: float
    ) -> Optional[Dict[str, Any]]:
        """Place take-profit order."""
        try:
            # Reverse side for take-profit
            tp_side = "sell" if side == "buy" else "buy"

            order = await self.exchange.create_order(
                symbol=symbol, order_type="limit", side=tp_side, amount=amount, price=tp_price
            )

            return order

        except Exception as e:
            logger.error(f"Error placing take-profit: {str(e)}")
            return None

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel
            symbol: Trading pair

        Returns:
            True if cancelled successfully
        """
        try:
            success = await self.exchange.cancel_order(order_id, symbol)

            if success and order_id in self.active_orders:
                # Also cancel SL/TP orders
                sl_id = self.active_orders[order_id].get("sl_order_id")
                tp_id = self.active_orders[order_id].get("tp_order_id")

                if sl_id:
                    await self.exchange.cancel_order(sl_id, symbol)
                if tp_id:
                    await self.exchange.cancel_order(tp_id, symbol)

                # Move to history
                self.order_history.append(self.active_orders.pop(order_id))

            return success

        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return False

    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current order status.

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            Order details with current status
        """
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            logger.warning(f"Error fetching order status {order_id}: {str(e)}")
            return None

    async def monitor_orders(self, check_interval: int = 5):
        """
        Monitor active orders and update their status.

        Args:
            check_interval: Seconds between status checks
        """
        logger.info(f"Starting order monitoring (interval={check_interval}s)")

        while True:
            try:
                for order_id, order_data in list(self.active_orders.items()):
                    symbol = order_data["symbol"]

                    # Check order status
                    status = await self.get_order_status(order_id, symbol)

                    if status:
                        order_status = status.get("status")

                        # Handle filled/cancelled orders
                        if order_status in ["closed", "filled", "cancelled", "expired"]:
                            logger.info(f"Order {order_id} {order_status}")

                            # Move to history
                            order_data["final_status"] = order_status
                            order_data["completed_at"] = datetime.now()
                            self.order_history.append(order_data)
                            del self.active_orders[order_id]

                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in order monitoring: {str(e)}")
                await asyncio.sleep(check_interval)

    async def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get list of active orders."""
        return list(self.active_orders.values())

    async def cancel_all_orders(self, symbol: Optional[str] = None):
        """
        Cancel all active orders.

        Args:
            symbol: Trading pair (None for all pairs)
        """
        logger.info(f"Cancelling all orders{f' for {symbol}' if symbol else ''}")

        for order_id, order_data in list(self.active_orders.items()):
            if symbol is None or order_data["symbol"] == symbol:
                await self.cancel_order(order_id, order_data["symbol"])

    async def close(self):
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()
            logger.info("OrderExecutor closed")

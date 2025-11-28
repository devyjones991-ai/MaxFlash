"""
Клиент для Binance Spot API.
"""
from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Dict, Optional, List
import structlog
from app.config import settings

logger = structlog.get_logger()


class BinanceClient:
    """Клиент для работы с Binance API."""
    
    def __init__(self, testnet: bool = None):
        self.testnet = testnet if testnet is not None else settings.BINANCE_TESTNET
        self.api_key = settings.BINANCE_API_KEY
        self.api_secret = settings.BINANCE_API_SECRET
        
        if not self.api_key or not self.api_secret:
            logger.warning("Binance API credentials not configured")
            self.client = None
        else:
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet
            )
    
    def get_account_info(self) -> Optional[Dict]:
        """Получить информацию об аккаунте."""
        if not self.client:
            return None
        
        try:
            account = self.client.get_account()
            return account
        except BinanceAPIException as e:
            logger.error("Error getting account info", error=str(e))
            return None
    
    def get_balance(self, asset: str = "USDT") -> float:
        """Получить баланс актива."""
        if not self.client:
            return 0.0
        
        try:
            balance = self.client.get_asset_balance(asset=asset)
            return float(balance.get("free", 0))
        except BinanceAPIException as e:
            logger.error("Error getting balance", asset=asset, error=str(e))
            return 0.0
    
    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """Получить текущую цену символа."""
        if not self.client:
            return None
        
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except BinanceAPIException as e:
            logger.error("Error getting price", symbol=symbol, error=str(e))
            return None
    
    def place_order(
        self,
        symbol: str,
        side: str,  # 'BUY' or 'SELL'
        order_type: str,  # 'MARKET', 'LIMIT', etc.
        quantity: float = None,
        price: float = None,
        time_in_force: str = "GTC"
    ) -> Optional[Dict]:
        """
        Разместить ордер.
        
        Args:
            symbol: Торговая пара (например, 'BTCUSDT')
            side: 'BUY' or 'SELL'
            order_type: Тип ордера
            quantity: Количество
            price: Цена (для LIMIT)
            time_in_force: Время действия (GTC, IOC, FOK)
        """
        if not self.client:
            logger.warning("Binance client not initialized")
            return None
        
        try:
            if order_type == "MARKET":
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity
                )
            elif order_type == "LIMIT":
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    timeInForce=time_in_force,
                    quantity=quantity,
                    price=price
                )
            else:
                logger.error("Unsupported order type", order_type=order_type)
                return None
            
            logger.info(
                "Order placed",
                symbol=symbol,
                side=side,
                order_id=order.get("orderId")
            )
            
            return order
        except BinanceAPIException as e:
            logger.error("Error placing order", symbol=symbol, error=str(e))
            return None
    
    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """Отменить ордер."""
        if not self.client:
            return False
        
        try:
            self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info("Order cancelled", symbol=symbol, order_id=order_id)
            return True
        except BinanceAPIException as e:
            logger.error("Error cancelling order", symbol=symbol, error=str(e))
            return False
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Получить открытые ордера."""
        if not self.client:
            return []
        
        try:
            if symbol:
                orders = self.client.get_open_orders(symbol=symbol)
            else:
                orders = self.client.get_open_orders()
            return orders
        except BinanceAPIException as e:
            logger.error("Error getting open orders", error=str(e))
            return []
    
    def get_order_status(self, symbol: str, order_id: int) -> Optional[Dict]:
        """Получить статус ордера."""
        if not self.client:
            return None
        
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return order
        except BinanceAPIException as e:
            logger.error("Error getting order status", error=str(e))
            return None


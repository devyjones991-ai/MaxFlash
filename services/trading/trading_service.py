"""
Сервис автоторговли на Binance Spot.
"""
from typing import Dict, Optional
import structlog
from datetime import datetime
from app.database import AsyncSession
from app.models.trade import Trade, TradeStatus, TradeSide
from app.models.signal import Signal
from app.repositories.signal_repository import SignalRepository
from services.trading.binance_client import BinanceClient
from services.trading.risk_manager import RiskManager

logger = structlog.get_logger()


class TradingService:
    """Сервис автоторговли."""
    
    def __init__(self, db: AsyncSession, paper_trading: bool = True):
        self.db = db
        self.paper_trading = paper_trading
        self.binance_client = BinanceClient(testnet=paper_trading)
        self.risk_manager = RiskManager(db, self.binance_client)
        self.signal_repo = SignalRepository(db)
    
    async def execute_signal(
        self,
        signal_id: int
    ) -> Optional[Trade]:
        """
        Исполнить торговый сигнал.
        
        Args:
            signal_id: ID сигнала
        
        Returns:
            Созданная сделка или None
        """
        # Получаем сигнал
        signal = await self.signal_repo.get_by_id(signal_id)
        
        if not signal:
            logger.warning("Signal not found", signal_id=signal_id)
            return None
        
        if not signal.is_active:
            logger.warning("Signal is not active", signal_id=signal_id)
            return None
        
        # Конвертируем символ для Binance (упрощённо)
        binance_symbol = signal.symbol.replace("/", "")
        
        # Получаем текущую цену
        current_price = self.binance_client.get_symbol_price(binance_symbol)
        
        if not current_price:
            logger.error("Could not get current price", symbol=binance_symbol)
            return None
        
        # Рассчитываем размер позиции
        quantity = await self.risk_manager.calculate_position_size(
            binance_symbol,
            current_price
        )
        
        if quantity <= 0:
            logger.warning("Invalid position size", quantity=quantity)
            return None
        
        # Валидируем сделку
        validation = await self.risk_manager.validate_trade(
            binance_symbol,
            current_price,
            quantity
        )
        
        if not validation.get("valid", False):
            logger.warning("Trade validation failed", validation=validation)
            return None
        
        # Создаём сделку в БД
        trade_data = {
            "signal_id": signal_id,
            "exchange": "binance",
            "symbol": signal.symbol,
            "side": TradeSide.BUY if signal.signal_type.value == "long" else TradeSide.SELL,
            "status": TradeStatus.PENDING,
            "quantity": quantity,
            "price": current_price,
            "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
            "take_profit": float(signal.take_profit) if signal.take_profit else None,
        }
        
        trade = Trade(**trade_data)
        self.db.add(trade)
        await self.db.commit()
        await self.db.refresh(trade)
        
        # Если не paper trading, размещаем реальный ордер
        if not self.paper_trading:
            order = self.binance_client.place_order(
                symbol=binance_symbol,
                side="BUY" if signal.signal_type.value == "long" else "SELL",
                order_type="MARKET",
                quantity=quantity
            )
            
            if order:
                trade.exchange_order_id = str(order.get("orderId"))
                trade.status = TradeStatus.OPEN
                trade.opened_at = datetime.utcnow()
                await self.db.commit()
            else:
                trade.status = TradeStatus.ERROR
                await self.db.commit()
                logger.error("Failed to place order", trade_id=trade.id)
                return None
        else:
            # Paper trading - просто отмечаем как открытую
            trade.status = TradeStatus.OPEN
            trade.opened_at = datetime.utcnow()
            await self.db.commit()
            logger.info("Paper trade executed", trade_id=trade.id)
        
        logger.info(
            "Signal executed",
            signal_id=signal_id,
            trade_id=trade.id,
            paper_trading=self.paper_trading
        )
        
        return trade
    
    async def monitor_open_trades(self):
        """Мониторинг открытых сделок (проверка SL/TP)."""
        # Получаем открытые сделки
        from sqlalchemy import select
        result = await self.db.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        open_trades = result.scalars().all()
        
        for trade in open_trades:
            try:
                # Получаем текущую цену
                binance_symbol = trade.symbol.replace("/", "")
                current_price = self.binance_client.get_symbol_price(binance_symbol)
                
                if not current_price:
                    continue
                
                # Проверяем Stop Loss
                if trade.stop_loss:
                    if trade.side.value == "buy":
                        if current_price <= float(trade.stop_loss):
                            await self._close_trade(trade, current_price, "stop_loss")
                            continue
                    else:  # sell
                        if current_price >= float(trade.stop_loss):
                            await self._close_trade(trade, current_price, "stop_loss")
                            continue
                
                # Проверяем Take Profit
                if trade.take_profit:
                    if trade.side.value == "buy":
                        if current_price >= float(trade.take_profit):
                            await self._close_trade(trade, current_price, "take_profit")
                            continue
                    else:  # sell
                        if current_price <= float(trade.take_profit):
                            await self._close_trade(trade, current_price, "take_profit")
                            continue
                
            except Exception as e:
                logger.error("Error monitoring trade", trade_id=trade.id, error=str(e))
                continue
    
    async def _close_trade(
        self,
        trade: Trade,
        exit_price: float,
        reason: str
    ):
        """Закрыть сделку."""
        entry_price = float(trade.price or 0)
        
        if trade.side.value == "buy":
            pnl = (exit_price - entry_price) * float(trade.quantity)
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:  # sell
            pnl = (entry_price - exit_price) * float(trade.quantity)
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
        trade.status = TradeStatus.CLOSED
        trade.exit_price = exit_price
        trade.pnl = pnl
        trade.pnl_percent = pnl_percent
        trade.closed_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(
            "Trade closed",
            trade_id=trade.id,
            reason=reason,
            pnl=pnl,
            pnl_percent=pnl_percent
        )


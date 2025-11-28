"""
Модели для торговых сделок.
"""
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class TradeStatus(str, enum.Enum):
    """Статус сделки."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    CLOSED = "closed"
    ERROR = "error"


class TradeSide(str, enum.Enum):
    """Сторона сделки."""
    BUY = "buy"
    SELL = "sell"


class Trade(Base):
    """Модель торговой сделки."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    
    # Основная информация
    exchange = Column(String(20), default="binance", nullable=False)
    symbol = Column(String(20), index=True, nullable=False)
    side = Column(SQLEnum(TradeSide), nullable=False)
    status = Column(SQLEnum(TradeStatus), default=TradeStatus.PENDING, index=True)
    
    # Размеры
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8))
    filled_quantity = Column(Numeric(20, 8), default=0.0)
    average_price = Column(Numeric(20, 8))
    
    # Цены для SL/TP
    stop_loss = Column(Numeric(20, 8))
    take_profit = Column(Numeric(20, 8))
    trailing_stop_percent = Column(Numeric(5, 2))
    
    # Результаты
    pnl = Column(Numeric(20, 8))
    pnl_percent = Column(Numeric(10, 4))
    fee = Column(Numeric(20, 8), default=0.0)
    
    # Exchange информация
    exchange_order_id = Column(String(100))
    exchange_client_order_id = Column(String(100))
    
    # Параметры обучения
    learning_params = Column(Text)  # JSON с параметрами от ML модели
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    opened_at = Column(DateTime)
    closed_at = Column(DateTime)
    
    # Relationships
    executions = relationship("TradeExecution", back_populates="trade", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Trade {self.symbol} {self.side.value} {self.status.value}>"


class TradeExecution(Base):
    """Модель исполнения сделки (частичное заполнение)."""
    __tablename__ = "trade_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    
    # Исполнение
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    fee = Column(Numeric(20, 8), default=0.0)
    
    # Exchange информация
    exchange_execution_id = Column(String(100))
    
    # Временная метка
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    trade = relationship("Trade", back_populates="executions")
    
    def __repr__(self):
        return f"<TradeExecution {self.quantity} @ {self.price}>"


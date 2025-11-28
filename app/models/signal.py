"""
Модели для торговых сигналов.
"""
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class SignalRating(str, enum.Enum):
    """Рейтинг сигнала."""
    FREE = "free"  # T1 - бесплатные
    PRO = "pro"    # T2 - платные
    ALPHA = "alpha"  # T3 - премиум


class SignalType(str, enum.Enum):
    """Тип сигнала."""
    LONG = "long"
    SHORT = "short"
    EXIT = "exit"


class Signal(Base):
    """Модель торгового сигнала."""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    
    # Основная информация
    symbol = Column(String(20), index=True, nullable=False)
    signal_type = Column(SQLEnum(SignalType), nullable=False)
    rating = Column(SQLEnum(SignalRating), nullable=False, index=True)
    
    # Цены
    entry_price = Column(Numeric(20, 8), nullable=False)
    stop_loss = Column(Numeric(20, 8))
    take_profit = Column(Numeric(20, 8))
    current_price = Column(Numeric(20, 8))
    
    # Метрики сигнала
    signal_score = Column(Numeric(5, 4), nullable=False)  # 0.0 - 1.0
    confidence = Column(Numeric(5, 4))  # 0.0 - 1.0
    risk_score = Column(Numeric(5, 4))  # 0.0 - 1.0
    
    # Описание и детали
    title = Column(String(200))
    description = Column(Text)
    full_description = Column(Text)  # Полное описание для платных подписок
    indicators_used = Column(Text)  # JSON список индикаторов
    confluence_factors = Column(Text)  # JSON список факторов конfluence
    
    # Таймфрейм
    timeframe = Column(String(10), default="15m")
    
    # Статус
    is_active = Column(Boolean, default=True, index=True)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    
    # Результаты (заполняется после закрытия)
    exit_price = Column(Numeric(20, 8))
    pnl_percent = Column(Numeric(10, 4))
    closed_at = Column(DateTime)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Relationships
    token = relationship("Token", back_populates="signals")
    
    def __repr__(self):
        return f"<Signal {self.symbol} {self.signal_type.value} ({self.rating.value})>"


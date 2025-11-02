"""
Pydantic модели для валидации данных.
"""
from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class SignalType(str):
    """Тип торгового сигнала."""
    LONG = "LONG"
    SHORT = "SHORT"


class OrderBlockModel(BaseModel):
    """Модель Order Block."""
    start_idx: int = Field(..., description="Индекс начала блока")
    end_idx: int = Field(..., description="Индекс конца блока")
    high: float = Field(..., description="Максимальная цена блока")
    low: float = Field(..., description="Минимальная цена блока")
    type: Literal["bullish", "bearish"] = Field(..., description="Тип блока")
    strength: float = Field(..., ge=0.0, le=1.0, description="Сила блока (0-1)")
    timestamp: datetime = Field(default_factory=datetime.now)

    @validator('end_idx')
    def end_after_start(cls, v, values):
        if 'start_idx' in values and v <= values['start_idx']:
            raise ValueError('end_idx must be greater than start_idx')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "start_idx": 50,
                "end_idx": 55,
                "high": 43500.0,
                "low": 43200.0,
                "type": "bullish",
                "strength": 0.85
            }
        }


class FairValueGapModel(BaseModel):
    """Модель Fair Value Gap."""
    start_idx: int
    end_idx: int
    high: float
    low: float
    type: Literal["bullish", "bearish"]
    strength: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class SignalModel(BaseModel):
    """Модель торгового сигнала."""
    symbol: str = Field(..., description="Торговая пара")
    type: Literal["LONG", "SHORT"] = Field(..., description="Тип сигнала")
    entry_price: float = Field(..., gt=0, description="Цена входа")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop Loss")
    take_profit: Optional[float] = Field(None, gt=0, description="Take Profit")
    confluence: int = Field(..., ge=0, description="Количество подтверждающих сигналов")
    timeframe: str = Field(default="15m", description="Таймфрейм")
    indicators: List[str] = Field(default_factory=list, description="Индикаторы")
    timestamp: datetime = Field(default_factory=datetime.now)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Уверенность (0-1)")

    @validator('take_profit')
    def tp_above_entry_for_long(cls, v, values):
        if v and 'type' in values and 'entry_price' in values:
            if values['type'] == 'LONG' and v <= values['entry_price']:
                raise ValueError('Take profit must be above entry for LONG')
            if values['type'] == 'SHORT' and v >= values['entry_price']:
                raise ValueError('Take profit must be below entry for SHORT')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC/USDT",
                "type": "LONG",
                "entry_price": 43500.0,
                "stop_loss": 43200.0,
                "take_profit": 44500.0,
                "confluence": 5,
                "timeframe": "15m",
                "indicators": ["Order Block", "Volume Profile POC", "Positive Delta"],
                "confidence": 0.85
            }
        }


class VolumeProfileModel(BaseModel):
    """Модель Volume Profile."""
    poc: float = Field(..., description="Point of Control")
    vah: float = Field(..., description="Value Area High")
    val: float = Field(..., description="Value Area Low")
    total_volume: float = Field(..., ge=0, description="Общий объем")
    value_area_percent: float = Field(default=0.70, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class MarketProfileModel(BaseModel):
    """Модель Market Profile."""
    vah: float = Field(..., description="Value Area High")
    val: float = Field(..., description="Value Area Low")
    poc: float = Field(..., description="Point of Control")
    initial_balance_high: Optional[float] = None
    initial_balance_low: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ConfluenceZoneModel(BaseModel):
    """Модель зоны конfluence."""
    price_level: float = Field(..., gt=0, description="Ценовой уровень")
    strength: float = Field(..., ge=0.0, le=1.0, description="Сила зоны")
    indicators: List[str] = Field(..., description="Индикаторы в зоне")
    weight: int = Field(..., ge=0, description="Вес конfluence")
    timestamp: datetime = Field(default_factory=datetime.now)


class TradeRequest(BaseModel):
    """Запрос на создание сделки."""
    symbol: str
    side: Literal["buy", "sell"]
    amount: Optional[float] = None
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class TradeResponse(BaseModel):
    """Ответ на создание сделки."""
    success: bool
    trade_id: Optional[str] = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """Статус здоровья системы."""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    services: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Модель ошибки."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


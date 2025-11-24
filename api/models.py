"""
Pydantic модели для валидации данных.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SignalType(str):
    """Тип торгового сигнала."""

    LONG = "LONG"
    SHORT = "SHORT"


class OrderBlockModel(BaseModel):
    """Модель Order Block."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_idx": 50,
                "end_idx": 55,
                "high": 43500.0,
                "low": 43200.0,
                "type": "bullish",
                "strength": 0.85,
            }
        }
    )

    start_idx: int = Field(..., description="Индекс начала блока")
    end_idx: int = Field(..., description="Индекс конца блока")
    high: float = Field(..., description="Максимальная цена блока")
    low: float = Field(..., description="Минимальная цена блока")
    type: Literal["bullish", "bearish"] = Field(..., description="Тип блока")
    strength: float = Field(..., ge=0.0, le=1.0, description="Сила блока (0-1)")
    timestamp: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="after")
    def end_after_start(self) -> "OrderBlockModel":
        if self.end_idx <= self.start_idx:
            raise ValueError("end_idx must be greater than start_idx")
        return self


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC/USDT",
                "type": "LONG",
                "entry_price": 43500.0,
                "stop_loss": 43200.0,
                "take_profit": 44500.0,
                "confluence": 5,
                "timeframe": "15m",
                "indicators": ["Order Block", "Volume Profile POC", "Positive Delta"],
                "confidence": 0.85,
            }
        }
    )

    symbol: str = Field(..., description="Торговая пара")
    type: Literal["LONG", "SHORT"] = Field(..., description="Тип сигнала")
    entry_price: float = Field(..., gt=0, description="Цена входа")
    stop_loss: float | None = Field(None, gt=0, description="Stop Loss")
    take_profit: float | None = Field(None, gt=0, description="Take Profit")
    confluence: int = Field(..., ge=0, description="Количество подтверждающих сигналов")
    timeframe: str = Field(default="15m", description="Таймфрейм")
    indicators: list[str] = Field(default_factory=list, description="Индикаторы")
    timestamp: datetime = Field(default_factory=datetime.now)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Уверенность (0-1)")

    @model_validator(mode="after")
    def tp_above_entry_for_long(self) -> "SignalModel":
        if self.take_profit:
            if self.type == "LONG" and self.take_profit <= self.entry_price:
                raise ValueError("Take profit must be above entry for LONG")
            if self.type == "SHORT" and self.take_profit >= self.entry_price:
                raise ValueError("Take profit must be below entry for SHORT")
        return self


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
    initial_balance_high: float | None = None
    initial_balance_low: float | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ConfluenceZoneModel(BaseModel):
    """Модель зоны конfluence."""

    price_level: float = Field(..., gt=0, description="Ценовой уровень")
    strength: float = Field(..., ge=0.0, le=1.0, description="Сила зоны")
    indicators: list[str] = Field(..., description="Индикаторы в зоне")
    weight: int = Field(..., ge=0, description="Вес конfluence")
    timestamp: datetime = Field(default_factory=datetime.now)


class TradeRequest(BaseModel):
    """Запрос на создание сделки."""

    symbol: str
    side: Literal["buy", "sell"]
    amount: float | None = None
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None


class TradeResponse(BaseModel):
    """Ответ на создание сделки."""

    success: bool
    trade_id: str | None = None
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
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

"""
Роутер для торговых сигналов.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.signal import Signal, SignalRating, SignalType
from app.models.token import Token

router = APIRouter()


@router.get("/signals")
async def get_signals(
    rating: Optional[SignalRating] = Query(None, description="Фильтр по рейтингу"),
    symbol: Optional[str] = Query(None, description="Фильтр по символу"),
    active_only: bool = Query(True, description="Только активные сигналы"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Получить список сигналов."""
    query = select(Signal).join(Token)
    
    if active_only:
        query = query.where(Signal.is_active == True)
    
    if rating:
        query = query.where(Signal.rating == rating)
    
    if symbol:
        query = query.where(Signal.symbol == symbol.upper())
    
    query = query.order_by(Signal.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    signals = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "symbol": s.symbol,
            "type": s.signal_type.value,
            "rating": s.rating.value,
            "entry_price": float(s.entry_price),
            "stop_loss": float(s.stop_loss) if s.stop_loss else None,
            "take_profit": float(s.take_profit) if s.take_profit else None,
            "signal_score": float(s.signal_score),
            "confidence": float(s.confidence) if s.confidence else None,
            "created_at": s.created_at.isoformat(),
        }
        for s in signals
    ]


@router.get("/signals/{signal_id}")
async def get_signal_detail(
    signal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить детальную информацию о сигнале."""
    result = await db.execute(
        select(Signal).where(Signal.id == signal_id)
    )
    signal = result.scalar_one_or_none()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    return {
        "id": signal.id,
        "symbol": signal.symbol,
        "type": signal.signal_type.value,
        "rating": signal.rating.value,
        "entry_price": float(signal.entry_price),
        "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
        "take_profit": float(signal.take_profit) if signal.take_profit else None,
        "current_price": float(signal.current_price) if signal.current_price else None,
        "signal_score": float(signal.signal_score),
        "confidence": float(signal.confidence) if signal.confidence else None,
        "risk_score": float(signal.risk_score) if signal.risk_score else None,
        "title": signal.title,
        "description": signal.description,
        "full_description": signal.full_description,
        "timeframe": signal.timeframe,
        "is_active": signal.is_active,
        "created_at": signal.created_at.isoformat(),
        "expires_at": signal.expires_at.isoformat() if signal.expires_at else None,
    }


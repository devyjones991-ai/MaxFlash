"""
Административный роутер.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.token import Token
from app.models.signal import Signal
from app.models.trade import Trade

router = APIRouter()


@router.get("/admin/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Получить статистику системы."""
    # Количество токенов
    token_count = await db.scalar(select(func.count(Token.id)))
    
    # Количество сигналов
    signal_count = await db.scalar(select(func.count(Signal.id)))
    active_signal_count = await db.scalar(
        select(func.count(Signal.id)).where(Signal.is_active == True)
    )
    
    # Количество сделок
    trade_count = await db.scalar(select(func.count(Trade.id)))
    open_trade_count = await db.scalar(
        select(func.count(Trade.id)).where(Trade.status == "open")
    )
    
    return {
        "tokens": {
            "total": token_count or 0,
        },
        "signals": {
            "total": signal_count or 0,
            "active": active_signal_count or 0,
        },
        "trades": {
            "total": trade_count or 0,
            "open": open_trade_count or 0,
        },
    }


"""
Роутер для торговых сделок.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.trade import Trade, TradeStatus, TradeSide

router = APIRouter()


@router.get("/trades")
async def get_trades(
    status: Optional[TradeStatus] = Query(None, description="Фильтр по статусу"),
    symbol: Optional[str] = Query(None, description="Фильтр по символу"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Получить список сделок."""
    query = select(Trade)
    
    if status:
        query = query.where(Trade.status == status)
    
    if symbol:
        query = query.where(Trade.symbol == symbol.upper())
    
    query = query.order_by(Trade.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    trades = result.scalars().all()
    
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "side": t.side.value,
            "status": t.status.value,
            "quantity": float(t.quantity),
            "price": float(t.price) if t.price else None,
            "filled_quantity": float(t.filled_quantity),
            "pnl": float(t.pnl) if t.pnl else None,
            "pnl_percent": float(t.pnl_percent) if t.pnl_percent else None,
            "created_at": t.created_at.isoformat(),
        }
        for t in trades
    ]


@router.get("/trades/{trade_id}")
async def get_trade_detail(
    trade_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить детальную информацию о сделке."""
    result = await db.execute(
        select(Trade).where(Trade.id == trade_id)
    )
    trade = result.scalar_one_or_none()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side.value,
        "status": trade.status.value,
        "quantity": float(trade.quantity),
        "price": float(trade.price) if trade.price else None,
        "filled_quantity": float(trade.filled_quantity),
        "average_price": float(trade.average_price) if trade.average_price else None,
        "stop_loss": float(trade.stop_loss) if trade.stop_loss else None,
        "take_profit": float(trade.take_profit) if trade.take_profit else None,
        "pnl": float(trade.pnl) if trade.pnl else None,
        "pnl_percent": float(trade.pnl_percent) if trade.pnl_percent else None,
        "created_at": trade.created_at.isoformat(),
        "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
        "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
    }


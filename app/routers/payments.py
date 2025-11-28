"""
Роутер для платежей и подписок.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.post("/payments/subscribe")
async def create_subscription(
    rating: str,  # 'pro' или 'alpha'
    db: AsyncSession = Depends(get_db),
):
    """Создать подписку (заглушка)."""
    # TODO: реализовать создание подписки и платежа
    return {
        "message": "Subscription creation not implemented yet",
        "rating": rating,
    }


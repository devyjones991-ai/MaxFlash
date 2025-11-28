"""
Health check роутер.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
from app.config import settings
from app.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Проверка здоровья системы."""
    checks = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "services": {}
    }
    
    # Проверка БД
    try:
        result = await db.execute(text("SELECT 1"))
        checks["services"]["database"] = "ok"
    except Exception as e:
        checks["services"]["database"] = f"error: {str(e)}"
        checks["status"] = "degraded"
    
    # Проверка Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["services"]["redis"] = "ok"
    except Exception as e:
        checks["services"]["redis"] = f"error: {str(e)}"
        checks["status"] = "degraded"
    
    return checks


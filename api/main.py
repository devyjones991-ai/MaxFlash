"""
FastAPI backend для MaxFlash Trading System.
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from datetime import datetime
import logging

# Импорт версии из централизованного модуля
try:
    from version import get_version
    VERSION = get_version()
except ImportError:
    # Fallback если модуль версии не найден
    VERSION = "1.0.0"

from api.models import (
    SignalModel,
    OrderBlockModel,
    FairValueGapModel,
    VolumeProfileModel,
    MarketProfileModel,
    ConfluenceZoneModel,
    TradeRequest,
    TradeResponse,
    HealthResponse,
    ErrorResponse
)
from api.market_api import router as market_router

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация FastAPI
app = FastAPI(
    title="MaxFlash Trading API",
    description="API для MaxFlash Trading System с Smart Money Concepts",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(market_router)


@app.get("/", response_model=dict)
async def root():
    """Корневой endpoint."""
    return {
        "name": "MaxFlash Trading API",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Проверка здоровья системы.
    """
    try:
        # Проверка импортов основных модулей
        from indicators.smart_money.order_blocks import OrderBlockDetector
        from utils.risk_manager import RiskManager
        
        services = {
            "indicators": "ok",
            "utils": "ok"
        }
        
        return HealthResponse(
            status="healthy",
            version=VERSION,
            services=services
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="degraded",
            version=VERSION,
            services={"error": str(e)}
        )


@app.get("/api/v1/signals", response_model=List[SignalModel])
async def get_signals(
    symbol: str | None = None,
    timeframe: str = "15m",
    limit: int = 10
):
    """
    Получить активные торговые сигналы.
    
    Args:
        symbol: Торговая пара (опционально)
        timeframe: Таймфрейм
        limit: Максимальное количество сигналов
        
    Returns:
        Список сигналов
    """
    try:
        # Здесь будет реальная логика получения сигналов
        # Пока возвращаем примеры
        return [
            SignalModel(
                symbol="BTC/USDT",
                type="LONG",
                entry_price=43500.0,
                stop_loss=43200.0,
                take_profit=44500.0,
                confluence=5,
                timeframe=timeframe,
                indicators=["Order Block", "Volume Profile POC", "Positive Delta"],
                confidence=0.85
            )
        ]
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/order-blocks", response_model=List[OrderBlockModel])
async def get_order_blocks(
    symbol: str,
    timeframe: str = "15m",
    limit: int = 20
):
    """
    Получить Order Blocks для торговой пары.
    
    Args:
        symbol: Торговая пара
        timeframe: Таймфрейм
        limit: Максимальное количество блоков
    """
    try:
        # Здесь будет реальная логика получения Order Blocks
        return []
    except Exception as e:
        logger.error(f"Error getting order blocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/volume-profile/{symbol}", response_model=VolumeProfileModel)
async def get_volume_profile(
    symbol: str,
    timeframe: str = "15m"
):
    """
    Получить Volume Profile для торговой пары.
    
    Args:
        symbol: Торговая пара
        timeframe: Таймфрейм
    """
    try:
        # Здесь будет реальная логика получения Volume Profile
        from indicators.volume_profile.volume_profile import VolumeProfileCalculator
        
        # Пример
        return VolumeProfileModel(
            poc=43500.0,
            vah=43800.0,
            val=43200.0,
            total_volume=1000000.0
        )
    except Exception as e:
        logger.error(f"Error getting volume profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/confluence/{symbol}", response_model=List[ConfluenceZoneModel])
async def get_confluence_zones(
    symbol: str,
    timeframe: str = "15m"
):
    """
    Получить зоны конfluence для торговой пары.
    
    Args:
        symbol: Торговая пара
        timeframe: Таймфрейм
    """
    try:
        # Здесь будет реальная логика получения confluence zones
        return []
    except Exception as e:
        logger.error(f"Error getting confluence zones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/trades", response_model=TradeResponse)
async def create_trade(trade: TradeRequest):
    """
    Создать торговую сделку.
    
    Args:
        trade: Данные сделки
    """
    try:
        # Здесь будет реальная логика создания сделки
        # Пока возвращаем успешный ответ
        return TradeResponse(
            success=True,
            trade_id="example_trade_123",
            message="Trade created successfully"
        )
    except Exception as e:
        logger.error(f"Error creating trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик исключений."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


"""
API endpoints для получения данных рынка.
FastAPI endpoints для market overview, pairs, tickers, sectors, correlations.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from utils.market_data_manager import MarketDataManager
from utils.market_analytics import MarketAnalytics
from utils.market_alerts import MarketAlerts
from config.market_config import get_all_sectors, get_sector_for_pair

router = APIRouter(prefix="/api/market", tags=["market"])

# Глобальные экземпляры менеджеров
data_manager = MarketDataManager()
analytics = MarketAnalytics(data_manager)
alerts = MarketAlerts(data_manager)


class MarketOverviewResponse(BaseModel):
    """Ответ с обзором рынка."""
    total_pairs: int
    active_pairs: int
    total_volume_24h: float
    avg_price: float
    pairs_up_24h: int
    pairs_down_24h: int
    btc_dominance: float
    top_volume_pairs: List[Dict[str, Any]]


class PairInfo(BaseModel):
    """Информация о торговой паре."""
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    high_24h: float
    low_24h: float
    sector: Optional[str]


@router.get("/overview", response_model=MarketOverviewResponse)
async def get_market_overview():
    """
    Получить обзор рынка.

    Returns:
        Статистика рынка
    """
    try:
        stats = data_manager.get_market_stats()
        return MarketOverviewResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pairs", response_model=List[str])
async def get_all_pairs(
    exchange_id: Optional[str] = Query(None, description="ID биржи")
):
    """
    Получить список всех торговых пар.

    Args:
        exchange_id: Идентификатор биржи (опционально)

    Returns:
        Список торговых пар
    """
    try:
        pairs = data_manager.get_all_pairs(exchange_id)
        return pairs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickers", response_model=Dict[str, Dict[str, Any]])
async def get_tickers(
    exchange_id: str = Query('binance', description="ID биржи"),
    symbols: Optional[List[str]] = Query(None, description="Список пар")
):
    """
    Получить тикеры для торговых пар.

    Args:
        exchange_id: Идентификатор биржи
        symbols: Список пар (опционально, по умолчанию все)

    Returns:
        Словарь с тикерами
    """
    try:
        tickers = data_manager.get_tickers(exchange_id, symbols)
        return tickers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors", response_model=List[str])
async def get_sectors():
    """
    Получить список всех секторов.

    Returns:
        Список секторов
    """
    try:
        sectors = get_all_sectors()
        return sectors
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/{sector}", response_model=Dict[str, Any])
async def get_sector_performance(sector: str):
    """
    Получить производительность сектора.

    Args:
        sector: Название сектора

    Returns:
        Метрики производительности сектора
    """
    try:
        performance = analytics.get_sector_performance(sector)
        if not performance:
            raise HTTPException(
                status_code=404,
                detail=f"Сектор {sector} не найден"
            )
        return performance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlations", response_model=Dict[str, Any])
async def get_correlations(
    pairs: List[str] = Query(..., description="Список пар для анализа"),
    timeframe: str = Query('1h', description="Таймфрейм"),
    period_days: int = Query(30, description="Период анализа в днях"),
    exchange_id: str = Query('binance', description="ID биржи")
):
    """
    Получить корреляционную матрицу между парами.

    Args:
        pairs: Список торговых пар
        timeframe: Таймфрейм
        period_days: Период анализа
        exchange_id: Идентификатор биржи

    Returns:
        Корреляционная матрица
    """
    try:
        correlation_matrix = analytics.calculate_correlations(
            pairs, timeframe, period_days, exchange_id
        )
        # Конвертируем DataFrame в словарь
        return {
            'matrix': correlation_matrix.to_dict(),
            'pairs': list(correlation_matrix.index)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{symbol}", response_model=Dict[str, Any])
async def get_trend(
    symbol: str,
    timeframe: str = Query('4h', description="Таймфрейм"),
    period_days: int = Query(7, description="Период анализа"),
    exchange_id: str = Query('binance', description="ID биржи")
):
    """
    Получить тренд для торговой пары.

    Args:
        symbol: Торговая пара
        timeframe: Таймфрейм
        period_days: Период анализа
        exchange_id: Идентификатор биржи

    Returns:
        Информация о тренде
    """
    try:
        trend = analytics.detect_trends(
            symbol, timeframe, period_days, exchange_id
        )
        return trend
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/opportunities", response_model=List[Dict[str, Any]])
async def get_opportunities(
    pairs: Optional[List[str]] = Query(None, description="Список пар"),
    min_correlation: float = Query(0.7, description="Минимальная корреляция"),
    exchange_id: str = Query('binance', description="ID биржи")
):
    """
    Найти торговые возможности.

    Args:
        pairs: Список пар для анализа
        min_correlation: Минимальная корреляция
        exchange_id: Идентификатор биржи

    Returns:
        Список возможностей
    """
    try:
        opportunities = analytics.find_opportunities(
            pairs, min_correlation, exchange_id
        )
        return opportunities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_alerts(
    symbol: Optional[str] = Query(None, description="Фильтр по символу"),
    limit: int = Query(50, description="Количество алертов")
):
    """
    Получить рыночные алерты.

    Args:
        symbol: Торговая пара (опционально)
        limit: Количество алертов

    Returns:
        Список алертов
    """
    try:
        if symbol:
            alerts_list = alerts.get_alerts_by_symbol(symbol, limit)
        else:
            alerts_list = alerts.get_recent_alerts(limit)
        return alerts_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


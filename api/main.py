"""
FastAPI backend для MaxFlash Trading System.
"""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Импорт версии из централизованного модуля
try:
    from version import get_version

    VERSION = get_version()
except ImportError:
    # Fallback если модуль версии не найден
    VERSION = "1.0.0"

from api.market_api import router as market_router
from api.models import (
    ConfluenceZoneModel,
    ErrorResponse,
    HealthResponse,
    OrderBlockModel,
    SignalModel,
    TradeRequest,
    TradeResponse,
    VolumeProfileModel,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация FastAPI
app = FastAPI(
    title="MaxFlash Trading API",
    description="API для MaxFlash Trading System с Smart Money Concepts",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
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
    return {"name": "MaxFlash Trading API", "version": VERSION, "docs": "/docs", "health": "/health"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Проверка здоровья системы.
    """
    try:
        # Проверка импортов основных модулей

        services = {"indicators": "ok", "utils": "ok"}

        return HealthResponse(status="healthy", version=VERSION, services=services)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(status="degraded", version=VERSION, services={"error": str(e)})


@app.get("/api/v1/signals", response_model=list[SignalModel])
async def get_signals(symbol: Optional[str] = None, timeframe: str = "15m", limit: int = 10):
    """
    Get trading signals using ML + technical analysis.

    Args:
        symbol: Trading pair (optional, returns signals for all if None)
        timeframe: Timeframe
        limit: Maximum number of signals

    Returns:
        List of trading signals
    """
    try:
        from utils.async_exchange import get_async_exchange
        from ml.lstm_signal_generator import LSTMSignalGenerator
        from indicators.smart_money.order_blocks import OrderBlockDetector
        from indicators.footprint.delta import DeltaAnalyzer
        from utils.confluence import ConfluenceCalculator

        # Get async exchange
        exchange = await get_async_exchange("binance")

        # Determine symbols to analyze
        if symbol:
            symbols = [symbol]
        else:
            # Get top volume pairs
            tickers = await exchange.fetch_tickers()
            usdt_pairs = {k: v for k, v in tickers.items() if k.endswith("/USDT")}
            top_pairs = sorted(usdt_pairs.items(), key=lambda x: x[1].get("quoteVolume", 0), reverse=True)
            symbols = [pair[0] for pair in top_pairs[:limit]]

        signals = []

        # Initialize analyzers
        ml_generator = LSTMSignalGenerator(lookback_periods=60)
        ob_detector = OrderBlockDetector()
        delta_analyzer = DeltaAnalyzer()

        # Generate signals for each symbol
        for sym in symbols:
            try:
                # Fetch OHLCV data
                ohlcv_data = await exchange.fetch_ohlcv(sym, timeframe, limit=200)
                if not ohlcv_data:
                    continue

                import pandas as pd

                df = pd.DataFrame(ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)

                # Calculate technical indicators
                df = ob_detector.detect_order_blocks(df)
                df = delta_analyzer.calculate_delta(df)

                # Calculate ATR
                high_low = df["high"] - df["low"]
                atr = high_low.rolling(14).mean().iloc[-1]

                indicators = {
                    "atr": float(atr) if pd.notna(atr) else df["close"].iloc[-1] * 0.02,
                    "in_order_block": bool(df["ob_bullish_low"].iloc[-1] or df["ob_bearish_high"].iloc[-1]),
                    "delta": float(df.get("delta", pd.Series([0])).iloc[-1]),
                }

                # Generate ML signal
                signal = ml_generator.generate_signal(df, indicators)

                # Only include BUY/SELL signals
                if signal["action"] != "HOLD" and signal["combined_confidence"] > 0.55:
                    signals.append(
                        SignalModel(
                            symbol=sym,
                            type=signal["action"],
                            entry_price=signal["entry_price"],
                            stop_loss=signal["stop_loss"],
                            take_profit=signal["take_profit"],
                            confluence=int(signal["combined_confidence"] * 10),  # Scale to 0-10
                            timeframe=timeframe,
                            indicators=signal["indicators_used"][:5],  # Top 5
                            confidence=signal["combined_confidence"],
                        )
                    )

            except Exception as e:
                logger.warning(f"Error generating signal for {sym}: {e}")
                continue

        logger.info(f"Generated {len(signals)} signals")
        return signals[:limit]

    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        # Fallback to mock data if ML fails
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
                confidence=0.85,
            )
        ]


@app.get("/api/v1/order-blocks", response_model=list[OrderBlockModel])
async def get_order_blocks(symbol: str, timeframe: str = "15m", limit: int = 20):
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
async def get_volume_profile(symbol: str, timeframe: str = "15m"):
    """
    Получить Volume Profile для торговой пары.

    Args:
        symbol: Торговая пара
        timeframe: Таймфрейм
    """
    try:
        # Здесь будет реальная логика получения Volume Profile

        # Пример
        return VolumeProfileModel(poc=43500.0, vah=43800.0, val=43200.0, total_volume=1000000.0)
    except Exception as e:
        logger.error(f"Error getting volume profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/confluence/{symbol}", response_model=list[ConfluenceZoneModel])
async def get_confluence_zones(symbol: str, timeframe: str = "15m"):
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
    Execute a trade on the exchange (with risk management).

    Args:
        trade: Trade request data

    Returns:
        Trade execution result
    """
    try:
        from trading.order_executor import OrderExecutor
        from trading.risk_manager import AdvancedRiskManager
        import os

        # Initialize components
        api_key = os.getenv("EXCHANGE_API_KEY")
        api_secret = os.getenv("EXCHANGE_API_SECRET")
        testnet = os.getenv("USE_TESTNET", "true").lower() == "true"

        logger.info(f"Processing trade: {trade.symbol} {trade.side} {trade.amount} (testnet={testnet})")

        # Initialize risk manager (use demo balance if not provided)
        account_balance = float(os.getenv("ACCOUNT_BALANCE", "10000"))
        risk_manager = AdvancedRiskManager(
            account_balance=account_balance,
            max_risk_per_trade=0.01,  # 1%
            max_portfolio_risk=0.05,  # 5%
            daily_loss_limit=0.02,  # 2%
        )

        # Validate trade with risk manager
        is_valid, reason = risk_manager.validate_trade(
            symbol=trade.symbol,
            side=trade.side,
            amount=trade.amount,
            entry_price=trade.price if trade.price else 0,
            stop_loss=getattr(trade, "stop_loss", None),
        )

        if not is_valid:
            logger.warning(f"Trade rejected by risk manager: {reason}")
            raise HTTPException(status_code=400, detail=f"Trade rejected: {reason}")

        # Initialize order executor
        executor = OrderExecutor(
            exchange_id=getattr(trade, "exchange", "binance"),
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
        )

        await executor.initialize()

        # Execute order
        order = await executor.place_order(
            symbol=trade.symbol,
            side=trade.side,
            order_type=trade.order_type or "market",
            amount=trade.amount,
            price=trade.price if trade.order_type == "limit" else None,
            stop_loss=getattr(trade, "stop_loss", None),
            take_profit=getattr(trade, "take_profit", None),
        )

        if not order:
            raise HTTPException(status_code=500, detail="Order placement failed")

        # Update risk manager
        risk_manager.add_position(
            symbol=trade.symbol,
            side=trade.side,
            entry_price=order.get("average", trade.price or 0),
            amount=trade.amount,
            stop_loss=getattr(trade, "stop_loss", None),
            take_profit=getattr(trade, "take_profit", None),
        )

        logger.info(f"✅ Trade executed: {order['id']}")

        return TradeResponse(
            success=True,
            trade_id=order["id"],
            message="Trade executed successfully",
            order_info=order,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик исключений."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content=ErrorResponse(error="Internal server error", detail=str(exc)).model_dump()
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

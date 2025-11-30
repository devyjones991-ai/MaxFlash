"""
Signal Service
Centralizes signal generation, aggregation, and logging.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from app.config import settings
from ml.llm_interpreter import LLMInterpreter
from ml.signal_filter import SignalFilter
from trading.risk_manager import AdvancedRiskManager
from utils.market_data_manager import MarketDataManager

# Optional ML import
try:
    from ml.lstm_signal_generator import LSTMSignalGenerator

    HAS_ML = True
except ImportError:
    HAS_ML = False
    # logger is not defined yet, so we'll log later

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


@dataclass
class SignalResult:
    symbol: str
    signal_type: SignalType
    confidence: float
    timestamp: datetime
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reasoning: list[str] = None
    metadata: dict[str, Any] = None


class SignalService:
    """
    Service for generating and managing trading signals.
    Aggregates data from strategies, ML models, and risk management.
    """

    def __init__(self):
        self.risk_manager = AdvancedRiskManager(account_balance=settings.MIN_LIQUIDITY_USD)
        self.data_manager = MarketDataManager()
        self.signal_filter = SignalFilter()
        self.llm_interpreter = LLMInterpreter()

        self.ml_model = None
        if HAS_ML:
            try:
                self.ml_model = LSTMSignalGenerator()
            except Exception as e:
                logger.error(f"Failed to initialize ML model: {e}")

    async def analyze_symbol(self, symbol: str) -> SignalResult:
        """
        Analyze a single symbol and return a signal.
        """
        logger.info(f"Analyzing {symbol}...")

        # 1. Fetch Data
        df = self.data_manager.get_ohlcv(symbol, timeframe="15m", limit=100)
        if df is None or df.empty:
            return self._create_neutral_signal(symbol, "Insufficient data")

        current_price = df["close"].iloc[-1]

        # 2. ML Analysis
        ml_signal = "NEUTRAL"
        ml_confidence = 0.0
        ml_probs = {}

        if self.ml_model and self.ml_model.is_trained:
            try:
                prediction = self.ml_model.predict(df)
                ml_signal = prediction["action"]
                ml_confidence = prediction["confidence"]
                ml_probs = prediction["probabilities"]
            except Exception as e:
                logger.error(f"ML prediction error for {symbol}: {e}")

        # 3. Technical Analysis (Basic) & Filtering
        # Calculate basic indicators for filter
        indicators = self._calculate_basic_indicators(df)

        # Validate/Adjust Confidence
        adjusted_confidence = self.signal_filter.validate_signal(ml_signal, ml_confidence, indicators)

        # 4. Determine Final Signal
        final_signal_type = SignalType.NEUTRAL
        if adjusted_confidence > settings.SIGNAL_CONFIDENCE_THRESHOLD:  # e.g. 0.7
            final_signal_type = SignalType(ml_signal)

        # 5. Risk Management
        stop_loss = None
        take_profit = None

        if final_signal_type != SignalType.NEUTRAL:
            risk_params = settings.get_risk_params()
            atr = indicators.get("atr", current_price * 0.02)

            if final_signal_type == SignalType.BUY:
                stop_loss = current_price - (atr * 1.5)
                take_profit = current_price + (atr * 3.0)
            else:
                stop_loss = current_price + (atr * 1.5)
                take_profit = current_price - (atr * 3.0)

        # 6. LLM Reasoning (only for strong signals)
        reasoning = []
        if final_signal_type != SignalType.NEUTRAL:
            llm_reasoning = self.llm_interpreter.interpret_signal(
                symbol, final_signal_type.value, adjusted_confidence, indicators
            )
            reasoning.append(llm_reasoning)
        else:
            reasoning.append("Signal confidence too low or neutral market conditions.")

        return SignalResult(
            symbol=symbol,
            signal_type=final_signal_type,
            confidence=adjusted_confidence,
            timestamp=datetime.now(),
            price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasoning=reasoning,
            metadata={"ml_probabilities": ml_probs, "indicators": indicators},
        )

    def _create_neutral_signal(self, symbol: str, reason: str) -> SignalResult:
        return SignalResult(
            symbol=symbol,
            signal_type=SignalType.NEUTRAL,
            confidence=0.0,
            timestamp=datetime.now(),
            price=0.0,
            reasoning=[reason],
        )

    def _calculate_basic_indicators(self, df: Any) -> Dict[str, float]:
        """Calculate basic indicators for filtering (RSI, ATR, Volume)."""
        # Simple implementation using pandas
        close = df["close"]

        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # ATR (Simplified)
        high_low = df["high"] - df["low"]
        atr = high_low.rolling(window=14).mean()

        # Volume Ratio
        vol_ma = df["volume"].rolling(window=20).mean()
        vol_ratio = df["volume"] / vol_ma

        return {
            "rsi": rsi.iloc[-1] if not rsi.empty else 50.0,
            "atr": atr.iloc[-1] if not atr.empty else close.iloc[-1] * 0.02,
            "volume_ratio": vol_ratio.iloc[-1] if not vol_ratio.empty else 1.0,
        }


# Global instance
signal_service = SignalService()

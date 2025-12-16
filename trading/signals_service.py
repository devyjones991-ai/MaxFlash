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

# LLM removed for stability - using deterministic reasoning
# from ml.llm_interpreter import LLMInterpreter
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
        # LLM removed for stability
        # self.llm_interpreter = LLMInterpreter()

        self.ml_model = None
        if HAS_ML:
            try:
                self.ml_model = LSTMSignalGenerator()
            except Exception as e:
                logger.error(f"Failed to initialize ML model: {e}")

    async def analyze_symbol(self, symbol: str) -> SignalResult:
        """
        Analyze symbol using EXACT same logic as dashboard.
        Pure score-based system without ML conflict blocking.
        """
        logger.info(f"Analyzing {symbol}...")

        # 1. Fetch Data
        df = self.data_manager.get_ohlcv(symbol, timeframe="15m", limit=100)
        if df is None or df.empty:
            return self._create_neutral_signal(symbol, "Insufficient data")

        current_price = df["close"].iloc[-1]
        
        # Get 24h change
        try:
            ticker = self.data_manager.get_ticker(symbol)
            change = ticker.get('percentage', 0) or 0
        except:
            if len(df) >= 96:
                change = (current_price - df["close"].iloc[-96]) / df["close"].iloc[-96] * 100
            else:
                change = 0

        # Initialize scores
        buy_score = 0
        sell_score = 0
        reasons = []
        
        # === 1. PRICE CHANGE (24h) ===
        if change <= -5:
            sell_score += 30
            reasons.append(f"📉 Падение {change:.1f}%")
        elif change <= -2:
            sell_score += 20
            reasons.append(f"📉 Снижение {change:.1f}%")
        elif change <= -0.5:
            sell_score += 10
        elif change >= 5:
            buy_score += 30
            reasons.append(f"📈 Рост {change:+.1f}%")
        elif change >= 2:
            buy_score += 20
            reasons.append(f"📈 Подъем {change:+.1f}%")
        elif change >= 0.5:
            buy_score += 10
        
        # === 2. OHLCV-based indicators ===
        if len(df) >= 26:
            close = df["close"]
            
            # --- RSI ---
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            rsi_series = 100 - (100 / (1 + rs))
            rsi = rsi_series.iloc[-1]
            rsi_prev = rsi_series.iloc[-2] if len(rsi_series) > 1 else rsi
            rsi_trend = rsi - rsi_prev
            
            if rsi < 30:
                buy_score += 25
                reasons.append(f"RSI {rsi:.0f} (перепродано)")
            elif rsi < 40:
                buy_score += 15
                reasons.append(f"RSI {rsi:.0f}↓")
            elif rsi > 70:
                sell_score += 25
                reasons.append(f"RSI {rsi:.0f} (перекуплено)")
            elif rsi > 60:
                sell_score += 15
                reasons.append(f"RSI {rsi:.0f}↑")
            elif rsi < 45 and rsi_trend < 0:
                sell_score += 10
                reasons.append(f"RSI {rsi:.0f}⬇")
            elif rsi > 55 and rsi_trend > 0:
                buy_score += 10
                reasons.append(f"RSI {rsi:.0f}⬆")
            
            # --- MACD (8-17-9) ---
            ema_fast = close.ewm(span=8, adjust=False).mean()
            ema_slow = close.ewm(span=17, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            
            macd = macd_line.iloc[-1]
            macd_prev = macd_line.iloc[-2] if len(macd_line) > 1 else macd
            signal = signal_line.iloc[-1]
            signal_prev = signal_line.iloc[-2] if len(signal_line) > 1 else signal
            
            if macd_prev < signal_prev and macd > signal:
                buy_score += 25
                reasons.append("MACD пересечение⬆")
            elif macd_prev > signal_prev and macd < signal:
                sell_score += 25
                reasons.append("MACD пересечение⬇")
            elif macd > signal:
                buy_score += 10
                reasons.append("MACD+")
            elif macd < signal:
                sell_score += 10
                reasons.append("MACD-")
            
            # --- Price vs MA ---
            price = close.iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else ma20
            
            if price > ma20 > ma50:
                buy_score += 15
                reasons.append("Тренд⬆")
            elif price < ma20 < ma50:
                sell_score += 15
                reasons.append("Тренд⬇")
            elif price < ma20:
                sell_score += 5
            elif price > ma20:
                buy_score += 5
        else:
            # Simple signal based only on 24h change
            if change <= -3:
                sell_score += 15
            elif change >= 3:
                buy_score += 15
            rsi = 50
        
        # === 3. CALCULATE CONFIDENCE ===
        max_score = max(buy_score, sell_score)
        
        if max_score >= 60:
            confidence = 0.85
        elif max_score >= 45:
            confidence = 0.75
        elif max_score >= 30:
            confidence = 0.60
        elif max_score >= 20:
            confidence = 0.50
        else:
            confidence = 0.40
        
        # === 4. DETERMINE SIGNAL (SAME AS DASHBOARD) ===
        diff = buy_score - sell_score
        
        if diff >= 20:
            final_signal_type = SignalType.BUY
        elif diff <= -20:
            final_signal_type = SignalType.SELL
        elif diff >= 10:
            final_signal_type = SignalType.BUY
            confidence = min(confidence, 0.55)
        elif diff <= -10:
            final_signal_type = SignalType.SELL
            confidence = min(confidence, 0.55)
        elif diff > 0:
            final_signal_type = SignalType.BUY
            confidence = min(confidence, 0.45)
        elif diff < 0:
            final_signal_type = SignalType.SELL
            confidence = min(confidence, 0.45)
        else:
            final_signal_type = SignalType.NEUTRAL
            confidence = 0.5
        
        # === 5. RISK MANAGEMENT ===
        stop_loss = None
        take_profit = None
        
        if final_signal_type != SignalType.NEUTRAL:
            atr = (df["high"] - df["low"]).rolling(window=14).mean().iloc[-1]
            
            if final_signal_type == SignalType.BUY:
                stop_loss = current_price - (atr * 1.5)
                take_profit = current_price + (atr * 3.0)
            else:
                stop_loss = current_price + (atr * 1.5)
                take_profit = current_price - (atr * 3.0)
        
        if not reasons:
            reasons.append("Нейтральный рынок")

        return SignalResult(
            symbol=symbol,
            signal_type=final_signal_type,
            confidence=confidence,
            timestamp=datetime.now(),
            price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasoning=reasons,
            metadata={
                "buy_score": buy_score,
                "sell_score": sell_score,
                "diff": diff,
                "rsi": rsi if 'rsi' in dir() else 50,
                "change": change
            },
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

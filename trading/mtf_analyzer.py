"""
Multi-Timeframe Analyzer for signal confirmation.
Checks higher timeframes before confirming signals on lower timeframes.
"""
import pandas as pd
import ccxt
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MTFAnalyzer:
    """
    Multi-Timeframe Analysis for signal confirmation.
    15m signal → confirm with 1h and 4h trends
    """
    
    # Timeframe hierarchy
    TF_HIERARCHY = {
        '5m': ['15m', '1h'],
        '15m': ['1h', '4h'],
        '1h': ['4h', '1d'],
        '4h': ['1d', '1w'],
    }
    
    def __init__(self, exchange: ccxt.Exchange):
        self.exchange = exchange
    
    def get_trend(self, df: pd.DataFrame) -> str:
        """
        Determine trend from OHLCV data.
        Returns: 'bullish', 'bearish', 'neutral'
        """
        if len(df) < 20:
            return 'neutral'
        
        close = df['close']
        
        # Calculate EMAs
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1] if len(close) >= 50 else ema20
        current_price = close.iloc[-1]
        
        # Trend determination
        if current_price > ema20 > ema50:
            return 'bullish'
        elif current_price < ema20 < ema50:
            return 'bearish'
        else:
            return 'neutral'
    
    def get_higher_tf_trends(self, symbol: str, current_tf: str = '15m') -> dict:
        """
        Get trends from higher timeframes.
        Returns dict with higher TF trends.
        """
        result = {
            'current_tf': current_tf,
            'trends': {},
            'aligned': False,
            'strength': 0
        }
        
        higher_tfs = self.TF_HIERARCHY.get(current_tf, ['1h', '4h'])
        
        for tf in higher_tfs:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, tf, limit=60)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                trend = self.get_trend(df)
                result['trends'][tf] = trend
            except Exception as e:
                logger.debug(f"Error fetching {tf} for {symbol}: {e}")
                result['trends'][tf] = 'neutral'
        
        # Check alignment
        trend_values = list(result['trends'].values())
        if all(t == 'bullish' for t in trend_values):
            result['aligned'] = True
            result['strength'] = 2  # Strong bullish
        elif all(t == 'bearish' for t in trend_values):
            result['aligned'] = True
            result['strength'] = -2  # Strong bearish
        elif 'bullish' in trend_values and 'bearish' not in trend_values:
            result['strength'] = 1  # Weak bullish
        elif 'bearish' in trend_values and 'bullish' not in trend_values:
            result['strength'] = -1  # Weak bearish
        else:
            result['strength'] = 0  # Mixed/neutral
        
        return result
    
    def confirm_signal(
        self, 
        symbol: str, 
        signal: str,  # 'BUY' or 'SELL'
        confidence: float,
        current_tf: str = '15m'
    ) -> Tuple[bool, float, str]:
        """
        Confirm signal using higher timeframes.
        Returns: (is_confirmed, adjusted_confidence, reason)
        """
        if signal == 'HOLD':
            return True, confidence, ""
        
        mtf_data = self.get_higher_tf_trends(symbol, current_tf)
        
        expected_trend = 'bullish' if signal == 'BUY' else 'bearish'
        opposite_trend = 'bearish' if signal == 'BUY' else 'bullish'
        
        # Check alignment
        trends = mtf_data['trends']
        
        # All higher TFs agree with signal
        if all(t == expected_trend for t in trends.values()):
            return True, min(100, confidence * 1.2), f"MTF: All {expected_trend}"
        
        # At least one higher TF agrees
        if expected_trend in trends.values() and opposite_trend not in trends.values():
            return True, confidence * 1.1, f"MTF: {expected_trend} aligned"
        
        # Higher TFs are neutral (no conflict)
        if all(t == 'neutral' for t in trends.values()):
            return True, confidence * 0.95, "MTF: Neutral"
        
        # Higher TFs conflict with signal
        if opposite_trend in trends.values():
            if all(t == opposite_trend for t in trends.values()):
                # Strong conflict - skip signal
                return False, confidence * 0.5, f"MTF: Conflict ({opposite_trend})"
            else:
                # Partial conflict - reduce confidence
                return True, confidence * 0.7, "MTF: Mixed"
        
        return True, confidence, ""


def get_mtf_analyzer(exchange: ccxt.Exchange) -> MTFAnalyzer:
    """Factory function to create MTF analyzer."""
    return MTFAnalyzer(exchange)

"""
Signal Direction Logic - Determines TRUE signal direction based on RSI, MACD, and trend.
Based on bot_polish_guide.md specifications.
"""

from typing import Tuple


class SignalDirection:
    """
    Determines TRUE signal direction based on RSI, MACD, and trend.
    
    Rules:
    - RSI < 30 = ALWAYS BUY (oversold)
    - RSI > 70 = ALWAYS SELL (overbought)
    - MACD crossover determines direction in neutral RSI zone
    """
    
    @staticmethod
    def determine_direction(
        rsi: float,
        macd_histogram: float,
        macd_line: float,
        signal_line: float,
        price_trend: str,
        confidence: float
    ) -> Tuple[str, float, str]:
        """
        Returns: (signal_direction, confidence_adjustment, reason)
        
        Args:
            rsi: Current RSI value (0-100)
            macd_histogram: MACD histogram value
            macd_line: MACD line value
            signal_line: MACD signal line value
            price_trend: "uptrend", "downtrend", or "neutral"
            confidence: Current confidence value
        """
        
        # ===== RULE 1: Oversold (RSI < 30) = ALWAYS BUY =====
        if rsi < 30:
            if macd_histogram > 0:
                return "BUY", +20, f"RSI {rsi:.1f} (extreme oversold) + MACD+ = Strong BUY"
            elif macd_line > signal_line:
                return "BUY", +15, f"RSI {rsi:.1f} (extreme oversold) + MACD cross = BUY"
            else:
                return "BUY", +10, f"RSI {rsi:.1f} (extreme oversold) = BUY (even without MACD)"
        
        # ===== RULE 2: Overbought (RSI > 70) = ALWAYS SELL =====
        elif rsi > 70:
            if macd_histogram < 0:
                return "SELL", +20, f"RSI {rsi:.1f} (extreme overbought) + MACD- = Strong SELL"
            elif macd_line < signal_line:
                return "SELL", +15, f"RSI {rsi:.1f} (extreme overbought) + MACD cross = SELL"
            else:
                return "SELL", +10, f"RSI {rsi:.1f} (extreme overbought) = SELL (even without MACD)"
        
        # ===== RULE 3: Bullish MACD cross (neutral RSI zone) =====
        elif (macd_histogram > 0.002 and 
              macd_line > signal_line and 
              30 <= rsi <= 70):
            return "BUY", +15, f"Bullish MACD cross + RSI {rsi:.1f} neutral = BUY"
        
        # ===== RULE 4: Bearish MACD cross (neutral RSI zone) =====
        elif (macd_histogram < -0.002 and 
              macd_line < signal_line and 
              30 <= rsi <= 70):
            return "SELL", +15, f"Bearish MACD cross + RSI {rsi:.1f} neutral = SELL"
        
        # ===== RULE 5: Trend confirmation =====
        elif price_trend == "uptrend" and macd_histogram > 0 and rsi < 70:
            return "BUY", +10, f"Uptrend + MACD+ + RSI {rsi:.1f} < 70 = BUY"
        
        elif price_trend == "downtrend" and macd_histogram < 0 and rsi > 30:
            return "SELL", +10, f"Downtrend + MACD- + RSI {rsi:.1f} > 30 = SELL"
        
        # ===== RULE 6: Neutral zone (no clear signal) =====
        else:
            return "NEUTRAL", 0, f"No clear signal (RSI {rsi:.1f}, MACD {macd_histogram:.6f})"

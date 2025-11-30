"""
Signal Filter
Deterministic filtering of trading signals based on Technical Analysis and Risk rules.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SignalFilter:
    """
    Filters and validates raw signals using deterministic rules.
    """

    def __init__(self):
        pass

    def validate_signal(
        self,
        signal_type: str,
        confidence: float,
        indicators: dict[str, Any],
    ) -> float:
        """
        Validate a signal and adjust confidence based on TA alignment.

        Args:
            signal_type: 'BUY', 'SELL', or 'NEUTRAL'
            confidence: Initial confidence (0.0-1.0)
            indicators: Dictionary of technical indicators (rsi, macd, etc.)

        Returns:
            Adjusted confidence score (0.0-1.0)
        """
        if signal_type == "NEUTRAL":
            return 0.0

        score = confidence
        alignment_bonus = 0.0

        # RSI Check
        if "rsi" in indicators:
            rsi = indicators["rsi"]
            if signal_type == "BUY":
                if rsi < 30:
                    alignment_bonus += 0.2  # Oversold
                elif rsi < 50:
                    alignment_bonus += 0.1
                elif rsi > 70:
                    alignment_bonus -= 0.2  # Overbought (risky buy)
            elif signal_type == "SELL":
                if rsi > 70:
                    alignment_bonus += 0.2  # Overbought
                elif rsi > 50:
                    alignment_bonus += 0.1
                elif rsi < 30:
                    alignment_bonus -= 0.2  # Oversold (risky sell)

        # MACD Check
        if "macd" in indicators and "macd_signal" in indicators:
            macd = indicators["macd"]
            signal = indicators["macd_signal"]
            if signal_type == "BUY" and macd > signal:
                alignment_bonus += 0.1
            elif signal_type == "SELL" and macd < signal:
                alignment_bonus += 0.1

        # Volume Check
        if "volume_ratio" in indicators and indicators["volume_ratio"] > 1.2:
            alignment_bonus += 0.1

        # Apply bonus (capped)
        final_score = score + alignment_bonus
        return max(0.0, min(1.0, final_score))

    def check_risk_rules(self, _signal_type: str, _price: float, indicators: dict[str, Any]) -> bool:
        """
        Check if signal violates any hard risk rules.
        """
        # Example: Don't buy if ADX < 20 (no trend)
        if "adx" in indicators and indicators["adx"] < 20:
            return False

        return True

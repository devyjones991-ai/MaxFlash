"""
Candlestick Pattern Recognition for signal confirmation.
Detects common patterns like Engulfing, Doji, Hammer, etc.
"""
import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PatternRecognizer:
    """Candlestick pattern recognition."""
    
    @staticmethod
    def is_bullish_engulfing(candles: pd.DataFrame) -> bool:
        """
        Bullish Engulfing: Current green candle fully engulfs previous red candle.
        Strong bullish reversal signal at bottoms.
        """
        if len(candles) < 2:
            return False
        
        prev = candles.iloc[-2]
        curr = candles.iloc[-1]
        
        prev_is_red = prev['close'] < prev['open']
        curr_is_green = curr['close'] > curr['open']
        curr_engulfs = curr['open'] < prev['close'] and curr['close'] > prev['open']
        
        return prev_is_red and curr_is_green and curr_engulfs
    
    @staticmethod
    def is_bearish_engulfing(candles: pd.DataFrame) -> bool:
        """
        Bearish Engulfing: Current red candle fully engulfs previous green candle.
        Strong bearish reversal signal at tops.
        """
        if len(candles) < 2:
            return False
        
        prev = candles.iloc[-2]
        curr = candles.iloc[-1]
        
        prev_is_green = prev['close'] > prev['open']
        curr_is_red = curr['close'] < curr['open']
        curr_engulfs = curr['open'] > prev['close'] and curr['close'] < prev['open']
        
        return prev_is_green and curr_is_red and curr_engulfs
    
    @staticmethod
    def is_doji(candle: pd.Series, threshold: float = 0.1) -> bool:
        """
        Doji: Open and close are nearly equal.
        Indicates indecision - reduce confidence.
        """
        body = abs(candle['close'] - candle['open'])
        range_size = candle['high'] - candle['low']
        
        if range_size == 0:
            return True  # No range = doji-like
        
        body_ratio = body / range_size
        return body_ratio < threshold
    
    @staticmethod
    def is_hammer(candle: pd.Series) -> bool:
        """
        Hammer: Small body at top, long lower wick.
        Bullish reversal at bottoms.
        """
        body = abs(candle['close'] - candle['open'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        
        if body == 0:
            return False
        
        return lower_wick >= body * 2 and upper_wick < body
    
    @staticmethod
    def is_shooting_star(candle: pd.Series) -> bool:
        """
        Shooting Star: Small body at bottom, long upper wick.
        Bearish reversal at tops.
        """
        body = abs(candle['close'] - candle['open'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        
        if body == 0:
            return False
        
        return upper_wick >= body * 2 and lower_wick < body
    
    def detect_patterns(self, candles: pd.DataFrame) -> Dict[str, bool]:
        """
        Detect all patterns in the last few candles.
        Returns dict of pattern names and their presence.
        """
        patterns = {
            'bullish_engulfing': self.is_bullish_engulfing(candles),
            'bearish_engulfing': self.is_bearish_engulfing(candles),
            'doji': self.is_doji(candles.iloc[-1]) if len(candles) > 0 else False,
            'hammer': self.is_hammer(candles.iloc[-1]) if len(candles) > 0 else False,
            'shooting_star': self.is_shooting_star(candles.iloc[-1]) if len(candles) > 0 else False,
        }
        return patterns
    
    def get_pattern_signal(self, candles: pd.DataFrame) -> tuple:
        """
        Get trading signal from patterns.
        Returns: (signal_adjustment, confidence_adjustment, pattern_name)
        
        signal_adjustment: 'bullish', 'bearish', 'neutral'
        confidence_adjustment: -20 to +20
        """
        patterns = self.detect_patterns(candles)
        
        # Bullish patterns
        if patterns['bullish_engulfing']:
            return 'bullish', 20, 'Engulfing⬆'
        if patterns['hammer']:
            return 'bullish', 15, 'Hammer⬆'
        
        # Bearish patterns
        if patterns['bearish_engulfing']:
            return 'bearish', 20, 'Engulfing⬇'
        if patterns['shooting_star']:
            return 'bearish', 15, 'ShootingStar⬇'
        
        # Indecision
        if patterns['doji']:
            return 'neutral', -10, 'Doji (indecision)'
        
        return 'neutral', 0, ''


class SupportResistance:
    """Support and Resistance level detection."""
    
    @staticmethod
    def find_levels(candles: pd.DataFrame, num_levels: int = 3) -> Dict[str, List[float]]:
        """
        Find support and resistance levels from recent price action.
        Uses pivot points and recent highs/lows.
        """
        if len(candles) < 20:
            return {'support': [], 'resistance': []}
        
        highs = candles['high'].values
        lows = candles['low'].values
        close = candles['close'].iloc[-1]
        
        # Find local highs (resistance) and lows (support)
        resistance_levels = []
        support_levels = []
        
        for i in range(2, len(candles) - 2):
            # Local high (resistance)
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance_levels.append(highs[i])
            
            # Local low (support)
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support_levels.append(lows[i])
        
        # Sort and deduplicate (cluster nearby levels)
        resistance_levels = sorted(set(resistance_levels), reverse=True)[:num_levels]
        support_levels = sorted(set(support_levels))[:num_levels]
        
        return {
            'support': support_levels,
            'resistance': resistance_levels
        }
    
    @staticmethod
    def price_near_level(price: float, levels: List[float], threshold_pct: float = 1.0) -> Optional[float]:
        """
        Check if price is near any level.
        Returns the nearest level or None.
        """
        for level in levels:
            distance_pct = abs(price - level) / level * 100
            if distance_pct <= threshold_pct:
                return level
        return None


def get_pattern_recognizer() -> PatternRecognizer:
    """Factory function."""
    return PatternRecognizer()


def get_sr_detector() -> SupportResistance:
    """Factory function."""
    return SupportResistance()

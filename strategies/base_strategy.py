"""
Base strategy class with common methods for multi-timeframe analysis.
Extends Freqtrade's IStrategy interface.
"""
from typing import Dict, Optional
from freqtrade.strategy import IStrategy
import pandas as pd
import numpy as np


class BaseStrategy(IStrategy):
    """
    Base strategy class providing common functionality for multi-timeframe analysis.
    """
    
    def get_timeframe(self, timeframe: str) -> pd.DataFrame:
        """
        Get data for a specific timeframe.
        Override this method to fetch data from different timeframes.
        
        Args:
            timeframe: Timeframe string (e.g., '1d', '4h', '1h', '15m')
            
        Returns:
            DataFrame with OHLCV data for the specified timeframe
        """
        # This will be implemented in the main strategy
        # to fetch data from Freqtrade's dataframe
        raise NotImplementedError("Subclasses must implement get_timeframe")
    
    def calculate_atr(self, dataframe: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR).
        
        Args:
            dataframe: DataFrame with OHLCV data
            period: Period for ATR calculation
            
        Returns:
            Series with ATR values
        """
        high = dataframe['high']
        low = dataframe['low']
        close = dataframe['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def detect_swing_high(self, dataframe: pd.DataFrame, lookback: int = 5) -> pd.Series:
        """
        Detect swing highs.
        
        Args:
            dataframe: DataFrame with OHLCV data
            lookback: Number of candles to look back/forward
            
        Returns:
            Series with swing high levels (NaN where not a swing high)
        """
        highs = dataframe['high']
        swing_highs = pd.Series(index=dataframe.index, dtype=float)
        
        for i in range(lookback, len(dataframe) - lookback):
            if highs.iloc[i] == highs.iloc[i-lookback:i+lookback+1].max():
                swing_highs.iloc[i] = highs.iloc[i]
        
        return swing_highs
    
    def detect_swing_low(self, dataframe: pd.DataFrame, lookback: int = 5) -> pd.Series:
        """
        Detect swing lows.
        
        Args:
            dataframe: DataFrame with OHLCV data
            lookback: Number of candles to look back/forward
            
        Returns:
            Series with swing low levels (NaN where not a swing low)
        """
        lows = dataframe['low']
        swing_lows = pd.Series(index=dataframe.index, dtype=float)
        
        for i in range(lookback, len(dataframe) - lookback):
            if lows.iloc[i] == lows.iloc[i-lookback:i+lookback+1].min():
                swing_lows.iloc[i] = lows.iloc[i]
        
        return swing_lows
    
    def calculate_pivot_points(self, dataframe: pd.DataFrame, period: int = 20) -> Dict[str, pd.Series]:
        """
        Calculate pivot points.
        
        Args:
            dataframe: DataFrame with OHLCV data
            period: Period for pivot calculation
            
        Returns:
            Dictionary with pivot, support, and resistance levels
        """
        high = dataframe['high'].rolling(window=period).max()
        low = dataframe['low'].rolling(window=period).min()
        close = dataframe['close']
        
        pivot = (high + low + close) / 3
        resistance1 = 2 * pivot - low
        support1 = 2 * pivot - high
        
        return {
            'pivot': pivot,
            'resistance1': resistance1,
            'support1': support1
        }

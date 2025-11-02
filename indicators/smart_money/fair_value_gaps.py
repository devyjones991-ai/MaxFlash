"""
Fair Value Gaps (FVG) detection module.
Identifies price gaps that indicate supply/demand imbalance.
"""
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


class FairValueGapDetector:
    """
    Detects Fair Value Gaps - price gaps between candles indicating imbalance.
    """
    
    def __init__(
        self,
        min_size_pct: float = 0.1,
        max_age_bars: int = 50,
        strong_threshold_pct: float = 0.5
    ):
        """
        Initialize Fair Value Gap detector.
        
        Args:
            min_size_pct: Minimum gap size as percentage (default 0.1%)
            max_age_bars: Maximum age of FVG in bars (default 50)
            strong_threshold_pct: Threshold for strong FVG (default 0.5%)
        """
        self.min_size_pct = min_size_pct
        self.max_age_bars = max_age_bars
        self.strong_threshold_pct = strong_threshold_pct
        self.active_fvgs: List[Dict] = []
    
    def detect_fair_value_gaps(
        self,
        dataframe: pd.DataFrame,
        store_active: bool = True
    ) -> pd.DataFrame:
        """
        Detect Fair Value Gaps in the dataframe.
        
        FVG structure:
        - Bullish FVG: Gap between candle 1 close and candle 3 open
          (candle 2 high < candle 1 close and candle 2 low > candle 3 open)
        - Bearish FVG: Gap between candle 1 close and candle 3 open
          (candle 2 low > candle 1 close and candle 2 high < candle 3 open)
        
        Args:
            dataframe: DataFrame with OHLCV data
            store_active: Whether to store active FVGs
            
        Returns:
            DataFrame with added columns:
            - fvg_bullish_high: Bullish FVG high
            - fvg_bullish_low: Bullish FVG low
            - fvg_bearish_high: Bearish FVG high
            - fvg_bearish_low: Bearish FVG low
            - fvg_type: Type of FVG (bullish/bearish/None)
            - fvg_strength: Strength of FVG (strong/weak)
        """
        df = dataframe.copy()
        
        # Initialize columns
        df['fvg_bullish_high'] = np.nan
        df['fvg_bullish_low'] = np.nan
        df['fvg_bearish_high'] = np.nan
        df['fvg_bearish_low'] = np.nan
        df['fvg_type'] = None
        df['fvg_strength'] = None
        
        fvgs = []
        
        # Detect FVGs by checking 3-candle patterns
        for i in range(2, len(df)):
            # Bullish FVG: candle 1 close < candle 3 open, candle 2 doesn't overlap
            if (df.iloc[i-2]['close'] < df.iloc[i]['open'] and
                df.iloc[i-1]['high'] < df.iloc[i-2]['close'] and
                df.iloc[i-1]['low'] > df.iloc[i]['open']):
                
                fvg_low = df.iloc[i]['open']
                fvg_high = df.iloc[i-2]['close']
                
                # Check minimum size
                size_pct = ((fvg_high - fvg_low) / fvg_low) * 100
                if size_pct >= self.min_size_pct:
                    strength = 'strong' if size_pct >= self.strong_threshold_pct else 'weak'
                    
                    fvg = {
                        'index': i,
                        'high': fvg_high,
                        'low': fvg_low,
                        'type': 'bullish',
                        'strength': strength,
                        'size_pct': size_pct
                    }
                    fvgs.append(fvg)
                    
                    df.loc[df.index[i], 'fvg_bullish_high'] = fvg_high
                    df.loc[df.index[i], 'fvg_bullish_low'] = fvg_low
                    df.loc[df.index[i], 'fvg_type'] = 'bullish'
                    df.loc[df.index[i], 'fvg_strength'] = strength
            
            # Bearish FVG: candle 1 close > candle 3 open, candle 2 doesn't overlap
            elif (df.iloc[i-2]['close'] > df.iloc[i]['open'] and
                  df.iloc[i-1]['low'] > df.iloc[i-2]['close'] and
                  df.iloc[i-1]['high'] < df.iloc[i]['open']):
                
                fvg_high = df.iloc[i]['open']
                fvg_low = df.iloc[i-2]['close']
                
                # Check minimum size
                size_pct = ((fvg_high - fvg_low) / fvg_low) * 100
                if size_pct >= self.min_size_pct:
                    strength = 'strong' if size_pct >= self.strong_threshold_pct else 'weak'
                    
                    fvg = {
                        'index': i,
                        'high': fvg_high,
                        'low': fvg_low,
                        'type': 'bearish',
                        'strength': strength,
                        'size_pct': size_pct
                    }
                    fvgs.append(fvg)
                    
                    df.loc[df.index[i], 'fvg_bearish_high'] = fvg_high
                    df.loc[df.index[i], 'fvg_bearish_low'] = fvg_low
                    df.loc[df.index[i], 'fvg_type'] = 'bearish'
                    df.loc[df.index[i], 'fvg_strength'] = strength
        
        # Forward fill FVG levels until filled or expired
        self._forward_fill_fvgs(df, fvgs)
        
        # Store active FVGs if requested
        if store_active:
            self.active_fvgs = self._get_active_fvgs(df, fvgs)
        
        return df
    
    def _forward_fill_fvgs(
        self,
        dataframe: pd.DataFrame,
        fvgs: List[Dict]
    ):
        """
        Forward fill FVG levels until filled or expired.
        
        FVG is filled when price closes within the gap.
        FVG expires after max_age_bars.
        
        Args:
            dataframe: DataFrame to modify
            fvgs: List of detected FVGs
        """
        for fvg in fvgs:
            fvg_type = fvg['type']
            fvg_high = fvg['high']
            fvg_low = fvg['low']
            start_idx = fvg['index']
            
            # Forward fill until filled or expired
            for i in range(start_idx + 1, min(start_idx + self.max_age_bars + 1, len(dataframe))):
                current_close = dataframe.loc[dataframe.index[i], 'close']
                
                # Check if FVG is filled
                if fvg_low <= current_close <= fvg_high:
                    # FVG filled, stop forward filling
                    break
                
                # Keep FVG active
                if fvg_type == 'bullish':
                    dataframe.loc[dataframe.index[i], 'fvg_bullish_high'] = fvg_high
                    dataframe.loc[dataframe.index[i], 'fvg_bullish_low'] = fvg_low
                    dataframe.loc[dataframe.index[i], 'fvg_type'] = 'bullish'
                    dataframe.loc[dataframe.index[i], 'fvg_strength'] = fvg['strength']
                elif fvg_type == 'bearish':
                    dataframe.loc[dataframe.index[i], 'fvg_bearish_high'] = fvg_high
                    dataframe.loc[dataframe.index[i], 'fvg_bearish_low'] = fvg_low
                    dataframe.loc[dataframe.index[i], 'fvg_type'] = 'bearish'
                    dataframe.loc[dataframe.index[i], 'fvg_strength'] = fvg['strength']
    
    def _get_active_fvgs(
        self,
        dataframe: pd.DataFrame,
        fvgs: List[Dict]
    ) -> List[Dict]:
        """
        Get currently active Fair Value Gaps.
        
        Args:
            dataframe: DataFrame with FVG data
            fvgs: List of all FVGs
            
        Returns:
            List of active FVGs
        """
        active = []
        current_idx = len(dataframe) - 1
        
        for fvg in fvgs:
            if fvg['index'] >= current_idx:
                continue
            
            # Check if FVG is still active (not filled and not expired)
            age = current_idx - fvg['index']
            if age > self.max_age_bars:
                continue
            
            current_close = dataframe.loc[dataframe.index[current_idx], 'close']
            
            # Check if FVG is filled
            if fvg['low'] <= current_close <= fvg['high']:
                continue  # FVG filled
            
            # FVG is still active
            active.append(fvg)
        
        return active
    
    def is_price_in_fvg(
        self,
        price: float,
        fvgs: Optional[List[Dict]] = None
    ) -> Optional[Dict]:
        """
        Check if price is currently in a Fair Value Gap.
        
        Args:
            price: Current price
            fvgs: List of FVGs (uses active_fvgs if None)
            
        Returns:
            FVG dictionary if price is in FVG, None otherwise
        """
        if fvgs is None:
            fvgs = self.active_fvgs
        
        for fvg in fvgs:
            if fvg['low'] <= price <= fvg['high']:
                return fvg
        
        return None
    
    def get_fvgs_list(self) -> List[Dict]:
        """
        Get list of active Fair Value Gaps.
        
        Returns:
            List of active FVG dictionaries
        """
        return self.active_fvgs.copy()


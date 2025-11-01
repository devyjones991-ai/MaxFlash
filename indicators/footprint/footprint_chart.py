"""
Footprint Chart module.
Builds footprint structure showing volume at each price level.
"""
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


class FootprintChart:
    """
    Builds footprint charts showing buy/sell volume at each price level.
    """
    
    def __init__(self, bins: int = 50):
        """
        Initialize Footprint Chart builder.
        
        Args:
            bins: Number of price bins (default 50)
        """
        self.bins = bins
    
    def build_footprint(
        self,
        dataframe: pd.DataFrame,
        period: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Build footprint chart for the dataframe.
        
        Args:
            dataframe: DataFrame with OHLCV data
            period: Period for rolling calculation (None = entire dataframe)
            
        Returns:
            DataFrame with added columns:
            - fp_buy_volume: Buy volume at price level
            - fp_sell_volume: Sell volume at price level
            - fp_total_volume: Total volume at price level
            - fp_price_level: Price level
        """
        df = dataframe.copy()
        
        # For now, we'll use simplified approach since full order flow data
        # requires Level 2 market data
        # We estimate buy/sell volume based on price action
        
        df['fp_buy_volume'] = np.where(
            df['close'] > df['open'],
            df['volume'] * 0.6,  # Assume 60% buy volume on green candles
            df['volume'] * 0.4
        )
        
        df['fp_sell_volume'] = np.where(
            df['close'] < df['open'],
            df['volume'] * 0.6,  # Assume 60% sell volume on red candles
            df['volume'] * 0.4
        )
        
        df['fp_total_volume'] = df['volume']
        
        return df
    
    def get_footprint_at_price(
        self,
        dataframe: pd.DataFrame,
        price: float,
        tolerance_pct: float = 0.001
    ) -> Dict:
        """
        Get footprint data at a specific price level.
        
        Args:
            dataframe: DataFrame with footprint data
            price: Target price
            tolerance_pct: Price tolerance
            
        Returns:
            Dictionary with footprint data at price level
        """
        tolerance = price * tolerance_pct
        
        # Find candles that include this price
        mask = (
            (dataframe['low'] <= price + tolerance) &
            (dataframe['high'] >= price - tolerance)
        )
        
        relevant_data = dataframe[mask]
        
        if len(relevant_data) == 0:
            return {
                'buy_volume': 0.0,
                'sell_volume': 0.0,
                'total_volume': 0.0
            }
        
        return {
            'buy_volume': relevant_data['fp_buy_volume'].sum(),
            'sell_volume': relevant_data['fp_sell_volume'].sum(),
            'total_volume': relevant_data['fp_total_volume'].sum()
        }

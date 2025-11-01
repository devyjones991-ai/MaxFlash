"""
Initial Balance (IB) calculation module.
IB is the price range established in the first hour of trading.
"""
from typing import Dict, Tuple
import pandas as pd
import numpy as np


class InitialBalanceCalculator:
    """
    Calculates Initial Balance - the price range from the first trading hour.
    """
    
    def __init__(self, ib_periods: int = 4):
        """
        Initialize Initial Balance calculator.
        
        Args:
            ib_periods: Number of periods for Initial Balance (default 4 for hourly = 4 hours)
        """
        self.ib_periods = ib_periods
    
    def calculate_initial_balance(
        self,
        dataframe: pd.DataFrame
    ) -> Tuple[float, float]:
        """
        Calculate Initial Balance for the current period.
        
        Args:
            dataframe: DataFrame with OHLCV data
            
        Returns:
            Tuple of (IB high, IB low)
        """
        if len(dataframe) < self.ib_periods:
            # Not enough data, use available data
            ib_data = dataframe
        else:
            # Use first IB_periods
            ib_data = dataframe.iloc[:self.ib_periods]
        
        ib_high = ib_data['high'].max()
        ib_low = ib_data['low'].min()
        
        return (ib_high, ib_low)
    
    def is_price_in_ib(
        self,
        price: float,
        ib_high: float,
        ib_low: float,
        tolerance_pct: float = 0.001
    ) -> bool:
        """
        Check if price is within Initial Balance.
        
        Args:
            price: Current price
            ib_high: IB high level
            ib_low: IB low level
            tolerance_pct: Percentage tolerance
            
        Returns:
            True if price is in IB
        """
        tolerance = ib_low * tolerance_pct
        return (ib_low - tolerance) <= price <= (ib_high + tolerance)

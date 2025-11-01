"""
Order Flow analysis module.
Analyzes the flow of buy and sell orders.
"""
from typing import Dict, List
import pandas as pd
import numpy as np


class OrderFlowAnalyzer:
    """
    Analyzes order flow patterns and imbalances.
    """
    
    def __init__(self, absorption_threshold: float = 2.0):
        """
        Initialize Order Flow analyzer.
        
        Args:
            absorption_threshold: Threshold for absorption detection (default 2.0)
        """
        self.absorption_threshold = absorption_threshold
    
    def analyze_order_flow(
        self,
        dataframe: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Analyze order flow patterns.
        
        Args:
            dataframe: DataFrame with footprint and delta data
            
        Returns:
            DataFrame with added columns:
            - of_buying_pressure: Buying pressure indicator
            - of_selling_pressure: Selling pressure indicator
            - of_imbalance: Order flow imbalance
        """
        df = dataframe.copy()
        
        # Calculate buying/selling pressure
        df['of_buying_pressure'] = df['fp_buy_volume'].rolling(window=5).mean()
        df['of_selling_pressure'] = df['fp_sell_volume'].rolling(window=5).mean()
        
        # Calculate imbalance
        df['of_imbalance'] = (
            (df['of_buying_pressure'] - df['of_selling_pressure']) /
            (df['of_buying_pressure'] + df['of_selling_pressure']).replace(0, np.nan)
        ) * 100
        
        return df
    
    def detect_liquidity_zones(
        self,
        dataframe: pd.DataFrame
    ) -> List[Dict]:
        """
        Detect liquidity zones based on order flow.
        
        Args:
            dataframe: DataFrame with order flow data
            
        Returns:
            List of liquidity zone dictionaries
        """
        liquidity_zones = []
        
        # High volume zones with low price movement = liquidity pools
        for i in range(20, len(dataframe)):
            window_data = dataframe.iloc[i-20:i]
            
            high_volume = window_data['fp_total_volume'].quantile(0.8)
            low_volatility = (window_data['high'] - window_data['low']).quantile(0.2)
            
            current_volume = dataframe.iloc[i]['fp_total_volume']
            current_range = dataframe.iloc[i]['high'] - dataframe.iloc[i]['low']
            
            if current_volume > high_volume and current_range < low_volatility:
                liquidity_zones.append({
                    'price': dataframe.iloc[i]['close'],
                    'high': dataframe.iloc[i]['high'],
                    'low': dataframe.iloc[i]['low'],
                    'volume': current_volume,
                    'type': 'liquidity_pool'
                })
        
        return liquidity_zones

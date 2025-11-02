"""
TPO (Time Price Opportunity) analysis module.
Analyzes price distribution over time using TPO letters.
"""
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


class TPOCalculator:
    """
    Calculates TPO (Time Price Opportunity) distribution.
    Each trading period is assigned a letter (A, B, C, etc.)
    showing how price spent time at different levels.
    """
    
    def __init__(
        self,
        periods_per_day: int = 24,
        bins: int = 30
    ):
        """
        Initialize TPO calculator.
        
        Args:
            periods_per_day: Number of TPO periods per day (default 24 for hourly)
            bins: Number of price bins (default 30)
        """
        self.periods_per_day = periods_per_day
        self.bins = bins
        self.tpo_letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    
    def calculate_tpo_distribution(
        self,
        dataframe: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate TPO distribution for the dataframe.
        
        Args:
            dataframe: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added columns:
            - tpo_distribution: TPO distribution data
            - tpo_single_prints: Single print levels (impulse zones)
            - tpo_poor_high: Poor high level
            - tpo_poor_low: Poor low level
            - tpo_initial_balance: Initial Balance range
        """
        df = dataframe.copy()
        
        # Initialize columns
        df['tpo_single_prints'] = None
        df['tpo_poor_high'] = np.nan
        df['tpo_poor_low'] = np.nan
        df['tpo_ib_high'] = np.nan
        df['tpo_ib_low'] = np.nan
        
        # Calculate TPO for rolling windows (e.g., daily)
        window_size = self.periods_per_day
        
        for i in range(window_size, len(df)):
            window_data = df.iloc[i-window_size:i+1]
            tpo_data = self._calculate_tpo_for_window(window_data, i - window_size)
            
            df.loc[df.index[i], 'tpo_single_prints'] = str(tpo_data['single_prints'])
            df.loc[df.index[i], 'tpo_poor_high'] = tpo_data['poor_high']
            df.loc[df.index[i], 'tpo_poor_low'] = tpo_data['poor_low']
            df.loc[df.index[i], 'tpo_ib_high'] = tpo_data['ib_high']
            df.loc[df.index[i], 'tpo_ib_low'] = tpo_data['ib_low']
        
        return df
    
    def _calculate_tpo_for_window(
        self,
        dataframe: pd.DataFrame,
        start_period: int
    ) -> Dict:
        """
        Calculate TPO distribution for a time window.
        
        Args:
            dataframe: DataFrame with OHLCV data for the window
            start_period: Starting period index for TPO letter assignment
            
        Returns:
            Dictionary with TPO data
        """
        if len(dataframe) == 0:
            return {
                'single_prints': [],
                'poor_high': np.nan,
                'poor_low': np.nan,
                'ib_high': np.nan,
                'ib_low': np.nan
            }
        
        # Get price range
        price_min = dataframe['low'].min()
        price_max = dataframe['high'].max()
        
        if price_min == price_max:
            midpoint = price_min
            return {
                'single_prints': [],
                'poor_high': midpoint,
                'poor_low': midpoint,
                'ib_high': midpoint,
                'ib_low': midpoint
            }
        
        # Create price bins
        bin_edges = np.linspace(price_min, price_max, self.bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Create TPO matrix: bins x periods
        tpo_matrix = {}
        
        # Assign TPO letters to each period
        for period_idx, (idx, row) in enumerate(dataframe.iterrows()):
            tpo_letter = self.tpo_letters[(start_period + period_idx) % len(self.tpo_letters)]
            
            low = row['low']
            high = row['high']
            
            # Find bins that this candle covers
            low_bin = np.searchsorted(bin_edges, low)
            high_bin = np.searchsorted(bin_edges, high)
            
            low_bin = max(0, min(low_bin, self.bins - 1))
            high_bin = max(0, min(high_bin, self.bins - 1))
            
            # Mark bins with TPO letter
            for bin_idx in range(low_bin, high_bin + 1):
                if bin_idx not in tpo_matrix:
                    tpo_matrix[bin_idx] = []
                tpo_matrix[bin_idx].append(tpo_letter)
        
        # Find single prints (bins with only one TPO letter)
        single_prints = []
        for bin_idx, tpo_letters in tpo_matrix.items():
            if len(tpo_letters) == 1:
                single_prints.append(bin_centers[bin_idx])
        
        # Find poor high and poor low (single prints at extremes)
        poor_high = np.nan
        poor_low = np.nan
        
        if single_prints:
            single_print_bins = [bin_idx for bin_idx, letters in tpo_matrix.items() 
                               if len(letters) == 1]
            if single_print_bins:
                highest_single = max(single_print_bins)
                lowest_single = min(single_print_bins)
                
                # Poor high: single print near top
                if highest_single >= self.bins * 0.8:  # Top 20% of range
                    poor_high = bin_centers[highest_single]
                
                # Poor low: single print near bottom
                if lowest_single <= self.bins * 0.2:  # Bottom 20% of range
                    poor_low = bin_centers[lowest_single]
        
        # Calculate Initial Balance (first hour range)
        ib_size = min(len(dataframe), 4)  # First 4 periods (roughly first hour)
        ib_data = dataframe.iloc[:ib_size]
        
        ib_high = ib_data['high'].max()
        ib_low = ib_data['low'].min()
        
        return {
            'single_prints': single_prints,
            'poor_high': poor_high,
            'poor_low': poor_low,
            'ib_high': ib_high,
            'ib_low': ib_low
        }
    
    def get_tpo_summary(
        self,
        dataframe: pd.DataFrame
    ) -> Dict:
        """
        Get current TPO summary.
        
        Args:
            dataframe: DataFrame with TPO data
            
        Returns:
            Dictionary with TPO summary
        """
        last_row = dataframe.iloc[-1]
        
        # Parse single prints if stored as string
        single_prints = last_row.get('tpo_single_prints', [])
        if isinstance(single_prints, str):
            try:
                single_prints = eval(single_prints)
            except:
                single_prints = []
        
        return {
            'single_prints': single_prints,
            'poor_high': last_row.get('tpo_poor_high', None),
            'poor_low': last_row.get('tpo_poor_low', None),
            'ib_high': last_row.get('tpo_ib_high', None),
            'ib_low': last_row.get('tpo_ib_low', None)
        }


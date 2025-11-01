"""
Order Blocks detection module.
Identifies consolidation zones before impulsive price movements.
"""
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


class OrderBlockDetector:
    """
    Detects Order Blocks (OB) - zones where institutions placed large orders
    before an impulsive move.
    """
    
    def __init__(
        self,
        min_candles: int = 3,
        max_candles: int = 5,
        impulse_threshold_pct: float = 1.5,
        lookback: int = 20
    ):
        """
        Initialize Order Block detector.
        
        Args:
            min_candles: Minimum candles in consolidation (default 3)
            max_candles: Maximum candles in consolidation (default 5)
            impulse_threshold_pct: Minimum impulse move percentage (default 1.5%)
            lookback: Lookback period for finding impulses (default 20)
        """
        self.min_candles = min_candles
        self.max_candles = max_candles
        self.impulse_threshold_pct = impulse_threshold_pct
        self.lookback = lookback
        self.active_blocks: List[Dict] = []
    
    def detect_order_blocks(
        self,
        dataframe: pd.DataFrame,
        store_active: bool = True
    ) -> pd.DataFrame:
        """
        Detect Order Blocks in the dataframe.
        
        Args:
            dataframe: DataFrame with OHLCV data
            store_active: Whether to store active blocks for confluence
            
        Returns:
            DataFrame with added columns:
            - ob_bullish_high: Bullish OB high
            - ob_bullish_low: Bullish OB low
            - ob_bearish_high: Bearish OB high
            - ob_bearish_low: Bearish OB low
            - ob_type: Type of OB (bullish/bearish/None)
        """
        df = dataframe.copy()
        
        # Initialize columns
        df['ob_bullish_high'] = np.nan
        df['ob_bullish_low'] = np.nan
        df['ob_bearish_high'] = np.nan
        df['ob_bearish_low'] = np.nan
        df['ob_type'] = None
        
        # Detect bullish Order Blocks
        bullish_obs = self._detect_bullish_order_blocks(df)
        
        # Detect bearish Order Blocks
        bearish_obs = self._detect_bearish_order_blocks(df)
        
        # Mark Order Blocks in dataframe
        for ob in bullish_obs:
            idx = ob['index']
            df.loc[idx, 'ob_bullish_high'] = ob['high']
            df.loc[idx, 'ob_bullish_low'] = ob['low']
            df.loc[idx, 'ob_type'] = 'bullish'
        
        for ob in bearish_obs:
            idx = ob['index']
            df.loc[idx, 'ob_bearish_high'] = ob['high']
            df.loc[idx, 'ob_bearish_low'] = ob['low']
            df.loc[idx, 'ob_type'] = 'bearish'
        
        # Forward fill Order Block levels until they're invalidated
        self._forward_fill_order_blocks(df, bullish_obs + bearish_obs)
        
        # Store active blocks if requested
        if store_active:
            self.active_blocks = self._get_active_blocks(df, bullish_obs + bearish_obs)
        
        return df
    
    def _detect_bullish_order_blocks(
        self,
        dataframe: pd.DataFrame
    ) -> List[Dict]:
        """
        Detect bullish Order Blocks.
        
        Bullish OB: Consolidation before upward impulse.
        
        Args:
            dataframe: DataFrame with OHLCV data
            
        Returns:
            List of Order Block dictionaries
        """
        order_blocks = []
        df = dataframe.copy()
        
        # Calculate price change percentage
        df['price_change_pct'] = df['close'].pct_change() * 100
        
        for i in range(self.lookback, len(df) - self.max_candles):
            # Look for upward impulse
            future_max = df['high'].iloc[i+1:i+self.lookback+1].max()
            current_close = df['close'].iloc[i]
            
            if future_max > current_close:
                impulse_pct = ((future_max - current_close) / current_close) * 100
                
                if impulse_pct >= self.impulse_threshold_pct:
                    # Found impulse, look back for consolidation
                    ob = self._find_consolidation_before_impulse(
                        df, i, direction='bullish'
                    )
                    if ob:
                        ob['index'] = i
                        order_blocks.append(ob)
        
        return order_blocks
    
    def _detect_bearish_order_blocks(
        self,
        dataframe: pd.DataFrame
    ) -> List[Dict]:
        """
        Detect bearish Order Blocks.
        
        Bearish OB: Consolidation before downward impulse.
        
        Args:
            dataframe: DataFrame with OHLCV data
            
        Returns:
            List of Order Block dictionaries
        """
        order_blocks = []
        df = dataframe.copy()
        
        # Calculate price change percentage
        df['price_change_pct'] = df['close'].pct_change() * 100
        
        for i in range(self.lookback, len(df) - self.max_candles):
            # Look for downward impulse
            future_min = df['low'].iloc[i+1:i+self.lookback+1].min()
            current_close = df['close'].iloc[i]
            
            if future_min < current_close:
                impulse_pct = ((current_close - future_min) / current_close) * 100
                
                if impulse_pct >= self.impulse_threshold_pct:
                    # Found impulse, look back for consolidation
                    ob = self._find_consolidation_before_impulse(
                        df, i, direction='bearish'
                    )
                    if ob:
                        ob['index'] = i
                        order_blocks.append(ob)
        
        return order_blocks
    
    def _find_consolidation_before_impulse(
        self,
        dataframe: pd.DataFrame,
        impulse_start_idx: int,
        direction: str
    ) -> Optional[Dict]:
        """
        Find consolidation zone before an impulse.
        
        Args:
            dataframe: DataFrame with OHLCV data
            impulse_start_idx: Index where impulse starts
            direction: 'bullish' or 'bearish'
            
        Returns:
            Order Block dictionary or None
        """
        # Look back for consolidation
        start_idx = max(0, impulse_start_idx - self.max_candles)
        end_idx = impulse_start_idx
        
        if end_idx - start_idx < self.min_candles:
            return None
        
        # Check consolidation: low volatility, sideways movement
        consolidation_range = dataframe.iloc[start_idx:end_idx]
        
        # Calculate volatility (ATR normalized)
        high_range = consolidation_range['high'].max()
        low_range = consolidation_range['low'].min()
        range_pct = ((high_range - low_range) / consolidation_range['close'].mean()) * 100
        
        # Check if range is small enough (consolidation)
        avg_range = (dataframe['high'] - dataframe['low']).mean()
        avg_range_pct = (avg_range / dataframe['close'].mean()) * 100
        
        if range_pct > avg_range_pct * 1.5:
            return None  # Too volatile for consolidation
        
        # Valid Order Block
        return {
            'high': high_range,
            'low': low_range,
            'type': direction,
            'start_index': start_idx,
            'end_index': end_idx,
            'impulse_start': impulse_start_idx
        }
    
    def _forward_fill_order_blocks(
        self,
        dataframe: pd.DataFrame,
        order_blocks: List[Dict]
    ):
        """
        Forward fill Order Block levels until invalidated.
        
        An OB is invalidated when:
        - Price closes beyond the OB (bullish OB: close below low, bearish OB: close above high)
        - Price has moved significantly away from OB
        
        Args:
            dataframe: DataFrame to modify
            order_blocks: List of detected Order Blocks
        """
        for ob in order_blocks:
            ob_type = ob['type']
            ob_high = ob['high']
            ob_low = ob['low']
            start_idx = ob['index']
            
            # Forward fill until invalidated
            for i in range(start_idx + 1, len(dataframe)):
                current_close = dataframe.loc[dataframe.index[i], 'close']
                
                # Check invalidation
                if ob_type == 'bullish':
                    # Bullish OB invalidated if close below low
                    if current_close < ob_low:
                        break
                    # Keep OB active
                    dataframe.loc[dataframe.index[i], 'ob_bullish_high'] = ob_high
                    dataframe.loc[dataframe.index[i], 'ob_bullish_low'] = ob_low
                    dataframe.loc[dataframe.index[i], 'ob_type'] = 'bullish'
                
                elif ob_type == 'bearish':
                    # Bearish OB invalidated if close above high
                    if current_close > ob_high:
                        break
                    # Keep OB active
                    dataframe.loc[dataframe.index[i], 'ob_bearish_high'] = ob_high
                    dataframe.loc[dataframe.index[i], 'ob_bearish_low'] = ob_low
                    dataframe.loc[dataframe.index[i], 'ob_type'] = 'bearish'
    
    def _get_active_blocks(
        self,
        dataframe: pd.DataFrame,
        order_blocks: List[Dict]
    ) -> List[Dict]:
        """
        Get currently active Order Blocks.
        
        Args:
            dataframe: DataFrame with Order Block data
            order_blocks: List of all Order Blocks
            
        Returns:
            List of active Order Blocks
        """
        active = []
        current_idx = len(dataframe) - 1
        
        for ob in order_blocks:
            if ob['index'] >= current_idx:
                continue
            
            # Check if OB is still active
            ob_type = ob['type']
            current_close = dataframe.loc[dataframe.index[current_idx], 'close']
            
            if ob_type == 'bullish':
                if current_close >= ob['low']:
                    active.append(ob)
            elif ob_type == 'bearish':
                if current_close <= ob['high']:
                    active.append(ob)
        
        return active
    
    def is_price_in_order_block(
        self,
        price: float,
        order_blocks: Optional[List[Dict]] = None
    ) -> Optional[Dict]:
        """
        Check if price is currently in an Order Block.
        
        Args:
            price: Current price
            order_blocks: List of Order Blocks (uses active_blocks if None)
            
        Returns:
            Order Block dictionary if price is in OB, None otherwise
        """
        if order_blocks is None:
            order_blocks = self.active_blocks
        
        for ob in order_blocks:
            if ob['low'] <= price <= ob['high']:
                return ob
        
        return None
    
    def get_order_blocks_list(self) -> List[Dict]:
        """
        Get list of active Order Blocks.
        
        Returns:
            List of active Order Block dictionaries
        """
        return self.active_blocks.copy()

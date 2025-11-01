"""
Optimized Order Blocks detection with vectorization.
Использует numpy векторизацию для максимальной скорости.
"""
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from utils.performance import global_profiler, global_cache


class OrderBlockDetectorOptimized:
    """
    Оптимизированный детектор Order Blocks с векторизацией.
    """
    
    def __init__(
        self,
        min_candles: int = 3,
        max_candles: int = 5,
        impulse_threshold_pct: float = 1.5,
        lookback: int = 20,
        use_cache: bool = True
    ):
        self.min_candles = min_candles
        self.max_candles = max_candles
        self.impulse_threshold_pct = impulse_threshold_pct
        self.lookback = lookback
        self.use_cache = use_cache
        self.active_blocks: List[Dict] = []
    
    def detect_order_blocks(
        self,
        dataframe: pd.DataFrame,
        store_active: bool = True
    ) -> pd.DataFrame:
        """
        Векторизованная детекция Order Blocks.
        """
        global_profiler.start('order_blocks_detection')
        
        df = dataframe.copy()
        
        # Initialize columns
        df['ob_bullish_high'] = np.nan
        df['ob_bullish_low'] = np.nan
        df['ob_bearish_high'] = np.nan
        df['ob_bearish_low'] = np.nan
        df['ob_type'] = None
        
        # Векторизованные вычисления
        high_values = df['high'].values
        low_values = df['low'].values
        close_values = df['close'].values
        
        # Bullish OB detection (векторизовано)
        bullish_obs = self._detect_bullish_ob_vectorized(
            high_values, low_values, close_values, df.index
        )
        
        # Bearish OB detection (векторизовано)
        bearish_obs = self._detect_bearish_ob_vectorized(
            high_values, low_values, close_values, df.index
        )
        
        # Mark Order Blocks
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
        
        # Forward fill
        self._forward_fill_order_blocks_vectorized(df, bullish_obs + bearish_obs)
        
        if store_active:
            self.active_blocks = self._get_active_blocks(df, bullish_obs + bearish_obs)
        
        global_profiler.stop('order_blocks_detection')
        return df
    
    def _detect_bullish_ob_vectorized(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        index: pd.Index
    ) -> List[Dict]:
        """
        Векторизованная детекция bullish Order Blocks.
        """
        order_blocks = []
        n = len(highs)
        
        # Векторизованный поиск импульсов вверх
        for i in range(self.lookback, n - self.max_candles):
            current_close = closes[i]
            
            # Векторизованный поиск максимума в будущем
            future_window = highs[i+1:min(i+self.lookback+1, n)]
            if len(future_window) > 0:
                future_max = np.max(future_window)
                
                if future_max > current_close:
                    impulse_pct = ((future_max - current_close) / current_close) * 100
                    
                    if impulse_pct >= self.impulse_threshold_pct:
                        # Поиск консолидации
                        ob = self._find_consolidation_vectorized(
                            highs, lows, closes, i, 'bullish'
                        )
                        if ob:
                            ob['index'] = index[i]
                            order_blocks.append(ob)
        
        return order_blocks
    
    def _detect_bearish_ob_vectorized(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        index: pd.Index
    ) -> List[Dict]:
        """
        Векторизованная детекция bearish Order Blocks.
        """
        order_blocks = []
        n = len(lows)
        
        for i in range(self.lookback, n - self.max_candles):
            current_close = closes[i]
            
            future_window = lows[i+1:min(i+self.lookback+1, n)]
            if len(future_window) > 0:
                future_min = np.min(future_window)
                
                if future_min < current_close:
                    impulse_pct = ((current_close - future_min) / current_close) * 100
                    
                    if impulse_pct >= self.impulse_threshold_pct:
                        ob = self._find_consolidation_vectorized(
                            highs, lows, closes, i, 'bearish'
                        )
                        if ob:
                            ob['index'] = index[i]
                            order_blocks.append(ob)
        
        return order_blocks
    
    def _find_consolidation_vectorized(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        impulse_start_idx: int,
        direction: str
    ) -> Optional[Dict]:
        """
        Векторизованный поиск консолидации.
        """
        start_idx = max(0, impulse_start_idx - self.max_candles)
        end_idx = impulse_start_idx
        
        if end_idx - start_idx < self.min_candles:
            return None
        
        # Векторизованные вычисления волатильности
        consolidation_highs = highs[start_idx:end_idx]
        consolidation_lows = lows[start_idx:end_idx]
        consolidation_closes = closes[start_idx:end_idx]
        
        high_range = np.max(consolidation_highs)
        low_range = np.min(consolidation_lows)
        range_pct = ((high_range - low_range) / np.mean(consolidation_closes)) * 100
        
        # Проверка на консолидацию
        avg_range_pct = ((highs - lows) / closes).mean() * 100
        
        if range_pct > avg_range_pct * 1.5:
            return None
        
        return {
            'high': high_range,
            'low': low_range,
            'type': direction,
            'start_index': start_idx,
            'end_index': end_idx,
            'impulse_start': impulse_start_idx
        }
    
    def _forward_fill_order_blocks_vectorized(
        self,
        dataframe: pd.DataFrame,
        order_blocks: List[Dict]
    ):
        """
        Оптимизированный forward fill с векторизацией где возможно.
        """
        close_values = dataframe['close'].values
        index_values = dataframe.index.values
        
        for ob in order_blocks:
            ob_type = ob['type']
            ob_high = ob['high']
            ob_low = ob['low']
            
            # Найти индекс начала
            start_pos = np.where(index_values == ob['index'])[0]
            if len(start_pos) == 0:
                continue
            start_idx = start_pos[0] + 1
            
            # Векторизованная проверка инвалидации
            if ob_type == 'bullish':
                # Bullish invalidated when close < ob_low
                invalidation_mask = close_values[start_idx:] < ob_low
                if np.any(invalidation_mask):
                    end_idx = start_idx + np.argmax(invalidation_mask)
                else:
                    end_idx = len(dataframe)
                
                # Векторизованное заполнение
                dataframe.iloc[start_idx:end_idx, dataframe.columns.get_loc('ob_bullish_high')] = ob_high
                dataframe.iloc[start_idx:end_idx, dataframe.columns.get_loc('ob_bullish_low')] = ob_low
                dataframe.iloc[start_idx:end_idx, dataframe.columns.get_loc('ob_type')] = 'bullish'
            
            elif ob_type == 'bearish':
                invalidation_mask = close_values[start_idx:] > ob_high
                if np.any(invalidation_mask):
                    end_idx = start_idx + np.argmax(invalidation_mask)
                else:
                    end_idx = len(dataframe)
                
                dataframe.iloc[start_idx:end_idx, dataframe.columns.get_loc('ob_bearish_high')] = ob_high
                dataframe.iloc[start_idx:end_idx, dataframe.columns.get_loc('ob_bearish_low')] = ob_low
                dataframe.iloc[start_idx:end_idx, dataframe.columns.get_loc('ob_type')] = 'bearish'
    
    def _get_active_blocks(
        self,
        dataframe: pd.DataFrame,
        order_blocks: List[Dict]
    ) -> List[Dict]:
        """Get active Order Blocks."""
        active = []
        current_idx = len(dataframe) - 1
        
        if current_idx < 0:
            return active
        
        current_close = dataframe['close'].iloc[current_idx]
        
        for ob in order_blocks:
            ob_type = ob.get('type')
            if ob_type == 'bullish' and current_close >= ob['low']:
                active.append(ob)
            elif ob_type == 'bearish' and current_close <= ob['high']:
                active.append(ob)
        
        return active
    
    def is_price_in_order_block(
        self,
        price: float,
        order_blocks: Optional[List[Dict]] = None
    ) -> Optional[Dict]:
        """Check if price is in Order Block."""
        if order_blocks is None:
            order_blocks = self.active_blocks
        
        for ob in order_blocks:
            if ob['low'] <= price <= ob['high']:
                return ob
        return None

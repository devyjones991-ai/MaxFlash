"""
Валидация данных для торговой системы.
Проверка корректности входных данных перед обработкой.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Валидатор данных для торговых индикаторов.
    """
    
    REQUIRED_COLUMNS = ['open', 'high', 'low', 'close', 'volume']
    
    @staticmethod
    def validate_ohlcv(dataframe: pd.DataFrame) -> Tuple[bool, Optional[str]]:
        """
        Валидация OHLCV данных.
        
        Args:
            dataframe: DataFrame для проверки
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if dataframe is None or len(dataframe) == 0:
            return (False, "DataFrame is empty or None")
        
        # Проверка обязательных колонок
        missing_cols = [col for col in DataValidator.REQUIRED_COLUMNS 
                       if col not in dataframe.columns]
        if missing_cols:
            return (False, f"Missing required columns: {missing_cols}")
        
        # Проверка на NaN
        for col in DataValidator.REQUIRED_COLUMNS:
            nan_count = dataframe[col].isna().sum()
            if nan_count > len(dataframe) * 0.1:  # Более 10% NaN
                logger.warning(f"Column {col} has {nan_count} NaN values ({nan_count/len(dataframe)*100:.1f}%)")
        
        # Проверка логики OHLC
        invalid_rows = (
            (dataframe['high'] < dataframe['low']) |
            (dataframe['high'] < dataframe['open']) |
            (dataframe['high'] < dataframe['close']) |
            (dataframe['low'] > dataframe['open']) |
            (dataframe['low'] > dataframe['close'])
        )
        
        if invalid_rows.any():
            invalid_count = invalid_rows.sum()
            return (False, f"Found {invalid_count} rows with invalid OHLC values")
        
        # Проверка объема
        negative_volume = (dataframe['volume'] < 0).sum()
        if negative_volume > 0:
            logger.warning(f"Found {negative_volume} rows with negative volume")
        
        return (True, None)
    
    @staticmethod
    def clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Очистка DataFrame от некорректных данных.
        
        Args:
            dataframe: DataFrame для очистки
            
        Returns:
            Очищенный DataFrame
        """
        df = dataframe.copy()
        
        # Удаление строк с NaN в критических колонках
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        
        # Исправление логических ошибок OHLC
        # High должен быть максимальным
        df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
        # Low должен быть минимальным
        df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
        
        # Отрицательный объем -> 0
        df.loc[df['volume'] < 0, 'volume'] = 0
        
        # Удаление дубликатов по индексу
        df = df[~df.index.duplicated(keep='last')]
        
        # Сортировка по индексу
        df = df.sort_index()
        
        return df
    
    @staticmethod
    def validate_price_level(price: float, min_price: float = 0.0) -> bool:
        """Валидация ценового уровня."""
        if not isinstance(price, (int, float)):
            return False
        if np.isnan(price) or np.isinf(price):
            return False
        if price < min_price:
            return False
        return True
    
    @staticmethod
    def validate_percentage(value: float, min_val: float = 0.0, max_val: float = 100.0) -> bool:
        """Валидация процентного значения."""
        if not isinstance(value, (int, float)):
            return False
        if np.isnan(value) or np.isinf(value):
            return False
        return min_val <= value <= max_val

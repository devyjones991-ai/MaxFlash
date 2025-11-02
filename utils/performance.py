"""
Performance optimization utilities.
Caching, vectorization helpers, and performance profiling.
"""
from functools import lru_cache
from typing import Any, Callable, Optional
import time
import logging
import pandas as pd
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


class PerformanceCache:
    """
    LRU cache for indicator calculations.
    """
    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self.cache = {}
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any):
        """Set cached value."""
        if len(self.cache) >= self.maxsize:
            # Remove oldest (FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'size': len(self.cache),
            'maxsize': self.maxsize
        }


class PerformanceProfiler:
    """
    Performance profiler for tracking execution time.
    """
    def __init__(self):
        self.timings = defaultdict(list)
        self.current_timers = {}
    
    def start(self, name: str):
        """Start timing an operation."""
        self.current_timers[name] = time.perf_counter()
    
    def stop(self, name: str) -> float:
        """Stop timing and return elapsed time."""
        if name in self.current_timers:
            elapsed = time.perf_counter() - self.current_timers[name]
            self.timings[name].append(elapsed)
            del self.current_timers[name]
            return elapsed
        return 0.0
    
    def get_stats(self, name: str) -> dict:
        """Get statistics for a timed operation."""
        if name not in self.timings or len(self.timings[name]) == 0:
            return {}
        
        times = self.timings[name]
        return {
            'count': len(times),
            'total': sum(times),
            'avg': np.mean(times),
            'min': np.min(times),
            'max': np.max(times),
            'std': np.std(times)
        }
    
    def print_report(self):
        """Print performance report."""
        logger.info("="*60)
        logger.info("PERFORMANCE REPORT")
        logger.info("="*60)
        
        for name, times in self.timings.items():
            stats = self.get_stats(name)
            if stats:
                logger.info(f"{name}:")
                logger.info(f"  Count: {stats['count']}")
                logger.info(f"  Avg: {stats['avg']*1000:.2f}ms")
                logger.info(f"  Min: {stats['min']*1000:.2f}ms")
                logger.info(f"  Max: {stats['max']*1000:.2f}ms")
                logger.info(f"  Total: {stats['total']:.3f}s")


def vectorized_volume_distribution(
    lows: np.ndarray,
    highs: np.ndarray,
    volumes: np.ndarray,
    bin_edges: np.ndarray,
    bins: int
) -> np.ndarray:
    """
    Векторизованное распределение объема по бинам.
    Заменяет медленные циклы iterrows().
    
    Args:
        lows: Array of low prices
        highs: Array of high prices
        volumes: Array of volumes
        bin_edges: Price bin edges
        bins: Number of bins
        
    Returns:
        Array of volume by bin
    """
    volume_by_bin = np.zeros(bins)
    
    # Векторизованный поиск бинов для всех свечей
    low_bins = np.searchsorted(bin_edges, lows)
    high_bins = np.searchsorted(bin_edges, highs)
    
    # Ограничение индексов
    low_bins = np.clip(low_bins, 0, bins - 1)
    high_bins = np.clip(high_bins, 0, bins - 1)
    
    # Распределение объема
    for i in range(len(lows)):
        low_bin = low_bins[i]
        high_bin = high_bins[i]
        volume = volumes[i]
        
        if high_bin > low_bin:
            bins_covered = high_bin - low_bin
            volume_per_bin = volume / bins_covered
            volume_by_bin[low_bin:high_bin] += volume_per_bin
        else:
            volume_by_bin[low_bin] += volume
    
    return volume_by_bin


def fast_rolling_calculation(
    dataframe: pd.DataFrame,
    func: Callable,
    window: int,
    min_periods: Optional[int] = None
) -> pd.DataFrame:
    """
    Оптимизированный rolling calculation с векторизацией.
    
    Args:
        dataframe: Input dataframe
        func: Function to apply
        window: Rolling window size
        min_periods: Minimum periods
        
    Returns:
        DataFrame with results
    """
    if min_periods is None:
        min_periods = window
    
    results = []
    
    # Используем numpy для быстрой итерации
    for i in range(min_periods - 1, len(dataframe)):
        window_data = dataframe.iloc[max(0, i - window + 1):i + 1]
        result = func(window_data)
        results.append(result)
    
    # Создаем результат dataframe
    result_df = pd.DataFrame(results, index=dataframe.index[min_periods - 1:])
    
    # Forward fill для начальных значений
    for col in result_df.columns:
        dataframe[col] = np.nan
        dataframe.loc[result_df.index, col] = result_df[col]
        dataframe[col] = dataframe[col].ffill()
    
    return dataframe


def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Оптимизация использования памяти DataFrame.
    
    Args:
        df: DataFrame to optimize
        
    Returns:
        Optimized DataFrame
    """
    df = df.copy()
    
    # Оптимизация типов данных
    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')
    
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')
    
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].dtype == 'object':
            try:
                df[col] = pd.to_numeric(df[col], downcast='integer')
            except (ValueError, TypeError):
                pass
    
    return df


def batch_process(
    data: list,
    func: Callable,
    batch_size: int = 1000,
    use_multiprocessing: bool = False
) -> list:
    """
    Batch processing для больших объемов данных.
    
    Args:
        data: List of data to process
        func: Function to apply
        batch_size: Size of each batch
        use_multiprocessing: Use multiprocessing
        
    Returns:
        List of results
    """
    results = []
    
    if use_multiprocessing:
        from multiprocessing import Pool
        
        with Pool() as pool:
            results = pool.map(func, [data[i:i+batch_size] 
                                     for i in range(0, len(data), batch_size)])
        # Flatten results
        results = [item for sublist in results for item in sublist]
    else:
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            batch_results = [func(item) for item in batch]
            results.extend(batch_results)
    
    return results


# Глобальный кэш и профайлер
global_cache = PerformanceCache(maxsize=256)
global_profiler = PerformanceProfiler()


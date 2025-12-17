"""
Barrier-based labeling for ML models.

Creates labels based on whether TP (Take Profit) is hit before SL (Stop Loss)
within a specified horizon. This is more realistic than simple next-candle
return labels.

Label types:
- BUY_WIN (2): Long position would win (TP hit before SL)
- SELL_WIN (0): Short position would win (price drops to TP before hitting SL)
- NO_TRADE (1): Neither barrier hit or ambiguous (HOLD)
"""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_atr(
    df: pd.DataFrame,
    period: int = 14,
) -> pd.Series:
    """
    Calculate Average True Range (ATR).
    
    Args:
        df: DataFrame with high, low, close columns
        period: ATR period (default 14)
        
    Returns:
        ATR series
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR (SMA of True Range)
    atr = true_range.rolling(window=period, min_periods=1).mean()
    
    return atr


def create_barrier_labels(
    df: pd.DataFrame,
    tp_atr_mult: float = 2.5,
    sl_atr_mult: float = 1.5,
    horizon_bars: int = 1,
    atr_period: int = 14,
) -> np.ndarray:
    """
    Create labels based on TP/SL barrier hits within horizon.
    
    For each bar, we look ahead `horizon_bars` to see if:
    - LONG would win: price goes up to TP before going down to SL
    - SHORT would win: price goes down to TP before going up to SL
    - Neither: ambiguous or no barrier hit
    
    Args:
        df: OHLCV DataFrame with columns [open, high, low, close, volume]
        tp_atr_mult: Take Profit multiplier (TP = entry + ATR * mult for LONG)
        sl_atr_mult: Stop Loss multiplier (SL = entry - ATR * mult for LONG)
        horizon_bars: Number of bars to look ahead for barrier hits
        atr_period: ATR calculation period
        
    Returns:
        Label array: 0=SELL_WIN, 1=NO_TRADE, 2=BUY_WIN
    """
    n = len(df)
    labels = np.ones(n, dtype=np.int32)  # Default: NO_TRADE (1)
    
    # Calculate ATR
    atr = calculate_atr(df, period=atr_period)
    
    # Get OHLC values
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    
    for i in range(n - horizon_bars):
        entry = close[i]
        current_atr = atr.iloc[i]
        
        if pd.isna(current_atr) or current_atr <= 0:
            continue
        
        # Calculate barriers for LONG
        long_tp = entry + (current_atr * tp_atr_mult)
        long_sl = entry - (current_atr * sl_atr_mult)
        
        # Calculate barriers for SHORT
        short_tp = entry - (current_atr * tp_atr_mult)
        short_sl = entry + (current_atr * sl_atr_mult)
        
        # Check future bars
        long_tp_hit_bar = None
        long_sl_hit_bar = None
        short_tp_hit_bar = None
        short_sl_hit_bar = None
        
        for j in range(1, horizon_bars + 1):
            future_idx = i + j
            if future_idx >= n:
                break
            
            future_high = high[future_idx]
            future_low = low[future_idx]
            
            # Check LONG barriers
            if long_tp_hit_bar is None and future_high >= long_tp:
                long_tp_hit_bar = j
            if long_sl_hit_bar is None and future_low <= long_sl:
                long_sl_hit_bar = j
            
            # Check SHORT barriers
            if short_tp_hit_bar is None and future_low <= short_tp:
                short_tp_hit_bar = j
            if short_sl_hit_bar is None and future_high >= short_sl:
                short_sl_hit_bar = j
        
        # Determine label
        # LONG wins if TP hit before SL (or TP hit and SL not hit)
        long_win = (
            long_tp_hit_bar is not None and
            (long_sl_hit_bar is None or long_tp_hit_bar <= long_sl_hit_bar)
        )
        
        # SHORT wins if TP hit before SL (or TP hit and SL not hit)
        short_win = (
            short_tp_hit_bar is not None and
            (short_sl_hit_bar is None or short_tp_hit_bar <= short_sl_hit_bar)
        )
        
        # Assign label
        if long_win and not short_win:
            labels[i] = 2  # BUY_WIN
        elif short_win and not long_win:
            labels[i] = 0  # SELL_WIN
        # else: NO_TRADE (1) - default
    
    return labels


def create_barrier_labels_vectorized(
    df: pd.DataFrame,
    tp_atr_mult: float = 2.5,
    sl_atr_mult: float = 1.5,
    horizon_bars: int = 4,
    atr_period: int = 14,
) -> np.ndarray:
    """
    Vectorized version of barrier label creation (faster for large datasets).
    
    For 1h timeframe with horizon_bars=4, we look 4 hours ahead.
    
    Args:
        df: OHLCV DataFrame
        tp_atr_mult: TP multiplier
        sl_atr_mult: SL multiplier
        horizon_bars: Horizon in bars
        atr_period: ATR period
        
    Returns:
        Label array
    """
    n = len(df)
    labels = np.ones(n, dtype=np.int32)  # Default: NO_TRADE
    
    # Calculate ATR
    atr = calculate_atr(df, period=atr_period).values
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    
    # For each bar, calculate rolling max high and min low over horizon
    for i in range(n - horizon_bars):
        entry = close[i]
        current_atr = atr[i]
        
        if np.isnan(current_atr) or current_atr <= 0:
            continue
        
        # Future window
        future_highs = high[i+1:i+1+horizon_bars]
        future_lows = low[i+1:i+1+horizon_bars]
        
        if len(future_highs) == 0:
            continue
        
        # Barriers
        long_tp = entry + (current_atr * tp_atr_mult)
        long_sl = entry - (current_atr * sl_atr_mult)
        short_tp = entry - (current_atr * tp_atr_mult)
        short_sl = entry + (current_atr * sl_atr_mult)
        
        # Find first bar where barrier is hit
        long_tp_idx = np.where(future_highs >= long_tp)[0]
        long_sl_idx = np.where(future_lows <= long_sl)[0]
        short_tp_idx = np.where(future_lows <= short_tp)[0]
        short_sl_idx = np.where(future_highs >= short_sl)[0]
        
        long_tp_bar = long_tp_idx[0] if len(long_tp_idx) > 0 else None
        long_sl_bar = long_sl_idx[0] if len(long_sl_idx) > 0 else None
        short_tp_bar = short_tp_idx[0] if len(short_tp_idx) > 0 else None
        short_sl_bar = short_sl_idx[0] if len(short_sl_idx) > 0 else None
        
        # LONG wins
        long_win = (
            long_tp_bar is not None and
            (long_sl_bar is None or long_tp_bar <= long_sl_bar)
        )
        
        # SHORT wins
        short_win = (
            short_tp_bar is not None and
            (short_sl_bar is None or short_tp_bar <= short_sl_bar)
        )
        
        if long_win and not short_win:
            labels[i] = 2  # BUY
        elif short_win and not long_win:
            labels[i] = 0  # SELL
    
    return labels


def evaluate_barrier_outcome(
    entry_price: float,
    tp_price: float,
    sl_price: float,
    future_ohlcv: pd.DataFrame,
    is_long: bool = True,
) -> Dict:
    """
    Evaluate the outcome of a trade based on barrier hits.
    
    Used for online tracking of signal outcomes.
    
    Args:
        entry_price: Entry price
        tp_price: Take profit price
        sl_price: Stop loss price
        future_ohlcv: Future OHLCV data to check
        is_long: True for long, False for short
        
    Returns:
        Dict with outcome info
    """
    if future_ohlcv is None or len(future_ohlcv) == 0:
        return {
            "outcome": "pending",
            "hit_bar": None,
            "hit_price": None,
            "pnl_percent": 0.0,
        }
    
    for idx, row in future_ohlcv.iterrows():
        high = row['high']
        low = row['low']
        
        if is_long:
            # Check TP first (more favorable)
            if high >= tp_price:
                pnl = (tp_price - entry_price) / entry_price * 100
                return {
                    "outcome": "win",
                    "hit_bar": idx,
                    "hit_price": tp_price,
                    "pnl_percent": pnl,
                }
            # Check SL
            if low <= sl_price:
                pnl = (sl_price - entry_price) / entry_price * 100
                return {
                    "outcome": "lose",
                    "hit_bar": idx,
                    "hit_price": sl_price,
                    "pnl_percent": pnl,
                }
        else:  # Short
            # Check TP first
            if low <= tp_price:
                pnl = (entry_price - tp_price) / entry_price * 100
                return {
                    "outcome": "win",
                    "hit_bar": idx,
                    "hit_price": tp_price,
                    "pnl_percent": pnl,
                }
            # Check SL
            if high >= sl_price:
                pnl = (entry_price - sl_price) / entry_price * 100
                return {
                    "outcome": "lose",
                    "hit_bar": idx,
                    "hit_price": sl_price,
                    "pnl_percent": pnl,
                }
    
    # Neither barrier hit
    last_close = future_ohlcv['close'].iloc[-1]
    if is_long:
        pnl = (last_close - entry_price) / entry_price * 100
    else:
        pnl = (entry_price - last_close) / entry_price * 100
    
    return {
        "outcome": "no_hit",
        "hit_bar": None,
        "hit_price": None,
        "pnl_percent": pnl,
    }


def resample_to_timeframe(
    df: pd.DataFrame,
    target_timeframe: str = '1h',
) -> pd.DataFrame:
    """
    Resample OHLCV data to target timeframe.
    
    Args:
        df: OHLCV DataFrame with datetime index
        target_timeframe: Target timeframe (e.g., '1h', '4h', '1d')
        
    Returns:
        Resampled DataFrame
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        if 'timestamp' in df.columns:
            df = df.set_index('timestamp')
        else:
            raise ValueError("DataFrame must have datetime index or 'timestamp' column")
    
    resampled = df.resample(target_timeframe).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
    }).dropna()
    
    return resampled


def get_label_distribution(labels: np.ndarray) -> Dict[str, int]:
    """
    Get distribution of labels.
    
    Args:
        labels: Label array
        
    Returns:
        Dict with counts
    """
    unique, counts = np.unique(labels, return_counts=True)
    
    label_names = {0: "SELL", 1: "HOLD", 2: "BUY"}
    
    return {
        label_names.get(u, str(u)): int(c)
        for u, c in zip(unique, counts)
    }


if __name__ == "__main__":
    # Test with sample data
    print("=" * 60)
    print("BARRIER LABELING TEST")
    print("=" * 60)
    
    # Create sample data
    np.random.seed(42)
    n = 1000
    
    # Simulate price with trend and noise
    returns = np.random.normal(0.0001, 0.02, n)
    price = 100 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'open': price * (1 + np.random.uniform(-0.005, 0.005, n)),
        'high': price * (1 + np.random.uniform(0, 0.02, n)),
        'low': price * (1 - np.random.uniform(0, 0.02, n)),
        'close': price,
        'volume': np.random.uniform(1000, 10000, n),
    })
    
    print(f"\nSample data: {len(df)} bars")
    print(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    # Create labels
    labels = create_barrier_labels_vectorized(
        df,
        tp_atr_mult=2.5,
        sl_atr_mult=1.5,
        horizon_bars=4,
    )
    
    print(f"\nLabel distribution:")
    dist = get_label_distribution(labels)
    for label, count in dist.items():
        pct = count / len(labels) * 100
        print(f"  {label}: {count} ({pct:.1f}%)")
    
    print("\n" + "=" * 60)


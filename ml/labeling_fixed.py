"""
FIXED Labeling System - NO Look-Ahead Bias!

This module creates labels CORRECTLY without using future data during training.

CRITICAL DIFFERENCE from labeling.py:
- OLD (WRONG): Creates labels by looking at future bars to see if TP hit before SL
- NEW (CORRECT): Creates labels based on PAST price action and indicators ONLY

For backtesting, we can use barrier evaluation, but ONLY on out-of-sample data!

Label Strategy:
- Use technical indicators and price patterns that exist AT THE TIME
- No peeking into the future
- Realistic labels that a trader could actually identify in real-time
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


def create_realistic_labels(
    df: pd.DataFrame,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    bb_period: int = 20,
    bb_std: float = 2.0,
    volume_ma_period: int = 20,
) -> np.ndarray:
    """
    Create labels based on CURRENT technical indicators (no future data).

    This uses a rule-based approach with indicators available at the time.
    These labels represent what a REAL trader could see and act on.

    BUY signals (label=2):
    - RSI oversold (<30) + bullish divergence pattern
    - MACD crossover up + volume spike
    - Price at lower Bollinger Band + bullish candle

    SELL signals (label=0):
    - RSI overbought (>70) + bearish divergence
    - MACD crossover down + volume spike
    - Price at upper Bollinger Band + bearish candle

    HOLD (label=1):
    - Everything else

    Args:
        df: OHLCV DataFrame
        rsi_period: RSI calculation period
        macd_fast: MACD fast period
        macd_slow: MACD slow period
        macd_signal: MACD signal period
        bb_period: Bollinger Bands period
        bb_std: Bollinger Bands standard deviation
        volume_ma_period: Volume MA period

    Returns:
        Label array: 0=SELL, 1=HOLD, 2=BUY
    """
    n = len(df)
    labels = np.ones(n, dtype=np.int32)  # Default: HOLD

    # === Calculate indicators ===

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema_fast = df['close'].ewm(span=macd_fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=macd_slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal_line = macd.ewm(span=macd_signal, adjust=False).mean()
    macd_hist = macd - macd_signal_line

    # Bollinger Bands
    bb_middle = df['close'].rolling(bb_period).mean()
    bb_std_dev = df['close'].rolling(bb_period).std()
    bb_upper = bb_middle + (bb_std_dev * bb_std)
    bb_lower = bb_middle - (bb_std_dev * bb_std)
    bb_width = (bb_upper - bb_lower) / bb_middle

    # Volume
    volume_ma = df['volume'].rolling(volume_ma_period).mean()
    volume_ratio = df['volume'] / volume_ma

    # Candle patterns
    bullish_candle = (df['close'] > df['open']).astype(int)
    bearish_candle = (df['close'] < df['open']).astype(int)
    body_size = np.abs(df['close'] - df['open']) / df['close']

    # Price position in BB
    bb_position = (df['close'] - bb_lower) / (bb_upper - bb_lower + 1e-10)

    # === Generate labels ===

    for i in range(50, n):  # Start after indicators are ready
        # Skip if not enough data
        if pd.isna(rsi.iloc[i]) or pd.isna(macd.iloc[i]):
            continue

        current_rsi = rsi.iloc[i]
        current_macd = macd.iloc[i]
        current_signal = macd_signal_line.iloc[i]
        prev_macd = macd.iloc[i-1]
        prev_signal = macd_signal_line.iloc[i-1]
        current_bb_pos = bb_position.iloc[i]
        current_volume_ratio = volume_ratio.iloc[i]
        current_bullish = bullish_candle.iloc[i]
        current_bearish = bearish_candle.iloc[i]
        current_body = body_size.iloc[i]

        # BUY conditions
        buy_score = 0

        # RSI oversold
        if current_rsi < 30:
            buy_score += 3
        elif current_rsi < 40:
            buy_score += 1

        # MACD crossover up
        if current_macd > current_signal and prev_macd <= prev_signal:
            buy_score += 3
        elif current_macd > current_signal:
            buy_score += 1

        # Price near lower BB
        if current_bb_pos < 0.2:
            buy_score += 2

        # Volume spike
        if current_volume_ratio > 1.5:
            buy_score += 1

        # Bullish candle
        if current_bullish and current_body > 0.01:
            buy_score += 1

        # SELL conditions
        sell_score = 0

        # RSI overbought
        if current_rsi > 70:
            sell_score += 3
        elif current_rsi > 60:
            sell_score += 1

        # MACD crossover down
        if current_macd < current_signal and prev_macd >= prev_signal:
            sell_score += 3
        elif current_macd < current_signal:
            sell_score += 1

        # Price near upper BB
        if current_bb_pos > 0.8:
            sell_score += 2

        # Volume spike
        if current_volume_ratio > 1.5:
            sell_score += 1

        # Bearish candle
        if current_bearish and current_body > 0.01:
            sell_score += 1

        # Assign label based on scores
        if buy_score >= 5 and buy_score > sell_score:
            labels[i] = 2  # BUY
        elif sell_score >= 5 and sell_score > buy_score:
            labels[i] = 0  # SELL
        # else: HOLD (default)

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

    IMPORTANT: This function CAN look at future data, but ONLY for:
    - Backtesting evaluation (out-of-sample data)
    - Real-time tracking of actual trades

    NEVER use this for creating training labels on the same data!

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
    print("=" * 80)
    print("FIXED LABELING SYSTEM TEST - NO LOOK-AHEAD BIAS")
    print("=" * 80)

    # Create sample data
    np.random.seed(42)
    n = 1000

    # Simulate realistic price with trend and noise
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

    # Create labels using FIXED method (no look-ahead)
    labels = create_realistic_labels(df)

    print(f"\nLabel distribution (realistic, no look-ahead):")
    dist = get_label_distribution(labels)
    for label, count in dist.items():
        pct = count / len(labels) * 100
        print(f"  {label}: {count} ({pct:.1f}%)")

    print("\n✅ These labels are SAFE - no future data used!")
    print("=" * 80)

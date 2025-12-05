"""
ADX (Average Directional Index) Calculator.
Measures trend strength and direction using DI+, DI-, and ADX.
"""

import numpy as np
import pandas as pd


class ADXCalculator:
    """
    Calculates ADX (Average Directional Index) to measure trend strength.

    ADX is a trend strength indicator that ranges from 0 to 100:
    - ADX > 25: Strong trend
    - ADX 20-25: Moderate trend
    - ADX < 20: Weak trend or ranging market

    Also calculates DI+ and DI- to determine trend direction:
    - DI+ > DI-: Bullish trend
    - DI- > DI+: Bearish trend
    """

    def __init__(self, period: int = 14):
        """
        Initialize ADX calculator.

        Args:
            period: Lookback period for ADX calculation (default 14)
        """
        self.period = period

    def calculate_adx(self, dataframe: pd.DataFrame, period: int = None) -> pd.DataFrame:
        """
        Calculate ADX, DI+, and DI- for the dataframe.

        Args:
            dataframe: DataFrame with OHLC data (must have 'high', 'low', 'close')
            period: Override default period (optional)

        Returns:
            DataFrame with added columns:
            - adx: Average Directional Index (trend strength)
            - di_plus: Positive Directional Indicator
            - di_minus: Negative Directional Indicator
            - adx_trend_strength: Categorical ('strong', 'moderate', 'weak')
            - adx_trend_direction: Categorical ('bullish', 'bearish', 'neutral')
        """
        if period is None:
            period = self.period

        df = dataframe.copy()

        # Step 1: Calculate True Range (TR)
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = abs(df['high'] - df['close'].shift(1))
        df['low_close'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)

        # Step 2: Calculate Directional Movement (DM+ and DM-)
        df['high_diff'] = df['high'] - df['high'].shift(1)
        df['low_diff'] = df['low'].shift(1) - df['low']

        # DM+ = high_diff if high_diff > low_diff and high_diff > 0, else 0
        df['dm_plus'] = np.where(
            (df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0),
            df['high_diff'],
            0
        )

        # DM- = low_diff if low_diff > high_diff and low_diff > 0, else 0
        df['dm_minus'] = np.where(
            (df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0),
            df['low_diff'],
            0
        )

        # Step 3: Smooth TR, DM+, DM- using Wilder's smoothing (exponential moving average)
        # Wilder's smoothing: first value is SMA, then EMA with alpha = 1/period
        alpha = 1 / period

        # Initialize smoothed values with SMA for first period
        df['atr'] = df['tr'].ewm(alpha=alpha, adjust=False).mean()
        df['smoothed_dm_plus'] = df['dm_plus'].ewm(alpha=alpha, adjust=False).mean()
        df['smoothed_dm_minus'] = df['dm_minus'].ewm(alpha=alpha, adjust=False).mean()

        # Step 4: Calculate Directional Indicators (DI+ and DI-)
        df['di_plus'] = 100 * (df['smoothed_dm_plus'] / df['atr'].replace(0, np.nan))
        df['di_minus'] = 100 * (df['smoothed_dm_minus'] / df['atr'].replace(0, np.nan))

        # Step 5: Calculate Directional Index (DX)
        df['di_diff'] = abs(df['di_plus'] - df['di_minus'])
        df['di_sum'] = df['di_plus'] + df['di_minus']
        df['dx'] = 100 * (df['di_diff'] / df['di_sum'].replace(0, np.nan))

        # Step 6: Calculate ADX (smoothed DX)
        df['adx'] = df['dx'].ewm(alpha=alpha, adjust=False).mean()

        # Step 7: Determine trend strength
        df['adx_trend_strength'] = np.where(
            df['adx'] > 25,
            'strong',
            np.where(df['adx'] > 20, 'moderate', 'weak')
        )

        # Step 8: Determine trend direction
        df['adx_trend_direction'] = np.where(
            df['di_plus'] > df['di_minus'] * 1.1,  # 10% threshold to avoid noise
            'bullish',
            np.where(df['di_minus'] > df['di_plus'] * 1.1, 'bearish', 'neutral')
        )

        # Clean up intermediate columns
        df.drop(columns=[
            'high_low', 'high_close', 'low_close', 'tr',
            'high_diff', 'low_diff', 'dm_plus', 'dm_minus',
            'atr', 'smoothed_dm_plus', 'smoothed_dm_minus',
            'di_diff', 'di_sum', 'dx'
        ], inplace=True, errors='ignore')

        return df

    def detect_trend_change(self, dataframe: pd.DataFrame, lookback: int = 3) -> pd.Series:
        """
        Detect trend direction changes based on DI crossovers.

        Args:
            dataframe: DataFrame with ADX data (must have 'di_plus' and 'di_minus')
            lookback: Lookback period to confirm trend change

        Returns:
            Series with trend change signals ('bullish_crossover', 'bearish_crossover', None)
        """
        trend_change = pd.Series(None, index=dataframe.index, dtype=object)

        for i in range(lookback, len(dataframe)):
            # Check for bullish crossover (DI+ crosses above DI-)
            current_bullish = dataframe.iloc[i]['di_plus'] > dataframe.iloc[i]['di_minus']
            previous_bearish = dataframe.iloc[i - lookback]['di_plus'] < dataframe.iloc[i - lookback]['di_minus']

            if current_bullish and previous_bearish:
                # Confirm DI+ stayed above DI- for recent candles
                recent_bullish = all(
                    dataframe.iloc[i - j]['di_plus'] >= dataframe.iloc[i - j]['di_minus']
                    for j in range(min(lookback, 2))
                )
                if recent_bullish:
                    trend_change.iloc[i] = 'bullish_crossover'

            # Check for bearish crossover (DI- crosses above DI+)
            current_bearish = dataframe.iloc[i]['di_minus'] > dataframe.iloc[i]['di_plus']
            previous_bullish = dataframe.iloc[i - lookback]['di_minus'] < dataframe.iloc[i - lookback]['di_plus']

            if current_bearish and previous_bullish:
                # Confirm DI- stayed above DI+ for recent candles
                recent_bearish = all(
                    dataframe.iloc[i - j]['di_minus'] >= dataframe.iloc[i - j]['di_plus']
                    for j in range(min(lookback, 2))
                )
                if recent_bearish:
                    trend_change.iloc[i] = 'bearish_crossover'

        return trend_change

    def get_adx_summary(self, dataframe: pd.DataFrame, lookback: int = 20) -> dict:
        """
        Get ADX summary for recent period.

        Args:
            dataframe: DataFrame with ADX data
            lookback: Lookback period

        Returns:
            Dictionary with ADX summary
        """
        recent_data = dataframe.tail(lookback)

        if len(recent_data) == 0:
            return {
                'avg_adx': 0.0,
                'current_adx': 0.0,
                'trend_strength': 'unknown',
                'trend_direction': 'unknown',
                'adx_rising': False,
            }

        current_adx = recent_data['adx'].iloc[-1]
        avg_adx = recent_data['adx'].mean()

        # Check if ADX is rising (comparing recent vs earlier values)
        mid_point = lookback // 2
        recent_avg = recent_data['adx'].iloc[mid_point:].mean()
        earlier_avg = recent_data['adx'].iloc[:mid_point].mean()
        adx_rising = recent_avg > earlier_avg

        return {
            'avg_adx': avg_adx,
            'current_adx': current_adx,
            'trend_strength': recent_data['adx_trend_strength'].iloc[-1],
            'trend_direction': recent_data['adx_trend_direction'].iloc[-1],
            'adx_rising': adx_rising,
            'di_plus': recent_data['di_plus'].iloc[-1],
            'di_minus': recent_data['di_minus'].iloc[-1],
        }

    def is_trending_market(self, dataframe: pd.DataFrame, threshold: float = 25.0) -> bool:
        """
        Check if current market is trending based on ADX.

        Args:
            dataframe: DataFrame with ADX data
            threshold: ADX threshold for trending market (default 25)

        Returns:
            True if market is trending, False otherwise
        """
        if len(dataframe) == 0 or 'adx' not in dataframe.columns:
            return False

        current_adx = dataframe['adx'].iloc[-1]
        return current_adx >= threshold

    def get_trend_direction(self, dataframe: pd.DataFrame) -> str:
        """
        Get current trend direction based on DI+ and DI-.

        Args:
            dataframe: DataFrame with ADX data

        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        if len(dataframe) == 0 or 'di_plus' not in dataframe.columns:
            return 'neutral'

        return dataframe['adx_trend_direction'].iloc[-1]

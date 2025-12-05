"""
Donchian Channel Calculator.
Creates dynamic support/resistance channels based on highest high and lowest low.
"""

import numpy as np
import pandas as pd


class DonchianChannelCalculator:
    """
    Calculates Donchian Channels for breakout detection and dynamic S/R levels.

    Donchian Channels are formed by:
    - Upper Band: Highest high over N periods
    - Lower Band: Lowest low over N periods
    - Middle Band: Average of upper and lower bands

    Usage:
    - Upper breakout: Potential LONG signal
    - Lower breakout: Potential SHORT signal
    - Channel width: Volatility indicator
    """

    def __init__(self, period: int = 20):
        """
        Initialize Donchian Channel calculator.

        Args:
            period: Lookback period for channel calculation (default 20)
        """
        self.period = period

    def calculate_donchian(self, dataframe: pd.DataFrame, period: int = None) -> pd.DataFrame:
        """
        Calculate Donchian Channels for the dataframe.

        Args:
            dataframe: DataFrame with OHLC data (must have 'high' and 'low')
            period: Override default period (optional)

        Returns:
            DataFrame with added columns:
            - dc_upper: Upper channel (highest high)
            - dc_lower: Lower channel (lowest low)
            - dc_middle: Middle channel (average)
            - dc_position: Price position in channel (0-1)
            - dc_width: Channel width as percentage
            - dc_breakout: Breakout signal ('upper', 'lower', None)
        """
        if period is None:
            period = self.period

        df = dataframe.copy()

        # Calculate upper and lower bands
        df['dc_upper'] = df['high'].rolling(window=period).max()
        df['dc_lower'] = df['low'].rolling(window=period).min()

        # Calculate middle band
        df['dc_middle'] = (df['dc_upper'] + df['dc_lower']) / 2

        # Calculate price position within channel (0 = at lower, 1 = at upper)
        channel_range = df['dc_upper'] - df['dc_lower']
        df['dc_position'] = (df['close'] - df['dc_lower']) / channel_range.replace(0, np.nan)

        # Calculate channel width as percentage
        df['dc_width'] = (channel_range / df['dc_middle'].replace(0, np.nan)) * 100

        # Detect breakouts
        df['dc_breakout'] = self._detect_breakout(df)

        # Additional features
        df['dc_squeeze'] = self._detect_squeeze(df)
        df['dc_trend'] = self._determine_trend(df)

        return df

    def _detect_breakout(self, dataframe: pd.DataFrame) -> pd.Series:
        """
        Detect breakouts from Donchian Channel.

        Args:
            dataframe: DataFrame with Donchian data

        Returns:
            Series with breakout signals ('upper', 'lower', None)
        """
        breakout = pd.Series(None, index=dataframe.index, dtype=object)

        for i in range(1, len(dataframe)):
            current = dataframe.iloc[i]
            previous = dataframe.iloc[i - 1]

            # Upper breakout: close breaks above upper band
            if current['close'] > current['dc_upper'] and previous['close'] <= previous['dc_upper']:
                breakout.iloc[i] = 'upper'

            # Lower breakout: close breaks below lower band
            elif current['close'] < current['dc_lower'] and previous['close'] >= previous['dc_lower']:
                breakout.iloc[i] = 'lower'

        return breakout

    def _detect_squeeze(self, dataframe: pd.DataFrame, threshold_percentile: float = 20) -> pd.Series:
        """
        Detect channel squeeze (low volatility periods).

        A squeeze occurs when channel width is in the lowest percentile,
        often preceding strong breakouts.

        Args:
            dataframe: DataFrame with Donchian data
            threshold_percentile: Percentile threshold for squeeze detection

        Returns:
            Series indicating squeeze (True/False)
        """
        if 'dc_width' not in dataframe.columns:
            return pd.Series(False, index=dataframe.index)

        # Calculate threshold (e.g., 20th percentile of channel width)
        threshold = dataframe['dc_width'].quantile(threshold_percentile / 100)

        # Squeeze when width is below threshold
        return dataframe['dc_width'] < threshold

    def _determine_trend(self, dataframe: pd.DataFrame) -> pd.Series:
        """
        Determine trend based on price position in channel.

        Args:
            dataframe: DataFrame with Donchian data

        Returns:
            Series with trend direction ('uptrend', 'downtrend', 'ranging')
        """
        trend = pd.Series('ranging', index=dataframe.index, dtype=object)

        # Uptrend: price in upper 30% of channel
        trend[dataframe['dc_position'] > 0.7] = 'uptrend'

        # Downtrend: price in lower 30% of channel
        trend[dataframe['dc_position'] < 0.3] = 'downtrend'

        return trend

    def calculate_multiple_channels(
        self,
        dataframe: pd.DataFrame,
        periods: list = [10, 20, 50]
    ) -> pd.DataFrame:
        """
        Calculate multiple Donchian Channels with different periods.

        Args:
            dataframe: DataFrame with OHLC data
            periods: List of periods for channels

        Returns:
            DataFrame with multiple channel columns
        """
        df = dataframe.copy()

        for period in periods:
            df[f'dc_upper_{period}'] = df['high'].rolling(window=period).max()
            df[f'dc_lower_{period}'] = df['low'].rolling(window=period).min()
            df[f'dc_middle_{period}'] = (df[f'dc_upper_{period}'] + df[f'dc_lower_{period}']) / 2

        return df

    def detect_false_breakout(
        self,
        dataframe: pd.DataFrame,
        lookback: int = 3,
        retracement_threshold: float = 0.5
    ) -> pd.Series:
        """
        Detect false breakouts (price breaks channel but quickly reverses).

        Args:
            dataframe: DataFrame with Donchian data
            lookback: Candles to look back for breakout validation
            retracement_threshold: Percentage of channel retracement to confirm false breakout

        Returns:
            Series with false breakout signals ('false_upper', 'false_lower', None)
        """
        false_breakout = pd.Series(None, index=dataframe.index, dtype=object)

        for i in range(lookback, len(dataframe)):
            current = dataframe.iloc[i]

            # Check recent candles for breakout
            for j in range(1, lookback + 1):
                past = dataframe.iloc[i - j]

                # False upper breakout: broke above, now back inside channel
                if (past['close'] > past['dc_upper'] and
                    current['close'] < current['dc_upper'] and
                    current['dc_position'] < 1 - retracement_threshold):
                    false_breakout.iloc[i] = 'false_upper'
                    break

                # False lower breakout: broke below, now back inside channel
                elif (past['close'] < past['dc_lower'] and
                      current['close'] > current['dc_lower'] and
                      current['dc_position'] > retracement_threshold):
                    false_breakout.iloc[i] = 'false_lower'
                    break

        return false_breakout

    def get_channel_summary(self, dataframe: pd.DataFrame, lookback: int = 20) -> dict:
        """
        Get Donchian Channel summary for recent period.

        Args:
            dataframe: DataFrame with Donchian data
            lookback: Lookback period

        Returns:
            Dictionary with channel summary
        """
        recent_data = dataframe.tail(lookback)

        if len(recent_data) == 0 or 'dc_upper' not in dataframe.columns:
            return {
                'dc_upper': 0.0,
                'dc_middle': 0.0,
                'dc_lower': 0.0,
                'dc_position': 0.5,
                'dc_width': 0.0,
                'dc_trend': 'unknown',
                'breakout_detected': False,
                'squeeze_detected': False,
            }

        current = recent_data.iloc[-1]

        return {
            'dc_upper': current['dc_upper'],
            'dc_middle': current['dc_middle'],
            'dc_lower': current['dc_lower'],
            'dc_position': current['dc_position'],
            'dc_width': current['dc_width'],
            'dc_trend': current['dc_trend'] if 'dc_trend' in current else 'unknown',
            'breakout_detected': recent_data['dc_breakout'].notna().any() if 'dc_breakout' in recent_data.columns else False,
            'last_breakout': recent_data['dc_breakout'].iloc[-1] if 'dc_breakout' in recent_data.columns and pd.notna(recent_data['dc_breakout'].iloc[-1]) else None,
            'squeeze_detected': recent_data['dc_squeeze'].iloc[-1] if 'dc_squeeze' in recent_data.columns else False,
            'avg_width': recent_data['dc_width'].mean(),
        }

    def calculate_channel_efficiency(self, dataframe: pd.DataFrame, lookback: int = 50) -> float:
        """
        Calculate channel efficiency (how well price stays within channel).

        Args:
            dataframe: DataFrame with Donchian data
            lookback: Lookback period

        Returns:
            Efficiency ratio (0-1, higher = more efficient)
        """
        if len(dataframe) < lookback or 'dc_position' not in dataframe.columns:
            return 0.0

        recent_data = dataframe.tail(lookback)

        # Count candles within channel (0 < position < 1)
        within_channel = ((recent_data['dc_position'] >= 0) &
                         (recent_data['dc_position'] <= 1)).sum()

        return within_channel / len(recent_data)

    def identify_support_resistance(
        self,
        dataframe: pd.DataFrame,
        lookback: int = 50,
        touch_tolerance: float = 0.02
    ) -> dict:
        """
        Identify support/resistance levels from channel bands.

        Args:
            dataframe: DataFrame with Donchian data
            lookback: Lookback period
            touch_tolerance: Distance tolerance for "touch" (2% default)

        Returns:
            Dictionary with support/resistance levels and touch counts
        """
        if len(dataframe) < lookback or 'dc_upper' not in dataframe.columns:
            return {'upper_touches': 0, 'lower_touches': 0, 'middle_touches': 0}

        recent_data = dataframe.tail(lookback)

        upper_touches = 0
        lower_touches = 0
        middle_touches = 0

        for i in range(len(recent_data)):
            row = recent_data.iloc[i]

            # Check upper band touch
            upper_distance = abs(row['high'] - row['dc_upper']) / row['dc_upper']
            if upper_distance <= touch_tolerance:
                upper_touches += 1

            # Check lower band touch
            lower_distance = abs(row['low'] - row['dc_lower']) / row['dc_lower']
            if lower_distance <= touch_tolerance:
                lower_touches += 1

            # Check middle band touch
            middle_distance = abs(row['close'] - row['dc_middle']) / row['dc_middle']
            if middle_distance <= touch_tolerance:
                middle_touches += 1

        return {
            'upper_touches': upper_touches,
            'lower_touches': lower_touches,
            'middle_touches': middle_touches,
            'upper_level': recent_data['dc_upper'].iloc[-1],
            'middle_level': recent_data['dc_middle'].iloc[-1],
            'lower_level': recent_data['dc_lower'].iloc[-1],
            'upper_strength': 'strong' if upper_touches >= 3 else ('moderate' if upper_touches >= 2 else 'weak'),
            'lower_strength': 'strong' if lower_touches >= 3 else ('moderate' if lower_touches >= 2 else 'weak'),
        }

    def is_expanding_channel(self, dataframe: pd.DataFrame, lookback: int = 10) -> bool:
        """
        Check if channel is expanding (increasing volatility).

        Args:
            dataframe: DataFrame with Donchian data
            lookback: Lookback period

        Returns:
            True if channel is expanding, False otherwise
        """
        if len(dataframe) < lookback or 'dc_width' not in dataframe.columns:
            return False

        recent_data = dataframe.tail(lookback)

        # Compare recent width to earlier width
        recent_avg = recent_data['dc_width'].tail(lookback // 2).mean()
        earlier_avg = recent_data['dc_width'].head(lookback // 2).mean()

        return recent_avg > earlier_avg * 1.1  # 10% increase

    def is_contracting_channel(self, dataframe: pd.DataFrame, lookback: int = 10) -> bool:
        """
        Check if channel is contracting (decreasing volatility).

        Args:
            dataframe: DataFrame with Donchian data
            lookback: Lookback period

        Returns:
            True if channel is contracting, False otherwise
        """
        if len(dataframe) < lookback or 'dc_width' not in dataframe.columns:
            return False

        recent_data = dataframe.tail(lookback)

        # Compare recent width to earlier width
        recent_avg = recent_data['dc_width'].tail(lookback // 2).mean()
        earlier_avg = recent_data['dc_width'].head(lookback // 2).mean()

        return recent_avg < earlier_avg * 0.9  # 10% decrease

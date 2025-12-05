"""
VWAP (Volume Weighted Average Price) Calculator.
Calculates the average price weighted by volume - institutional price benchmark.
"""

import numpy as np
import pandas as pd
from datetime import datetime, time


class VWAPCalculator:
    """
    Calculates VWAP (Volume Weighted Average Price).

    VWAP is the average price weighted by volume:
    - Price > VWAP: Bullish sentiment (institutional buying)
    - Price < VWAP: Bearish sentiment (institutional selling)
    - VWAP acts as dynamic support/resistance

    VWAP is typically reset daily for intraday trading.
    """

    def __init__(self, reset_daily: bool = True, std_dev_multiplier: float = 2.0):
        """
        Initialize VWAP calculator.

        Args:
            reset_daily: Reset VWAP at start of each day (default True)
            std_dev_multiplier: Multiplier for standard deviation bands (default 2.0)
        """
        self.reset_daily = reset_daily
        self.std_dev_multiplier = std_dev_multiplier

    def calculate_vwap(
        self,
        dataframe: pd.DataFrame,
        reset_daily: bool = None,
        anchored: bool = False,
        anchor_index: int = 0
    ) -> pd.DataFrame:
        """
        Calculate VWAP for the dataframe.

        Args:
            dataframe: DataFrame with OHLCV data
            reset_daily: Override default daily reset behavior
            anchored: Use anchored VWAP (starts from anchor_index)
            anchor_index: Starting index for anchored VWAP

        Returns:
            DataFrame with added columns:
            - vwap: Volume Weighted Average Price
            - vwap_upper: Upper standard deviation band
            - vwap_lower: Lower standard deviation band
            - vwap_position: Price position relative to VWAP ('above', 'below', 'at')
            - vwap_distance_pct: Distance from VWAP as percentage
        """
        if reset_daily is None:
            reset_daily = self.reset_daily

        df = dataframe.copy()

        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)

        # Calculate typical price
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3

        # Calculate price * volume
        df['pv'] = df['typical_price'] * df['volume']

        if anchored:
            # Anchored VWAP (starts from specific point)
            df['cumulative_pv'] = df['pv'].iloc[anchor_index:].cumsum()
            df['cumulative_volume'] = df['volume'].iloc[anchor_index:].cumsum()
            df.loc[:anchor_index, 'cumulative_pv'] = 0
            df.loc[:anchor_index, 'cumulative_volume'] = 0

        elif reset_daily and isinstance(df.index, pd.DatetimeIndex):
            # Daily reset VWAP
            df['date'] = df.index.date
            df['cumulative_pv'] = df.groupby('date')['pv'].cumsum()
            df['cumulative_volume'] = df.groupby('date')['volume'].cumsum()
            df.drop(columns=['date'], inplace=True)

        else:
            # Cumulative VWAP (no reset)
            df['cumulative_pv'] = df['pv'].cumsum()
            df['cumulative_volume'] = df['volume'].cumsum()

        # Calculate VWAP
        df['vwap'] = df['cumulative_pv'] / df['cumulative_volume'].replace(0, np.nan)

        # Calculate standard deviation for bands
        df['price_deviation'] = (df['typical_price'] - df['vwap']) ** 2
        df['weighted_deviation'] = df['price_deviation'] * df['volume']

        if reset_daily and isinstance(df.index, pd.DatetimeIndex):
            df['date'] = df.index.date
            df['cumulative_weighted_deviation'] = df.groupby('date')['weighted_deviation'].cumsum()
            df.drop(columns=['date'], inplace=True)
        else:
            df['cumulative_weighted_deviation'] = df['weighted_deviation'].cumsum()

        df['vwap_variance'] = df['cumulative_weighted_deviation'] / df['cumulative_volume'].replace(0, np.nan)
        df['vwap_std'] = np.sqrt(df['vwap_variance'])

        # Calculate bands
        df['vwap_upper'] = df['vwap'] + (df['vwap_std'] * self.std_dev_multiplier)
        df['vwap_lower'] = df['vwap'] - (df['vwap_std'] * self.std_dev_multiplier)

        # Additional bands (1 std dev)
        df['vwap_upper_1std'] = df['vwap'] + df['vwap_std']
        df['vwap_lower_1std'] = df['vwap'] - df['vwap_std']

        # Determine position relative to VWAP
        tolerance = 0.001  # 0.1% tolerance
        df['vwap_position'] = np.where(
            df['close'] > df['vwap'] * (1 + tolerance),
            'above',
            np.where(df['close'] < df['vwap'] * (1 - tolerance), 'below', 'at')
        )

        # Calculate distance from VWAP as percentage
        df['vwap_distance_pct'] = ((df['close'] - df['vwap']) / df['vwap'].replace(0, np.nan)) * 100

        # Clean up intermediate columns
        df.drop(columns=[
            'typical_price', 'pv', 'cumulative_pv', 'cumulative_volume',
            'price_deviation', 'weighted_deviation', 'cumulative_weighted_deviation',
            'vwap_variance', 'vwap_std'
        ], inplace=True, errors='ignore')

        return df

    def calculate_vwap_cross(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Detect VWAP crosses.

        Args:
            dataframe: DataFrame with VWAP data

        Returns:
            DataFrame with vwap_cross column ('bullish', 'bearish', None)
        """
        df = dataframe.copy()

        if 'vwap' not in df.columns:
            df = self.calculate_vwap(df)

        # Detect crosses
        df['price_above_vwap'] = df['close'] > df['vwap']
        df['price_above_vwap_prev'] = df['price_above_vwap'].shift(1)

        df['vwap_cross'] = None
        df.loc[(df['price_above_vwap'] == True) & (df['price_above_vwap_prev'] == False), 'vwap_cross'] = 'bullish'
        df.loc[(df['price_above_vwap'] == False) & (df['price_above_vwap_prev'] == True), 'vwap_cross'] = 'bearish'

        # Clean up
        df.drop(columns=['price_above_vwap', 'price_above_vwap_prev'], inplace=True, errors='ignore')

        return df

    def detect_vwap_bounce(self, dataframe: pd.DataFrame, tolerance: float = 0.002) -> pd.Series:
        """
        Detect bounces from VWAP (price touches VWAP and reverses).

        Args:
            dataframe: DataFrame with VWAP data
            tolerance: Distance tolerance for "touch" (default 0.2%)

        Returns:
            Series with bounce signals ('bullish_bounce', 'bearish_bounce', None)
        """
        df = dataframe.copy()
        bounce = pd.Series(None, index=df.index, dtype=object)

        for i in range(2, len(df)):
            # Check if price touched VWAP
            distance_pct = abs(df.iloc[i - 1]['vwap_distance_pct']) if 'vwap_distance_pct' in df.columns else 999

            if distance_pct <= tolerance * 100:  # Within tolerance
                # Check for bullish bounce (price was below, touched, now above)
                if (df.iloc[i - 2]['close'] < df.iloc[i - 2]['vwap'] and
                    df.iloc[i]['close'] > df.iloc[i]['vwap']):
                    bounce.iloc[i] = 'bullish_bounce'

                # Check for bearish bounce (price was above, touched, now below)
                elif (df.iloc[i - 2]['close'] > df.iloc[i - 2]['vwap'] and
                      df.iloc[i]['close'] < df.iloc[i]['vwap']):
                    bounce.iloc[i] = 'bearish_bounce'

        return bounce

    def get_vwap_summary(self, dataframe: pd.DataFrame, lookback: int = 20) -> dict:
        """
        Get VWAP summary for recent period.

        Args:
            dataframe: DataFrame with VWAP data
            lookback: Lookback period

        Returns:
            Dictionary with VWAP summary
        """
        recent_data = dataframe.tail(lookback)

        if len(recent_data) == 0 or 'vwap' not in dataframe.columns:
            return {
                'current_vwap': 0.0,
                'vwap_position': 'unknown',
                'vwap_distance_pct': 0.0,
                'above_vwap_ratio': 0.0,
            }

        current_vwap = recent_data['vwap'].iloc[-1]
        current_price = recent_data['close'].iloc[-1]
        vwap_distance_pct = recent_data['vwap_distance_pct'].iloc[-1]

        # Calculate ratio of candles above VWAP
        above_vwap_count = (recent_data['close'] > recent_data['vwap']).sum()
        above_vwap_ratio = above_vwap_count / len(recent_data)

        return {
            'current_vwap': current_vwap,
            'current_price': current_price,
            'vwap_position': recent_data['vwap_position'].iloc[-1] if 'vwap_position' in recent_data.columns else 'unknown',
            'vwap_distance_pct': vwap_distance_pct,
            'vwap_upper': recent_data['vwap_upper'].iloc[-1] if 'vwap_upper' in recent_data.columns else current_vwap,
            'vwap_lower': recent_data['vwap_lower'].iloc[-1] if 'vwap_lower' in recent_data.columns else current_vwap,
            'above_vwap_ratio': above_vwap_ratio,
            'sentiment': 'bullish' if above_vwap_ratio > 0.6 else ('bearish' if above_vwap_ratio < 0.4 else 'neutral'),
        }

    def calculate_multiple_vwaps(
        self,
        dataframe: pd.DataFrame,
        periods: list = [20, 50, 100]
    ) -> pd.DataFrame:
        """
        Calculate rolling VWAP for multiple periods.

        Args:
            dataframe: DataFrame with OHLCV data
            periods: List of periods for rolling VWAP

        Returns:
            DataFrame with multiple VWAP columns
        """
        df = dataframe.copy()

        # Calculate typical price
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3

        for period in periods:
            # Rolling VWAP
            df[f'pv_{period}'] = df['typical_price'] * df['volume']
            df[f'vwap_{period}'] = (
                df[f'pv_{period}'].rolling(window=period).sum() /
                df['volume'].rolling(window=period).sum()
            )

            # Clean up
            df.drop(columns=[f'pv_{period}'], inplace=True, errors='ignore')

        df.drop(columns=['typical_price'], inplace=True, errors='ignore')

        return df

    def is_institutional_support(self, dataframe: pd.DataFrame, lookback: int = 10) -> bool:
        """
        Check if VWAP is acting as support (price bouncing from VWAP).

        Args:
            dataframe: DataFrame with VWAP data
            lookback: Lookback period

        Returns:
            True if VWAP is support, False otherwise
        """
        if len(dataframe) < lookback or 'vwap' not in dataframe.columns:
            return False

        recent_data = dataframe.tail(lookback)

        # Count touches and bounces
        touches = 0
        bounces = 0

        for i in range(1, len(recent_data)):
            # Check if price touched VWAP (within 0.5%)
            distance = abs((recent_data.iloc[i]['low'] - recent_data.iloc[i]['vwap']) / recent_data.iloc[i]['vwap'])

            if distance <= 0.005:  # Within 0.5%
                touches += 1

                # Check if bounced up
                if recent_data.iloc[i]['close'] > recent_data.iloc[i - 1]['close']:
                    bounces += 1

        # VWAP is support if >60% of touches resulted in bounces
        return touches > 0 and (bounces / touches) >= 0.6

    def is_institutional_resistance(self, dataframe: pd.DataFrame, lookback: int = 10) -> bool:
        """
        Check if VWAP is acting as resistance (price rejecting from VWAP).

        Args:
            dataframe: DataFrame with VWAP data
            lookback: Lookback period

        Returns:
            True if VWAP is resistance, False otherwise
        """
        if len(dataframe) < lookback or 'vwap' not in dataframe.columns:
            return False

        recent_data = dataframe.tail(lookback)

        # Count touches and rejections
        touches = 0
        rejections = 0

        for i in range(1, len(recent_data)):
            # Check if price touched VWAP from below (within 0.5%)
            distance = abs((recent_data.iloc[i]['high'] - recent_data.iloc[i]['vwap']) / recent_data.iloc[i]['vwap'])

            if distance <= 0.005:  # Within 0.5%
                touches += 1

                # Check if rejected down
                if recent_data.iloc[i]['close'] < recent_data.iloc[i - 1]['close']:
                    rejections += 1

        # VWAP is resistance if >60% of touches resulted in rejections
        return touches > 0 and (rejections / touches) >= 0.6

"""
OBV (On-Balance Volume) Calculator.
Measures accumulation/distribution by tracking cumulative volume flow.
"""

import numpy as np
import pandas as pd


class OBVCalculator:
    """
    Calculates OBV (On-Balance Volume) to identify buying/selling pressure.

    OBV is a cumulative volume indicator:
    - Rising OBV: Buying pressure (accumulation)
    - Falling OBV: Selling pressure (distribution)
    - OBV divergence vs price: Potential trend reversal signal
    """

    def __init__(self, ma_period: int = 20):
        """
        Initialize OBV calculator.

        Args:
            ma_period: Period for OBV moving average (default 20)
        """
        self.ma_period = ma_period

    def calculate_obv(self, dataframe: pd.DataFrame, ma_period: int = None) -> pd.DataFrame:
        """
        Calculate OBV for the dataframe.

        Args:
            dataframe: DataFrame with OHLCV data (must have 'close' and 'volume')
            ma_period: Override default MA period (optional)

        Returns:
            DataFrame with added columns:
            - obv: On-Balance Volume
            - obv_ma: Moving average of OBV
            - obv_signal: Signal based on OBV vs OBV MA ('bullish', 'bearish', 'neutral')
            - obv_trend: OBV trend ('rising', 'falling', 'flat')
            - obv_divergence: Price/OBV divergence ('bullish', 'bearish', None)
        """
        if ma_period is None:
            ma_period = self.ma_period

        df = dataframe.copy()

        # Calculate price changes
        df['price_change'] = df['close'].diff()

        # Initialize OBV
        obv = [0]

        # Calculate cumulative OBV
        for i in range(1, len(df)):
            if df.iloc[i]['price_change'] > 0:
                # Price up: add volume
                obv.append(obv[-1] + df.iloc[i]['volume'])
            elif df.iloc[i]['price_change'] < 0:
                # Price down: subtract volume
                obv.append(obv[-1] - df.iloc[i]['volume'])
            else:
                # Price unchanged: OBV unchanged
                obv.append(obv[-1])

        df['obv'] = obv

        # Calculate OBV moving average
        df['obv_ma'] = df['obv'].rolling(window=ma_period).mean()

        # Generate signal based on OBV vs OBV MA
        df['obv_signal'] = np.where(
            df['obv'] > df['obv_ma'] * 1.02,  # 2% threshold
            'bullish',
            np.where(df['obv'] < df['obv_ma'] * 0.98, 'bearish', 'neutral')
        )

        # Determine OBV trend
        df['obv_slope'] = df['obv'].diff(5)  # 5-period slope
        df['obv_trend'] = np.where(
            df['obv_slope'] > 0,
            'rising',
            np.where(df['obv_slope'] < 0, 'falling', 'flat')
        )

        # Detect divergences
        df['obv_divergence'] = self._detect_divergence(df)

        # Clean up intermediate columns
        df.drop(columns=['price_change', 'obv_slope'], inplace=True, errors='ignore')

        return df

    def _detect_divergence(self, dataframe: pd.DataFrame, lookback: int = 10) -> pd.Series:
        """
        Detect OBV/Price divergence.

        Divergence types:
        - Bullish divergence: Price makes lower low, OBV makes higher low
        - Bearish divergence: Price makes higher high, OBV makes lower high

        Args:
            dataframe: DataFrame with price and OBV data
            lookback: Lookback period for divergence detection

        Returns:
            Series with divergence signals ('bullish', 'bearish', None)
        """
        divergence = pd.Series(None, index=dataframe.index, dtype=object)

        for i in range(lookback * 2, len(dataframe)):
            # Get recent data window
            window = dataframe.iloc[i - lookback * 2:i + 1]

            # Find price peaks and troughs
            price_series = window['close']
            obv_series = window['obv']

            # Check for bullish divergence (price lower low, OBV higher low)
            price_min_idx = price_series.idxmin()
            price_min_idx_pos = window.index.get_loc(price_min_idx)

            if price_min_idx_pos > lookback:  # Ensure it's in second half
                # Find earlier low in first half
                earlier_price = price_series.iloc[:lookback].min()
                earlier_obv_idx = price_series.iloc[:lookback].idxmin()
                earlier_obv = obv_series.loc[earlier_obv_idx]

                current_price = price_series.iloc[price_min_idx_pos]
                current_obv = obv_series.iloc[price_min_idx_pos]

                # Bullish divergence: price lower low, OBV higher low
                if current_price < earlier_price and current_obv > earlier_obv:
                    divergence.iloc[i] = 'bullish'

            # Check for bearish divergence (price higher high, OBV lower high)
            price_max_idx = price_series.idxmax()
            price_max_idx_pos = window.index.get_loc(price_max_idx)

            if price_max_idx_pos > lookback:  # Ensure it's in second half
                # Find earlier high in first half
                earlier_price = price_series.iloc[:lookback].max()
                earlier_obv_idx = price_series.iloc[:lookback].idxmax()
                earlier_obv = obv_series.loc[earlier_obv_idx]

                current_price = price_series.iloc[price_max_idx_pos]
                current_obv = obv_series.iloc[price_max_idx_pos]

                # Bearish divergence: price higher high, OBV lower high
                if current_price > earlier_price and current_obv < earlier_obv:
                    divergence.iloc[i] = 'bearish'

        return divergence

    def calculate_obv_oscillator(self, dataframe: pd.DataFrame, short_period: int = 10, long_period: int = 30) -> pd.DataFrame:
        """
        Calculate OBV Oscillator (OBV - OBV MA).

        The oscillator helps identify overbought/oversold conditions.

        Args:
            dataframe: DataFrame with OBV data
            short_period: Short MA period
            long_period: Long MA period

        Returns:
            DataFrame with added columns:
            - obv_oscillator: OBV - Long MA
            - obv_oscillator_signal: Short MA of oscillator
            - obv_oscillator_histogram: Oscillator - Signal
        """
        df = dataframe.copy()

        if 'obv' not in df.columns:
            df = self.calculate_obv(df)

        # Calculate oscillator components
        df['obv_ma_long'] = df['obv'].rolling(window=long_period).mean()
        df['obv_oscillator'] = df['obv'] - df['obv_ma_long']

        # Calculate signal line
        df['obv_oscillator_signal'] = df['obv_oscillator'].rolling(window=short_period).mean()

        # Calculate histogram
        df['obv_oscillator_histogram'] = df['obv_oscillator'] - df['obv_oscillator_signal']

        # Clean up intermediate columns
        df.drop(columns=['obv_ma_long'], inplace=True, errors='ignore')

        return df

    def get_obv_summary(self, dataframe: pd.DataFrame, lookback: int = 20) -> dict:
        """
        Get OBV summary for recent period.

        Args:
            dataframe: DataFrame with OBV data
            lookback: Lookback period

        Returns:
            Dictionary with OBV summary
        """
        recent_data = dataframe.tail(lookback)

        if len(recent_data) == 0 or 'obv' not in dataframe.columns:
            return {
                'current_obv': 0.0,
                'obv_signal': 'unknown',
                'obv_trend': 'unknown',
                'divergence_detected': False,
                'obv_change_pct': 0.0,
            }

        current_obv = recent_data['obv'].iloc[-1]
        obv_ma = recent_data['obv_ma'].iloc[-1] if 'obv_ma' in recent_data.columns else current_obv

        # Calculate OBV change percentage
        if len(recent_data) >= 2:
            obv_start = recent_data['obv'].iloc[0]
            obv_change_pct = ((current_obv - obv_start) / abs(obv_start)) * 100 if obv_start != 0 else 0.0
        else:
            obv_change_pct = 0.0

        return {
            'current_obv': current_obv,
            'obv_ma': obv_ma,
            'obv_signal': recent_data['obv_signal'].iloc[-1] if 'obv_signal' in recent_data.columns else 'neutral',
            'obv_trend': recent_data['obv_trend'].iloc[-1] if 'obv_trend' in recent_data.columns else 'flat',
            'divergence_detected': recent_data['obv_divergence'].notna().any() if 'obv_divergence' in recent_data.columns else False,
            'divergence_type': recent_data['obv_divergence'].iloc[-1] if 'obv_divergence' in recent_data.columns and pd.notna(recent_data['obv_divergence'].iloc[-1]) else None,
            'obv_change_pct': obv_change_pct,
        }

    def is_accumulation_phase(self, dataframe: pd.DataFrame, lookback: int = 10) -> bool:
        """
        Check if current period shows accumulation (rising OBV with sideways/down price).

        Args:
            dataframe: DataFrame with OBV data
            lookback: Lookback period

        Returns:
            True if accumulation detected, False otherwise
        """
        if len(dataframe) < lookback or 'obv' not in dataframe.columns:
            return False

        recent_data = dataframe.tail(lookback)

        # OBV should be rising
        obv_trend = recent_data['obv'].iloc[-1] > recent_data['obv'].iloc[0]

        # Price should be sideways or slightly down
        price_start = recent_data['close'].iloc[0]
        price_end = recent_data['close'].iloc[-1]
        price_change_pct = ((price_end - price_start) / price_start) * 100

        # Accumulation: OBV rising while price flat or down
        return obv_trend and price_change_pct <= 5.0  # Max 5% price increase

    def is_distribution_phase(self, dataframe: pd.DataFrame, lookback: int = 10) -> bool:
        """
        Check if current period shows distribution (falling OBV with sideways/up price).

        Args:
            dataframe: DataFrame with OBV data
            lookback: Lookback period

        Returns:
            True if distribution detected, False otherwise
        """
        if len(dataframe) < lookback or 'obv' not in dataframe.columns:
            return False

        recent_data = dataframe.tail(lookback)

        # OBV should be falling
        obv_trend = recent_data['obv'].iloc[-1] < recent_data['obv'].iloc[0]

        # Price should be sideways or slightly up
        price_start = recent_data['close'].iloc[0]
        price_end = recent_data['close'].iloc[-1]
        price_change_pct = ((price_end - price_start) / price_start) * 100

        # Distribution: OBV falling while price flat or up
        return obv_trend and price_change_pct >= -5.0  # Max 5% price decrease

    def normalize_obv(self, dataframe: pd.DataFrame, window: int = 50) -> pd.DataFrame:
        """
        Normalize OBV to make it comparable across different assets.

        Args:
            dataframe: DataFrame with OBV data
            window: Rolling window for normalization

        Returns:
            DataFrame with normalized_obv column
        """
        df = dataframe.copy()

        if 'obv' not in df.columns:
            df = self.calculate_obv(df)

        # Normalize using rolling z-score
        obv_mean = df['obv'].rolling(window=window).mean()
        obv_std = df['obv'].rolling(window=window).std()

        df['normalized_obv'] = (df['obv'] - obv_mean) / obv_std.replace(0, 1)

        return df

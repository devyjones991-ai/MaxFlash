"""
Market Profile calculation module.
Calculates Value Area High (VAH), Value Area Low (VAL), and POC for Market Profile.
"""

import numpy as np
import pandas as pd


class MarketProfileCalculator:
    """
    Calculates Market Profile indicators: VAH, VAL, POC.
    Market Profile analyzes price and volume distribution over time.
    """

    def __init__(self, bins: int = 30, value_area_percent: float = 0.70, period: int = 24):
        """
        Initialize Market Profile calculator.

        Args:
            bins: Number of price bins (default 30)
            value_area_percent: Percentage of volume for Value Area (default 0.70)
            period: Period for Market Profile calculation (default 24 hours/candles)
        """
        self.bins = bins
        self.value_area_percent = value_area_percent
        self.period = period

    def calculate_market_profile(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Market Profile for the dataframe.

        Args:
            dataframe: DataFrame with OHLCV data

        Returns:
            DataFrame with added columns:
            - mp_poc: Point of Control (price with most time/volume)
            - mp_vah: Value Area High
            - mp_val: Value Area Low
            - mp_profile_high: Profile high (highest price in profile)
            - mp_profile_low: Profile low (lowest price in profile)
            - mp_market_state: Market state ('trending' or 'balanced')
        """
        df = dataframe.copy()

        # Initialize columns
        df["mp_poc"] = np.nan
        df["mp_vah"] = np.nan
        df["mp_val"] = np.nan
        df["mp_profile_high"] = np.nan
        df["mp_profile_low"] = np.nan
        df["mp_market_state"] = None

        # Calculate Market Profile for each period
        for i in range(self.period, len(df)):
            period_data = df.iloc[i - self.period : i + 1]
            profile = self._calculate_profile_for_period(period_data)

            df.loc[df.index[i], "mp_poc"] = profile["poc"]
            df.loc[df.index[i], "mp_vah"] = profile["vah"]
            df.loc[df.index[i], "mp_val"] = profile["val"]
            df.loc[df.index[i], "mp_profile_high"] = profile["profile_high"]
            df.loc[df.index[i], "mp_profile_low"] = profile["profile_low"]
            df.loc[df.index[i], "mp_market_state"] = profile["market_state"]

        return df

    def _calculate_profile_for_period(self, dataframe: pd.DataFrame) -> dict:
        """
        Calculate Market Profile for a specific period.

        Args:
            dataframe: DataFrame with OHLCV data for the period

        Returns:
            Dictionary with profile data
        """
        if len(dataframe) == 0:
            return {
                "poc": np.nan,
                "vah": np.nan,
                "val": np.nan,
                "profile_high": np.nan,
                "profile_low": np.nan,
                "market_state": "balanced",
            }

        # Get price range
        price_min = dataframe["low"].min()
        price_max = dataframe["high"].max()

        if price_min == price_max:
            midpoint = price_min
            return {
                "poc": midpoint,
                "vah": midpoint,
                "val": midpoint,
                "profile_high": midpoint,
                "profile_low": midpoint,
                "market_state": "balanced",
            }

        # Create price bins
        bin_edges = np.linspace(price_min, price_max, self.bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Distribute volume/time across bins (using volume as proxy for time)
        volume_by_bin = np.zeros(self.bins)

        for _idx, row in dataframe.iterrows():
            low = row["low"]
            high = row["high"]
            volume = row["volume"]

            # Find bins that this candle covers
            low_bin = np.searchsorted(bin_edges, low)
            high_bin = np.searchsorted(bin_edges, high)

            # Ensure indices are within bounds
            low_bin = max(0, min(low_bin, self.bins - 1))
            high_bin = max(0, min(high_bin, self.bins - 1))

            # Distribute volume across covered bins
            if high_bin > low_bin:
                bins_covered = high_bin - low_bin
                volume_per_bin = volume / bins_covered
                volume_by_bin[low_bin:high_bin] += volume_per_bin
            else:
                volume_by_bin[low_bin] += volume

        # Find POC (bin with maximum volume/time)
        poc_bin = np.argmax(volume_by_bin)
        poc = bin_centers[poc_bin]

        # Calculate Value Area
        total_volume = volume_by_bin.sum()
        target_volume = total_volume * self.value_area_percent

        val, vah = self._calculate_value_area(volume_by_bin, bin_centers, poc_bin, target_volume)

        # Determine market state
        current_price = dataframe["close"].iloc[-1]
        market_state = self._determine_market_state(current_price, val, vah)

        return {
            "poc": poc,
            "vah": vah,
            "val": val,
            "profile_high": price_max,
            "profile_low": price_min,
            "market_state": market_state,
        }

    def _calculate_value_area(
        self, volume_by_bin: np.ndarray, bin_centers: np.ndarray, poc_bin: int, target_volume: float
    ) -> tuple:
        """Calculate Value Area starting from POC."""
        if volume_by_bin.sum() == 0:
            return (np.nan, np.nan)

        cumulative_volume = volume_by_bin[poc_bin]
        lower_bound = poc_bin
        upper_bound = poc_bin

        while cumulative_volume < target_volume:
            can_expand_lower = lower_bound > 0
            can_expand_upper = upper_bound < len(volume_by_bin) - 1

            if not can_expand_lower and not can_expand_upper:
                break

            if can_expand_lower and can_expand_upper:
                lower_volume = volume_by_bin[lower_bound - 1]
                upper_volume = volume_by_bin[upper_bound + 1]

                if lower_volume >= upper_volume:
                    lower_bound -= 1
                    cumulative_volume += volume_by_bin[lower_bound]
                else:
                    upper_bound += 1
                    cumulative_volume += volume_by_bin[upper_bound]
            elif can_expand_lower:
                lower_bound -= 1
                cumulative_volume += volume_by_bin[lower_bound]
            else:
                upper_bound += 1
                cumulative_volume += volume_by_bin[upper_bound]

        val = bin_centers[lower_bound]
        vah = bin_centers[upper_bound]

        return (val, vah)

    def _determine_market_state(self, current_price: float, val: float, vah: float) -> str:
        """
        Determine market state: trending or balanced.

        Args:
            current_price: Current price
            val: Value Area Low
            vah: Value Area High

        Returns:
            'trending' if price outside Value Area, 'balanced' if inside
        """
        if pd.isna(val) or pd.isna(vah):
            return "balanced"

        if current_price < val or current_price > vah:
            return "trending"
        else:
            return "balanced"

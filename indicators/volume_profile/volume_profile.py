"""
Volume Profile calculation module.
Calculates POC, HVN, LVN, and Value Area.
"""

from typing import Optional

import numpy as np
import pandas as pd


class VolumeProfileCalculator:
    """
    Calculates Volume Profile indicators: POC, HVN, LVN, Value Area.
    """

    def __init__(
        self,
        bins: int = 70,
        value_area_percent: float = 0.70,
        hvn_threshold_multiplier: float = 1.5,
        lvn_threshold_multiplier: float = 0.5,
    ):
        """
        Initialize Volume Profile calculator.

        Args:
            bins: Number of price bins for volume distribution (default 70)
            value_area_percent: Percentage of volume for Value Area (default 0.70 = 70%)
            hvn_threshold_multiplier: Multiplier for average volume to identify HVN (default 1.5)
            lvn_threshold_multiplier: Multiplier for average volume to identify LVN (default 0.5)
        """
        self.bins = bins
        self.value_area_percent = value_area_percent
        self.hvn_threshold_multiplier = hvn_threshold_multiplier
        self.lvn_threshold_multiplier = lvn_threshold_multiplier

    def calculate_volume_profile(self, dataframe: pd.DataFrame, period: Optional[int] = None) -> pd.DataFrame:
        """
        Calculate Volume Profile for the dataframe.

        Args:
            dataframe: DataFrame with OHLCV data
            period: Period for rolling calculation (None = entire dataframe)

        Returns:
            DataFrame with added columns:
            - vp_poc: Point of Control (price level with max volume)
            - vp_vah: Value Area High
            - vp_val: Value Area Low
            - vp_hvn: High Volume Nodes (list)
            - vp_lvn: Low Volume Nodes (list)
            - vp_total_volume: Total volume in profile
        """
        df = dataframe.copy()

        # Initialize columns
        df["vp_poc"] = np.nan
        df["vp_vah"] = np.nan
        df["vp_val"] = np.nan
        df["vp_total_volume"] = 0.0

        if period is None:
            # Calculate for entire dataframe
            profile = self._calculate_profile_for_period(df)
            # Forward fill results
            df["vp_poc"] = profile["poc"]
            df["vp_vah"] = profile["vah"]
            df["vp_val"] = profile["val"]
            df["vp_total_volume"] = profile["total_volume"]

            # Add HVN and LVN as lists (stored in last row)
            df.loc[df.index[-1], "vp_hvn"] = str(profile["hvn"])
            df.loc[df.index[-1], "vp_lvn"] = str(profile["lvn"])
        else:
            # Rolling calculation
            for i in range(period, len(df)):
                period_data = df.iloc[i - period : i + 1]
                profile = self._calculate_profile_for_period(period_data)

                df.loc[df.index[i], "vp_poc"] = profile["poc"]
                df.loc[df.index[i], "vp_vah"] = profile["vah"]
                df.loc[df.index[i], "vp_val"] = profile["val"]
                df.loc[df.index[i], "vp_total_volume"] = profile["total_volume"]
                df.loc[df.index[i], "vp_hvn"] = str(profile["hvn"])
                df.loc[df.index[i], "vp_lvn"] = str(profile["lvn"])

        return df

    def _calculate_profile_for_period(self, dataframe: pd.DataFrame) -> dict:
        """
        Calculate Volume Profile for a specific period.

        Args:
            dataframe: DataFrame with OHLCV data for the period

        Returns:
            Dictionary with profile data:
            - poc: Point of Control
            - vah: Value Area High
            - val: Value Area Low
            - hvn: List of High Volume Nodes
            - lvn: List of Low Volume Nodes
            - total_volume: Total volume
        """
        if len(dataframe) == 0:
            return {"poc": np.nan, "vah": np.nan, "val": np.nan, "hvn": [], "lvn": [], "total_volume": 0.0}

        # Get price range
        price_min = dataframe["low"].min()
        price_max = dataframe["high"].max()

        if price_min == price_max:
            # Flat price, return midpoint
            midpoint = (price_min + price_max) / 2
            return {
                "poc": midpoint,
                "vah": midpoint,
                "val": midpoint,
                "hvn": [],
                "lvn": [],
                "total_volume": dataframe["volume"].sum(),
            }

        # Create price bins
        bin_edges = np.linspace(price_min, price_max, self.bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Distribute volume across bins
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

            # Distribute volume evenly across covered bins
            if high_bin > low_bin:
                bins_covered = high_bin - low_bin
                volume_per_bin = volume / bins_covered
                volume_by_bin[low_bin:high_bin] += volume_per_bin
            else:
                # Single bin
                volume_by_bin[low_bin] += volume

        # Find POC (bin with maximum volume)
        poc_bin = np.argmax(volume_by_bin)
        poc = bin_centers[poc_bin]

        # Calculate Value Area (70% of volume)
        total_volume = volume_by_bin.sum()
        target_volume = total_volume * self.value_area_percent

        # Start from POC and expand outward
        val, vah = self._calculate_value_area(volume_by_bin, bin_centers, poc_bin, target_volume)

        # Find HVN and LVN
        avg_volume = volume_by_bin.mean()
        hvn_threshold = avg_volume * self.hvn_threshold_multiplier
        lvn_threshold = avg_volume * self.lvn_threshold_multiplier

        hvn = [bin_centers[i] for i in range(self.bins) if volume_by_bin[i] >= hvn_threshold]
        lvn = [bin_centers[i] for i in range(self.bins) if volume_by_bin[i] <= lvn_threshold and volume_by_bin[i] > 0]

        return {"poc": poc, "vah": vah, "val": val, "hvn": hvn, "lvn": lvn, "total_volume": total_volume}

    def _calculate_value_area(
        self, volume_by_bin: np.ndarray, bin_centers: np.ndarray, poc_bin: int, target_volume: float
    ) -> tuple[float, float]:
        """
        Calculate Value Area (VAH and VAL) starting from POC.

        Args:
            volume_by_bin: Volume distribution across bins
            bin_centers: Center prices of bins
            poc_bin: Index of POC bin
            target_volume: Target volume for Value Area

        Returns:
            Tuple of (VAL, VAH)
        """
        if volume_by_bin.sum() == 0:
            return (np.nan, np.nan)

        # Start from POC and expand outward
        cumulative_volume = volume_by_bin[poc_bin]
        lower_bound = poc_bin
        upper_bound = poc_bin

        # Expand until we reach target volume
        while cumulative_volume < target_volume:
            # Check which direction to expand
            can_expand_lower = lower_bound > 0
            can_expand_upper = upper_bound < len(volume_by_bin) - 1

            if not can_expand_lower and not can_expand_upper:
                break

            # Prefer expanding in direction with more volume
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

    def get_volume_profile_summary(self, dataframe: pd.DataFrame) -> dict:
        """
        Get current Volume Profile summary.

        Args:
            dataframe: DataFrame with Volume Profile data

        Returns:
            Dictionary with Volume Profile summary
        """
        last_row = dataframe.iloc[-1]

        # Parse HVN and LVN lists if stored as strings
        hvn = last_row.get("vp_hvn", [])
        lvn = last_row.get("vp_lvn", [])

        if isinstance(hvn, str):
            try:
                hvn = eval(hvn)  # Convert string representation to list
            except:
                hvn = []

        if isinstance(lvn, str):
            try:
                lvn = eval(lvn)
            except:
                lvn = []

        return {
            "poc": last_row.get("vp_poc", None),
            "vah": last_row.get("vp_vah", None),
            "val": last_row.get("vp_val", None),
            "hvn": hvn,
            "lvn": lvn,
            "total_volume": last_row.get("vp_total_volume", 0.0),
        }

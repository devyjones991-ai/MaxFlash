"""
Multi-timeframe data fetcher utility.
Provides methods to fetch and align data from different timeframes.
"""

import pandas as pd


class DataFetcher:
    """
    Utility class for fetching and managing multi-timeframe data.
    """

    def __init__(self):
        self.data_cache: dict[str, pd.DataFrame] = {}

    def get_timeframe_data(self, dataframe: pd.DataFrame, timeframe: str, current_timeframe: str) -> pd.DataFrame:
        """
        Resample dataframe to target timeframe.

        Args:
            dataframe: Source dataframe (OHLCV)
            timeframe: Target timeframe (e.g., '1d', '4h', '1h', '15m')
            current_timeframe: Current timeframe of the dataframe

        Returns:
            Resampled dataframe
        """
        if timeframe == current_timeframe:
            return dataframe

        # Convert timeframe strings to pandas resample frequencies
        timeframe_map = {
            "1m": "1T",
            "5m": "5T",
            "15m": "15T",
            "30m": "30T",
            "1h": "1H",
            "4h": "4H",
            "1d": "1D",
            "1w": "1W",
        }

        if timeframe not in timeframe_map:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        freq = timeframe_map[timeframe]

        # Resample OHLCV data
        resampled = (
            dataframe.resample(freq)
            .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
            .dropna()
        )

        return resampled

    def align_timeframes(self, higher_tf_data: pd.DataFrame, lower_tf_data: pd.DataFrame) -> pd.DataFrame:
        """
        Align lower timeframe data with higher timeframe data.
        Forward-fills higher timeframe values to match lower timeframe index.

        Args:
            higher_tf_data: Higher timeframe dataframe
            lower_tf_data: Lower timeframe dataframe

        Returns:
            Aligned higher timeframe data
        """
        aligned = higher_tf_data.reindex(lower_tf_data.index, method="ffill")
        return aligned

    def calculate_cumulative_volume(self, dataframe: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate cumulative volume over a period.

        Args:
            dataframe: DataFrame with volume data
            period: Number of periods to sum

        Returns:
            Series with cumulative volume
        """
        return dataframe["volume"].rolling(window=period).sum()

    def normalize_timeframe_data(self, dataframe: pd.DataFrame, reference_index: pd.Index) -> pd.DataFrame:
        """
        Normalize dataframe to match reference index by forward-filling.

        Args:
            dataframe: Source dataframe
            reference_index: Target index to align with

        Returns:
            Normalized dataframe with reference index
        """
        normalized = dataframe.reindex(reference_index, method="ffill")
        return normalized

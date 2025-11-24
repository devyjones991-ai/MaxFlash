"""
Delta analysis module.
Calculates the difference between buy and sell volume (Delta).
"""

import numpy as np
import pandas as pd


class DeltaAnalyzer:
    """
    Analyzes Delta (buy volume - sell volume) to identify buying/selling pressure.
    """

    def __init__(self, delta_threshold: float = 0.1):
        """
        Initialize Delta analyzer.

        Args:
            delta_threshold: Minimum Delta percentage for significance (default 0.1 = 10%)
        """
        self.delta_threshold = delta_threshold

    def calculate_delta(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Delta for the dataframe.

        Args:
            dataframe: DataFrame with footprint data (must have fp_buy_volume and fp_sell_volume)

        Returns:
            DataFrame with added columns:
            - delta: Buy volume - Sell volume
            - delta_pct: Delta as percentage of total volume
            - delta_alignment: 'bullish', 'bearish', or 'neutral'
            - delta_divergence: Detected divergence
        """
        df = dataframe.copy()

        # Calculate Delta
        df["delta"] = df["fp_buy_volume"] - df["fp_sell_volume"]

        # Calculate Delta percentage
        df["delta_pct"] = (df["delta"] / df["fp_total_volume"].replace(0, np.nan)) * 100

        # Determine alignment
        df["delta_alignment"] = np.where(
            df["delta_pct"] > self.delta_threshold,
            "bullish",
            np.where(df["delta_pct"] < -self.delta_threshold, "bearish", "neutral"),
        )

        # Detect divergence
        df["delta_divergence"] = self._detect_divergence(df)

        return df

    def _detect_divergence(self, dataframe: pd.DataFrame, lookback: int = 5) -> pd.Series:
        """
        Detect Delta divergence.

        Divergence occurs when:
        - Price moves up but Delta is negative (bearish divergence)
        - Price moves down but Delta is positive (bullish divergence)

        Args:
            dataframe: DataFrame with price and delta data
            lookback: Lookback period for divergence detection

        Returns:
            Series with divergence signals
        """
        divergence = pd.Series(None, index=dataframe.index, dtype=object)

        for i in range(lookback, len(dataframe)):
            # Price movement
            price_change = dataframe.iloc[i]["close"] - dataframe.iloc[i - lookback]["close"]

            # Delta change
            delta_change = dataframe.iloc[i]["delta"] - dataframe.iloc[i - lookback]["delta"]

            # Check for divergence
            if price_change > 0 and delta_change < 0:
                # Price up, Delta down = bearish divergence
                divergence.iloc[i] = "bearish"
            elif price_change < 0 and delta_change > 0:
                # Price down, Delta up = bullish divergence
                divergence.iloc[i] = "bullish"

        return divergence

    def detect_absorption(self, dataframe: pd.DataFrame, price_level: float, lookback: int = 10) -> dict:
        """
        Detect absorption at a specific price level.

        Absorption occurs when one side (buyers/sellers) absorbs all the other side's orders
        without significant price movement.

        Args:
            dataframe: DataFrame with footprint and delta data
            price_level: Price level to check for absorption
            lookback: Lookback period

        Returns:
            Dictionary with absorption data
        """
        # Find candles near price level
        tolerance = price_level * 0.002  # 0.2% tolerance

        relevant_data = dataframe[
            (dataframe["low"] <= price_level + tolerance) & (dataframe["high"] >= price_level - tolerance)
        ].tail(lookback)

        if len(relevant_data) == 0:
            return {"absorption_detected": False, "type": None, "strength": 0.0}

        # Calculate average delta and price movement
        avg_delta = relevant_data["delta"].mean()
        price_volatility = relevant_data["high"].max() - relevant_data["low"].min()
        avg_range = (dataframe["high"] - dataframe["low"]).mean()

        # Absorption: high delta but low price movement
        if abs(avg_delta) > avg_range * 2 and price_volatility < avg_range * 0.5:
            absorption_type = "bullish" if avg_delta > 0 else "bearish"
            strength = abs(avg_delta) / relevant_data["fp_total_volume"].sum()

            return {"absorption_detected": True, "type": absorption_type, "strength": strength}

        return {"absorption_detected": False, "type": None, "strength": 0.0}

    def get_delta_summary(self, dataframe: pd.DataFrame, lookback: int = 20) -> dict:
        """
        Get Delta summary for recent period.

        Args:
            dataframe: DataFrame with delta data
            lookback: Lookback period

        Returns:
            Dictionary with delta summary
        """
        recent_data = dataframe.tail(lookback)

        return {
            "avg_delta": recent_data["delta"].mean(),
            "avg_delta_pct": recent_data["delta_pct"].mean(),
            "delta_alignment": recent_data["delta_alignment"].mode()[0] if len(recent_data) > 0 else "neutral",
            "divergence_detected": recent_data["delta_divergence"].notna().any(),
            "current_delta": recent_data["delta"].iloc[-1] if len(recent_data) > 0 else 0.0,
        }

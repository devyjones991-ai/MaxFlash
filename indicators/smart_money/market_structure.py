"""
Market Structure analysis module.
Identifies Break of Structure (BOS), Change of Character (ChoCH), and trend direction.
"""

import numpy as np
import pandas as pd


class MarketStructureAnalyzer:
    """
    Analyzes market structure: BOS, ChoCH, trend, and liquidity zones.
    """

    def __init__(self, swing_lookback: int = 5):
        """
        Initialize Market Structure analyzer.

        Args:
            swing_lookback: Lookback period for swing high/low detection
        """
        self.swing_lookback = swing_lookback

    def analyze_market_structure(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze market structure and add columns to dataframe.

        Args:
            dataframe: DataFrame with OHLCV data

        Returns:
            DataFrame with added columns:
            - swing_high: Swing high levels
            - swing_low: Swing low levels
            - market_structure: 'bullish', 'bearish', 'range'
            - bos_detected: Break of Structure detected
            - choch_detected: Change of Character detected
            - liquidity_zone: Liquidity zone levels
        """
        df = dataframe.copy()

        # Detect swing points
        swing_highs = self._detect_swing_highs(df)
        swing_lows = self._detect_swing_lows(df)

        df["swing_high"] = swing_highs
        df["swing_low"] = swing_lows

        # Detect Break of Structure
        bos_events = self._detect_break_of_structure(df, swing_highs, swing_lows)
        df["bos_detected"] = bos_events
        df["bos_type"] = None

        # Detect Change of Character
        choch_events = self._detect_change_of_character(df, swing_highs, swing_lows)
        df["choch_detected"] = choch_events
        df["choch_type"] = None

        # Determine trend
        trend = self._determine_trend(df, swing_highs, swing_lows)
        df["market_structure"] = trend

        # Identify liquidity zones
        liquidity_zones = self._identify_liquidity_zones(df, swing_highs, swing_lows)
        df["liquidity_zone_high"] = liquidity_zones["high"]
        df["liquidity_zone_low"] = liquidity_zones["low"]

        return df

    def _detect_swing_highs(self, dataframe: pd.DataFrame) -> pd.Series:
        """
        Detect swing highs.

        Args:
            dataframe: DataFrame with OHLCV data

        Returns:
            Series with swing high levels
        """
        highs = dataframe["high"]
        swing_highs = pd.Series(index=dataframe.index, dtype=float)

        for i in range(self.swing_lookback, len(dataframe) - self.swing_lookback):
            if highs.iloc[i] == highs.iloc[i - self.swing_lookback : i + self.swing_lookback + 1].max():
                swing_highs.iloc[i] = highs.iloc[i]

        return swing_highs

    def _detect_swing_lows(self, dataframe: pd.DataFrame) -> pd.Series:
        """
        Detect swing lows.

        Args:
            dataframe: DataFrame with OHLCV data

        Returns:
            Series with swing low levels
        """
        lows = dataframe["low"]
        swing_lows = pd.Series(index=dataframe.index, dtype=float)

        for i in range(self.swing_lookback, len(dataframe) - self.swing_lookback):
            if lows.iloc[i] == lows.iloc[i - self.swing_lookback : i + self.swing_lookback + 1].min():
                swing_lows.iloc[i] = lows.iloc[i]

        return swing_lows

    def _detect_break_of_structure(
        self, dataframe: pd.DataFrame, swing_highs: pd.Series, swing_lows: pd.Series
    ) -> pd.Series:
        """
        Detect Break of Structure (BOS).

        BOS occurs when price breaks a previous swing high (bullish BOS)
        or swing low (bearish BOS).

        Args:
            dataframe: DataFrame with OHLCV data
            swing_highs: Series with swing high levels
            swing_lows: Series with swing low levels

        Returns:
            Series with BOS events
        """
        bos = pd.Series(False, index=dataframe.index)
        bos_type = pd.Series(None, index=dataframe.index, dtype=object)

        # Track last swing high and low
        last_swing_high = None
        last_swing_low = None

        for i in range(len(dataframe)):
            # Update last swing points
            if pd.notna(swing_highs.iloc[i]):
                last_swing_high = swing_highs.iloc[i]

            if pd.notna(swing_lows.iloc[i]):
                last_swing_low = swing_lows.iloc[i]

            # Check for bullish BOS (break above swing high)
            if last_swing_high is not None and dataframe.iloc[i]["close"] > last_swing_high:
                bos.iloc[i] = True
                bos_type.iloc[i] = "bullish"
                last_swing_high = None  # Reset to avoid multiple triggers

            # Check for bearish BOS (break below swing low)
            if last_swing_low is not None and dataframe.iloc[i]["close"] < last_swing_low:
                bos.iloc[i] = True
                bos_type.iloc[i] = "bearish"
                last_swing_low = None  # Reset to avoid multiple triggers

        dataframe["bos_type"] = bos_type
        return bos

    def _detect_change_of_character(
        self, dataframe: pd.DataFrame, swing_highs: pd.Series, swing_lows: pd.Series
    ) -> pd.Series:
        """
        Detect Change of Character (ChoCH).

        ChoCH is a change in price behavior, often appearing after BOS.
        - Bullish ChoCH: Price makes a higher low after breaking structure
        - Bearish ChoCH: Price makes a lower high after breaking structure

        Args:
            dataframe: DataFrame with OHLCV data
            swing_highs: Series with swing high levels
            swing_lows: Series with swing low levels

        Returns:
            Series with ChoCH events
        """
        choch = pd.Series(False, index=dataframe.index)
        choch_type = pd.Series(None, index=dataframe.index, dtype=object)

        # Track recent swing points
        recent_swing_highs = []
        recent_swing_lows = []

        for i in range(len(dataframe)):
            # Update recent swings (keep last 3)
            if pd.notna(swing_highs.iloc[i]):
                recent_swing_highs.append(swing_highs.iloc[i])
                if len(recent_swing_highs) > 3:
                    recent_swing_highs.pop(0)

            if pd.notna(swing_lows.iloc[i]):
                recent_swing_lows.append(swing_lows.iloc[i])
                if len(recent_swing_lows) > 3:
                    recent_swing_lows.pop(0)

            # Check for bullish ChoCH (higher low)
            if len(recent_swing_lows) >= 2 and recent_swing_lows[-1] > recent_swing_lows[-2]:
                choch.iloc[i] = True
                choch_type.iloc[i] = "bullish"

            # Check for bearish ChoCH (lower high)
            if len(recent_swing_highs) >= 2 and recent_swing_highs[-1] < recent_swing_highs[-2]:
                choch.iloc[i] = True
                choch_type.iloc[i] = "bearish"

        dataframe["choch_type"] = choch_type
        return choch

    def _determine_trend(self, dataframe: pd.DataFrame, swing_highs: pd.Series, swing_lows: pd.Series) -> pd.Series:
        """
        Determine market trend: bullish, bearish, or range.

        Args:
            dataframe: DataFrame with OHLCV data
            swing_highs: Series with swing high levels
            swing_lows: Series with swing low levels

        Returns:
            Series with trend: 'bullish', 'bearish', or 'range'
        """
        trend = pd.Series("range", index=dataframe.index, dtype=object)

        # Get recent swing points
        [h for h in swing_highs.dropna().tail(3) if pd.notna(h)]
        [l for l in swing_lows.dropna().tail(3) if pd.notna(l)]

        for i in range(len(dataframe)):
            # Update recent swings up to current index
            current_highs = swing_highs.iloc[: i + 1].dropna().tail(3).tolist()
            current_lows = swing_lows.iloc[: i + 1].dropna().tail(3).tolist()

            if len(current_highs) >= 2 and len(current_lows) >= 2:
                # Bullish trend: higher highs and higher lows
                if current_highs[-1] > current_highs[-2] and current_lows[-1] > current_lows[-2]:
                    trend.iloc[i] = "bullish"

                # Bearish trend: lower highs and lower lows
                elif current_highs[-1] < current_highs[-2] and current_lows[-1] < current_lows[-2]:
                    trend.iloc[i] = "bearish"

                else:
                    trend.iloc[i] = "range"
            else:
                trend.iloc[i] = "range"

        return trend

    def _identify_liquidity_zones(
        self, dataframe: pd.DataFrame, swing_highs: pd.Series, swing_lows: pd.Series
    ) -> dict[str, pd.Series]:
        """
        Identify liquidity zones (areas where stops are likely).

        Liquidity zones are typically:
        - Above swing highs (for long liquidations)
        - Below swing lows (for short liquidations)

        Args:
            dataframe: DataFrame with OHLCV data
            swing_highs: Series with swing high levels
            swing_lows: Series with swing low levels

        Returns:
            Dictionary with 'high' and 'low' liquidity zones
        """
        liquidity_high = pd.Series(np.nan, index=dataframe.index)
        liquidity_low = pd.Series(np.nan, index=dataframe.index)

        # Forward fill swing points
        last_swing_high = None
        last_swing_low = None

        for i in range(len(dataframe)):
            if pd.notna(swing_highs.iloc[i]):
                last_swing_high = swing_highs.iloc[i]

            if pd.notna(swing_lows.iloc[i]):
                last_swing_low = swing_lows.iloc[i]

            # Liquidity zones (with small buffer for stop hunts)
            if last_swing_high is not None:
                buffer = last_swing_high * 0.001  # 0.1% buffer
                liquidity_high.iloc[i] = last_swing_high + buffer

            if last_swing_low is not None:
                buffer = last_swing_low * 0.001  # 0.1% buffer
                liquidity_low.iloc[i] = last_swing_low - buffer

        return {"high": liquidity_high, "low": liquidity_low}

    def get_market_structure_summary(self, dataframe: pd.DataFrame) -> dict:
        """
        Get current market structure summary.

        Args:
            dataframe: DataFrame with market structure data

        Returns:
            Dictionary with market structure summary
        """
        last_row = dataframe.iloc[-1]

        return {
            "trend": last_row.get("market_structure", "range"),
            "last_swing_high": last_row.get("swing_high", None),
            "last_swing_low": last_row.get("swing_low", None),
            "bos_detected": last_row.get("bos_detected", False),
            "choch_detected": last_row.get("choch_detected", False),
            "liquidity_high": last_row.get("liquidity_zone_high", None),
            "liquidity_low": last_row.get("liquidity_zone_low", None),
        }

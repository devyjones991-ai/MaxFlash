"""
Whale Detector module.
Analyzes public trade history to identify large transactions and whale pressure.
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from utils.logger_config import setup_logging

logger = setup_logging()


class WhaleDetector:
    """
    Detects large trades (whales) and calculates buying/selling pressure.
    """

    def __init__(self, large_trade_threshold: float = 100000.0):
        """
        Initialize Whale Detector.

        Args:
            large_trade_threshold: Minimum value in USD to consider a trade "large".
        """
        self.threshold = large_trade_threshold

    def detect_whales(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a list of trades for whale activity.

        Args:
            trades: List of trade dictionaries (from ccxt.fetch_trades)

        Returns:
            Dictionary with whale metrics.
        """
        if not trades:
            return self._empty_metrics()

        df = pd.DataFrame(trades)

        # Ensure required columns exist
        required_cols = ["amount", "price", "side", "cost"]
        for col in required_cols:
            if col not in df.columns:
                # Try to calculate cost if missing
                if col == "cost" and "amount" in df.columns and "price" in df.columns:
                    df["cost"] = df["amount"] * df["price"]
                else:
                    logger.warning(f"Missing column {col} in trades data")
                    return self._empty_metrics()

        # Filter large trades
        large_trades = df[df["cost"] >= self.threshold]

        if large_trades.empty:
            return self._empty_metrics()

        # Calculate metrics
        buy_trades = large_trades[large_trades["side"] == "buy"]
        sell_trades = large_trades[large_trades["side"] == "sell"]

        buy_vol = buy_trades["cost"].sum()
        sell_vol = sell_trades["cost"].sum()

        net_flow = buy_vol - sell_vol
        total_vol = buy_vol + sell_vol

        # Whale Dominance: Share of volume taken by whales vs total volume of all trades
        total_market_vol = df["cost"].sum()
        dominance = total_vol / total_market_vol if total_market_vol > 0 else 0.0

        # Pressure: -1.0 (All Sell) to 1.0 (All Buy)
        pressure = (buy_vol - sell_vol) / total_vol if total_vol > 0 else 0.0

        return {
            "whale_count": len(large_trades),
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "buy_volume": float(buy_vol),
            "sell_volume": float(sell_vol),
            "net_flow": float(net_flow),
            "pressure": float(pressure),
            "dominance": float(dominance),
            "largest_trade": float(large_trades["cost"].max()),
            "has_whale_activity": True,
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """Return default empty metrics."""
        return {
            "whale_count": 0,
            "buy_count": 0,
            "sell_count": 0,
            "buy_volume": 0.0,
            "sell_volume": 0.0,
            "net_flow": 0.0,
            "pressure": 0.0,
            "dominance": 0.0,
            "largest_trade": 0.0,
            "has_whale_activity": False,
        }

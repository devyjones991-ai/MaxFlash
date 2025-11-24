"""
Feature engineering for machine learning models.
Transforms raw OHLCV data into ML-ready features.
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional
import warnings

warnings.filterwarnings("ignore")

from utils.logger_config import setup_logging

logger = setup_logging()


def create_price_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Create price-based features from OHLCV data.

    Args:
        ohlcv: OHLCV DataFrame

    Returns:
        DataFrame with price features
    """
    features = pd.DataFrame(index=ohlcv.index)

    # Returns
    features["returns"] = ohlcv["close"].pct_change()
    features["log_returns"] = np.log(ohlcv["close"] / ohlcv["close"].shift(1))

    # Volatility
    features["volatility_5"] = features["returns"].rolling(5).std()
    features["volatility_20"] = features["returns"].rolling(20).std()
    features["volatility_ratio"] = features["volatility_5"] / features["volatility_20"]

    # Price ratios
    features["hl_ratio"] = (ohlcv["high"] - ohlcv["low"]) / ohlcv["close"]
    features["co_ratio"] = (ohlcv["close"] - ohlcv["open"]) / ohlcv["open"]

    # Momentum
    features["momentum_5"] = ohlcv["close"] / ohlcv["close"].shift(5) - 1
    features["momentum_10"] = ohlcv["close"] / ohlcv["close"].shift(10) - 1
    features["momentum_20"] = ohlcv["close"] / ohlcv["close"].shift(20) - 1

    return features


def create_volume_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Create volume-based features.

    Args:
        ohlcv: OHLCV DataFrame

    Returns:
        DataFrame with volume features
    """
    features = pd.DataFrame(index=ohlcv.index)

    # Volume moving averages
    features["volume_ma_5"] = ohlcv["volume"].rolling(5).mean()
    features["volume_ma_20"] = ohlcv["volume"].rolling(20).mean()

    # Volume ratios
    features["volume_ratio_5"] = ohlcv["volume"] / features["volume_ma_5"]
    features["volume_ratio_20"] = ohlcv["volume"] / features["volume_ma_20"]

    # Volume-price correlation
    features["vp_corr_5"] = ohlcv["volume"].rolling(5).corr(ohlcv["close"])
    features["vp_corr_20"] = ohlcv["volume"].rolling(20).corr(ohlcv["close"])

    return features


def create_technical_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Create technical indicator features.

    Args:
        ohlcv: OHLCV DataFrame

    Returns:
        DataFrame with technical features
    """
    features = pd.DataFrame(index=ohlcv.index)

    # Moving averages
    for period in [5, 10, 20, 50]:
        features[f"sma_{period}"] = ohlcv["close"].rolling(period).mean()
        features[f"sma_{period}_ratio"] = ohlcv["close"] / features[f"sma_{period}"]

    # Exponential moving averages
    for period in [12, 26]:
        features[f"ema_{period}"] = ohlcv["close"].ewm(span=period, adjust=False).mean()

    # MACD
    features["macd"] = features["ema_12"] - features["ema_26"]
    features["macd_signal"] = features["macd"].ewm(span=9, adjust=False).mean()
    features["macd_hist"] = features["macd"] - features["macd_signal"]

    # RSI
    delta = ohlcv["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    features["rsi"] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    sma_20 = ohlcv["close"].rolling(20).mean()
    std_20 = ohlcv["close"].rolling(20).std()
    features["bb_upper"] = sma_20 + (std_20 * 2)
    features["bb_lower"] = sma_20 - (std_20 * 2)
    features["bb_position"] = (ohlcv["close"] - features["bb_lower"]) / (features["bb_upper"] - features["bb_lower"])

    # ATR (Average True Range)
    high_low = ohlcv["high"] - ohlcv["low"]
    high_close = np.abs(ohlcv["high"] - ohlcv["close"].shift())
    low_close = np.abs(ohlcv["low"] - ohlcv["close"].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    features["atr"] = true_range.rolling(14).mean()
    features["atr_ratio"] = features["atr"] / ohlcv["close"]

    return features


def create_smart_money_features(indicators: Dict[str, Any]) -> pd.Series:
    """
    Create features from Smart Money indicators.

    Args:
        indicators: Dictionary of calculated Smart Money indicators

    Returns:
        Series with Smart Money features
    """
    features = {}

    # Order Blocks
    features["in_bullish_ob"] = 1 if indicators.get("in_bullish_order_block") else 0
    features["in_bearish_ob"] = 1 if indicators.get("in_bearish_order_block") else 0

    # Fair Value Gaps
    features["in_fvg"] = 1 if indicators.get("in_fvg") else 0
    features["fvg_size"] = indicators.get("fvg_size", 0)

    # Market Structure
    market_structure = indicators.get("market_structure", "range")
    features["structure_bullish"] = 1 if market_structure == "bullish" else 0
    features["structure_bearish"] = 1 if market_structure == "bearish" else 0

    # Delta & Order Flow
    features["delta"] = indicators.get("delta", 0)
    features["delta_normalized"] = np.tanh(features["delta"] / 1000)  # Normalize large values

    # Volume Profile
    features["near_poc"] = 1 if indicators.get("near_volume_poc") else 0
    features["in_value_area"] = 1 if indicators.get("in_value_area") else 0

    return pd.Series(features)


def create_all_features(ohlcv: pd.DataFrame, smart_money_indicators: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Create complete feature set for ML models.

    Args:
        ohlcv: OHLCV DataFrame
        smart_money_indicators: Optional Smart Money indicators

    Returns:
        Complete feature DataFrame
    """
    # Create base features
    price_features = create_price_features(ohlcv)
    volume_features = create_volume_features(ohlcv)
    technical_features = create_technical_features(ohlcv)

    # Combine features
    all_features = pd.concat([price_features, volume_features, technical_features], axis=1)

    # Add Smart Money features if available
    if smart_money_indicators:
        sm_features = create_smart_money_features(smart_money_indicators)
        for col, value in sm_features.items():
            all_features[col] = value

    # Drop NaN values
    all_features = all_features.dropna()

    logger.debug(f"Created {len(all_features.columns)} features from OHLCV data")

    return all_features


def select_top_features(features: pd.DataFrame, target: pd.Series, n_features: int = 20) -> List[str]:
    """
    Select top N most important features using correlation.

    Args:
        features: Feature DataFrame
        target: Target variable
        n_features: Number of features to select

    Returns:
        List of selected feature names
    """
    try:
        from sklearn.feature_selection import SelectKBest, f_classif

        # Select top features
        selector = SelectKBest(score_func=f_classif, k=min(n_features, len(features.columns)))
        selector.fit(features, target)

        # Get selected feature names
        selected_indices = selector.get_support(indices=True)
        selected_features = features.columns[selected_indices].tolist()

        logger.info(f"Selected {len(selected_features)} top features")
        return selected_features

    except ImportError:
        logger.warning("scikit-learn not available for feature selection")
        return features.columns[:n_features].tolist()

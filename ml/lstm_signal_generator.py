"""
ML-based signal generation using LSTM neural networks.
Combines deep learning predictions with traditional technical analysis.
"""

import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    import tensorflow as tf
    from tensorflow import keras
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.model_selection import train_test_split

    HAS_ML = True
except ImportError:
    HAS_ML = False
    tf = None
    keras = None

from utils.logger_config import setup_logging

logger = setup_logging()


class LSTMSignalGenerator:
    """
    LSTM-based trading signal generator.
    Uses Long Short-Term Memory networks for price prediction and signal generation.
    """

    def __init__(
        self,
        lookback_periods: int = 60,
        model_path: Optional[str] = None,
        prediction_threshold: float = 0.55,
    ):
        """
        Initialize LSTM signal generator.

        Args:
            lookback_periods: Number of historical periods to use for prediction
            model_path: Path to pre-trained model (optional)
            prediction_threshold: Confidence threshold for signals (0.5-1.0)
        """
        if not HAS_ML:
            raise ImportError("TensorFlow not available. Install with: pip install tensorflow scikit-learn")

        self.lookback = lookback_periods
        self.prediction_threshold = prediction_threshold
        self.scaler = MinMaxScaler(feature_range=(0, 1)) if HAS_ML else None
        self.is_trained = False

        if model_path and HAS_ML:
            self.model = keras.models.load_model(model_path)
            self.is_trained = True
            logger.info(f"Loaded pre-trained model from {model_path}")
        elif HAS_ML:
            self.model = self._build_model()
            logger.info("Initialized new LSTM model")
        else:
            self.model = None

    def _build_model(self) -> "keras.Model":
        """
        Build LSTM model architecture.

        Returns:
            Compiled Keras model
        """
        model = keras.Sequential(
            [
                # First LSTM layer with return sequences
                keras.layers.LSTM(
                    128,
                    return_sequences=True,
                    input_shape=(self.lookback, 6),  # OHLCV + volume indicators
                ),
                keras.layers.Dropout(0.2),
                # Second LSTM layer
                keras.layers.LSTM(64, return_sequences=False),
                keras.layers.Dropout(0.2),
                # Dense layers
                keras.layers.Dense(32, activation="relu"),
                keras.layers.Dropout(0.1),
                # Output layer: 3 classes (Buy, Sell, Hold)
                keras.layers.Dense(3, activation="softmax"),
            ]
        )

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )

        logger.info(f"LSTM model built: {model.count_params()} parameters")
        return model

    def _prepare_features(self, ohlcv_df: pd.DataFrame) -> np.ndarray:
        """
        Prepare features from OHLCV data.

        Args:
            ohlcv_df: DataFrame with OHLCV data

        Returns:
            Scaled feature array
        """
        # Calculate additional features
        df = ohlcv_df.copy()

        # Price-based features
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        df["hl_ratio"] = (df["high"] - df["low"]) / df["close"]
        df["co_ratio"] = (df["close"] - df["open"]) / df["open"]

        # Volume indicators
        df["volume_ma"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma"]

        # Select features for model
        feature_columns = ["open", "high", "low", "close", "volume", "volume_ratio"]
        features = df[feature_columns].dropna()

        # Scale features
        scaled_features = self.scaler.fit_transform(features)

        return scaled_features

    def _create_sequences(self, data: np.ndarray, lookback: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for LSTM training.

        Args:
            data: Scaled feature data
            lookback: Number of lookback periods

        Returns:
            (X, y) sequences
        """
        X, y = [], []

        for i in range(lookback, len(data)):
            X.append(data[i - lookback : i])

            # Label: price movement in next period
            current_price = data[i, 3]  # Close price
            prev_price = data[i - 1, 3]

            if current_price > prev_price * 1.005:  # +0.5% threshold
                label = [1, 0, 0]  # Buy
            elif current_price < prev_price * 0.995:  # -0.5% threshold
                label = [0, 1, 0]  # Sell
            else:
                label = [0, 0, 1]  # Hold

            y.append(label)

        return np.array(X), np.array(y)

    def train(
        self,
        ohlcv_df: pd.DataFrame,
        epochs: int = 50,
        batch_size: int = 32,
        validation_split: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Train the LSTM model on historical data.

        Args:
            ohlcv_df: Historical OHLCV DataFrame
            epochs: Number of training epochs
            batch_size: Batch size for training
            validation_split: Validation data split ratio

        Returns:
            Training history
        """
        logger.info(f"Training LSTM model on {len(ohlcv_df)} samples...")

        # Prepare features
        features = self._prepare_features(ohlcv_df)

        # Create sequences
        X, y = self._create_sequences(features, self.lookback)

        logger.info(f"Created {len(X)} training sequences")

        # Train model
        history = self.model.fit(
            X,
            y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=1,
            callbacks=[
                keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
                keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=0.00001),
            ],
        )

        self.is_trained = True
        logger.info("Training completed")

        return {
            "final_loss": float(history.history["loss"][-1]),
            "final_accuracy": float(history.history["accuracy"][-1]),
            "val_loss": float(history.history["val_loss"][-1]),
            "val_accuracy": float(history.history["val_accuracy"][-1]),
        }

    def predict(self, ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate prediction from recent price data.

        Args:
            ohlcv_df: Recent OHLCV DataFrame (minimum lookback periods)

        Returns:
            Prediction dictionary
        """
        if not self.is_trained:
            logger.warning("Model not trained - prediction may be unreliable")

        # Prepare features
        features = self._prepare_features(ohlcv_df)

        # Get last sequence
        if len(features) < self.lookback:
            raise ValueError(f"Insufficient data: need {self.lookback} periods, got {len(features)}")

        last_sequence = features[-self.lookback :]
        last_sequence = last_sequence.reshape(1, self.lookback, -1)

        # Predict
        prediction = self.model.predict(last_sequence, verbose=0)[0]

        buy_prob, sell_prob, hold_prob = prediction

        # Determine action
        if buy_prob > self.prediction_threshold:
            action = "BUY"
            confidence = float(buy_prob)
        elif sell_prob > self.prediction_threshold:
            action = "SELL"
            confidence = float(sell_prob)
        else:
            action = "HOLD"
            confidence = float(hold_prob)

        return {
            "action": action,
            "confidence": confidence,
            "probabilities": {"buy": float(buy_prob), "sell": float(sell_prob), "hold": float(hold_prob)},
            "timestamp": datetime.now().isoformat(),
        }

    def generate_signal(self, ohlcv_df: pd.DataFrame, technical_indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signal combining LSTM prediction with technical analysis.

        Args:
            ohlcv_df: OHLCV DataFrame
            technical_indicators: Dictionary of calculated technical indicators

        Returns:
            Complete trading signal
        """
        # Get ML prediction
        ml_prediction = self.predict(ohlcv_df)

        # Current price
        current_price = float(ohlcv_df["close"].iloc[-1])

        # Calculate stop-loss and take-profit based on volatility
        atr = technical_indicators.get("atr", current_price * 0.02)  # 2% default
        stop_loss_distance = atr * 1.5
        take_profit_distance = atr * 3.0

        if ml_prediction["action"] == "BUY":
            stop_loss = current_price - stop_loss_distance
            take_profit = current_price + take_profit_distance
        elif ml_prediction["action"] == "SELL":
            stop_loss = current_price + stop_loss_distance
            take_profit = current_price - take_profit_distance
        else:
            stop_loss = None
            take_profit = None

        # Confluence check with technical indicators
        ta_alignment = self._check_ta_alignment(ml_prediction["action"], technical_indicators)

        signal = {
            "action": ml_prediction["action"],
            "confidence": ml_prediction["confidence"],
            "ml_probabilities": ml_prediction["probabilities"],
            "entry_price": current_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "ta_alignment": ta_alignment,
            "combined_confidence": (ml_prediction["confidence"] * 0.7 + ta_alignment * 0.3),
            "timestamp": ml_prediction["timestamp"],
            "indicators_used": list(technical_indicators.keys()),
        }

        return signal

    def _check_ta_alignment(self, ml_action: str, indicators: Dict[str, Any]) -> float:
        """
        Check alignment between ML prediction and technical indicators.

        Args:
            ml_action: ML predicted action
            indicators: Technical indicators

        Returns:
            Alignment score (0.0-1.0)
        """
        score = 0.0
        total_checks = 0

        # RSI alignment
        if "rsi" in indicators:
            total_checks += 1
            rsi = indicators["rsi"]
            if ml_action == "BUY" and rsi < 40:
                score += 1
            elif ml_action == "SELL" and rsi > 60:
                score += 1
            elif ml_action == "HOLD" and 40 <= rsi <= 60:
                score += 1

        # MACD alignment
        if "macd" in indicators and "macd_signal" in indicators:
            total_checks += 1
            macd = indicators["macd"]
            macd_signal = indicators["macd_signal"]
            if ml_action == "BUY" and macd > macd_signal:
                score += 1
            elif ml_action == "SELL" and macd < macd_signal:
                score += 1

        # Volume alignment
        if "volume_ratio" in indicators:
            total_checks += 1
            if ml_action in ["BUY", "SELL"] and indicators["volume_ratio"] > 1.2:
                score += 1

        return score / total_checks if total_checks > 0 else 0.5

    def save_model(self, path: str):
        """Save trained model to disk."""
        self.model.save(path)
        logger.info(f"Model saved to {path}")

    def evaluate(self, ohlcv_df: pd.DataFrame) -> Dict[str, float]:
        """
        Evaluate model performance on test data.

        Args:
            ohlcv_df: Test OHLCV DataFrame

        Returns:
            Evaluation metrics
        """
        features = self._prepare_features(ohlcv_df)
        X, y = self._create_sequences(features, self.lookback)

        loss, accuracy = self.model.evaluate(X, y, verbose=0)

        return {"test_loss": float(loss), "test_accuracy": float(accuracy)}

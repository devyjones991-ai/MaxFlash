"""
Ensemble Signal Generator.
Combines LSTM (Deep Learning) and Random Forest (Traditional ML) for robust predictions.
"""

import logging
import pickle
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from ml.lstm_signal_generator import LSTMSignalGenerator
from utils.logger_config import setup_logging

logger = setup_logging()

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class EnsembleSignalGenerator:
    """
    Combines predictions from multiple models (LSTM + Random Forest).
    """

    def __init__(
        self,
        lstm_model_path: Optional[str] = None,
        rf_model_path: Optional[str] = None,
    ):
        """
        Initialize Ensemble Generator.
        """
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn is required for EnsembleSignalGenerator")

        self.lstm = LSTMSignalGenerator(model_path=lstm_model_path)
        self.rf_model = None
        self.is_trained = False

        if rf_model_path:
            self.load_rf_model(rf_model_path)

    def train(
        self,
        ohlcv_df: pd.DataFrame,
        epochs: int = 50,
    ) -> Dict[str, Any]:
        """
        Train both models.
        """
        logger.info("Starting Ensemble Training...")

        # 1. Train LSTM
        lstm_metrics = self.lstm.train(ohlcv_df, epochs=epochs)

        # 2. Train Random Forest
        rf_metrics = self._train_rf(ohlcv_df)

        self.is_trained = True

        return {
            "lstm_metrics": lstm_metrics,
            "rf_metrics": rf_metrics,
            "combined_accuracy": (lstm_metrics["final_accuracy"] + rf_metrics["accuracy"]) / 2,
        }

    def _train_rf(self, ohlcv_df: pd.DataFrame) -> Dict[str, float]:
        """Train Random Forest model."""
        logger.info("Training Random Forest component...")

        # Prepare features (reuse LSTM's feature engineering)
        features = self.lstm._prepare_features(ohlcv_df)

        # Create targets (same logic as LSTM but flattened for RF)
        # LSTM uses sequences, RF uses rows. We need to align them.
        # For RF, we predict next candle direction based on current row features.

        X = features[:-1]  # All but last

        # Create labels: 0=Sell, 1=Hold, 2=Buy
        # Logic: if next close > current close * 1.005 -> Buy (2)
        #        if next close < current close * 0.995 -> Sell (0)
        #        else -> Hold (1)

        y = []
        closes = ohlcv_df["close"].values
        for i in range(len(features) - 1):
            curr = closes[i]
            next_p = closes[i + 1]
            if next_p > curr * 1.005:
                y.append(2)  # Buy
            elif next_p < curr * 0.995:
                y.append(0)  # Sell
            else:
                y.append(1)  # Hold

        y = np.array(y)

        # Align lengths
        min_len = min(len(X), len(y))
        X = X[:min_len]
        y = y[:min_len]

        # Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

        # Train
        self.rf_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        self.rf_model.fit(X_train, y_train)

        # Evaluate
        preds = self.rf_model.predict(X_test)
        acc = accuracy_score(y_test, preds)

        logger.info(f"Random Forest Accuracy: {acc:.4f}")
        return {"accuracy": float(acc)}

    def predict(self, ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate ensemble prediction.
        """
        if not self.is_trained and not self.rf_model:
            logger.warning("Ensemble not fully trained")

        # 1. Get LSTM Prediction
        lstm_pred = self.lstm.predict(ohlcv_df)

        # 2. Get RF Prediction
        rf_pred = self._predict_rf(ohlcv_df)

        # 3. Combine (Voting or Weighted Average)
        # LSTM returns probs for [Buy, Sell, Hold]
        # RF returns class or probs. Let's get probs.

        lstm_probs = lstm_pred["probabilities"]
        rf_probs = rf_pred["probabilities"]

        # Weighted average (give slightly more weight to LSTM usually, or equal)
        combined_buy = (lstm_probs["buy"] + rf_probs["buy"]) / 2
        combined_sell = (lstm_probs["sell"] + rf_probs["sell"]) / 2
        combined_hold = (lstm_probs["hold"] + rf_probs["hold"]) / 2

        # Determine final action
        if combined_buy > 0.5:
            action = "BUY"
            confidence = combined_buy
        elif combined_sell > 0.5:
            action = "SELL"
            confidence = combined_sell
        else:
            action = "HOLD"
            confidence = combined_hold

        return {
            "action": action,
            "confidence": float(confidence),
            "ensemble_probabilities": {
                "buy": float(combined_buy),
                "sell": float(combined_sell),
                "hold": float(combined_hold),
            },
            "components": {"lstm": lstm_pred, "rf": rf_pred},
            "timestamp": lstm_pred["timestamp"],
        }

    def _predict_rf(self, ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate Random Forest prediction."""
        if not self.rf_model:
            return {"probabilities": {"buy": 0.33, "sell": 0.33, "hold": 0.33}}

        features = self.lstm._prepare_features(ohlcv_df)
        last_row = features[-1].reshape(1, -1)

        # Predict proba: returns array of shape (1, 3) -> [[prob_0, prob_1, prob_2]]
        # Classes are 0=Sell, 1=Hold, 2=Buy (based on training logic)
        probs = self.rf_model.predict_proba(last_row)[0]

        # Map back to names. Note: verify class order in self.rf_model.classes_
        # Usually sorted: 0, 1, 2

        # Safety check for class indices
        class_map = {0: "sell", 1: "hold", 2: "buy"}
        result_probs = {"buy": 0.0, "sell": 0.0, "hold": 0.0}

        for idx, class_label in enumerate(self.rf_model.classes_):
            if class_label in class_map:
                result_probs[class_map[class_label]] = probs[idx]

        return {"probabilities": result_probs}

    def save_models(self, path_prefix: str):
        """Save both models."""
        self.lstm.save_model(f"{path_prefix}_lstm.h5")
        if self.rf_model:
            with open(f"{path_prefix}_rf.pkl", "wb") as f:
                pickle.dump(self.rf_model, f)
        logger.info(f"Ensemble models saved to {path_prefix}_*")

    def load_rf_model(self, path: str):
        """Load RF model."""
        with open(path, "rb") as f:
            self.rf_model = pickle.load(f)
        self.is_trained = True

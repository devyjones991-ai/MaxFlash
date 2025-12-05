"""
Ensemble Signal Generator.
Combines Smart Money Concepts, LightGBM, and LSTM for robust predictions.

Voting weights:
- Smart Money Concepts: 40%
- LightGBM: 35%
- LSTM: 25%
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

try:
    from ml.lightgbm_model import LightGBMSignalGenerator
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    LightGBMSignalGenerator = None

try:
    import tensorflow as tf
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False


class EnsembleSignalGenerator:
    """
    Combines predictions from multiple models with weighted voting:
    - Smart Money Concepts: 40%
    - LightGBM: 35%
    - LSTM: 25%
    """
    
    # Voting weights
    WEIGHT_SMC = 0.40
    WEIGHT_LIGHTGBM = 0.35
    WEIGHT_LSTM = 0.25

    def __init__(
        self,
        lstm_model_path: Optional[str] = None,
        rf_model_path: Optional[str] = None,
        lightgbm_model_path: Optional[str] = None,
    ):
        """
        Initialize Ensemble Generator with all model components.
        
        Args:
            lstm_model_path: Path to pre-trained LSTM model
            rf_model_path: Path to pre-trained Random Forest model (legacy)
            lightgbm_model_path: Path to pre-trained LightGBM model
        """
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn is required for EnsembleSignalGenerator")

        # LSTM component (optional, requires TensorFlow)
        self.lstm = None
        if HAS_TENSORFLOW:
            try:
                self.lstm = LSTMSignalGenerator(model_path=lstm_model_path)
                logger.info("LSTM component initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize LSTM: {e}")
        else:
            logger.info("TensorFlow not available - LSTM disabled, using LightGBM + SMC only")

        # LightGBM component
        self.lightgbm = None
        if HAS_LIGHTGBM:
            try:
                self.lightgbm = LightGBMSignalGenerator(model_path=lightgbm_model_path)
                logger.info("LightGBM component initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize LightGBM: {e}")
        else:
            logger.warning("LightGBM not available - using SMC only")
        
        # Legacy RF model (kept for backward compatibility)
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
        Train all ensemble components.
        """
        logger.info("Starting Ensemble Training...")
        metrics = {}
        accuracies = []

        # 1. Train LSTM (weight: 25%) - Optional, requires TensorFlow
        if self.lstm:
            try:
                lstm_metrics = self.lstm.train(ohlcv_df, epochs=epochs)
                metrics["lstm_metrics"] = lstm_metrics
                accuracies.append(lstm_metrics["final_accuracy"])
                logger.info(f"LSTM trained - accuracy: {lstm_metrics['final_accuracy']:.4f}")
            except Exception as e:
                logger.error(f"LSTM training failed: {e}")
                metrics["lstm_metrics"] = {"error": str(e)}
        else:
            logger.info("Skipping LSTM training (TensorFlow not available)")
            metrics["lstm_metrics"] = {"skipped": "TensorFlow not available"}

        # 2. Train LightGBM (weight: 35%)
        if self.lightgbm:
            try:
                lgb_metrics = self.lightgbm.train(ohlcv_df)
                metrics["lightgbm_metrics"] = lgb_metrics
                accuracies.append(lgb_metrics["accuracy"])
                logger.info(f"LightGBM trained - accuracy: {lgb_metrics['accuracy']:.4f}")
            except Exception as e:
                logger.error(f"LightGBM training failed: {e}")
                metrics["lightgbm_metrics"] = {"error": str(e)}

        # 3. Train Random Forest (legacy, only if LightGBM not available)
        if not self.lightgbm:
            try:
                rf_metrics = self._train_rf(ohlcv_df)
                metrics["rf_metrics"] = rf_metrics
                accuracies.append(rf_metrics["accuracy"])
            except Exception as e:
                logger.error(f"RF training failed: {e}")
                metrics["rf_metrics"] = {"error": str(e)}

        self.is_trained = True
        
        # Calculate weighted average accuracy
        combined_accuracy = np.mean(accuracies) if accuracies else 0.0
        metrics["combined_accuracy"] = float(combined_accuracy)
        
        logger.info(f"Ensemble training complete - combined accuracy: {combined_accuracy:.4f}")

        return metrics

    def _train_rf(self, ohlcv_df: pd.DataFrame) -> Dict[str, float]:
        """Train Random Forest model."""
        logger.info("Training Random Forest component...")

        # Prepare features (reuse LSTM's feature engineering if available)
        if self.lstm:
            features = self.lstm._prepare_features(ohlcv_df)
        else:
            # Fallback feature engineering if LSTM not available
            features = self._prepare_simple_features(ohlcv_df)

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

    def predict(self, ohlcv_df: pd.DataFrame, smc_signal: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate ensemble prediction with weighted voting.
        
        Args:
            ohlcv_df: OHLCV DataFrame for prediction
            smc_signal: Optional Smart Money Concepts signal dict
                        Expected format: {'action': 'BUY/SELL/HOLD', 'confidence': 0.0-1.0}
        
        Returns:
            Combined prediction with all component contributions
        """
        if not self.is_trained and not self.rf_model and not self.lightgbm:
            logger.warning("Ensemble not fully trained")

        components = {}
        weighted_probs = {"buy": 0.0, "sell": 0.0, "hold": 0.0}
        total_weight = 0.0

        # 1. Smart Money Concepts (weight: 40%)
        if smc_signal:
            smc_probs = self._convert_signal_to_probs(smc_signal)
            for key in weighted_probs:
                weighted_probs[key] += smc_probs[key] * self.WEIGHT_SMC
            total_weight += self.WEIGHT_SMC
            components["smc"] = {
                "action": smc_signal.get("action", "HOLD"),
                "confidence": smc_signal.get("confidence", 0.5),
                "probabilities": smc_probs,
                "weight": self.WEIGHT_SMC,
            }

        # 2. LightGBM Prediction (weight: 35%)
        if self.lightgbm and self.lightgbm.is_trained:
            try:
                lgb_pred = self.lightgbm.predict(ohlcv_df)
                lgb_probs = lgb_pred["probabilities"]
                for key in weighted_probs:
                    weighted_probs[key] += lgb_probs[key] * self.WEIGHT_LIGHTGBM
                total_weight += self.WEIGHT_LIGHTGBM
                components["lightgbm"] = {
                    **lgb_pred,
                    "weight": self.WEIGHT_LIGHTGBM,
                }
            except Exception as e:
                logger.error(f"LightGBM prediction failed: {e}")

        # 3. LSTM Prediction (weight: 25%) - Optional, requires TensorFlow
        if self.lstm and self.lstm.is_trained:
            try:
                lstm_pred = self.lstm.predict(ohlcv_df)
                lstm_probs = lstm_pred["probabilities"]
                for key in weighted_probs:
                    weighted_probs[key] += lstm_probs[key] * self.WEIGHT_LSTM
                total_weight += self.WEIGHT_LSTM
                components["lstm"] = {
                    **lstm_pred,
                    "weight": self.WEIGHT_LSTM,
                }
            except Exception as e:
                logger.error(f"LSTM prediction failed: {e}")

        # 4. Fallback to RF if no other ML models available
        if not self.lightgbm and self.rf_model:
            try:
                rf_pred = self._predict_rf(ohlcv_df)
                rf_probs = rf_pred["probabilities"]
                rf_weight = self.WEIGHT_LIGHTGBM  # Use LightGBM's weight
                for key in weighted_probs:
                    weighted_probs[key] += rf_probs[key] * rf_weight
                total_weight += rf_weight
                components["rf"] = rf_pred
            except Exception as e:
                logger.error(f"RF prediction failed: {e}")

        # Normalize probabilities if we have any predictions
        if total_weight > 0:
            for key in weighted_probs:
                weighted_probs[key] /= total_weight
        else:
            # Default to neutral
            weighted_probs = {"buy": 0.33, "sell": 0.33, "hold": 0.34}

        # Determine final action
        if weighted_probs["buy"] > 0.45:  # Lower threshold for combined signal
            action = "BUY"
            confidence = weighted_probs["buy"]
        elif weighted_probs["sell"] > 0.45:
            action = "SELL"
            confidence = weighted_probs["sell"]
        else:
            action = "HOLD"
            confidence = weighted_probs["hold"]

        from datetime import datetime
        
        return {
            "action": action,
            "confidence": float(confidence),
            "ensemble_probabilities": {
                "buy": float(weighted_probs["buy"]),
                "sell": float(weighted_probs["sell"]),
                "hold": float(weighted_probs["hold"]),
            },
            "components": components,
            "total_weight_used": float(total_weight),
            "timestamp": datetime.now().isoformat(),
        }
    
    def _convert_signal_to_probs(self, signal: Dict[str, Any]) -> Dict[str, float]:
        """Convert a signal action/confidence to probability distribution."""
        action = signal.get("action", "HOLD").upper()
        confidence = signal.get("confidence", 0.5)
        
        # Distribute remaining probability
        remaining = 1.0 - confidence
        other_prob = remaining / 2
        
        if action == "BUY":
            return {"buy": confidence, "sell": other_prob, "hold": other_prob}
        elif action == "SELL":
            return {"buy": other_prob, "sell": confidence, "hold": other_prob}
        else:  # HOLD
            return {"buy": other_prob, "sell": other_prob, "hold": confidence}

    def _predict_rf(self, ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate Random Forest prediction."""
        if not self.rf_model:
            return {"probabilities": {"buy": 0.33, "sell": 0.33, "hold": 0.33}}

        if self.lstm:
            features = self.lstm._prepare_features(ohlcv_df)
        else:
            features = self._prepare_simple_features(ohlcv_df)

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
        """Save all ensemble models."""
        # Save LSTM (if available)
        if self.lstm:
            try:
                self.lstm.save_model(f"{path_prefix}_lstm.h5")
            except Exception as e:
                logger.error(f"Failed to save LSTM: {e}")
        
        # Save LightGBM
        if self.lightgbm and self.lightgbm.is_trained:
            try:
                self.lightgbm.save_model(f"{path_prefix}_lightgbm.txt")
            except Exception as e:
                logger.error(f"Failed to save LightGBM: {e}")
        
        # Save RF (legacy)
        if self.rf_model:
            try:
                with open(f"{path_prefix}_rf.pkl", "wb") as f:
                    pickle.dump(self.rf_model, f)
            except Exception as e:
                logger.error(f"Failed to save RF: {e}")
                
        logger.info(f"Ensemble models saved to {path_prefix}_*")

    def load_rf_model(self, path: str):
        """Load RF model."""
        with open(path, "rb") as f:
            self.rf_model = pickle.load(f)
        self.is_trained = True
    
    def load_lightgbm_model(self, path: str):
        """Load LightGBM model."""
        if self.lightgbm:
            self.lightgbm.load_model(path)
        else:
            logger.warning("LightGBM not initialized, cannot load model")

    def _prepare_simple_features(self, ohlcv_df: pd.DataFrame) -> np.ndarray:
        """
        Simple feature engineering fallback when LSTM is not available.

        Args:
            ohlcv_df: OHLCV DataFrame

        Returns:
            Feature matrix
        """
        df = ohlcv_df.copy()

        # Basic technical indicators
        df['returns'] = df['close'].pct_change()
        df['high_low'] = (df['high'] - df['low']) / df['close']
        df['close_open'] = (df['close'] - df['open']) / df['open']

        # Moving averages
        df['sma_5'] = df['close'].rolling(5).mean()
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()

        # Volume features
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # Select features
        feature_cols = ['returns', 'high_low', 'close_open', 'sma_5', 'sma_10', 'sma_20', 'volume_ratio']
        features = df[feature_cols].fillna(0).values

        return features

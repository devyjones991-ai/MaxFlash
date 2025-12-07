"""
LightGBM-based signal generation for MaxFlash.
Fast gradient boosting model optimized for real-time trading signals.
"""

import pickle
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    import lightgbm as lgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.preprocessing import StandardScaler
    
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    lgb = None

from utils.logger_config import setup_logging
from ml.feature_engineering import create_all_features

logger = setup_logging()


class LightGBMSignalGenerator:
    """
    LightGBM-based trading signal generator.
    Uses gradient boosting for fast and accurate signal prediction.
    
    Features used:
    - OHLCV data and derivatives
    - Technical indicators (RSI, MACD, BB)
    - Smart Money features (Order Blocks, FVG, Market Structure)
    - Order Flow (Delta, Cumulative Delta)
    - Volume Profile (POC, VAH, VAL proximity)
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        prediction_threshold: float = 0.55,
        lookback_periods: int = 20,
    ):
        """
        Initialize LightGBM signal generator.
        
        Args:
            model_path: Path to pre-trained model (optional)
            prediction_threshold: Confidence threshold for signals (0.5-1.0)
            lookback_periods: Number of periods for feature calculation
        """
        if not HAS_LIGHTGBM:
            raise ImportError(
                "LightGBM not available. Install with: pip install lightgbm"
            )
        
        self.prediction_threshold = prediction_threshold
        self.lookback = lookback_periods
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model: Optional[lgb.Booster] = None
        self.feature_names: List[str] = []
        
        # Model parameters optimized for trading signals
        self.params = {
            'objective': 'multiclass',
            'num_class': 3,  # BUY, SELL, HOLD
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'max_depth': 8,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'min_child_samples': 20,
            'lambda_l1': 0.1,
            'lambda_l2': 0.1,
            'verbose': -1,
            'seed': 42,
        }
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
            logger.info(f"Loaded pre-trained LightGBM model from {model_path}")
        else:
            logger.info("Initialized new LightGBM model (not trained)")
    
    def _prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """
        Prepare comprehensive feature set for the model.
        
        Args:
            df: OHLCV DataFrame with optional Smart Money indicators
            
        Returns:
            Tuple of (feature_array, feature_names)
        """
        features = pd.DataFrame(index=df.index)
        
        # === 1. Price-based features ===
        features['returns'] = df['close'].pct_change()
        features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        features['hl_ratio'] = (df['high'] - df['low']) / df['close']
        features['co_ratio'] = (df['close'] - df['open']) / df['open']
        
        # Momentum
        for period in [5, 10, 20]:
            features[f'momentum_{period}'] = df['close'] / df['close'].shift(period) - 1
        
        # Volatility
        features['volatility_5'] = features['returns'].rolling(5).std()
        features['volatility_20'] = features['returns'].rolling(20).std()
        features['volatility_ratio'] = features['volatility_5'] / features['volatility_20']
        
        # === 2. Moving Averages ===
        for period in [5, 10, 20, 50]:
            features[f'sma_{period}'] = df['close'].rolling(period).mean()
            features[f'sma_{period}_ratio'] = df['close'] / features[f'sma_{period}']
            features[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
            features[f'ema_{period}_ratio'] = df['close'] / features[f'ema_{period}']
        
        # === 3. RSI ===
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        features['rsi'] = 100 - (100 / (1 + rs))
        features['rsi_oversold'] = (features['rsi'] < 30).astype(int)
        features['rsi_overbought'] = (features['rsi'] > 70).astype(int)
        
        # === 4. MACD ===
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        features['macd'] = exp12 - exp26
        features['macd_signal'] = features['macd'].ewm(span=9, adjust=False).mean()
        features['macd_hist'] = features['macd'] - features['macd_signal']
        features['macd_cross_up'] = ((features['macd'] > features['macd_signal']) & 
                                      (features['macd'].shift(1) <= features['macd_signal'].shift(1))).astype(int)
        features['macd_cross_down'] = ((features['macd'] < features['macd_signal']) & 
                                        (features['macd'].shift(1) >= features['macd_signal'].shift(1))).astype(int)
        
        # === 5. Bollinger Bands ===
        sma_20 = df['close'].rolling(20).mean()
        std_20 = df['close'].rolling(20).std()
        features['bb_upper'] = sma_20 + (std_20 * 2)
        features['bb_lower'] = sma_20 - (std_20 * 2)
        features['bb_position'] = (df['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'] + 1e-10)
        features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / sma_20
        
        # === 6. ATR (Average True Range) ===
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        features['atr'] = true_range.rolling(14).mean()
        features['atr_ratio'] = features['atr'] / df['close']
        
        # === 7. Volume features ===
        features['volume_ma_5'] = df['volume'].rolling(5).mean()
        features['volume_ma_20'] = df['volume'].rolling(20).mean()
        features['volume_ratio_5'] = df['volume'] / (features['volume_ma_5'] + 1e-10)
        features['volume_ratio_20'] = df['volume'] / (features['volume_ma_20'] + 1e-10)
        features['vp_corr'] = df['volume'].rolling(20).corr(df['close'])
        
        # === 8. Smart Money Features (if available) ===
        # Order Blocks
        if 'ob_bullish_low' in df.columns:
            features['in_bullish_ob'] = ((df['close'] >= df['ob_bullish_low']) & 
                                          (df['close'] <= df['ob_bullish_high'])).astype(int)
        else:
            features['in_bullish_ob'] = 0
            
        if 'ob_bearish_low' in df.columns:
            features['in_bearish_ob'] = ((df['close'] >= df['ob_bearish_low']) & 
                                          (df['close'] <= df['ob_bearish_high'])).astype(int)
        else:
            features['in_bearish_ob'] = 0
        
        # Fair Value Gaps
        if 'fvg_bullish_low' in df.columns:
            features['in_bullish_fvg'] = ((df['close'] >= df['fvg_bullish_low']) & 
                                           (df['close'] <= df['fvg_bullish_high'])).astype(int)
        else:
            features['in_bullish_fvg'] = 0
            
        if 'fvg_bearish_low' in df.columns:
            features['in_bearish_fvg'] = ((df['close'] >= df['fvg_bearish_low']) & 
                                           (df['close'] <= df['fvg_bearish_high'])).astype(int)
        else:
            features['in_bearish_fvg'] = 0
        
        # Market Structure
        if 'market_structure' in df.columns:
            features['structure_bullish'] = (df['market_structure'].str.lower() == 'bullish').astype(int)
            features['structure_bearish'] = (df['market_structure'].str.lower() == 'bearish').astype(int)
        else:
            features['structure_bullish'] = 0
            features['structure_bearish'] = 0
        
        # === 9. Order Flow / Delta (if available) ===
        if 'delta' in df.columns:
            features['delta'] = df['delta']
            features['delta_normalized'] = np.tanh(df['delta'] / (df['volume'] + 1e-10))
            features['cumulative_delta'] = df['delta'].cumsum()
            features['delta_ma_5'] = df['delta'].rolling(5).mean()
        else:
            features['delta'] = 0
            features['delta_normalized'] = 0
            features['cumulative_delta'] = 0
            features['delta_ma_5'] = 0
        
        # === 10. Volume Profile (if available) ===
        if 'vp_poc' in df.columns:
            features['poc_distance'] = (df['close'] - df['vp_poc']) / df['close']
            features['near_poc'] = (np.abs(features['poc_distance']) < 0.01).astype(int)
        else:
            features['poc_distance'] = 0
            features['near_poc'] = 0
            
        if 'vp_vah' in df.columns and 'vp_val' in df.columns:
            features['in_value_area'] = ((df['close'] >= df['vp_val']) & 
                                          (df['close'] <= df['vp_vah'])).astype(int)
        else:
            features['in_value_area'] = 0
        
        # === 11. Stochastic Oscillator ===
        low_14 = df['low'].rolling(14).min()
        high_14 = df['high'].rolling(14).max()
        features['stoch_k'] = 100 * (df['close'] - low_14) / (high_14 - low_14 + 1e-10)
        features['stoch_d'] = features['stoch_k'].rolling(3).mean()
        
        # === 12. Price patterns ===
        features['higher_high'] = (df['high'] > df['high'].shift(1)).astype(int)
        features['lower_low'] = (df['low'] < df['low'].shift(1)).astype(int)
        features['bullish_candle'] = (df['close'] > df['open']).astype(int)
        features['body_size'] = np.abs(df['close'] - df['open']) / df['close']
        
        # Drop NaN values
        features = features.dropna()
        
        feature_names = features.columns.tolist()
        
        return features.values, feature_names
    
    def _create_labels(self, df: pd.DataFrame, threshold: float = 0.005) -> np.ndarray:
        """
        Create classification labels based on future price movement.
        
        Args:
            df: OHLCV DataFrame
            threshold: Price change threshold (0.5% default)
            
        Returns:
            Label array: 0=SELL, 1=HOLD, 2=BUY
        """
        # Look at next candle's close vs current close
        future_returns = df['close'].shift(-1) / df['close'] - 1
        
        labels = np.where(
            future_returns > threshold, 2,  # BUY
            np.where(future_returns < -threshold, 0, 1)  # SELL or HOLD
        )
        
        return labels[:-1]  # Remove last (no future data)
    
    def train(
        self,
        df: pd.DataFrame,
        num_boost_round: int = 500,
        early_stopping_rounds: int = 50,
        test_size: float = 0.2,
        use_new_features: bool = False,
    ) -> Dict[str, Any]:
        """
        Train the LightGBM model.

        Args:
            df: OHLCV DataFrame with optional indicators
            num_boost_round: Number of boosting rounds
            early_stopping_rounds: Early stopping patience
            test_size: Test set proportion
            use_new_features: Use enhanced feature engineering (ADX, OBV, VWAP, Donchian)

        Returns:
            Training metrics dictionary
        """
        logger.info(f"Training LightGBM on {len(df)} samples...")
        logger.info(f"Using enhanced features: {use_new_features}")

        # Prepare features
        if use_new_features:
            # Use enhanced feature engineering from feature_engineering.py
            features_df = create_all_features(df, smart_money_indicators=None, use_new_features=True)
            X = features_df.values
            self.feature_names = features_df.columns.tolist()
            logger.info(f"Using {len(self.feature_names)} enhanced features (ADX, OBV, VWAP, Donchian)")
        else:
            # Use legacy feature engineering
            X, self.feature_names = self._prepare_features(df)
            logger.info(f"Using {len(self.feature_names)} legacy features")

        y = self._create_labels(df)
        
        # Align lengths
        min_len = min(len(X), len(y))
        X = X[:min_len]
        y = y[:min_len]
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, shuffle=False
        )
        
        # Create datasets
        train_data = lgb.Dataset(X_train, label=y_train, feature_name=self.feature_names)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
        
        # Train model
        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=[valid_data],
            callbacks=[
                lgb.early_stopping(stopping_rounds=early_stopping_rounds),
                lgb.log_evaluation(period=100),
            ],
        )
        
        self.is_trained = True
        
        # Evaluate
        y_pred = np.argmax(self.model.predict(X_test), axis=1)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Feature importance
        importance = dict(zip(
            self.feature_names,
            self.model.feature_importance(importance_type='gain')
        ))
        top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]
        
        logger.info(f"LightGBM Training Complete - Accuracy: {accuracy:.4f}")
        logger.info(f"Top 5 features: {[f[0] for f in top_features[:5]]}")
        
        return {
            'accuracy': float(accuracy),
            'num_iterations': self.model.num_trees(),
            'top_features': top_features,
            'class_distribution': {
                'buy': int(np.sum(y == 2)),
                'sell': int(np.sum(y == 0)),
                'hold': int(np.sum(y == 1)),
            }
        }
    
    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate prediction from current market data.
        
        Args:
            df: Recent OHLCV DataFrame
            
        Returns:
            Prediction dictionary with action, confidence, and probabilities
        """
        if self.model is None:
            logger.warning("LightGBM model not trained - returning neutral prediction")
            return {
                'action': 'HOLD',
                'confidence': 0.33,
                'probabilities': {'buy': 0.33, 'sell': 0.33, 'hold': 0.33},
                'timestamp': datetime.now().isoformat(),
            }
        
        # Prepare features
        X, _ = self._prepare_features(df)
        
        if len(X) == 0:
            return {
                'action': 'HOLD',
                'confidence': 0.33,
                'probabilities': {'buy': 0.33, 'sell': 0.33, 'hold': 0.33},
                'timestamp': datetime.now().isoformat(),
            }
        
        # Scale and predict
        X_scaled = self.scaler.transform(X[-1:])  # Last row only
        probs = self.model.predict(X_scaled)[0]
        
        # probs order: [SELL, HOLD, BUY] (0, 1, 2)
        sell_prob, hold_prob, buy_prob = probs
        
        # Determine action
        if buy_prob > self.prediction_threshold:
            action = 'BUY'
            confidence = float(buy_prob)
        elif sell_prob > self.prediction_threshold:
            action = 'SELL'
            confidence = float(sell_prob)
        else:
            action = 'HOLD'
            confidence = float(hold_prob)
        
        return {
            'action': action,
            'confidence': confidence,
            'probabilities': {
                'buy': float(buy_prob),
                'sell': float(sell_prob),
                'hold': float(hold_prob),
            },
            'timestamp': datetime.now().isoformat(),
        }
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        if self.model is None:
            return {}
        
        importance = self.model.feature_importance(importance_type='gain')
        return dict(zip(self.feature_names, importance))
    
    def save_model(self, path: str):
        """Save model and scaler to disk."""
        if self.model is None:
            logger.warning("No model to save")
            return
        
        # Save LightGBM model
        self.model.save_model(path)
        
        # Save scaler and feature names
        meta_path = path.replace('.txt', '_meta.pkl').replace('.lgb', '_meta.pkl')
        if not meta_path.endswith('_meta.pkl'):
            meta_path = path + '_meta.pkl'
            
        with open(meta_path, 'wb') as f:
            pickle.dump({
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'is_trained': self.is_trained,
            }, f)
        
        logger.info(f"LightGBM model saved to {path}")
    
    def load_model(self, path: str):
        """Load model and scaler from disk."""
        self.model = lgb.Booster(model_file=path)
        
        # Load metadata
        meta_path = path.replace('.txt', '_meta.pkl').replace('.lgb', '_meta.pkl')
        if not meta_path.endswith('_meta.pkl'):
            meta_path = path + '_meta.pkl'
        
        if Path(meta_path).exists():
            with open(meta_path, 'rb') as f:
                meta = pickle.load(f)
                self.scaler = meta['scaler']
                self.feature_names = meta['feature_names']
                self.is_trained = meta['is_trained']
        else:
            logger.warning("Metadata file not found, using default scaler")
            self.is_trained = True
        
        logger.info(f"LightGBM model loaded from {path}")


# Singleton instance for easy access
_lightgbm_generator: Optional[LightGBMSignalGenerator] = None


def get_lightgbm_generator() -> LightGBMSignalGenerator:
    """Get or create LightGBM generator singleton."""
    global _lightgbm_generator
    if _lightgbm_generator is None:
        try:
            _lightgbm_generator = LightGBMSignalGenerator()
        except ImportError as e:
            logger.error(f"Failed to create LightGBM generator: {e}")
            raise
    return _lightgbm_generator





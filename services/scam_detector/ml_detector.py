"""
ML модель для детекции скама (XGBoost/LightGBM).
"""
from typing import Dict, Optional
import structlog
import numpy as np
import pickle
from pathlib import Path
from app.config import settings

logger = structlog.get_logger()

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available, using rule-based only")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM not available")


class MLScamDetector:
    """ML детектор скама."""
    
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or (settings.ML_ARTIFACTS_DIR / "scam_detector.pkl")
        self.model = None
        self.feature_names = [
            "is_proxy", "is_upgradeable", "has_blacklist", "has_whitelist",
            "has_mint", "has_pause", "tax_buy_percent", "tax_sell_percent",
            "total_liquidity_usd", "lp_locked", "volume_24h_usd",
            "buy_sell_ratio"
        ]
        
        if self.model_path.exists():
            self.load_model()
        else:
            logger.warning("ML model not found, using rule-based only")
    
    def load_model(self):
        """Загрузить модель из файла."""
        try:
            with open(self.model_path, "rb") as f:
                self.model = pickle.load(f)
            logger.info("ML model loaded", path=str(self.model_path))
        except Exception as e:
            logger.error("Error loading ML model", error=str(e))
            self.model = None
    
    def save_model(self, model):
        """Сохранить модель в файл."""
        try:
            settings.ML_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.model_path, "wb") as f:
                pickle.dump(model, f)
            logger.info("ML model saved", path=str(self.model_path))
        except Exception as e:
            logger.error("Error saving ML model", error=str(e))
    
    def predict(self, features: Dict) -> float:
        """
        Предсказать scam score используя ML модель.
        
        Args:
            features: Словарь с фичами
        
        Returns:
            Scam score (0.0 - 1.0)
        """
        if not self.model:
            return 0.5  # Дефолтный score если модель не загружена
        
        try:
            # Подготавливаем фичи в правильном порядке
            feature_vector = np.array([
                float(features.get(name, 0.0))
                for name in self.feature_names
            ]).reshape(1, -1)
            
            # Предсказание
            score = self.model.predict_proba(feature_vector)[0][1]  # Вероятность класса "scam"
            
            return float(score)
        except Exception as e:
            logger.error("Error predicting with ML model", error=str(e))
            return 0.5
    
    def train_model(self, X, y):
        """
        Обучить модель (заглушка для будущей реализации).
        
        Args:
            X: Матрица фич
            y: Целевая переменная (0 = safe, 1 = scam)
        """
        if not XGBOOST_AVAILABLE and not LIGHTGBM_AVAILABLE:
            logger.error("No ML library available for training")
            return
        
        try:
            if XGBOOST_AVAILABLE:
                model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=42
                )
            else:
                model = lgb.LGBMClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=42
                )
            
            model.fit(X, y)
            self.model = model
            self.save_model(model)
            
            logger.info("ML model trained and saved")
        except Exception as e:
            logger.error("Error training ML model", error=str(e))


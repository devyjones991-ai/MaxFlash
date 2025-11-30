"""
Конфигурация приложения MaxFlash Trading System.
"""

from enum import Enum
import os
from pathlib import Path
from typing import Any, Optional

from pydantic_settings import BaseSettings

# Import market config data
try:
    from config.market_config import EXCHANGE_RATE_LIMITS, SECTOR_CLASSIFICATION
except ImportError:
    # Fallback if run from different context
    SECTOR_CLASSIFICATION = {}
    EXCHANGE_RATE_LIMITS = {}


class RiskProfile(str, Enum):
    AGGRESSIVE = "AGGRESSIVE"
    BALANCED = "BALANCED"
    CONSERVATIVE = "CONSERVATIVE"


class Settings(BaseSettings):
    """Настройки приложения."""

    # Основные настройки
    APP_NAME: str = "MaxFlash Trading System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # База данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./maxflash.db")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CACHE_TTL: int = 3600

    # API настройки
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    # Безопасность
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Биржи и Рынки
    EXCHANGE_NAME: str = os.getenv("EXCHANGE_NAME", "binance")
    EXCHANGE_API_KEY: Optional[str] = os.getenv("EXCHANGE_API_KEY")
    EXCHANGE_API_SECRET: Optional[str] = os.getenv("EXCHANGE_API_SECRET")
    EXCHANGE_TESTNET: bool = os.getenv("USE_TESTNET", "true").lower() == "true"

    # DEX настройки
    ETH_RPC_URL: str = os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com")
    BSC_RPC_URL: str = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")

    # Внешние API
    ETHERSCAN_API_KEY: Optional[str] = os.getenv("ETHERSCAN_API_KEY")
    BSCSCAN_API_KEY: Optional[str] = os.getenv("BSCSCAN_API_KEY")
    DEXSCREENER_API_URL: str = "https://api.dexscreener.com/latest/dex"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")

    # Риск-менеджмент
    RISK_PROFILE: RiskProfile = RiskProfile(os.getenv("RISK_PROFILE", "BALANCED"))

    # Параметры риска (будут переопределены в зависимости от профиля в post_init, если нужно,
    # но пока зададим базовые значения, которые можно переопределить через env)
    MAX_POSITION_SIZE_USD: float = float(os.getenv("MAX_POSITION_SIZE_USD", "100.0"))
    MAX_DAILY_LOSS_USD: float = float(os.getenv("MAX_DAILY_LOSS_USD", "50.0"))
    MAX_SLIPPAGE_PERCENT: float = float(os.getenv("MAX_SLIPPAGE_PERCENT", "1.0"))
    STOP_LOSS_PERCENT: float = float(os.getenv("STOP_LOSS_PERCENT", "0.02"))  # 2%
    TAKE_PROFIT_PERCENT: float = float(os.getenv("TAKE_PROFIT_PERCENT", "0.04"))  # 4%
    MIN_LIQUIDITY_USD: float = float(os.getenv("MIN_LIQUIDITY_USD", "1000.0"))

    # Сигналы
    SIGNAL_CONFIDENCE_THRESHOLD: float = float(os.getenv("SIGNAL_CONFIDENCE_THRESHOLD", "0.7"))
    USE_ML_FILTER: bool = True

    # LLM Settings
    USE_LOCAL_LLM: bool = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "qwen2.5:7b")

    # Dashboard Settings
    DASHBOARD_HOST: str = "0.0.0.0"
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8050"))
    UPDATE_INTERVAL: int = int(os.getenv("UPDATE_INTERVAL", "30")) * 1000  # ms

    # Пути
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    ML_ARTIFACTS_DIR: Path = BASE_DIR / "ml" / "artifacts"
    LOGS_DIR: Path = BASE_DIR / "logs"

    # Market Config Data
    SECTORS: dict[str, list[str]] = SECTOR_CLASSIFICATION
    RATE_LIMITS: dict[str, float] = EXCHANGE_RATE_LIMITS

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"
        use_enum_values = True

    def get_risk_params(self) -> dict[str, Any]:
        """Возвращает параметры риска в зависимости от профиля."""
        if self.RISK_PROFILE == RiskProfile.AGGRESSIVE:
            return {"stop_loss": 0.05, "take_profit": 0.10, "max_risk_per_trade": 0.03, "leverage": 3}
        elif self.RISK_PROFILE == RiskProfile.CONSERVATIVE:
            return {"stop_loss": 0.01, "take_profit": 0.02, "max_risk_per_trade": 0.01, "leverage": 1}
        else:  # BALANCED
            return {"stop_loss": 0.02, "take_profit": 0.04, "max_risk_per_trade": 0.02, "leverage": 1}


# Глобальный экземпляр настроек
settings = Settings()

# Создаём необходимые директории
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.ML_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

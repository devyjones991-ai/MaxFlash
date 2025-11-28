"""
Конфигурация приложения MaxFlash Trading System.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Основные настройки
    APP_NAME: str = "MaxFlash Trading System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # База данных PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://maxflash:maxflash_dev@localhost:5432/maxflash"
    )
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
    
    # DEX настройки
    ETH_RPC_URL: str = os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com")
    BSC_RPC_URL: str = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
    UNISWAP_V3_FACTORY: str = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
    PANCAKESWAP_FACTORY: str = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
    
    # Внешние API
    ETHERSCAN_API_KEY: Optional[str] = os.getenv("ETHERSCAN_API_KEY")
    BSCSCAN_API_KEY: Optional[str] = os.getenv("BSCSCAN_API_KEY")
    HONEYPOT_API_KEY: Optional[str] = os.getenv("HONEYPOT_API_KEY")
    DEXSCREENER_API_URL: str = "https://api.dexscreener.com/latest/dex"
    
    # Binance API
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "false").lower() == "true"
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
    
    # Торговые лимиты
    MAX_POSITION_SIZE_USD: float = 1000.0
    MAX_DAILY_LOSS_USD: float = 500.0
    MIN_LIQUIDITY_USD: float = 10000.0
    MAX_SLIPPAGE_PERCENT: float = 2.0
    
    # Scam detection пороги
    SCAM_SCORE_THRESHOLD_HIGH: float = 0.7
    SCAM_SCORE_THRESHOLD_MEDIUM: float = 0.4
    
    # Сигналы ранжирование
    SIGNAL_FREE_MIN_SCORE: float = 0.5
    SIGNAL_PRO_MIN_SCORE: float = 0.7
    SIGNAL_ALPHA_MIN_SCORE: float = 0.85
    
    # Логирование
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE", "logs/maxflash.log")
    
    # Пути
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    ML_ARTIFACTS_DIR: Path = BASE_DIR / "ml" / "artifacts"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Глобальный экземпляр настроек
settings = Settings()

# Создаём необходимые директории
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.ML_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
(settings.BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)


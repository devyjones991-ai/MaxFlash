"""
Конфигурация для web интерфейса.
"""
import os
from pathlib import Path

# Путь к проекту
PROJECT_ROOT = Path(__file__).parent.parent

# Freqtrade API настройки
FREQTRADE_API_URL = os.getenv("FREQTRADE_API_URL", "http://localhost:8080")
FREQTRADE_API_USERNAME = os.getenv("FREQTRADE_API_USERNAME", None)
FREQTRADE_API_PASSWORD = os.getenv("FREQTRADE_API_PASSWORD", None)

# Dashboard настройки
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8050"))
DASHBOARD_DEBUG = os.getenv("DASHBOARD_DEBUG", "True").lower() == "true"

# Интервал обновления (миллисекунды)
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "15000"))  # 15 секунд

# Пути к данным
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
BACKTEST_RESULTS_DIR = DATA_DIR / "backtest_results"

# Логирование
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "dashboard.log"


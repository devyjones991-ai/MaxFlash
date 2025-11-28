"""
Конфигурация для web интерфейса.
Перенаправляет на app.config.settings
"""

from app.config import settings

# Путь к проекту
PROJECT_ROOT = settings.BASE_DIR

# Freqtrade API настройки
FREQTRADE_API_URL = settings.FREQTRADE_API_URL
FREQTRADE_API_USERNAME = settings.FREQTRADE_API_USERNAME
FREQTRADE_API_PASSWORD = settings.FREQTRADE_API_PASSWORD

# Dashboard настройки
DASHBOARD_HOST = settings.DASHBOARD_HOST
DASHBOARD_PORT = settings.DASHBOARD_PORT
DASHBOARD_DEBUG = settings.DASHBOARD_DEBUG

# Интервал обновления (миллисекунды)
UPDATE_INTERVAL = settings.UPDATE_INTERVAL

# Пути к данным
DATA_DIR = settings.DATA_DIR
LOGS_DIR = settings.BASE_DIR / "logs"
BACKTEST_RESULTS_DIR = DATA_DIR / "backtest_results"

# Логирование
LOG_LEVEL = settings.LOG_LEVEL
LOG_FILE = settings.LOG_FILE

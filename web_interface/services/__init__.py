"""
Сервисы для web интерфейса.
"""

from .stream_processor import RealTimeMonitoringSystem, StreamProcessor
from .websocket_stream import PriceStreamManager, WebSocketPriceStream

try:
    from .discord_bot import TradingAlertBot, create_discord_bot

    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    TradingAlertBot = None
    create_discord_bot = None

__all__ = [
    "PriceStreamManager",
    "RealTimeMonitoringSystem",
    "StreamProcessor",
    "WebSocketPriceStream",
]

if DISCORD_AVAILABLE:
    __all__.extend(["TradingAlertBot", "create_discord_bot"])

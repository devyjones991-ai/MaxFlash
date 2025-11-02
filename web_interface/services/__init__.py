"""
Сервисы для web интерфейса.
"""
from .websocket_stream import WebSocketPriceStream, PriceStreamManager
from .stream_processor import StreamProcessor, RealTimeMonitoringSystem

try:
    from .discord_bot import TradingAlertBot, create_discord_bot
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    TradingAlertBot = None
    create_discord_bot = None

__all__ = [
    'WebSocketPriceStream',
    'PriceStreamManager',
    'StreamProcessor',
    'RealTimeMonitoringSystem',
]

if DISCORD_AVAILABLE:
    __all__.extend(['TradingAlertBot', 'create_discord_bot'])


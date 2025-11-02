"""
WebSocket streaming для real-time обновлений цен.
Интеграция из Crypto Price Monitoring System.
"""
import asyncio
import json
import logging
import websocket
import threading
from typing import Dict, Callable, Optional, List
from datetime import datetime
import ccxt
import pandas as pd

logger = logging.getLogger(__name__)


class WebSocketPriceStream:
    """
    WebSocket stream для real-time цен криптовалют.
    Поддерживает множественные подписки и callback функции.
    """
    
    def __init__(self, exchange_name: str = 'binance', api_key: Optional[str] = None, 
                 secret: Optional[str] = None):
        """
        Инициализация WebSocket stream.
        
        Args:
            exchange_name: Имя биржи (binance, bybit, okx)
            api_key: API ключ (опционально для public streams)
            secret: API секрет (опционально)
        """
        self.exchange_name = exchange_name.lower()
        self.api_key = api_key
        self.secret = secret
        self.exchange = None
        self.ws = None
        self.is_connected = False
        self.subscribers: List[str] = []  # Список торговых пар
        self.callbacks: Dict[str, List[Callable]] = {}  # Callback функции по парам
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Поддержка разных бирж
        self.exchange_configs = {
            'binance': {
                'websocket_url': 'wss://stream.binance.com:9443/ws/',
                'ticker_format': '{symbol}@ticker'
            },
            'bybit': {
                'websocket_url': 'wss://stream.bybit.com/v5/public/spot',
                'ticker_format': 'tickers.{symbol}'
            },
            'okx': {
                'websocket_url': 'wss://ws.okx.com:8443/ws/v5/public',
                'ticker_format': 'tickers.{symbol}'
            }
        }
    
    def start(self):
        """Запуск WebSocket stream в отдельном потоке."""
        if self.running:
            logger.warning("WebSocket stream уже запущен")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"WebSocket stream запущен для {self.exchange_name}")
    
    def stop(self):
        """Остановка WebSocket stream."""
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        logger.info("WebSocket stream остановлен")
    
    def subscribe(self, symbol: str, callback: Callable):
        """
        Подписка на обновления цены для торговой пары.
        
        Args:
            symbol: Торговая пара (например, 'BTC/USDT')
            callback: Функция для обработки обновлений (получает dict с данными)
        """
        normalized_symbol = symbol.replace('/', '').upper()
        
        if symbol not in self.subscribers:
            self.subscribers.append(symbol)
        
        if symbol not in self.callbacks:
            self.callbacks[symbol] = []
        
        self.callbacks[symbol].append(callback)
        logger.info(f"Подписка на {symbol} добавлена")
        
        # Перезапускаем stream если нужно добавить новые пары
        if self.running and self.is_connected:
            self._subscribe_to_symbols()
    
    def unsubscribe(self, symbol: str):
        """Отписка от обновлений для торговой пары."""
        if symbol in self.subscribers:
            self.subscribers.remove(symbol)
        if symbol in self.callbacks:
            del self.callbacks[symbol]
        logger.info(f"Отписка от {symbol}")
    
    def _run(self):
        """Основной цикл WebSocket connection."""
        if self.exchange_name == 'binance':
            self._run_binance_stream()
        else:
            # Для других бирж используем универсальный подход через CCXT
            self._run_ccxt_stream()
    
    def _run_binance_stream(self):
        """WebSocket stream для Binance."""
        try:
            # Binance комбинированный stream URL
            streams = [f"{symbol.replace('/', '').lower()}@ticker" 
                      for symbol in self.subscribers]
            stream_names = "/".join(streams)
            url = f"wss://stream.binance.com:9443/stream?streams={stream_names}"
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if 'data' in data:
                        ticker_data = data['data']
                        symbol = ticker_data['s']  # Symbol from Binance
                        # Конвертируем в формат 'BTC/USDT'
                        formatted_symbol = f"{symbol[:-4]}/{symbol[-4:]}"
                        
                        price_update = {
                            'symbol': formatted_symbol,
                            'price': float(ticker_data['c']),  # Last price
                            'volume': float(ticker_data['v']),  # Volume
                            'change_24h': float(ticker_data['P']),  # 24h change %
                            'high_24h': float(ticker_data['h']),
                            'low_24h': float(ticker_data['l']),
                            'timestamp': datetime.now().isoformat(),
                            'exchange': self.exchange_name
                        }
                        
                        # Вызываем все callbacks для этого символа
                        if formatted_symbol in self.callbacks:
                            for callback in self.callbacks[formatted_symbol]:
                                try:
                                    callback(price_update)
                                except Exception as e:
                                    logger.error(f"Ошибка в callback для {formatted_symbol}: {e}")
                
                except Exception as e:
                    logger.error(f"Ошибка обработки сообщения: {e}")
            
            def on_error(ws, error):
                logger.error(f"WebSocket ошибка: {error}")
                self.is_connected = False
            
            def on_close(ws, close_status_code, close_msg):
                logger.warning("WebSocket соединение закрыто")
                self.is_connected = False
                # Переподключение
                if self.running:
                    import time
                    time.sleep(5)
                    self._run_binance_stream()
            
            def on_open(ws):
                logger.info("WebSocket соединение открыто")
                self.is_connected = True
            
            self.ws = websocket.WebSocketApp(
                url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            self.ws.run_forever()
        
        except Exception as e:
            logger.error(f"Ошибка в Binance WebSocket stream: {e}")
            self.is_connected = False
    
    def _run_ccxt_stream(self):
        """Универсальный WebSocket через CCXT (если биржа поддерживает)."""
        try:
            # Инициализируем exchange через CCXT
            exchange_class = getattr(ccxt, self.exchange_name)
            self.exchange = exchange_class({
                'apiKey': self.api_key,
                'secret': self.secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            # Проверяем поддержку WebSocket
            if not hasattr(self.exchange, 'watch_ticker'):
                logger.warning(f"{self.exchange_name} не поддерживает WebSocket через CCXT")
                return
            
            # Асинхронный loop для watch_ticker
            async def watch_loop():
                while self.running:
                    try:
                        for symbol in self.subscribers:
                            ticker = await self.exchange.watch_ticker(symbol)
                            
                            price_update = {
                                'symbol': symbol,
                                'price': ticker.get('last', 0),
                                'volume': ticker.get('baseVolume', 0),
                                'change_24h': ticker.get('percentage', 0),
                                'high_24h': ticker.get('high', 0),
                                'low_24h': ticker.get('low', 0),
                                'timestamp': datetime.now().isoformat(),
                                'exchange': self.exchange_name
                            }
                            
                            # Вызываем callbacks
                            if symbol in self.callbacks:
                                for callback in self.callbacks[symbol]:
                                    try:
                                        callback(price_update)
                                    except Exception as e:
                                        logger.error(f"Ошибка в callback: {e}")
                        
                        await asyncio.sleep(1)
                    
                    except Exception as e:
                        logger.error(f"Ошибка в watch loop: {e}")
                        await asyncio.sleep(5)
            
            # Запускаем async loop
            asyncio.run(watch_loop())
        
        except Exception as e:
            logger.error(f"Ошибка в CCXT WebSocket stream: {e}")
            self.is_connected = False


class PriceStreamManager:
    """
    Менеджер для управления несколькими WebSocket streams.
    """
    
    def __init__(self):
        self.streams: Dict[str, WebSocketPriceStream] = {}
    
    def get_stream(self, exchange_name: str, api_key: Optional[str] = None, 
                   secret: Optional[str] = None) -> WebSocketPriceStream:
        """Получить или создать stream для биржи."""
        if exchange_name not in self.streams:
            self.streams[exchange_name] = WebSocketPriceStream(
                exchange_name=exchange_name,
                api_key=api_key,
                secret=secret
            )
            self.streams[exchange_name].start()
        
        return self.streams[exchange_name]
    
    def stop_all(self):
        """Остановить все streams."""
        for stream in self.streams.values():
            stream.stop()
        self.streams.clear()


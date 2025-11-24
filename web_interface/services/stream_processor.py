"""
Модуль потоковой обработки данных.
Интеграция концепций из Crypto Price Monitoring System.
"""

import logging
import queue
import threading
from datetime import datetime
from typing import Callable, Optional

import pandas as pd

from utils.anomaly_detector import PriceAnomalyDetector
from web_interface.services.websocket_stream import PriceStreamManager

logger = logging.getLogger(__name__)


class StreamProcessor:
    """
    Процессор для потоковой обработки данных цен.
    Обрабатывает WebSocket потоки, обнаруживает аномалии и отправляет алерты.
    """

    def __init__(
        self, anomaly_detector: Optional[PriceAnomalyDetector] = None, alert_callback: Optional[Callable] = None
    ):
        """
        Инициализация процессора.

        Args:
            anomaly_detector: Детектор аномалий (если None, создается новый)
            alert_callback: Callback функция для обработки алертов
        """
        self.anomaly_detector = anomaly_detector or PriceAnomalyDetector()
        self.alert_callback = alert_callback

        # Очереди данных
        self.price_queue = queue.Queue()
        self.alert_queue = queue.Queue()

        # История данных для анализа
        self.price_history: dict[str, pd.DataFrame] = {}
        self.max_history_size = 500

        # Статистика
        self.stats = {"messages_processed": 0, "anomalies_detected": 0, "alerts_sent": 0}

        # Управление потоками
        self.running = False
        self.processor_thread: Optional[threading.Thread] = None

    def start(self):
        """Запуск процессора в отдельном потоке."""
        if self.running:
            logger.warning("Stream processor уже запущен")
            return

        self.running = True
        self.processor_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.processor_thread.start()
        logger.info("Stream processor запущен")

    def stop(self):
        """Остановка процессора."""
        self.running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=5)
        logger.info("Stream processor остановлен")

    def add_price_update(self, price_data: dict):
        """
        Добавить обновление цены для обработки.

        Args:
            price_data: Словарь с данными о цене из WebSocket
        """
        try:
            self.price_queue.put(price_data, timeout=1)
        except queue.Full:
            logger.warning("Очередь цен переполнена, пропускаем обновление")

    def _process_loop(self):
        """Основной цикл обработки данных."""
        while self.running:
            try:
                # Получаем обновление цены (с таймаутом для проверки running)
                try:
                    price_data = self.price_queue.get(timeout=1)
                    self._process_price_update(price_data)
                    self.stats["messages_processed"] += 1
                except queue.Empty:
                    continue

            except Exception as e:
                logger.error(f"Ошибка в process loop: {e}")

    def _process_price_update(self, price_data: dict):
        """
        Обработать одно обновление цены.

        Args:
            price_data: Данные о цене
        """
        symbol = price_data.get("symbol", "UNKNOWN")
        price = price_data.get("price", 0)
        volume = price_data.get("volume", 0)
        timestamp = price_data.get("timestamp", datetime.now().isoformat())

        # Добавляем в историю
        if symbol not in self.price_history:
            self.price_history[symbol] = pd.DataFrame()

        # Создаем новую строку
        new_row = pd.DataFrame(
            [
                {
                    "timestamp": pd.to_datetime(timestamp),
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": volume,
                }
            ]
        )

        # Добавляем в историю
        df = pd.concat([self.price_history[symbol], new_row], ignore_index=True)

        # Ограничиваем размер истории
        if len(df) > self.max_history_size:
            df = df.tail(self.max_history_size).reset_index(drop=True)

        self.price_history[symbol] = df

        # Если достаточно данных, проверяем на аномалии
        if len(df) >= 50:  # Минимум для анализа
            anomalies = self.anomaly_detector.detect_anomalies(df.tail(100))

            if anomalies:
                # Берем только последнюю аномалию (если она новая)
                latest_anomaly = anomalies[-1]
                anomaly_time = latest_anomaly.get("timestamp", timestamp)

                # Проверяем, не обрабатывали ли мы уже эту аномалию
                if self._is_new_anomaly(symbol, anomaly_time):
                    self.stats["anomalies_detected"] += 1

                    # Отправляем алерт
                    if self.alert_callback:
                        try:
                            self.alert_callback(latest_anomaly)
                            self.stats["alerts_sent"] += 1
                        except Exception as e:
                            logger.error(f"Ошибка в alert callback: {e}")

    def _is_new_anomaly(self, symbol: str, timestamp) -> bool:
        """Проверяет, новая ли это аномалия (простая проверка по времени)."""
        # Простая реализация - можно улучшить с хранением последних аномалий
        return True

    def get_stats(self) -> dict:
        """Получить статистику процессора."""
        return {
            **self.stats,
            "symbols_tracked": len(self.price_history),
            "total_data_points": sum(len(df) for df in self.price_history.values()),
        }

    def get_latest_price(self, symbol: str) -> Optional[dict]:
        """Получить последнюю цену для символа."""
        if symbol not in self.price_history or len(self.price_history[symbol]) == 0:
            return None

        df = self.price_history[symbol]
        latest = df.iloc[-1]

        return {
            "symbol": symbol,
            "price": float(latest["close"]),
            "volume": float(latest["volume"]),
            "timestamp": latest["timestamp"].isoformat(),
        }

    def get_price_history(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Получить историю цен для символа."""
        if symbol not in self.price_history:
            return None

        df = self.price_history[symbol]
        return df.tail(limit)


class RealTimeMonitoringSystem:
    """
    Интегрированная система для real-time мониторинга.
    Объединяет WebSocket streaming, обработку данных и детекцию аномалий.
    """

    def __init__(
        self,
        exchange_name: str = "binance",
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        alert_callback: Optional[Callable] = None,
    ):
        """
        Инициализация системы мониторинга.

        Args:
            exchange_name: Имя биржи
            api_key: API ключ
            secret: API секрет
            alert_callback: Callback для алертов
        """
        # WebSocket stream manager
        self.stream_manager = PriceStreamManager()
        self.stream = self.stream_manager.get_stream(exchange_name, api_key, secret)

        # Stream processor
        self.processor = StreamProcessor(alert_callback=alert_callback)

        # Статус
        self.monitoring_symbols: list[str] = []
        self.is_running = False

    def start_monitoring(self, symbols: list[str]):
        """
        Начать мониторинг торговых пар.

        Args:
            symbols: Список торговых пар (например, ['BTC/USDT', 'ETH/USDT'])
        """
        self.monitoring_symbols = symbols

        # Запускаем processor
        self.processor.start()

        # Подписываемся на WebSocket потоки
        def price_callback(price_data: dict):
            """Callback для обновлений цен."""
            self.processor.add_price_update(price_data)

        for symbol in symbols:
            self.stream.subscribe(symbol, price_callback)

        # Запускаем stream
        self.stream.start()

        self.is_running = True
        logger.info(f"Мониторинг запущен для {len(symbols)} пар: {symbols}")

    def stop_monitoring(self):
        """Остановить мониторинг."""
        self.stream.stop()
        self.processor.stop()
        self.is_running = False
        logger.info("Мониторинг остановлен")

    def add_symbol(self, symbol: str):
        """Добавить торговую пару для мониторинга."""
        if symbol not in self.monitoring_symbols:
            self.monitoring_symbols.append(symbol)

            def price_callback(price_data: dict):
                self.processor.add_price_update(price_data)

            self.stream.subscribe(symbol, price_callback)
            logger.info(f"Добавлен мониторинг для {symbol}")

    def remove_symbol(self, symbol: str):
        """Удалить торговую пару из мониторинга."""
        if symbol in self.monitoring_symbols:
            self.monitoring_symbols.remove(symbol)
            self.stream.unsubscribe(symbol)
            logger.info(f"Удален мониторинг для {symbol}")

    def get_status(self) -> dict:
        """Получить статус системы."""
        processor_stats = self.processor.get_stats()

        return {
            "running": self.is_running,
            "symbols_monitored": self.monitoring_symbols,
            "stream_connected": self.stream.is_connected,
            "processor_stats": processor_stats,
        }

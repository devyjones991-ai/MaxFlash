"""
Система алертов для рыночных событий.
Отслеживание значительных изменений цен, объемов, прорывов уровней.
"""
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from collections import defaultdict
import threading

from utils.logger_config import setup_logging
from utils.market_data_manager import MarketDataManager

logger = setup_logging()


class MarketAlert:
    """Класс для представления алерта."""

    def __init__(
        self,
        symbol: str,
        alert_type: str,
        message: str,
        severity: str = 'info',
        timestamp: Optional[datetime] = None
    ):
        """
        Инициализация алерта.

        Args:
            symbol: Торговая пара
            alert_type: Тип алерта (price_spike, volume_surge, breakout, etc.)
            message: Сообщение алерта
            severity: Уровень важности (info, warning, critical)
            timestamp: Время создания алерта
        """
        self.symbol = symbol
        self.alert_type = alert_type
        self.message = message
        self.severity = severity
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать алерт в словарь."""
        return {
            'symbol': self.symbol,
            'type': self.alert_type,
            'message': self.message,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat()
        }


class MarketAlerts:
    """
    Система алертов для отслеживания рыночных событий.
    """

    def __init__(self, data_manager: Optional[MarketDataManager] = None):
        """
        Инициализация системы алертов.

        Args:
            data_manager: Менеджер данных рынка
        """
        self.data_manager = data_manager or MarketDataManager()
        self.alerts: List[MarketAlert] = []
        self.alert_callbacks: List[Callable[[MarketAlert], None]] = []
        self.price_history: Dict[str, List[float]] = defaultdict(list)
        self.volume_history: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        
        # Пороги для алертов
        self.thresholds = {
            'price_change_percent': 5.0,  # 5% изменение цены
            'volume_surge_multiplier': 2.0,  # Увеличение объема в 2 раза
            'breakout_percent': 2.0,  # Прорыв уровня на 2%
        }

    def add_callback(self, callback: Callable[[MarketAlert], None]):
        """
        Добавить callback для обработки алертов.

        Args:
            callback: Функция для обработки алерта
        """
        self.alert_callbacks.append(callback)

    def _trigger_alert(self, alert: MarketAlert):
        """Вызвать все callbacks для алерта."""
        with self.lock:
            self.alerts.append(alert)
            # Храним только последние 1000 алертов
            if len(self.alerts) > 1000:
                self.alerts = self.alerts[-1000:]

        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error("Alert callback error: %s", str(e))

    def check_price_spike(self, symbol: str, current_price: float, previous_price: float):
        """
        Проверить резкое изменение цены.

        Args:
            symbol: Торговая пара
            current_price: Текущая цена
            previous_price: Предыдущая цена
        """
        if previous_price == 0:
            return

        change_percent = abs((current_price - previous_price) / previous_price) * 100
        
        if change_percent >= self.thresholds['price_change_percent']:
            direction = "вверх" if current_price > previous_price else "вниз"
            severity = 'critical' if change_percent >= 10 else 'warning'
            
            alert = MarketAlert(
                symbol=symbol,
                alert_type='price_spike',
                message=f"Резкое движение цены {direction} на {change_percent:.2f}%",
                severity=severity
            )
            self._trigger_alert(alert)

    def check_volume_surge(self, symbol: str, current_volume: float, avg_volume: float):
        """
        Проверить всплеск объема.

        Args:
            symbol: Торговая пара
            current_volume: Текущий объем
            avg_volume: Средний объем
        """
        if avg_volume == 0:
            return

        surge_multiplier = current_volume / avg_volume
        
        if surge_multiplier >= self.thresholds['volume_surge_multiplier']:
            alert = MarketAlert(
                symbol=symbol,
                alert_type='volume_surge',
                message=f"Всплеск объема: {surge_multiplier:.1f}x среднего",
                severity='warning'
            )
            self._trigger_alert(alert)

    def check_breakout(self, symbol: str, current_price: float, resistance: float, support: float):
        """
        Проверить прорыв уровня поддержки/сопротивления.

        Args:
            symbol: Торговая пара
            current_price: Текущая цена
            resistance: Уровень сопротивления
            support: Уровень поддержки
        """
        if current_price > resistance:
            breakout_percent = ((current_price - resistance) / resistance) * 100
            if breakout_percent >= self.thresholds['breakout_percent']:
                alert = MarketAlert(
                    symbol=symbol,
                    alert_type='breakout',
                    message=f"Прорыв сопротивления на {breakout_percent:.2f}%",
                    severity='warning'
                )
                self._trigger_alert(alert)
        
        elif current_price < support:
            breakdown_percent = ((support - current_price) / support) * 100
            if breakdown_percent >= self.thresholds['breakout_percent']:
                alert = MarketAlert(
                    symbol=symbol,
                    alert_type='breakdown',
                    message=f"Прорыв поддержки на {breakdown_percent:.2f}%",
                    severity='warning'
                )
                self._trigger_alert(alert)

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получить последние алерты.

        Args:
            limit: Количество алертов

        Returns:
            Список алертов в виде словарей
        """
        with self.lock:
            recent = self.alerts[-limit:]
            return [alert.to_dict() for alert in recent]

    def get_alerts_by_symbol(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Получить алерты для конкретной пары.

        Args:
            symbol: Торговая пара
            limit: Количество алертов

        Returns:
            Список алертов
        """
        with self.lock:
            symbol_alerts = [a for a in self.alerts if a.symbol == symbol]
            recent = symbol_alerts[-limit:]
            return [alert.to_dict() for alert in recent]


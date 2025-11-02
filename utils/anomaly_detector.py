"""
Anomaly Detection для выявления аномальных движений цен.
Интеграция концепций из Crypto Price Monitoring System.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PriceAnomalyDetector:
    """
    Детектор аномалий в движении цен.
    Использует Z-score анализ, процентные изменения и паттерн-распознавание.
    """
    
    def __init__(self, 
                 z_score_threshold: float = 3.0,
                 price_change_threshold: float = 5.0,
                 volume_spike_threshold: float = 2.0,
                 window_size: int = 100):
        """
        Инициализация детектора.
        
        Args:
            z_score_threshold: Порог для Z-score детекции (стандартные отклонения)
            price_change_threshold: Порог процентного изменения цены (%)
            volume_spike_threshold: Порог для всплеска объема (кратность среднего)
            window_size: Размер окна для статистического анализа
        """
        self.z_score_threshold = z_score_threshold
        self.price_change_threshold = price_change_threshold
        self.volume_spike_threshold = volume_spike_threshold
        self.window_size = window_size
    
    def detect_anomalies(self, dataframe: pd.DataFrame) -> List[Dict]:
        """
        Обнаруживает аномалии в данных цен.
        
        Args:
            dataframe: DataFrame с колонками ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            
        Returns:
            Список словарей с информацией об аномалиях
        """
        if len(dataframe) < self.window_size:
            logger.warning(f"Недостаточно данных для анализа (нужно минимум {self.window_size})")
            return []
        
        anomalies = []
        
        # Z-score анализ
        z_score_anomalies = self._detect_z_score_anomalies(dataframe)
        anomalies.extend(z_score_anomalies)
        
        # Анализ процентных изменений
        price_change_anomalies = self._detect_price_change_anomalies(dataframe)
        anomalies.extend(price_change_anomalies)
        
        # Анализ всплесков объема
        volume_anomalies = self._detect_volume_spikes(dataframe)
        anomalies.extend(volume_anomalies)
        
        # Паттерн-распознавание (резкие движения)
        pattern_anomalies = self._detect_price_spikes(dataframe)
        anomalies.extend(pattern_anomalies)
        
        # Сортируем по времени
        anomalies.sort(key=lambda x: x.get('timestamp', datetime.now()))
        
        return anomalies
    
    def _detect_z_score_anomalies(self, dataframe: pd.DataFrame) -> List[Dict]:
        """Z-score анализ для выявления статистических аномалий."""
        anomalies = []
        
        # Рассчитываем изменения цены
        dataframe = dataframe.copy()
        dataframe['price_change'] = dataframe['close'].pct_change() * 100
        
        # Используем скользящее окно для расчета статистики
        dataframe['mean_change'] = dataframe['price_change'].rolling(
            window=self.window_size, min_periods=1
        ).mean()
        dataframe['std_change'] = dataframe['price_change'].rolling(
            window=self.window_size, min_periods=1
        ).std()
        
        # Рассчитываем Z-score
        dataframe['z_score'] = (dataframe['price_change'] - dataframe['mean_change']) / (
            dataframe['std_change'] + 1e-10  # Избегаем деления на 0
        )
        
        # Находим аномалии
        mask = abs(dataframe['z_score']) > self.z_score_threshold
        anomalous_rows = dataframe[mask]
        
        for idx, row in anomalous_rows.iterrows():
            anomalies.append({
                'type': 'z_score_anomaly',
                'timestamp': row.get('timestamp', idx),
                'z_score': float(row['z_score']),
                'price_change': float(row['price_change']),
                'price': float(row['close']),
                'severity': 'high' if abs(row['z_score']) > 4.0 else 'medium',
                'message': f"Z-score аномалия: {row['z_score']:.2f} стандартных отклонений"
            })
        
        return anomalies
    
    def _detect_price_change_anomalies(self, dataframe: pd.DataFrame) -> List[Dict]:
        """Детекция аномалий на основе процентного изменения цены."""
        anomalies = []
        
        dataframe = dataframe.copy()
        
        # Рассчитываем процентные изменения
        dataframe['price_change_pct'] = dataframe['close'].pct_change() * 100
        
        # Находим резкие изменения
        mask = abs(dataframe['price_change_pct']) > self.price_change_threshold
        anomalous_rows = dataframe[mask]
        
        for idx, row in anomalous_rows.iterrows():
            direction = 'up' if row['price_change_pct'] > 0 else 'down'
            anomalies.append({
                'type': 'price_change_anomaly',
                'timestamp': row.get('timestamp', idx),
                'price_change': float(row['price_change_pct']),
                'price': float(row['close']),
                'direction': direction,
                'severity': 'high' if abs(row['price_change_pct']) > 10.0 else 'medium',
                'message': f"Резкое движение цены: {row['price_change_pct']:.2f}%"
            })
        
        return anomalies
    
    def _detect_volume_spikes(self, dataframe: pd.DataFrame) -> List[Dict]:
        """Детекция всплесков объема торгов."""
        anomalies = []
        
        dataframe = dataframe.copy()
        
        # Рассчитываем средний объем за окно
        dataframe['avg_volume'] = dataframe['volume'].rolling(
            window=self.window_size, min_periods=1
        ).mean()
        
        # Находим всплески
        dataframe['volume_ratio'] = dataframe['volume'] / (dataframe['avg_volume'] + 1e-10)
        mask = dataframe['volume_ratio'] > self.volume_spike_threshold
        spike_rows = dataframe[mask]
        
        for idx, row in spike_rows.iterrows():
            anomalies.append({
                'type': 'volume_spike',
                'timestamp': row.get('timestamp', idx),
                'volume': float(row['volume']),
                'avg_volume': float(row['avg_volume']),
                'volume_ratio': float(row['volume_ratio']),
                'price': float(row['close']),
                'severity': 'high' if row['volume_ratio'] > 3.0 else 'medium',
                'message': f"Всплеск объема: {row['volume_ratio']:.2f}x среднего"
            })
        
        return anomalies
    
    def _detect_price_spikes(self, dataframe: pd.DataFrame) -> List[Dict]:
        """Детекция резких ценовых движений (паттерн-распознавание)."""
        anomalies = []
        
        dataframe = dataframe.copy()
        
        # Рассчитываем волатильность
        dataframe['high_low_range'] = ((dataframe['high'] - dataframe['low']) / 
                                       dataframe['close']) * 100
        dataframe['avg_range'] = dataframe['high_low_range'].rolling(
            window=self.window_size, min_periods=1
        ).mean()
        
        # Находим свечи с аномально большим диапазоном
        mask = dataframe['high_low_range'] > dataframe['avg_range'] * 2
        spike_rows = dataframe[mask]
        
        for idx, row in spike_rows.iterrows():
            anomalies.append({
                'type': 'price_spike',
                'timestamp': row.get('timestamp', idx),
                'range_pct': float(row['high_low_range']),
                'avg_range_pct': float(row['avg_range']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'severity': 'high' if row['high_low_range'] > row['avg_range'] * 3 else 'medium',
                'message': f"Резкое ценовое движение: диапазон {row['high_low_range']:.2f}%"
            })
        
        return anomalies
    
    def get_anomaly_summary(self, dataframe: pd.DataFrame) -> Dict:
        """
        Получить сводку по аномалиям.
        
        Returns:
            Словарь со статистикой аномалий
        """
        anomalies = self.detect_anomalies(dataframe)
        
        if not anomalies:
            return {
                'total_anomalies': 0,
                'high_severity': 0,
                'medium_severity': 0,
                'by_type': {}
            }
        
        summary = {
            'total_anomalies': len(anomalies),
            'high_severity': sum(1 for a in anomalies if a.get('severity') == 'high'),
            'medium_severity': sum(1 for a in anomalies if a.get('severity') == 'medium'),
            'by_type': {}
        }
        
        # Группируем по типам
        for anomaly in anomalies:
            anomaly_type = anomaly.get('type', 'unknown')
            if anomaly_type not in summary['by_type']:
                summary['by_type'][anomaly_type] = 0
            summary['by_type'][anomaly_type] += 1
        
        return summary


class AnomalyAlert:
    """Класс для форматирования алертов об аномалиях."""
    
    @staticmethod
    def format_alert(anomaly: Dict) -> str:
        """Форматирует аномалию в читаемый алерт."""
        anomaly_type = anomaly.get('type', 'unknown')
        timestamp = anomaly.get('timestamp', 'N/A')
        message = anomaly.get('message', 'Anomaly detected')
        severity = anomaly.get('severity', 'medium')
        
        emoji = '🔥' if severity == 'high' else '⚠️'
        
        return f"{emoji} {anomaly_type.upper()} [{timestamp}]: {message}"


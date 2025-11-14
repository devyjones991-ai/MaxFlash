"""
Аналитика рынка: корреляции, тренды, возможности.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging

from utils.logger_config import setup_logging
from utils.market_data_manager import MarketDataManager
from config.market_config import CORRELATION_CONFIG

logger = setup_logging()


class MarketAnalytics:
    """
    Класс для расчета корреляций, выявления трендов и поиска возможностей.
    """

    def __init__(self, data_manager: Optional[MarketDataManager] = None):
        """
        Инициализация аналитики.

        Args:
            data_manager: Менеджер данных рынка
        """
        self.data_manager = data_manager or MarketDataManager()
        self.correlation_cache: Dict[str, pd.DataFrame] = {}
        self.trends_cache: Dict[str, Dict] = {}

    def calculate_correlations(
        self, pairs: List[str], timeframe: str = '1h',
        period_days: int = 30, exchange_id: str = 'binance'
    ) -> pd.DataFrame:
        """
        Рассчитать корреляционную матрицу между парами.

        Args:
            pairs: Список торговых пар
            timeframe: Таймфрейм для анализа
            period_days: Период анализа в днях
            exchange_id: Идентификатор биржи

        Returns:
            DataFrame с корреляционной матрицей
        """
        cache_key = f"{timeframe}:{period_days}:{','.join(sorted(pairs))}"
        if cache_key in self.correlation_cache:
            return self.correlation_cache[cache_key]

        # Загружаем данные для всех пар
        price_data = {}
        limit = int(period_days * 24 / self._timeframe_to_hours(timeframe))

        for pair in pairs:
            try:
                df = self.data_manager.get_ohlcv(
                    pair, timeframe, limit, exchange_id
                )
                if df is not None and len(df) >= CORRELATION_CONFIG['min_data_points']:
                    price_data[pair] = df['close']
            except Exception as e:
                logger.warning(
                    "Ошибка загрузки данных для %s: %s",
                    pair, str(e)
                )

        if len(price_data) < 2:
            logger.warning("Недостаточно данных для расчета корреляций")
            return pd.DataFrame()

        # Создаем DataFrame с ценами
        prices_df = pd.DataFrame(price_data)

        # Рассчитываем процентные изменения
        returns_df = prices_df.pct_change().dropna()

        # Рассчитываем корреляционную матрицу
        correlation_matrix = returns_df.corr()

        # Кэшируем результат
        self.correlation_cache[cache_key] = correlation_matrix

        logger.info(
            "Рассчитана корреляционная матрица для %s пар",
            len(pairs)
        )
        return correlation_matrix

    def detect_trends(
        self, pair: str, timeframe: str = '4h',
        period_days: int = 7, exchange_id: str = 'binance'
    ) -> Dict[str, Any]:
        """
        Выявить тренд для торговой пары.

        Args:
            pair: Торговая пара
            timeframe: Таймфрейм для анализа
            period_days: Период анализа в днях
            exchange_id: Идентификатор биржи

        Returns:
            Словарь с информацией о тренде
        """
        cache_key = f"trend:{pair}:{timeframe}:{period_days}"
        if cache_key in self.trends_cache:
            return self.trends_cache[cache_key]

        try:
            limit = int(period_days * 24 / self._timeframe_to_hours(timeframe))
            df = self.data_manager.get_ohlcv(
                pair, timeframe, limit, exchange_id
            )

            if df is None or len(df) < 20:
                return {'trend': 'unknown', 'strength': 0}

            # Рассчитываем индикаторы тренда
            closes = df['close'].values
            highs = df['high'].values
            lows = df['low'].values

            # SMA для определения тренда
            sma_short = pd.Series(closes).rolling(window=10).mean()
            sma_long = pd.Series(closes).rolling(window=20).mean()

            # Процентное изменение за период
            price_change = ((closes[-1] - closes[0]) / closes[0]) * 100

            # Волатильность
            volatility = np.std(closes) / np.mean(closes) * 100

            # Определяем тренд
            if sma_short.iloc[-1] > sma_long.iloc[-1] and price_change > 2:
                trend = 'bullish'
                strength = min(abs(price_change) / 10, 1.0)
            elif sma_short.iloc[-1] < sma_long.iloc[-1] and price_change < -2:
                trend = 'bearish'
                strength = min(abs(price_change) / 10, 1.0)
            else:
                trend = 'sideways'
                strength = 0.3

            result = {
                'trend': trend,
                'strength': strength,
                'price_change_24h': price_change,
                'volatility': volatility,
                'current_price': closes[-1],
                'sma_short': sma_short.iloc[-1],
                'sma_long': sma_long.iloc[-1]
            }

            self.trends_cache[cache_key] = result
            return result

        except Exception as e:
            logger.error("Ошибка определения тренда для %s: %s", pair, str(e))
            return {'trend': 'unknown', 'strength': 0}

    def find_opportunities(
        self, pairs: Optional[List[str]] = None,
        min_correlation: float = 0.7, exchange_id: str = 'binance'
    ) -> List[Dict[str, Any]]:
        """
        Найти торговые возможности на основе корреляций и трендов.

        Args:
            pairs: Список пар для анализа (None для популярных)
            min_correlation: Минимальная корреляция для анализа
            exchange_id: Идентификатор биржи

        Returns:
            Список возможностей с описанием
        """
        if pairs is None:
            from config.market_config import POPULAR_PAIRS
            pairs = POPULAR_PAIRS[:50]  # Ограничиваем для производительности

        opportunities = []

        try:
            # Рассчитываем корреляции
            correlation_matrix = self.calculate_correlations(
                pairs, timeframe='4h', period_days=7, exchange_id=exchange_id
            )

            if correlation_matrix.empty:
                return opportunities

            # Определяем тренды для всех пар
            trends = {}
            for pair in pairs:
                trend_info = self.detect_trends(
                    pair, timeframe='4h', period_days=7,
                    exchange_id=exchange_id
                )
                trends[pair] = trend_info

            # Ищем возможности
            for i, pair1 in enumerate(pairs):
                trend1 = trends.get(pair1, {})
                if trend1.get('trend') == 'unknown':
                    continue

                for pair2 in pairs[i+1:]:
                    if pair1 == pair2:
                        continue

                    # Проверяем корреляцию
                    if (pair1 in correlation_matrix.index and
                            pair2 in correlation_matrix.columns):
                        corr = correlation_matrix.loc[pair1, pair2]
                        if abs(corr) < min_correlation:
                            continue

                        trend2 = trends.get(pair2, {})
                        if trend2.get('trend') == 'unknown':
                            continue

                        # Ищем расхождения в трендах при высокой корреляции
                        if (abs(corr) > min_correlation and
                                trend1['trend'] != trend2['trend']):
                            opportunities.append({
                                'type': 'divergence',
                                'pair1': pair1,
                                'pair2': pair2,
                                'correlation': corr,
                                'trend1': trend1['trend'],
                                'trend2': trend2['trend'],
                                'description': (
                                    f"{pair1} ({trend1['trend']}) и "
                                    f"{pair2} ({trend2['trend']}) "
                                    f"имеют высокую корреляцию ({corr:.2f}) "
                                    f"но разные тренды"
                                )
                            })

                        # Ищем сильные тренды с высокой корреляцией
                        if (abs(corr) > min_correlation and
                                trend1['trend'] == trend2['trend'] and
                                trend1['strength'] > 0.7):
                            opportunities.append({
                                'type': 'strong_trend',
                                'pair1': pair1,
                                'pair2': pair2,
                                'correlation': corr,
                                'trend': trend1['trend'],
                                'strength': trend1['strength'],
                                'description': (
                                    f"Сильный {trend1['trend']} тренд "
                                    f"в {pair1} и {pair2} "
                                    f"(корреляция: {corr:.2f})"
                                )
                            })

        except Exception as e:
            logger.error("Ошибка поиска возможностей: %s", str(e))

        return opportunities

    def get_sector_performance(
        self, sector: str, exchange_id: str = 'binance'
    ) -> Dict[str, Any]:
        """
        Получить производительность сектора.

        Args:
            sector: Название сектора
            exchange_id: Идентификатор биржи

        Returns:
            Словарь с метриками производительности сектора
        """
        from config.market_config import get_pairs_by_sector

        pairs = get_pairs_by_sector(sector)
        if not pairs:
            return {}

        # Получаем тренды для всех пар сектора
        trends = []
        for pair in pairs:
            trend_info = self.detect_trends(
                pair, timeframe='1d', period_days=7,
                exchange_id=exchange_id
            )
            if trend_info.get('trend') != 'unknown':
                trends.append({
                    'pair': pair,
                    **trend_info
                })

        if not trends:
            return {}

        # Рассчитываем метрики сектора
        bullish_count = sum(1 for t in trends if t['trend'] == 'bullish')
        bearish_count = sum(1 for t in trends if t['trend'] == 'bearish')
        avg_strength = np.mean([t['strength'] for t in trends])
        avg_change = np.mean([t.get('price_change_24h', 0) for t in trends])

        return {
            'sector': sector,
            'total_pairs': len(trends),
            'bullish_pairs': bullish_count,
            'bearish_pairs': bearish_count,
            'sideways_pairs': len(trends) - bullish_count - bearish_count,
            'avg_strength': avg_strength,
            'avg_price_change': avg_change,
            'bullish_percentage': (bullish_count / len(trends)) * 100
        }

    def _timeframe_to_hours(self, timeframe: str) -> float:
        """Конвертировать таймфрейм в часы."""
        timeframe_map = {
            '1m': 1/60,
            '5m': 5/60,
            '15m': 15/60,
            '30m': 30/60,
            '1h': 1,
            '4h': 4,
            '1d': 24,
            '1w': 168
        }
        return timeframe_map.get(timeframe, 1)


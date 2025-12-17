"""
Advanced Signal Validator

Комплексная валидация сигналов с:
1. Обнаружением противоречий между индикаторами (RSI, MACD, цена)
2. Статистической валидацией на основе исторических паттернов
3. Правильной дедупликацией сигналов (избежание дублей в окне времени)
4. Детальным логированием каждого решения для отладки

Использование:
    validator = AdvancedSignalValidator(duplicate_window_minutes=15)
    result = validator.validate(
        symbol="BTC/USDT",
        signal_direction="BUY",
        confidence=70,
        rsi=45,
        macd_histogram=-0.001,
        price_change_24h=-2.0,
        volume_ratio=1.2
    )
    
    if result.is_valid:
        signal = result.signal
        confidence = result.confidence
    else:
        print(f"Отклонен: {result.contradictions}")
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Результат валидации сигнала."""
    signal: Optional[str]  # "BUY", "SELL", "HOLD", или None (rejected)
    confidence: float
    is_valid: bool
    issues: List[str]
    contradictions: List[str]
    was_duplicate: bool
    validation_log: List[str]
    stats_confidence_adjustment: float = 0.0


class AdvancedSignalValidator:
    """
    Продвинутый валидатор сигналов с:
    - Обнаружением противоречий между индикаторами
    - Статистической валидацией на основе исторических данных
    - Дедупликацией сигналов (избежание дублей)
    - Детальным логированием каждого решения
    """
    
    def __init__(self, duplicate_window_minutes: int = 15):
        """
        Инициализация валидатора.
        
        Args:
            duplicate_window_minutes: Окно времени для дедупликации (минуты)
        """
        self.duplicate_window_minutes = duplicate_window_minutes
        
        # Хранилище последних сигналов для дедупликации
        # Формат: {symbol: [(signal, timestamp, confidence), ...]}
        self.recent_signals: Dict[str, List[Tuple[str, datetime, float]]] = defaultdict(list)
        
        # Статистика для валидации (можно расширить)
        self.validation_stats = {
            'total_validated': 0,
            'rejected_contradictions': 0,
            'rejected_duplicates': 0,
            'adjusted_confidence': 0,
        }
    
    def validate(
        self,
        symbol: str,
        signal_direction: str,
        confidence: float,
        rsi: float,
        macd_histogram: float,
        price_change_24h: float,
        volume_ratio: float = 1.0,
        macd_line: float = 0.0,
        signal_line: float = 0.0,
        reasons: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Комплексная валидация сигнала.
        
        Returns:
            ValidationResult с полной информацией о валидации
        """
        validation_log = []
        issues = []
        contradictions = []
        final_signal = signal_direction
        final_confidence = confidence
        stats_adjustment = 0.0
        
        validation_log.append(f"[{symbol}] Начало валидации: {signal_direction} (conf={confidence:.1f}%)")
        
        # Если уже HOLD, пропускаем
        if signal_direction == "HOLD":
            validation_log.append(f"[{symbol}] HOLD сигнал - пропуск валидации")
            return ValidationResult(
                signal="HOLD",
                confidence=confidence,
                is_valid=True,
                issues=[],
                contradictions=[],
                was_duplicate=False,
                validation_log=validation_log,
                stats_confidence_adjustment=0.0
            )
        
        # === 1. ОБНАРУЖЕНИЕ ПРОТИВОРЕЧИЙ ===
        contradictions_found = self._detect_contradictions(
            signal_direction, rsi, macd_histogram, macd_line, signal_line,
            price_change_24h, validation_log
        )
        
        if contradictions_found:
            contradictions.extend(contradictions_found)
            validation_log.append(f"[{symbol}] 🚫 Обнаружены противоречия: {len(contradictions_found)}")
            
            # Критические противоречия - отклоняем сигнал
            if self._has_critical_contradiction(contradictions_found):
                validation_log.append(f"[{symbol}] ❌ КРИТИЧЕСКОЕ противоречие - сигнал отклонен")
                self.validation_stats['rejected_contradictions'] += 1
                
                return ValidationResult(
                    signal=None,  # Отклонен
                    confidence=0,
                    is_valid=False,
                    issues=issues,
                    contradictions=contradictions_found,
                    was_duplicate=False,
                    validation_log=validation_log,
                    stats_confidence_adjustment=0.0
                )
            
            # Не критические - снижаем confidence
            penalty = len(contradictions_found) * 15
            final_confidence = max(0, final_confidence - penalty)
            validation_log.append(f"[{symbol}] ⚠️ Штраф за противоречия: -{penalty}% → {final_confidence:.1f}%")
        
        # === 2. СТАТИСТИЧЕСКАЯ ВАЛИДАЦИЯ ===
        stats_result = self._statistical_validation(
            symbol, signal_direction, rsi, macd_histogram, price_change_24h,
            final_confidence, validation_log
        )
        
        if stats_result:
            stats_adjustment = stats_result.get('adjustment', 0.0)
            final_confidence = max(0, min(100, final_confidence + stats_adjustment))
            if stats_result.get('issues'):
                issues.extend(stats_result['issues'])
            validation_log.append(f"[{symbol}] 📊 Статистическая валидация: {stats_adjustment:+.1f}% → {final_confidence:.1f}%")
        
        # === 3. ДЕДУПЛИКАЦИЯ ===
        is_duplicate, duplicate_info = self._check_duplicate(symbol, signal_direction, final_confidence)
        
        if is_duplicate:
            self.validation_stats['rejected_duplicates'] += 1
            validation_log.append(f"[{symbol}] 🔄 ДУБЛИКАТ обнаружен: {duplicate_info}")
            validation_log.append(f"[{symbol}] ❌ Сигнал отклонен как дубликат")
            
            return ValidationResult(
                signal=None,  # Отклонен
                confidence=0,
                is_valid=False,
                issues=issues,
                contradictions=contradictions,
                was_duplicate=True,
                validation_log=validation_log,
                stats_confidence_adjustment=stats_adjustment
            )
        
        # Сохраняем сигнал для дедупликации
        self._register_signal(symbol, signal_direction, final_confidence)
        
        # === 4. ФИНАЛЬНАЯ ВАЛИДАЦИЯ ===
        if final_confidence < 40:
            validation_log.append(f"[{symbol}] ⚠️ Confidence слишком низкий ({final_confidence:.1f}% < 40%) - HOLD")
            final_signal = "HOLD"
            final_confidence = 40
        
        # Обновляем статистику
        self.validation_stats['total_validated'] += 1
        if stats_adjustment != 0:
            self.validation_stats['adjusted_confidence'] += 1
        
        validation_log.append(f"[{symbol}] ✅ Валидация завершена: {final_signal} (conf={final_confidence:.1f}%)")
        
        # Логируем результат
        logger.info(
            f"Signal validated: {symbol} {final_signal} "
            f"(conf={final_confidence:.1f}%, contradictions={len(contradictions)}, duplicate={is_duplicate})"
        )
        
        return ValidationResult(
            signal=final_signal,
            confidence=final_confidence,
            is_valid=final_signal != "HOLD" and final_signal is not None,
            issues=issues,
            contradictions=contradictions,
            was_duplicate=False,
            validation_log=validation_log,
            stats_confidence_adjustment=stats_adjustment
        )
    
    def _detect_contradictions(
        self,
        signal_direction: str,
        rsi: float,
        macd_histogram: float,
        macd_line: float,
        signal_line: float,
        price_change_24h: float,
        validation_log: List[str]
    ) -> List[str]:
        """
        Обнаружение противоречий между индикаторами.
        
        Returns:
            Список описаний противоречий
        """
        contradictions = []
        
        # 1. SELL при перепроданности (RSI < 35)
        if signal_direction == "SELL" and rsi < 35:
            contradictions.append(f"🚨 SELL при перепроданности (RSI {rsi:.1f} < 35)")
            validation_log.append(f"  → Противоречие: SELL + RSI {rsi:.1f} (перепроданность)")
        
        # 2. BUY при перекупленности (RSI > 75)
        if signal_direction == "BUY" and rsi > 75:
            contradictions.append(f"🚨 BUY при перекупленности (RSI {rsi:.1f} > 75)")
            validation_log.append(f"  → Противоречие: BUY + RSI {rsi:.1f} (перекупленность)")
        
        # 3. SELL при положительном MACD (бычий тренд)
        if signal_direction == "SELL" and macd_histogram > 0.0005:
            contradictions.append(f"⚠️ SELL при бычьем MACD (hist={macd_histogram:.6f} > 0)")
            validation_log.append(f"  → Противоречие: SELL + MACD+ ({macd_histogram:.6f})")
        
        # 4. BUY при отрицательном MACD (медвежий тренд) + сильное падение
        if signal_direction == "BUY" and macd_histogram < -0.001 and price_change_24h < -5:
            contradictions.append(f"⚠️ BUY при медвежьем MACD и падении {price_change_24h:.1f}%")
            validation_log.append(f"  → Противоречие: BUY + MACD- + падение {price_change_24h:.1f}%")
        
        # 5. SELL при росте > 10% и RSI < 55 (растущий тренд)
        if signal_direction == "SELL" and price_change_24h > 10 and rsi < 55:
            contradictions.append(f"⚠️ SELL при росте {price_change_24h:.1f}% и RSI {rsi:.1f} < 55")
            validation_log.append(f"  → Противоречие: SELL + рост {price_change_24h:.1f}% + RSI {rsi:.1f}")
        
        # 6. MACD crossover противоречие
        if macd_line != 0 and signal_line != 0:
            macd_bullish = macd_line > signal_line
            macd_bearish = macd_line < signal_line
            
            if signal_direction == "SELL" and macd_bullish and macd_histogram > 0.001:
                contradictions.append(f"⚠️ SELL при бычьем MACD crossover")
                validation_log.append(f"  → Противоречие: SELL + MACD crossover бычий")
            
            if signal_direction == "BUY" and macd_bearish and macd_histogram < -0.001:
                contradictions.append(f"⚠️ BUY при медвежьем MACD crossover")
                validation_log.append(f"  → Противоречие: BUY + MACD crossover медвежий")
        
        return contradictions
    
    def _has_critical_contradiction(self, contradictions: List[str]) -> bool:
        """
        Проверка наличия критических противоречий (которые требуют отклонения сигнала).
        """
        critical_patterns = [
            "SELL при перепроданности",
            "BUY при перекупленности",
            "SELL при бычьем MACD",
        ]
        
        for contradiction in contradictions:
            for pattern in critical_patterns:
                if pattern in contradiction and "🚨" in contradiction:
                    return True
        
        return False
    
    def _statistical_validation(
        self,
        symbol: str,
        signal_direction: str,
        rsi: float,
        macd_histogram: float,
        price_change_24h: float,
        confidence: float,
        validation_log: List[str]
    ) -> Optional[Dict]:
        """
        Статистическая валидация на основе исторических паттернов.
        
        Returns:
            Dict с adjustment и issues или None
        """
        result = {'adjustment': 0.0, 'issues': []}
        
        # 1. Завышенная confidence при нейтральном RSI
        if 50 <= rsi <= 55 and confidence > 70:
            adjustment = -25  # Снижаем confidence
            result['adjustment'] += adjustment
            result['issues'].append(f"📊 Завышенная confidence ({confidence:.0f}%) при нейтральном RSI ({rsi:.1f})")
            validation_log.append(f"  → Статистика: confidence завышена при RSI {rsi:.1f}")
        
        # 2. Низкая confidence при экстремальных условиях
        if rsi < 20 and signal_direction == "BUY" and confidence < 60:
            adjustment = +15  # Повышаем confidence
            result['adjustment'] += adjustment
            result['issues'].append(f"📊 Заниженная confidence при экстремальной перепроданности")
            validation_log.append(f"  → Статистика: confidence занижена при RSI {rsi:.1f}")
        
        if rsi > 80 and signal_direction == "SELL" and confidence < 60:
            adjustment = +15
            result['adjustment'] += adjustment
            result['issues'].append(f"📊 Заниженная confidence при экстремальной перекупленности")
            validation_log.append(f"  → Статистика: confidence занижена при RSI {rsi:.1f}")
        
        # 3. MACD confirmation bonus
        if signal_direction == "BUY" and macd_histogram > 0.002:
            adjustment = +5  # Бонус за подтверждение MACD
            result['adjustment'] += adjustment
            validation_log.append(f"  → Статистика: MACD подтверждает BUY")
        
        if signal_direction == "SELL" and macd_histogram < -0.002:
            adjustment = +5
            result['adjustment'] += adjustment
            validation_log.append(f"  → Статистика: MACD подтверждает SELL")
        
        # 4. Волатильность penalty
        if abs(price_change_24h) > 20:
            adjustment = -10  # Штраф за высокую волатильность
            result['adjustment'] += adjustment
            result['issues'].append(f"📊 Высокая волатильность ({price_change_24h:+.1f}%)")
            validation_log.append(f"  → Статистика: штраф за волатильность {price_change_24h:+.1f}%")
        
        if result['adjustment'] != 0:
            return result
        
        return None
    
    def _check_duplicate(
        self,
        symbol: str,
        signal_direction: str,
        confidence: float
    ) -> Tuple[bool, str]:
        """
        Проверка на дубликат сигнала.
        
        Returns:
            (is_duplicate, info_string)
        """
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=self.duplicate_window_minutes)
        
        # Очистка старых сигналов
        if symbol in self.recent_signals:
            self.recent_signals[symbol] = [
                (s, t, c) for s, t, c in self.recent_signals[symbol]
                if t > cutoff_time
            ]
        
        # Проверка на дубликат
        recent = self.recent_signals.get(symbol, [])
        for prev_signal, prev_time, prev_conf in recent:
            # Тот же тип сигнала
            if prev_signal == signal_direction:
                time_diff = (now - prev_time).total_seconds() / 60
                
                # Если confidence близкий (разница < 10%)
                if abs(prev_conf - confidence) < 10:
                    return True, f"Дубликат {prev_signal} (conf={prev_conf:.1f}%, {time_diff:.1f} мин назад)"
        
        return False, ""
    
    def _register_signal(self, symbol: str, signal_direction: str, confidence: float):
        """Регистрация сигнала для дедупликации."""
        now = datetime.now()
        self.recent_signals[symbol].append((signal_direction, now, confidence))
        
        # Ограничение размера истории (последние 10 сигналов)
        if len(self.recent_signals[symbol]) > 10:
            self.recent_signals[symbol] = self.recent_signals[symbol][-10:]
    
    def get_stats(self) -> Dict:
        """Получить статистику валидации."""
        return {
            **self.validation_stats,
            'duplicate_window_minutes': self.duplicate_window_minutes,
            'tracked_symbols': len(self.recent_signals),
        }
    
    def clear_stats(self):
        """Очистить статистику."""
        self.validation_stats = {
            'total_validated': 0,
            'rejected_contradictions': 0,
            'rejected_duplicates': 0,
            'adjusted_confidence': 0,
        }


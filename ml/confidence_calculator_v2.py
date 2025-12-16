import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class SignalAnalysis:
    signal_direction: str  # "BUY", "SELL", "WAIT"
    confidence: float  # 0-100
    contradictions: List[str]
    should_emit: bool
    position_size_percent: float
    explanation: str

class ConfidenceCalculatorV2:
    """
    Второе поколение калькулятора уверенности с поддержкой
    статистической валидации и анализом противоречий
    """
    
    def __init__(self):
        # Базовые пороги (калибруются по историческим данным)
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.rsi_neutral_min = 45
        self.rsi_neutral_max = 55
        
        # Штрафы за противоречия (жестко закодированы по науке)
        self.penalties = {
            'critical_contradiction': 50,  # SELL при RSI < 30 или BUY при RSI > 70
            'major_contradiction': 25,     # SELL при MACD+ или BUY при MACD-
            'minor_contradiction': 15,     # Противоречие с трендом, большой скачок
            'mtf_contradiction': 10        # MTF mixed
        }
    
    def analyze_signal(
        self,
        signal_direction: str,
        rsi: float,
        macd_histogram: float,
        macd_line: float,
        signal_line: float,
        trend: str,
        price_change_24h: float,
        volume: float,
        volume_sma20: float,
        has_doji: bool = False,
        mtf_status: str = "aligned"
    ) -> SignalAnalysis:
        """
        Главный метод для анализа сигнала
        """
        
        # Шаг 1: Определить базовую уверенность по RSI
        base_confidence = self._get_base_confidence_from_rsi(rsi, signal_direction)
        
        # Шаг 2: Обнаружить противоречия
        contradictions = self._detect_contradictions(
            signal_direction, rsi, macd_histogram, trend, 
            price_change_24h, has_doji, mtf_status
        )
        
        # Шаг 3: Применить штрафы
        confidence = base_confidence
        for contradiction in contradictions:
            if 'CRITICAL' in contradiction:
                confidence -= self.penalties['critical_contradiction']
            elif 'WARNING' in contradiction:
                confidence -= self.penalties.get('major_contradiction', 15)
        
        # Шаг 4: Применить бонусы за подтверждение
        confidence += self._get_confirmation_bonus(
            signal_direction, macd_histogram, macd_line, 
            signal_line, volume, volume_sma20
        )
        
        # Шаг 5: Ограничить результат (0-100)
        confidence = max(0, min(100, confidence))
        
        # Шаг 6: Решить о выводе сигнала
        should_emit = self._should_emit_signal(confidence, contradictions)
        
        # Шаг 7: Рассчитать размер позиции
        position_size = self._get_position_size_percent(confidence)
        
        # Шаг 8: Вернуть результат
        return SignalAnalysis(
            signal_direction=signal_direction,
            confidence=confidence,
            contradictions=contradictions,
            should_emit=should_emit,
            position_size_percent=position_size,
            explanation=self._format_explanation(
                signal_direction, confidence, contradictions, should_emit
            )
        )
    
    def _get_base_confidence_from_rsi(
        self, 
        rsi: float, 
        signal_direction: str
    ) -> float:
        """
        Базовая уверенность зависит от RSI и типа сигнала
        """
        if signal_direction == "BUY":
            if rsi < 20:
                return 70  # Экстремальная перепроданность
            elif rsi < 30:
                return 60  # Сильная перепроданность
            elif rsi < 40:
                return 40  # Слабая перепроданность
            else:
                return 20  # Никакого сигнала
        
        elif signal_direction == "SELL":
            if rsi > 80:
                return 70  # Экстремальная перекупленность
            elif rsi > 70:
                return 60  # Сильная перекупленность
            elif rsi > 60:
                return 40  # Слабая перекупленность
            else:
                return 20  # Никакого сигнала
        
        return 0
    
    def _detect_contradictions(
        self, signal_direction, rsi, macd_histogram, trend,
        price_change_24h, has_doji, mtf_status
    ) -> List[str]:
        """
        Обнаруживает противоречия в сигнале
        """
        contradictions = []
        
        # Критические противоречия
        # Критические противоречия (validate_signal_logic rules)
        if signal_direction == "SELL" and rsi < 35:
            contradictions.append(f"CRITICAL: SELL при RSI {rsi:.1f} (перепроданность!)")
        
        if signal_direction == "BUY" and rsi > 75:
            contradictions.append(f"CRITICAL: BUY при RSI {rsi:.1f} (перекупленность!)")
        
        # Восстановление / Падение (Warning)
        if signal_direction == "SELL" and price_change_24h > 10 and rsi < 50:
             contradictions.append("WARNING: SELL при восстановлении +10% (RSI < 50)")

        if signal_direction == "BUY" and price_change_24h < -10 and rsi > 50:
             contradictions.append("WARNING: BUY при падении -10% (RSI > 50)")
        
        # Основные противоречия
        if signal_direction == "SELL" and macd_histogram > 0:
            contradictions.append(f"WARNING: SELL при MACD+ ({macd_histogram:.6f})")
        
        if signal_direction == "BUY" and macd_histogram < 0:
            contradictions.append(f"WARNING: BUY при MACD- ({macd_histogram:.6f})")
        
        # Противоречие с трендом
        if signal_direction == "SELL" and trend == "uptrend" and rsi < 65:
            contradictions.append("WARNING: SELL против восходящего тренда")
        
        if signal_direction == "BUY" and trend == "downtrend" and rsi > 35:
            contradictions.append("WARNING: BUY против нисходящего тренда")
        
        # Большие скачки
        if abs(price_change_24h) > 30:
            contradictions.append(f"WARNING: Большой скачок {price_change_24h:.1f}% за 24h")
        
        # Doji + нейтральный RSI
        if has_doji and self.rsi_neutral_min <= rsi <= self.rsi_neutral_max:
            contradictions.append(f"WARNING: Doji + neutral RSI {rsi:.1f} (неопределенность)")
        
        # MTF противоречие
        if mtf_status == "conflict":
            contradictions.append("WARNING: MTF conflict (противоречие на старших ТФ)")
        elif mtf_status == "mixed":
            contradictions.append("WARNING: MTF mixed (смешанная картина ТФ)")
        
        # Specific User Request: Neutral RSI Penalty for SELL
        if signal_direction == "SELL" and 45 <= rsi <= 55:
            if price_change_24h > 1:
                contradictions.append("WARNING: Neutral RSI (45-55) + Price Gain > 1% on SELL")
        
        return contradictions
    
    def _get_confirmation_bonus(
        self, signal_direction, macd_histogram, macd_line, signal_line,
        volume, volume_sma20
    ) -> float:
        """
        Рассчитывает бонусы за подтверждение сигнала
        """
        bonus = 0
        
        # Bullish/Bearish MACD cross
        if macd_line > signal_line and macd_histogram > 0:
            if signal_direction == "BUY":
                bonus += 15
        elif macd_line < signal_line and macd_histogram < 0:
            if signal_direction == "SELL":
                bonus += 15
        
        # Объем подтверждение
        if volume_sma20 > 0:
            volume_ratio = volume / volume_sma20
            if volume_ratio > 1.5:
                bonus += 10
            elif volume_ratio < 0.5:
                bonus -= 10 # Penalty for low volume
        
        return bonus
    
    def _should_emit_signal(self, confidence: float, contradictions: List[str]) -> bool:
        """
        Решает, выводить ли сигнал
        """
        # Критические противоречия = SKIP
        if any('CRITICAL' in c for c in contradictions):
            return False
        
        # < 40% = SKIP
        if confidence < 40:
            return False
        
        # 40-55% с противоречиями = SKIP
        if 40 <= confidence <= 55:
            if contradictions:
                return False
        
        # Иначе OK
        return True
    
    def _get_position_size_percent(self, confidence: float) -> float:
        """
        Рассчитывает размер позиции как % от депозита
        """
        if confidence < 40:
            return 0
        elif confidence < 55:
            return 0.5  # 0.5%
        elif confidence < 70:
            return 1.5  # 1.5%
        elif confidence < 80:
            return 2.0  # 2%
        else:
            return 3.0  # 3%
    
    def _format_explanation(
        self, signal_direction, confidence, contradictions, should_emit
    ) -> str:
        """
        Форматирует объяснение для пользователя
        """
        status = "✅ EMIT" if should_emit else "❌ SKIP"
        
        explanation = f"{status} | {signal_direction} {confidence:.0f}%"
        
        if contradictions:
            explanation += f" | Issues: {len(contradictions)}"
        
        return explanation

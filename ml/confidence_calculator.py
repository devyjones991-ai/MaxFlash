"""
Advanced Confidence Calculator for Trading Signals
Trained on historical data 2021-2025

This module provides sophisticated confidence calculation based on:
- RSI zones with multipliers
- MACD crossovers and position
- Moving average trends (EMA20, EMA50, SMA200)
- Volume confirmation
- Price action dynamics
"""

import numpy as np
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """
    New confidence calculation system based on 5-parameter analysis.
    Trained on 2021-2025 historical dataset.
    """
    
    def __init__(self):
        # Parameters optimized on historical dataset
        self.rsi_weights = {
            'extreme_oversold': {'range': (0, 20), 'weight': 35, 'multiplier': 1.3},
            'strong_oversold': {'range': (20, 30), 'weight': 30, 'multiplier': 1.2},
            'oversold': {'range': (30, 40), 'weight': 15, 'multiplier': 1.0},
            'weak_signal': {'range': (40, 50), 'weight': 0, 'multiplier': 0.8},
            'neutral': {'range': (50, 55), 'weight': -15, 'multiplier': 0.7},
            'weak_overbought': {'range': (55, 60), 'weight': -20, 'multiplier': 0.6},
            'overbought': {'range': (60, 70), 'weight': -25, 'multiplier': 0.5},
            'extreme_overbought': {'range': (70, 100), 'weight': -40, 'multiplier': 0.3}
        }
        
        self.macd_weights = {
            'bullish_cross': 20,
            'positive': 12,
            'near_zero': 0,
            'negative': -10,
            'bearish_cross': -25
        }
        
        self.ma_trend_weights = {
            'price_above_all': 15,
            'above_fast': 10,
            'at_support': 8,
            'below_ema20': -12,
            'in_downtrend': -20
        }
        
        self.volume_weights = {
            'high': 8,
            'average': 5,
            'normal': 0,
            'low': -5,
            'very_low': -15
        }
        
        self.price_action_weights = {
            'fresh_dip': 10,
            'recent_dip': 5,
            'stable': 0,
            'rising': 5,
            'strong_rally': 12
        }
    
    def calculate_signal_confidence(
        self,
        rsi: float,
        macd_value: float,
        macd_signal_line: float,
        price: float,
        ema20: float,
        ema50: float,
        sma200: float,
        volume: float,
        volume_sma20: float,
        price_change_24h: float,
        price_change_4h: float = 0,
        current_trend: str = "neutral",
        rsi_trend: str = "stable"
    ) -> Tuple[float, Dict, str]:
        """
        Calculate BUY signal confidence based on indicator complex.
        
        Returns:
            (confidence: float, details: dict, recommendation: str)
        """
        
        confidence = 50  # Base confidence 50%
        details = {}
        
        # ===== 1. RSI ANALYSIS (35% weight) =====
        rsi_weight = self._evaluate_rsi(rsi, rsi_trend)
        details['rsi'] = rsi_weight
        confidence += rsi_weight['weight']
        
        # Extreme conditions
        if rsi < 20 and current_trend == "downtrend":
            confidence *= rsi_weight['multiplier']
        elif rsi > 70 and price_change_24h > 20:
            confidence *= 0.4
        
        # ===== 2. MACD ANALYSIS (25% weight) =====
        macd_weight = self._evaluate_macd(macd_value, macd_signal_line)
        details['macd'] = macd_weight
        confidence += macd_weight['weight']
        
        # ===== 3. MOVING AVERAGES ANALYSIS (20% weight) =====
        ma_weight = self._evaluate_moving_averages(price, ema20, ema50, sma200, current_trend)
        details['moving_averages'] = ma_weight
        confidence += ma_weight['weight']
        
        # ===== 4. VOLUME ANALYSIS (10% weight) =====
        volume_weight = self._evaluate_volume(volume, volume_sma20)
        details['volume'] = volume_weight
        confidence += volume_weight['weight']
        
        # ===== 5. PRICE ACTION ANALYSIS (10% weight) =====
        price_weight = self._evaluate_price_action(price_change_24h, price_change_4h)
        details['price_action'] = price_weight
        confidence += price_weight['weight']
        
        # ===== PENALTIES AND ADJUSTMENTS =====
        
        # PENALTY: Late entry if price already pumped > 25%
        if price_change_24h > 25:
            confidence -= 25
            details['late_entry_penalty'] = -25
        
        # PENALTY: No volume confirmation
        if volume < volume_sma20 * 0.8:
            confidence -= 10
            details['low_volume_penalty'] = -10
        
        # BONUS: Extreme RSI + MACD confirmation
        if rsi < 25 and macd_weight['weight'] > 15:
            confidence += 10
            details['extreme_oversold_bonus'] = 10
        
        # PENALTY: Neutral RSI (50-55) - contradictory signal
        if 50 <= rsi <= 55 and macd_weight['weight'] < 15:
            confidence -= 20
            details['neutral_rsi_penalty'] = -20
        
        # Cap result (0-100%)
        confidence = max(0, min(100, confidence))
        
        # Generate recommendation
        recommendation = self._generate_recommendation(confidence, rsi, current_trend, details)
        
        return confidence, details, recommendation
    
    def _evaluate_rsi(self, rsi: float, rsi_trend: str) -> Dict:
        """Evaluate RSI and its trend."""
        
        for category, config in self.rsi_weights.items():
            if config['range'][0] <= rsi < config['range'][1]:
                weight = config['weight']
                
                if rsi_trend == "rising" and weight > 0:
                    weight *= 1.15
                elif rsi_trend == "falling" and weight < 0:
                    weight *= 1.2
                
                return {
                    'category': category,
                    'value': rsi,
                    'weight': weight,
                    'multiplier': config['multiplier']
                }
        
        return {'category': 'unknown', 'value': rsi, 'weight': 0, 'multiplier': 1.0}
    
    def _evaluate_macd(self, macd_value: float, signal_line: float) -> Dict:
        """Evaluate MACD position relative to signal line."""
        
        diff = macd_value - signal_line
        
        if macd_value > signal_line and diff > 0.001:
            if diff > 0.002:
                category = 'bullish_cross'
                weight = self.macd_weights['bullish_cross']
            else:
                category = 'positive'
                weight = self.macd_weights['positive']
        elif macd_value > 0:
            category = 'positive'
            weight = self.macd_weights['positive']
        elif macd_value > -0.001:
            category = 'near_zero'
            weight = self.macd_weights['near_zero']
        elif macd_value < signal_line and abs(diff) > 0.002:
            category = 'bearish_cross'
            weight = self.macd_weights['bearish_cross']
        else:
            category = 'negative'
            weight = self.macd_weights['negative']
        
        return {
            'category': category,
            'macd': macd_value,
            'signal_line': signal_line,
            'diff': diff,
            'weight': weight
        }
    
    def _evaluate_moving_averages(
        self, 
        price: float, 
        ema20: float, 
        ema50: float, 
        sma200: float,
        trend: str
    ) -> Dict:
        """Evaluate price position relative to moving averages."""
        
        if price > ema20 and ema20 > ema50 and ema50 > sma200:
            category = 'price_above_all'
            weight = self.ma_trend_weights['price_above_all']
        elif price > ema20 and price < sma200:
            category = 'above_fast'
            weight = self.ma_trend_weights['above_fast']
        elif abs(price - sma200) / sma200 < 0.01:
            category = 'at_support'
            weight = self.ma_trend_weights['at_support']
        elif price < ema20:
            category = 'below_ema20'
            weight = self.ma_trend_weights['below_ema20']
        else:
            category = 'in_downtrend'
            weight = self.ma_trend_weights['in_downtrend']
        
        if trend == "downtrend" and weight < 0:
            weight *= 1.2
        elif trend == "uptrend" and weight > 0:
            weight *= 1.15
        
        return {
            'category': category,
            'price': price,
            'ema20': ema20,
            'ema50': ema50,
            'sma200': sma200,
            'weight': weight
        }
    
    def _evaluate_volume(self, volume: float, volume_sma20: float) -> Dict:
        """Evaluate volume confirmation."""
        
        volume_ratio = volume / volume_sma20 if volume_sma20 > 0 else 0
        
        if volume_ratio > 1.5:
            category = 'high'
        elif volume_ratio > 1.2:
            category = 'average'
        elif volume_ratio > 0.8:
            category = 'normal'
        elif volume_ratio > 0.5:
            category = 'low'
        else:
            category = 'very_low'
        
        weight = self.volume_weights[category]
        
        return {
            'category': category,
            'volume': volume,
            'volume_sma20': volume_sma20,
            'ratio': volume_ratio,
            'weight': weight
        }
    
    def _evaluate_price_action(self, price_change_24h: float, price_change_4h: float) -> Dict:
        """Evaluate price dynamics (freshness of dip/rally)."""
        
        if price_change_4h < -3:
            category = 'fresh_dip'
            weight = self.price_action_weights['fresh_dip']
        elif price_change_24h < -2:
            category = 'recent_dip'
            weight = self.price_action_weights['recent_dip']
        elif -1 <= price_change_24h <= 1:
            category = 'stable'
            weight = self.price_action_weights['stable']
        elif 1 < price_change_24h < 5:
            category = 'rising'
            weight = self.price_action_weights['rising']
        else:
            category = 'strong_rally'
            weight = self.price_action_weights['strong_rally']
        
        return {
            'category': category,
            'change_24h': price_change_24h,
            'change_4h': price_change_4h,
            'weight': weight
        }
    
    def _generate_recommendation(
        self, 
        confidence: float, 
        rsi: float, 
        trend: str,
        details: Dict
    ) -> str:
        """Generate text recommendation based on analysis."""
        
        if confidence > 75:
            if rsi < 30:
                return "🟢 STRONG BUY: Extreme oversold + confirmation. High bounce potential."
            elif trend == "uptrend":
                return "🟢 BUY: Uptrend with good indicator confirmation."
            else:
                return "🟢 BUY: All indicators confirm entry."
        
        elif confidence >= 60:
            if rsi < 30:
                return "🟡 BUY (HIGH RISK): Oversold but bearish trend. Risky entry."
            else:
                return "🟡 BUY: Good signals, manage risk properly."
        
        elif confidence >= 45:
            return "🟡 SPECULATIVE BUY: Low confidence. Use small position size."
        
        elif confidence >= 30:
            return "🔴 WAIT: Too many contradictory signals. Wait for better entry."
        
        else:
            return "🔴 DON'T BUY: Indicators don't confirm entry."
    
    def get_optimal_position_size(self, confidence: float, account_balance: float, max_risk_percent: float = 1.0) -> float:
        """Recommend position size based on confidence."""
        risk_multiplier = confidence / 100
        position_size = (account_balance * max_risk_percent * risk_multiplier) / 100
        return position_size
    
    def get_optimal_stop_loss(self, confidence: float, entry_price: float) -> float:
        """Recommend SL based on confidence."""
        base_sl_percent = 2.0
        sl_percent = base_sl_percent + (confidence - 50) * 0.04
        sl_price = entry_price * (1 - sl_percent / 100)
        return sl_price


# Singleton instance
_confidence_calculator: Optional[ConfidenceCalculator] = None


def get_confidence_calculator() -> ConfidenceCalculator:
    """Get or create ConfidenceCalculator singleton."""
    global _confidence_calculator
    if _confidence_calculator is None:
        _confidence_calculator = ConfidenceCalculator()
    return _confidence_calculator

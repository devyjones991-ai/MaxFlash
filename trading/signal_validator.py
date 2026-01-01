"""
Signal Quality Validator - Validates and fixes contradictory signals.
Based on quick_start_code.md specifications.
"""

from typing import Dict, List, Tuple


class SignalQualityChecker:
    """
    Checks signals for logic consistency and FIXES contradictions.
    
    Key validations:
    - SELL at oversold (RSI < 35) -> INVERT to BUY
    - BUY at overbought (RSI > 75) -> INVERT to SELL
    - High confidence at neutral RSI (50-55) -> REDUCE
    - Very low volume -> PENALTY
    """
    
    def validate_and_fix(
        self,
        symbol: str,
        signal_direction: str,
        confidence: float,
        rsi: float,
        macd_histogram: float,
        price_change_24h: float,
        volume_ratio: float
    ) -> Dict:
        """
        Validates signal and returns FIXED result.
        
        Returns dict with:
            - symbol, original_signal, original_confidence
            - final_signal, final_confidence
            - was_inverted, issues, is_valid
        """
        
        result = {
            'symbol': symbol,
            'original_signal': signal_direction,
            'original_confidence': confidence,
            'final_signal': signal_direction,
            'final_confidence': confidence,
            'was_inverted': False,
            'issues': [],
            'is_valid': True
        }
        
        # ===== CHECK 1: SELL at oversold (RSI < 35) =====
        if signal_direction == "SELL" and rsi < 35:
            result['issues'].append(
                f"🚨 CRITICAL: SELL at RSI {rsi:.1f} (oversold)"
            )
            result['final_signal'] = "BUY"  # Invert
            result['final_confidence'] = max(confidence - 20, 30)
            result['was_inverted'] = True
            result['is_valid'] = False
        
        # ===== CHECK 2: BUY at overbought (RSI > 75) =====
        elif signal_direction == "BUY" and rsi > 75:
            result['issues'].append(
                f"🚨 CRITICAL: BUY at RSI {rsi:.1f} (overbought)"
            )
            result['final_signal'] = "SELL"  # Invert
            result['final_confidence'] = max(confidence - 20, 30)
            result['was_inverted'] = True
            result['is_valid'] = False
        
        # ===== CHECK 3: SELL with positive MACD =====
        elif signal_direction == "SELL" and macd_histogram > 0.0005:
            result['issues'].append(
                f"⚠️ CONTRADICTION: SELL with MACD+ ({macd_histogram:.6f})"
            )
            result['final_confidence'] -= 20
        
        # ===== CHECK 4: High confidence at neutral RSI =====
        elif 50 <= rsi <= 55 and confidence > 70:
            result['issues'].append(
                f"⚠️ INFLATED: {confidence:.0f}% confidence at neutral RSI {rsi:.1f}"
            )
            result['final_confidence'] = 50  # Reduce to neutral
        
        # ===== CHECK 5: Volatile drop > 30% =====
        elif price_change_24h < -30:
            result['issues'].append(
                f"🚫 REJECTED: Drop {price_change_24h:.2f}% in 24h (too volatile)"
            )
            result['final_signal'] = "WAIT"
            result['final_confidence'] = 0
            result['is_valid'] = False
        
        # ===== CHECK 6: Volume too low =====
        elif volume_ratio < 0.3:
            result['issues'].append(
                f"🚫 WARNING: Volume only {volume_ratio*100:.0f}% of average"
            )
            result['final_confidence'] = int(result['final_confidence'] * 0.5)
        
        # Cap result (0-100%)
        result['final_confidence'] = max(0, min(100, result['final_confidence']))
        
        return result


class SignalValidator:
    """
    Alternative validator with consistency checking.
    """
    
    def validate_signal_consistency(
        self,
        signal_direction: str,
        rsi: float,
        macd_histogram: float,
        price_change_24h: float,
        confidence: float
    ) -> Tuple[bool, str, float]:
        """
        Checks if signal is logically consistent.
        
        Returns: (is_valid, reason, confidence_penalty)
        """
        
        issues = []
        confidence_penalty = 0
        
        # ISSUE 1: SELL at RSI < 35
        if signal_direction == "SELL" and rsi < 35:
            issues.append(f"CRITICAL: SELL at RSI {rsi:.1f} (oversold)")
            return False, "INVERT_TO_BUY", 0
        
        # ISSUE 2: BUY at RSI > 75
        if signal_direction == "BUY" and rsi > 75:
            issues.append(f"CRITICAL: BUY at RSI {rsi:.1f} (overbought)")
            return False, "INVERT_TO_SELL", 0
        
        # ISSUE 3: SELL with positive MACD + stable/rising price
        if signal_direction == "SELL" and macd_histogram > 0 and price_change_24h > -2:
            issues.append("CONTRADICTION: SELL with MACD+ and stable/rising price")
            confidence_penalty += 20
        
        # ISSUE 4: BUY with negative MACD + strong decline > -5%
        if signal_direction == "BUY" and macd_histogram < 0 and price_change_24h < -5:
            issues.append("CONTRADICTION: BUY with MACD- and strong decline")
            confidence_penalty += 15
        
        # ISSUE 5: High confidence at neutral RSI
        if confidence > 70 and 45 <= rsi <= 55:
            issues.append(f"INFLATED: {confidence:.0f}% at neutral RSI {rsi:.1f}")
            confidence_penalty += 25
        
        # ISSUE 6: Low confidence for extreme oversold
        if confidence < 60 and rsi < 20 and signal_direction == "BUY":
            issues.append(f"UNDERVALUED: {confidence:.0f}% at extreme oversold RSI {rsi:.1f}")
            confidence_penalty = -15  # Negative penalty = bonus
        
        is_valid = len(issues) == 0
        reason = "; ".join(issues) if issues else "OK"
        
        return is_valid, reason, confidence_penalty

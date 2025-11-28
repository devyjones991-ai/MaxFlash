"""
Тесты для генератора сигналов.
"""
import pytest
from services.signals.signal_generator import SignalGenerator
from app.models.signal import SignalRating


def test_signal_rating_determination():
    """Тест определения рейтинга сигнала."""
    generator = SignalGenerator(None)  # db не нужен для этого теста
    
    # Alpha сигнал
    assert generator.determine_signal_rating(0.9) == SignalRating.ALPHA
    
    # Pro сигнал
    assert generator.determine_signal_rating(0.75) == SignalRating.PRO
    
    # Free сигнал
    assert generator.determine_signal_rating(0.5) == SignalRating.FREE


def test_signal_score_calculation():
    """Тест расчёта signal score."""
    generator = SignalGenerator(None)
    
    # Мок токена и пулов
    class MockToken:
        scam_score = 0.1
    
    class MockPool:
        liquidity_usd = 50000.0
        volume_24h_usd = 10000.0
        lp_locked = True
    
    token = MockToken()
    pools = [MockPool(), MockPool()]
    
    score = generator.calculate_signal_score(token, pools)
    
    assert 0.0 <= score <= 1.0


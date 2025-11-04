"""
Smoke тесты для проверки базовой функциональности системы.

Smoke тесты - это быстрые тесты, которые проверяют, что основные компоненты
системы могут быть импортированы и работают без критических ошибок.
"""
import pytest
import sys
from pathlib import Path

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.mark.smoke
class TestSmokeImports:
    """Проверка импортов основных модулей."""
    
    def test_import_version(self):
        """Проверка импорта модуля версии."""
        from version import get_version, get_version_info
        version = get_version()
        assert version is not None
        assert isinstance(version, str)
        assert len(version.split('.')) == 3  # Semantic versioning
        
        info = get_version_info()
        assert "version" in info
        assert "major" in info
        assert "minor" in info
        assert "patch" in info
    
    def test_import_indicators_order_blocks(self):
        """Проверка импорта Order Blocks."""
        from indicators.smart_money.order_blocks import OrderBlockDetector
        assert OrderBlockDetector is not None
    
    def test_import_indicators_fvg(self):
        """Проверка импорта Fair Value Gaps."""
        from indicators.smart_money.fair_value_gaps import FairValueGapDetector
        assert FairValueGapDetector is not None
    
    def test_import_indicators_market_structure(self):
        """Проверка импорта Market Structure."""
        from indicators.smart_money.market_structure import MarketStructureAnalyzer
        assert MarketStructureAnalyzer is not None
    
    def test_import_volume_profile(self):
        """Проверка импорта Volume Profile."""
        from indicators.volume_profile.volume_profile import VolumeProfileCalculator
        assert VolumeProfileCalculator is not None
    
    def test_import_market_profile(self):
        """Проверка импорта Market Profile."""
        from indicators.market_profile.market_profile import MarketProfileCalculator
        assert MarketProfileCalculator is not None
    
    def test_import_delta(self):
        """Проверка импорта Delta."""
        from indicators.footprint.delta import DeltaCalculator
        assert DeltaCalculator is not None
    
    def test_import_risk_manager(self):
        """Проверка импорта Risk Manager."""
        from utils.risk_manager import RiskManager
        assert RiskManager is not None
    
    def test_import_confluence(self):
        """Проверка импорта Confluence."""
        from utils.confluence import ConfluenceAnalyzer
        assert ConfluenceAnalyzer is not None
    
    def test_import_strategy(self):
        """Проверка импорта стратегии."""
        from strategies.smc_footprint_strategy import SMCFootprintStrategy
        assert SMCFootprintStrategy is not None
    
    def test_import_api_models(self):
        """Проверка импорта API моделей."""
        from api.models import (
            SignalModel,
            OrderBlockModel,
            VolumeProfileModel,
            HealthResponse
        )
        assert SignalModel is not None
        assert OrderBlockModel is not None
        assert VolumeProfileModel is not None
        assert HealthResponse is not None


@pytest.mark.smoke
class TestSmokeBasicFunctionality:
    """Проверка базовой функциональности."""
    
    def test_version_format(self):
        """Проверка формата версии."""
        from version import get_version
        version = get_version()
        parts = version.split('.')
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)
    
    def test_order_block_detector_instantiation(self):
        """Проверка создания экземпляра OrderBlockDetector."""
        from indicators.smart_money.order_blocks import OrderBlockDetector
        detector = OrderBlockDetector()
        assert detector is not None
    
    def test_risk_manager_instantiation(self):
        """Проверка создания экземпляра RiskManager."""
        from utils.risk_manager import RiskManager
        manager = RiskManager(account_balance=10000.0, risk_per_trade=0.01)
        assert manager is not None
        assert manager.account_balance == 10000.0
        assert manager.risk_per_trade == 0.01
    
    def test_confluence_analyzer_instantiation(self):
        """Проверка создания экземпляра ConfluenceAnalyzer."""
        from utils.confluence import ConfluenceAnalyzer
        analyzer = ConfluenceAnalyzer()
        assert analyzer is not None


@pytest.mark.smoke
class TestSmokeDataProcessing:
    """Проверка обработки данных."""
    
    def test_sample_dataframe_creation(self):
        """Проверка создания тестового датафрейма."""
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range('2024-01-01', periods=10, freq='15T')
        df = pd.DataFrame({
            'open': np.linspace(100, 110, 10),
            'high': np.linspace(101, 111, 10),
            'low': np.linspace(99, 109, 10),
            'close': np.linspace(100, 110, 10),
            'volume': np.random.uniform(1000, 5000, 10)
        }, index=dates)
        
        assert len(df) == 10
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
    
    def test_order_block_detection_with_sample_data(self, sample_dataframe):
        """Проверка обнаружения Order Blocks с тестовыми данными."""
        from indicators.smart_money.order_blocks import OrderBlockDetector
        
        detector = OrderBlockDetector()
        order_blocks = detector.detect(sample_dataframe)
        
        # Order blocks могут быть пустыми для тестовых данных
        assert order_blocks is not None
        assert isinstance(order_blocks, list)


@pytest.mark.smoke
class TestSmokeAPI:
    """Проверка API компонентов."""
    
    def test_api_models_validation(self):
        """Проверка валидации API моделей."""
        from api.models import HealthResponse
        from datetime import datetime
        
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            services={"test": "ok"}
        )
        
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert isinstance(health.timestamp, datetime)
    
    def test_version_in_api(self):
        """Проверка что версия доступна в API."""
        try:
            from version import get_version
            from api.main import VERSION
            
            version_from_module = get_version()
            assert VERSION == version_from_module
        except ImportError:
            # Если API не может быть импортирован, это нормально для smoke тестов
            pytest.skip("API модуль не доступен")


@pytest.mark.smoke
class TestSmokeIntegration:
    """Проверка интеграции компонентов."""
    
    def test_strategy_components_available(self):
        """Проверка что все компоненты стратегии доступны."""
        from strategies.smc_footprint_strategy import SMCFootprintStrategy
        from indicators.smart_money.order_blocks import OrderBlockDetector
        from indicators.volume_profile.volume_profile import VolumeProfileCalculator
        from utils.risk_manager import RiskManager
        
        # Все компоненты должны быть импортируемы
        assert SMCFootprintStrategy is not None
        assert OrderBlockDetector is not None
        assert VolumeProfileCalculator is not None
        assert RiskManager is not None


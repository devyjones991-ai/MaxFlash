# Руководство по тестированию

## Обзор тестов

Проект включает комплексные unit-тесты для всех основных компонентов системы.

## Структура тестов

```
tests/
├── test_order_blocks.py          # Тесты Order Blocks
├── test_fair_value_gaps.py       # Тесты Fair Value Gaps
├── test_volume_profile.py        # Тесты Volume Profile
├── test_market_profile.py        # Тесты Market Profile
├── test_delta.py                 # Тесты Delta анализа
├── test_confluence.py            # Тесты Confluence calculator
├── test_risk_manager.py          # Тесты Risk Management
├── test_market_structure.py      # Тесты Market Structure
├── conftest.py                   # Pytest fixtures
├── run_tests.py                  # Test runner
└── pytest.ini                    # Pytest configuration
```

## Установка зависимостей для тестирования

### Windows
```bash
pip install pytest pytest-cov pytest-mock
```

### Linux/Mac
```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock
```

## Запуск тестов

### Все тесты

**С использованием pytest:**
```bash
pytest tests/ -v
```

**С использованием unittest:**
```bash
python tests/run_tests.py
```

### Отдельные тестовые файлы

```bash
# Order Blocks
pytest tests/test_order_blocks.py -v

# Volume Profile
pytest tests/test_volume_profile.py -v

# Risk Manager
pytest tests/test_risk_manager.py -v
```

### С покрытием кода

```bash
pytest tests/ --cov=indicators --cov=utils --cov=strategies --cov-report=html
```

Это создаст HTML отчет в `htmlcov/index.html`.

### Только быстрые тесты

```bash
pytest tests/ -v -m "not slow"
```

## Что тестируется

### Order Blocks (`test_order_blocks.py`)
- ✅ Детекция bullish Order Blocks
- ✅ Детекция bearish Order Blocks
- ✅ Валидация Order Blocks
- ✅ Инвалидация Order Blocks
- ✅ Проверка цены в Order Block

### Fair Value Gaps (`test_fair_value_gaps.py`)
- ✅ Детекция bullish FVG
- ✅ Детекция bearish FVG
- ✅ Заполнение FVG
- ✅ Истечение срока FVG
- ✅ Классификация по силе

### Volume Profile (`test_volume_profile.py`)
- ✅ Расчет POC (Point of Control)
- ✅ Расчет Value Area (VAH/VAL)
- ✅ Детекция HVN и LVN
- ✅ Rolling period calculation
- ✅ Обработка пустых данных

### Market Profile (`test_market_profile.py`)
- ✅ Расчет Market Profile
- ✅ Value Area High/Low
- ✅ Определение market state (trending/balanced)
- ✅ Profile high/low

### Delta Analysis (`test_delta.py`)
- ✅ Расчет Delta
- ✅ Delta alignment (bullish/bearish/neutral)
- ✅ Детекция divergence
- ✅ Детекция absorption
- ✅ Delta summary

### Confluence Calculator (`test_confluence.py`)
- ✅ Поиск confluence зон
- ✅ Группировка уровней
- ✅ Проверка цены в зоне
- ✅ Минимальный threshold сигналов

### Risk Manager (`test_risk_manager.py`)
- ✅ Расчет размера позиции
- ✅ Расчет stop loss (long/short)
- ✅ Расчет take profit
- ✅ Trailing stop
- ✅ Валидация сделки
- ✅ Risk:Reward ratio

### Market Structure (`test_market_structure.py`)
- ✅ Детекция swing high/low
- ✅ Break of Structure (BOS)
- ✅ Change of Character (ChoCH)
- ✅ Определение тренда
- ✅ Зоны ликвидности

## Фикстуры (Fixtures)

В `conftest.py` определены общие фикстуры:

- `sample_dataframe`: Базовый OHLCV dataframe
- `order_block_pattern`: Данные с паттерном Order Block

Использование в тестах:

```python
def test_something(sample_dataframe):
    result = detector.detect(sample_dataframe)
    assert len(result) > 0
```

## Написание новых тестов

### Структура теста

```python
import unittest
import pandas as pd
from indicators.your_module import YourDetector

class TestYourDetector(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.detector = YourDetector()
        self.dataframe = create_sample_data()
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        result = self.detector.process(self.dataframe)
        self.assertIsNotNone(result)
```

### Best Practices

1. **Именование**: Используйте `test_` префикс для всех тестовых функций
2. **Документация**: Добавляйте docstrings к тестам
3. **Изоляция**: Каждый тест должен быть независимым
4. **Assertions**: Используйте конкретные assertions
5. **Edge cases**: Тестируйте граничные случаи

### Пример полного теста

```python
def test_order_block_detection(self):
    """Test Order Block detection with specific pattern."""
    # Arrange
    dates = pd.date_range('2024-01-01', periods=30, freq='15T')
    prices = [100] * 20  # Consolidation
    prices.extend([100 + i * 0.5 for i in range(1, 11)])  # Impulse
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p * 1.002 for p in prices],
        'low': [p * 0.998 for p in prices],
        'close': prices,
        'volume': np.ones(30) * 1000
    }, index=dates[:30])
    
    # Act
    result = self.detector.detect_order_blocks(df)
    
    # Assert
    bullish_obs = result[result['ob_type'] == 'bullish']
    self.assertGreater(len(bullish_obs.dropna()), 0)
```

## Continuous Integration

Для автоматического запуска тестов при коммитах добавьте `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/ -v --cov
```

## Troubleshooting

### Импорты не работают

Убедитесь, что проект в PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

Или используйте:

```bash
python -m pytest tests/
```

### Тесты падают из-за отсутствия Freqtrade

Стратегия имеет fallback для тестирования без Freqtrade. Если проблемы остаются, используйте моки:

```python
from unittest.mock import patch, MagicMock

@patch('freqtrade.strategy.IStrategy')
def test_strategy(mock_strategy):
    # Your test here
    pass
```

## Метрики качества

Целевые показатели:
- **Code Coverage**: > 80%
- **Test Execution Time**: < 30 секунд для всех тестов
- **Test Reliability**: 100% прохождение на CI/CD

Проверка покрытия:

```bash
pytest tests/ --cov=indicators --cov=utils --cov=strategies --cov-report=term-missing
```


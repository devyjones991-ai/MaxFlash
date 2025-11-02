# Руководство по интеграции с Freqtrade

## Шаги интеграции

### 1. Подготовка файлов

Убедитесь, что все файлы на месте:
```
MaxFlash/
├── strategies/
│   ├── smc_footprint_strategy.py
│   └── base_strategy.py
├── indicators/
│   ├── smart_money/
│   ├── volume_profile/
│   ├── market_profile/
│   └── footprint/
└── utils/
    ├── confluence.py
    ├── risk_manager.py
    └── data_fetcher.py
```

### 2. Копирование в Freqtrade

#### Windows
```batch
xcopy strategies\*.py freqtrade\user_data\strategies\ /Y
xcopy indicators freqtrade\user_data\strategies\indicators\ /E /I /Y
xcopy utils freqtrade\user_data\strategies\utils\ /E /I /Y
```

#### Linux/Mac
```bash
cp strategies/*.py freqtrade/user_data/strategies/
cp -r indicators freqtrade/user_data/strategies/
cp -r utils freqtrade/user_data/strategies/
```

### 3. Структура после копирования

```
freqtrade/user_data/strategies/
├── smc_footprint_strategy.py
├── base_strategy.py
├── indicators/
│   ├── __init__.py
│   ├── smart_money/
│   │   ├── __init__.py
│   │   ├── order_blocks.py
│   │   ├── fair_value_gaps.py
│   │   └── market_structure.py
│   ├── volume_profile/
│   │   ├── __init__.py
│   │   ├── volume_profile.py
│   │   └── value_area.py
│   ├── market_profile/
│   │   ├── __init__.py
│   │   ├── market_profile.py
│   │   ├── tpo.py
│   │   └── initial_balance.py
│   └── footprint/
│       ├── __init__.py
│       ├── footprint_chart.py
│       ├── delta.py
│       └── order_flow.py
└── utils/
    ├── __init__.py
    ├── confluence.py
    ├── risk_manager.py
    ├── data_fetcher.py
    └── backtest_analyzer.py
```

### 4. Обновление импортов

Убедитесь, что в `smc_footprint_strategy.py` импорты корректны:

```python
from strategies.base_strategy import BaseStrategy
from indicators.smart_money.order_blocks import OrderBlockDetector
# ... остальные импорты
```

### 5. Настройка конфигурации

Отредактируйте `freqtrade/user_data/config.json`:

```json
{
  "strategy": "SMCFootprintStrategy",
  "timeframe": "15m",
  "stake_currency": "USDT",
  "stake_amount": "unlimited",
  "dry_run": true,
  "dry_run_wallet": 10000,
  "max_open_trades": 3
}
```

### 6. Валидация стратегии

```bash
cd freqtrade
freqtrade test-pairlist -c user_data/config.json
freqtrade list-strategies
```

### 7. Бэктестинг

```bash
freqtrade backtesting \
    --strategy SMCFootprintStrategy \
    --timeframe 15m \
    --timerange 20240101-20240301 \
    --config user_data/config.json
```

### 8. Оптимизация (опционально)

```bash
freqtrade hyperopt \
    --strategy SMCFootprintStrategy \
    --hyperopt-loss SharpeHyperOptLoss \
    --epochs 100 \
    --spaces roi stoploss trailing
```

### 9. Paper Trading

```bash
freqtrade trade \
    --strategy SMCFootprintStrategy \
    --config user_data/config.json \
    --dry-run
```

## Проверка работоспособности

### 1. Проверка импортов

```python
# В Python shell
cd freqtrade/user_data/strategies
python -c "from smc_footprint_strategy import SMCFootprintStrategy; print('OK')"
```

### 2. Запуск тестов

```bash
cd ../../..  # Вернуться в MaxFlash
pytest tests/ -v
```

### 3. Проверка стратегии

```bash
cd freqtrade
freqtrade list-strategies
# Должна появиться SMCFootprintStrategy
```

## Troubleshooting

### Ошибка: ModuleNotFoundError

**Проблема**: Freqtrade не находит модули

**Решение**:
1. Убедитесь, что все файлы скопированы в правильные папки
2. Проверьте структуру папок
3. Убедитесь, что есть `__init__.py` в каждой папке

### Ошибка: ImportError в стратегии

**Проблема**: Стратегия не может импортировать индикаторы

**Решение**:
1. Проверьте пути импортов в `smc_footprint_strategy.py`
2. Убедитесь, что все файлы находятся в `user_data/strategies/`

### Ошибка: AttributeError при запуске

**Проблема**: Отсутствуют атрибуты или методы

**Решение**:
1. Проверьте, что используете правильную версию Freqtrade
2. Убедитесь, что `INTERFACE_VERSION = 3` в стратегии

### Стратегия не появляется в списке

**Проблема**: `freqtrade list-strategies` не показывает стратегию

**Решение**:
1. Проверьте синтаксис Python файла
2. Запустите `python -m py_compile user_data/strategies/smc_footprint_strategy.py`
3. Проверьте логи ошибок

## Оптимизация производительности

### 1. Кэширование данных

Стратегия автоматически кэширует данные multi-timeframe через Freqtrade's `@informative` декоратор.

### 2. Оптимизация параметров

Начните с оптимизации ключевых параметров:
- `risk_per_trade`: 0.01 - 0.02
- `min_confluence_signals`: 2 - 4
- `ob_impulse_threshold_pct`: 1.0 - 2.0

### 3. Мониторинг производительности

Используйте `utils/backtest_analyzer.py` для анализа результатов:

```python
from utils.backtest_analyzer import BacktestAnalyzer

analyzer = BacktestAnalyzer()
stats = analyzer.calculate_statistics(trades_df, equity_curve, returns)
analyzer.print_performance_report(stats)
```

## Следующие шаги

1. ✅ Завершите интеграцию
2. ✅ Запустите бэктестинг на исторических данных
3. ✅ Оптимизируйте параметры
4. ✅ Протестируйте на paper trading (минимум 1 месяц)
5. ✅ Анализируйте результаты и корректируйте стратегию

---

**Готово! Система интегрирована и готова к использованию.** 🚀


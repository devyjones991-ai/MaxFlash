# Быстрый старт

## Установка и настройка

### 1. Установка зависимостей

```bash
# Установить все зависимости
python scripts/setup_project.py

# Или вручную
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock
```

### 2. Настройка Freqtrade

```bash
cd freqtrade
./setup.sh -i
```

### 3. Конфигурация

Отредактируйте `config/config.json`:
- Добавьте API ключи биржи
- Настройте торговые пары
- Установите параметры риска

## Быстрый тест системы

### Запуск примеров

```bash
python scripts/quick_start.py
```

Это запустит примеры использования всех основных компонентов.

### Запуск тестов

```bash
# Все тесты
pytest tests/ -v

# Отдельный модуль
pytest tests/test_order_blocks.py -v
```

## Использование стратегии

### 1. Копирование стратегии в Freqtrade

```bash
# Копируйте стратегию в папку Freqtrade
cp strategies/smc_footprint_strategy.py freqtrade/user_data/strategies/
cp strategies/base_strategy.py freqtrade/user_data/strategies/
```

### 2. Копирование индикаторов

```bash
# Создайте папку для кастомных индикаторов
mkdir -p freqtrade/user_data/strategies/indicators

# Скопируйте индикаторы
cp -r indicators/* freqtrade/user_data/strategies/indicators/
cp -r utils freqtrade/user_data/strategies/
```

### 3. Бэктестинг

```bash
cd freqtrade
freqtrade backtesting \
    --strategy SMCFootprintStrategy \
    --timeframe 15m \
    --timerange 20240101-20240301
```

### 4. Paper Trading

```bash
cd freqtrade
freqtrade trade --strategy SMCFootprintStrategy --dry-run
```

## Примеры кода

### Использование Order Blocks

```python
from indicators.smart_money.order_blocks import OrderBlockDetector
import pandas as pd

detector = OrderBlockDetector()
df = pd.DataFrame(...)  # Ваши OHLCV данные
result = detector.detect_order_blocks(df)

# Получить активные блоки
active_blocks = detector.get_order_blocks_list()
```

### Использование Volume Profile

```python
from indicators.volume_profile.volume_profile import VolumeProfileCalculator

calculator = VolumeProfileCalculator()
df = calculator.calculate_volume_profile(dataframe)
summary = calculator.get_volume_profile_summary(df)

print(f"POC: {summary['poc']}")
print(f"VAH: {summary['vah']}")
print(f"VAL: {summary['val']}")
```

### Использование Risk Manager

```python
from utils.risk_manager import RiskManager

risk_mgr = RiskManager(risk_per_trade=0.01)
position_size = risk_mgr.calculate_position_size(
    entry_price=100,
    stop_loss_price=98,
    account_balance=10000
)
```

## Структура проекта для Freqtrade

После копирования файлов структура должна быть:

```
freqtrade/user_data/strategies/
├── smc_footprint_strategy.py
├── base_strategy.py
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

## Следующие шаги

1. ✅ Запустите тесты: `pytest tests/ -v`
2. ✅ Проверьте примеры: `python scripts/quick_start.py`
3. ✅ Настройте конфигурацию
4. ✅ Запустите бэктестинг
5. ✅ Начните paper trading
6. ✅ Оптимизируйте параметры

## Troubleshooting

### Импорты не работают

Убедитесь, что все файлы скопированы в правильные папки Freqtrade.

### Стратегия не найдена

Проверьте, что файл стратегии находится в `freqtrade/user_data/strategies/`.

### Ошибки индикаторов

Убедитесь, что все зависимости установлены: `pip install -r requirements.txt`


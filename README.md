# Integrated Crypto Trading System

Комплексная торговая система на базе Freqtrade, интегрирующая Smart Money Concepts, Footprint Analysis, Volume Profile, Market Profile и TPO в единую многоуровневую стратегию.

[![Tests](https://github.com/devyjones991-ai/MaxFlash/actions/workflows/tests.yml/badge.svg)](https://github.com/devyjones991-ai/MaxFlash/actions/workflows/tests.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## 🌟 Особенности

- **Smart Money Concepts**: Order Blocks, Fair Value Gaps, Market Structure
- **Volume Profile**: POC, HVN, LVN, Value Area расчеты
- **Market Profile & TPO**: VAH/VAL, TPO distribution, Initial Balance
- **Footprint Analysis**: Delta, Order Flow, Absorption detection
- **Top-Down Strategy**: Multi-timeframe анализ (Daily → 1H → 15min)
- **Risk Management**: Автоматический расчет позиций и stop loss
- **Полное тестирование**: ~42 unit-тестов покрывают все компоненты

## 📊 Результаты тестирования

```
✅ Order Blocks Detection: Работает
✅ Volume Profile: POC, VAH, VAL рассчитаны
✅ Footprint & Delta: Analysis корректна
✅ Market Structure: Trend detection работает
✅ Risk Management: Position sizing корректен
✅ Backtest Results:
   - Win Rate: 60%
   - Profit Factor: 3.00
   - Sharpe Ratio: 8.20
   - Total Return: 8.00%
```

## ✨ Новые возможности

- 🔴 **Real-time Monitoring** - WebSocket streaming для live обновлений цен
- 🚨 **Anomaly Detection** - Автоматическое выявление аномалий в движении цен
- 🤖 **Discord Bot** - Алерты и уведомления в Discord
- 📊 **Stream Processing** - Потоковая обработка данных в реальном времени

[Подробнее о Real-time Monitoring →](docs/REALTIME_MONITORING.md)

## 🚀 Быстрый старт

**👥 Для партнеров:** [QUICK_START_PARTNER.md](QUICK_START_PARTNER.md) - простая инструкция с настройкой API

### 1. Установка

```bash
# Клонировать репозиторий
git clone https://github.com/devyjones991-ai/MaxFlash.git
cd MaxFlash

# Установить зависимости
python scripts/setup_project.py

# Или вручную
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock ccxt cachetools
```

### 1.5. Настройка API (для реальных сигналов)

Создайте файл `.env` в корне проекта:

```env
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=ваш_api_ключ
EXCHANGE_API_SECRET=ваш_api_секрет
```

**Где получить:** [Инструкция для партнеров](QUICK_START_PARTNER.md#2️-настройка-api-обязательно-для-реальных-сигналов)

### 2. Запуск Web Dashboard (НОВОЕ! 🎉)

**Windows:**
```bash
cd web_interface
start_dashboard.bat
# Или просто дважды кликните на start_dashboard.bat
```

**Linux/Mac:**
```bash
cd web_interface
chmod +x start_dashboard.sh
./start_dashboard.sh
```

**Откройте в браузере:** http://localhost:8050

📊 Полная визуализация всех индикаторов в реальном времени!

### 3. Тестирование

```bash
# Быстрый тест
python scripts/quick_test.py

# Полный тест
python scripts/test_basic_parameters.py

# Unit-тесты
pytest tests/ -v
```

### 3. Интеграция с Freqtrade

См. [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)

```bash
# Копирование файлов в Freqtrade
cp strategies/*.py freqtrade/user_data/strategies/
cp -r indicators freqtrade/user_data/strategies/
cp -r utils freqtrade/user_data/strategies/
```

### 4. Бэктестинг

```bash
cd freqtrade
freqtrade backtesting --strategy SMCFootprintStrategy --timeframe 15m
```

## 📁 Структура проекта

```
MaxFlash/
├── strategies/          # Торговые стратегии
│   ├── smc_footprint_strategy.py  # Главная стратегия
│   └── base_strategy.py
├── indicators/          # 13 индикаторных модулей
│   ├── smart_money/     # Order Blocks, FVG, Market Structure
│   ├── volume_profile/  # POC, HVN, LVN, Value Area
│   ├── market_profile/  # Market Profile, TPO
│   └── footprint/      # Footprint, Delta, Order Flow
├── utils/               # Утилиты
│   ├── confluence.py
│   ├── risk_manager.py
│   ├── data_fetcher.py
│   └── backtest_analyzer.py
├── tests/               # ~42 unit-тестов
├── scripts/             # Скрипты для тестирования
├── config/              # Конфигурация
└── docs/                # Документация
```

## 📚 Документация

- [README.md](README.md) - Основная документация
- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - Руководство по интеграции
- [docs/QUICK_START.md](docs/QUICK_START.md) - Быстрый старт
- [docs/testing_guide.md](docs/testing_guide.md) - Руководство по тестированию
- [docs/strategy_documentation.md](docs/strategy_documentation.md) - Документация стратегии

## 🧪 Тестирование

```bash
# Все тесты
pytest tests/ -v

# С покрытием
pytest tests/ --cov=indicators --cov=utils --cov=strategies --cov-report=html

# Отдельные модули
pytest tests/test_order_blocks.py -v
pytest tests/test_volume_profile.py -v
```

## 📈 Архитектура стратегии

### Top-Down подход

1. **Макроуровень (Daily/4H)**
   - Order Blocks detection
   - Fair Value Gaps
   - Volume Profile (POC, HVN, LVN)
   - Market Structure (BOS, ChoCH, Trend)

2. **Промежуточный уровень (1H)**
   - Market Profile (VAH, VAL, POC)
   - TPO distribution
   - Value Area filtering

3. **Микроуровень (15min)**
   - Footprint Delta
   - Order Flow analysis
   - Absorption detection

### Условия входа

**Long Entry**:
- Макро: Цена в bullish Order Block + тренд bullish/range
- Промежуточный: Цена в Value Area или отскок от VAL
- Микро: Положительный Delta + Absorption
- Confluence: Минимум 3 сигнала

**Short Entry**: Аналогично, но с bearish условиями

## 🛠️ Технологии

- Python 3.9+
- pandas, numpy для анализа данных
- Freqtrade для торговли
- pytest для тестирования

## 📝 Лицензия

MIT License

## 🤝 Вклад в проект

Приветствуются Pull Requests! Пожалуйста, убедитесь что:
1. Все тесты проходят
2. Код соответствует стилю проекта
3. Добавлена документация для новых функций

## ⚠️ Disclaimer

Эта система предназначена только для образовательных целей. Торговля криптовалютами связана с высокими рисками. Используйте на свой страх и риск.

## 📞 Контакты

Создайте Issue для вопросов и предложений.

---

**Сделано с ❤️ для криптотрейдеров**
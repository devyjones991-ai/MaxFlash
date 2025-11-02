# MaxFlash Trading System Web Interface

Современный веб-интерфейс для визуализации и мониторинга торговой системы.

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install dash dash-bootstrap-components dash-table requests
```

Или используйте requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Запуск интерфейса

```bash
cd web_interface
python app.py
```

### 3. Открыть в браузере

Перейдите на: **http://localhost:8050**

## 📊 Возможности интерфейса

### Главный график цены:
- ✅ Candlesticks с ценами
- ✅ Order Blocks (цветные зоны)
- ✅ Fair Value Gaps (прозрачные зоны)
- ✅ Confluence zones (выделенные области)
- ✅ Volume bars
- ✅ Delta индикатор

### Volume Profile панель:
- ✅ Боковая гистограмма объема
- ✅ POC (Point of Control) линия
- ✅ Value Area (VAH/VAL)
- ✅ HVN/LVN маркеры

### Панель сигналов:
- ✅ Активные торговые сигналы
- ✅ Confluence score
- ✅ Entry/Stop Loss/Take Profit
- ✅ Risk:Reward ratio

### Метрики:
- ✅ Win Rate
- ✅ Profit Factor
- ✅ Sharpe Ratio
- ✅ Total Return
- ✅ Max Drawdown

### Дополнительные вкладки:
- 📊 **Footprint Chart**: Delta и Order Flow визуализация
- 📈 **Market Profile**: TPO distribution и Value Area
- 🔗 **Confluence Zones**: Карта confluence зон
- 📉 **Backtest Results**: Результаты бэктестинга
- ⚡ **Real-time Signals**: Активные сигналы в реальном времени

## ⚙️ Настройка

### Подключение к Freqtrade

Создайте файл `.env` или установите переменные окружения:

```bash
FREQTRADE_API_URL=http://localhost:8080
FREQTRADE_API_USERNAME=your_username  # Опционально
FREQTRADE_API_PASSWORD=your_password   # Опционально
```

Или отредактируйте `config.py`:

```python
FREQTRADE_API_URL = "http://localhost:8080"
```

### Изменение порта

```bash
export DASHBOARD_PORT=8051
python app.py
```

Или измените в `config.py`:
```python
DASHBOARD_PORT = 8051
```

## 🎨 Кастомизация

### Темы

Интерфейс использует темную тему (`DARKLY`). Можно изменить в `app.py`:

```python
app = dash.Dash(
    external_stylesheets=[dbc.themes.DARKLY]  # Или DARKLY, CYBORG, SLATE
)
```

### Обновление данных

Интервал обновления по умолчанию: 15 секунд

Изменить в `app.py`:
```python
dcc.Interval(
    interval=15*1000,  # Изменить на нужное значение
    ...
)
```

## 📱 Мобильная версия

Интерфейс адаптивен и работает на мобильных устройствах!

## 🔧 Структура проекта

```
web_interface/
├── app.py                      # Главное приложение
├── config.py                   # Конфигурация
├── components/                  # UI компоненты
│   ├── price_chart.py          # График цены
│   ├── volume_profile_viz.py  # Volume Profile
│   ├── footprint_viz.py       # Footprint
│   ├── market_profile_viz.py  # Market Profile
│   ├── confluence_viz.py      # Confluence
│   ├── signals_panel.py       # Сигналы
│   ├── metrics_panel.py       # Метрики
│   ├── backtest_viz.py        # Бэктест
│   └── realtime_signals.py    # Real-time
├── api/
│   └── freqtrade_client.py    # Freqtrade API клиент
└── assets/
    └── style.css              # Кастомные стили
```

## 🐛 Troubleshooting

### Интерфейс не запускается

1. Проверьте установку зависимостей: `pip list | grep dash`
2. Проверьте порт: `netstat -an | grep 8050`
3. Проверьте логи в консоли

### Нет данных от Freqtrade

1. Убедитесь что Freqtrade запущен
2. Проверьте URL в `config.py`
3. Проверьте доступность API: `curl http://localhost:8080/api/v1/status`

### Графики не обновляются

1. Проверьте интервал обновления
2. Проверьте логи на наличие ошибок
3. Обновите страницу в браузере (Ctrl+F5)

## 📚 Документация

- [Dash Documentation](https://dash.plotly.com/)
- [Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/)
- [Plotly Python](https://plotly.com/python/)

## 🚀 Production deployment

Для production используйте gunicorn:

```bash
pip install gunicorn
gunicorn app:server -b 0.0.0.0:8050
```

Или через systemd service (см. документацию Dash).



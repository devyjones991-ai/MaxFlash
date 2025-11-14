# 🔴 WebSocket Integration для Real-time обновлений

## Обзор

MaxFlash теперь поддерживает real-time обновления цен через WebSocket для мгновенного отображения изменений на рынке без необходимости polling.

## Архитектура

### Компоненты

1. **WebSocketManager** (`utils/websocket_manager.py`)
   - Управление WebSocket соединениями
   - Подписка на обновления цен для множества пар
   - Кэширование последних цен
   - Callback система для обработки обновлений

2. **MarketMonitor Integration** (`utils/market_monitor.py`)
   - Использование WebSocket для мониторинга вместо polling
   - Автоматический fallback на polling при недоступности WebSocket
   - Real-time обработка алертов

3. **Dashboard Integration** (`web_interface/app.py`)
   - Автоматический запуск WebSocket при старте приложения
   - Подписка на популярные пары для real-time обновлений

## Использование

### Автоматическая инициализация

WebSocket автоматически запускается при старте приложения:

```python
# В web_interface/app.py
from utils.websocket_manager import get_websocket_manager

ws_manager = get_websocket_manager('binance')
ws_manager.start()
```

### Подписка на обновления

```python
from utils.websocket_manager import get_websocket_manager

ws_manager = get_websocket_manager('binance')

def price_update_handler(price_data):
    """Обработчик обновлений цены."""
    symbol = price_data['symbol']
    price = price_data['price']
    print(f"{symbol}: ${price}")

# Подписываемся на пару
ws_manager.subscribe('BTC/USDT', price_update_handler)
ws_manager.start()
```

### Получение последней цены

```python
# Получить последнюю цену из кэша
latest_price = ws_manager.get_latest_price('BTC/USDT')
if latest_price:
    print(f"Последняя цена: ${latest_price['price']}")

# Получить все кэшированные цены
all_prices = ws_manager.get_all_prices()
```

## Поддерживаемые биржи

- **Binance** (основная)
- **Bybit** (поддержка через CCXT)
- **OKX** (поддержка через CCXT)

## Fallback механизм

Если WebSocket недоступен, система автоматически переключается на polling:

```python
# MarketMonitor автоматически определяет доступность WebSocket
monitor = MarketMonitor(use_websocket=True)  # Попытается использовать WebSocket
monitor.start()  # Fallback на polling если WebSocket недоступен
```

## Преимущества WebSocket

### По сравнению с Polling:

1. **Мгновенные обновления** - нет задержки в 30 секунд
2. **Меньше нагрузка на API** - обновления только при изменении цены
3. **Эффективность** - одно соединение вместо множества запросов
4. **Real-time алерты** - мгновенное обнаружение событий

### Метрики:

- **Polling**: Обновление каждые 30 секунд, ~120 запросов/час на пару
- **WebSocket**: Мгновенные обновления, 1 соединение для всех пар

## Конфигурация

### Настройка количества пар

```python
# В web_interface/app.py
popular_symbols = POPULAR_PAIRS[:20]  # Топ-20 пар для WebSocket
```

### Интервал мониторинга (для fallback)

```python
monitor = MarketMonitor(
    monitoring_interval=30  # Используется только при polling
)
```

## Отладка

### Логирование

```python
import logging
logging.getLogger('utils.websocket_manager').setLevel(logging.DEBUG)
```

### Проверка статуса

```python
ws_manager = get_websocket_manager('binance')
if ws_manager.is_connected():
    print("WebSocket подключен")
else:
    print("WebSocket не подключен, используется polling")
```

## Обработка ошибок

Система автоматически обрабатывает:
- Разрыв соединения (автоматическое переподключение)
- Недоступность WebSocket (fallback на polling)
- Ошибки в callbacks (логирование без прерывания работы)

## Примеры использования

### Real-time обновление таблицы

```python
def update_table_with_websocket():
    ws_manager = get_websocket_manager('binance')
    
    def update_table_row(price_data):
        symbol = price_data['symbol']
        price = price_data['price']
        # Обновить строку в таблице
        update_table_cell(symbol, 'price', price)
    
    for symbol in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
        ws_manager.subscribe(symbol, update_table_row)
    
    ws_manager.start()
```

### Real-time алерты

```python
def setup_realtime_alerts():
    from utils.market_monitor import MarketMonitor
    from utils.market_alerts import MarketAlerts
    
    alerts = MarketAlerts(data_manager)
    monitor = MarketMonitor(
        alerts=alerts,
        use_websocket=True  # Использовать WebSocket для real-time
    )
    monitor.start()
```

## Производительность

### До WebSocket:
- Обновление цен: каждые 30 секунд
- Задержка обнаружения событий: до 30 секунд
- Нагрузка на API: высокая (polling)

### После WebSocket:
- Обновление цен: мгновенно
- Задержка обнаружения событий: <1 секунда
- Нагрузка на API: минимальная (одно соединение)

## Будущие улучшения

1. Расширение WebSocket на все компоненты dashboard
2. Real-time обновления графиков через WebSocket
3. WebSocket для Multi-View компонента
4. Поддержка большего количества бирж через WebSocket

---

**Дата обновления**: 2024
**Версия**: 1.0


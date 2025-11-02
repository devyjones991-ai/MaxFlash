# 🔴 Real-time Monitoring System

Интеграция компонентов из Crypto Price Monitoring System для real-time мониторинга цен и алертов.

## 🎯 Возможности

### 1. WebSocket Streaming
- Real-time обновления цен через WebSocket
- Поддержка Binance, Bybit, OKX
- Автоматическое переподключение
- Множественные подписки на торговые пары

### 2. Anomaly Detection
- Z-score анализ для статистических аномалий
- Детекция резких движений цен
- Всплески объема торгов
- Паттерн-распознавание ценовых движений

### 3. Discord Bot
- Автоматические алерты о сигналах
- Уведомления об аномалиях
- Команды для статуса и истории
- Красивые embed сообщения

### 4. Stream Processing
- Потоковая обработка данных
- История цен для анализа
- Статистика обработки

## 🚀 Быстрый старт

### Установка зависимостей

```bash
pip install websocket-client discord.py
```

### WebSocket Streaming

```python
from web_interface.services.websocket_stream import WebSocketPriceStream

# Создаем stream
stream = WebSocketPriceStream(exchange_name='binance')

# Подписываемся на обновления
def on_price_update(price_data):
    print(f"{price_data['symbol']}: ${price_data['price']}")

stream.subscribe('BTC/USDT', on_price_update)
stream.start()
```

### Anomaly Detection

```python
from utils.anomaly_detector import PriceAnomalyDetector

detector = PriceAnomalyDetector(
    z_score_threshold=3.0,
    price_change_threshold=5.0
)

anomalies = detector.detect_anomalies(dataframe)
for anomaly in anomalies:
    print(AnomalyAlert.format_alert(anomaly))
```

### Discord Bot

```python
from web_interface.services.discord_bot import TradingAlertBot

# Создаем бота
bot = TradingAlertBot(
    token='YOUR_DISCORD_BOT_TOKEN',
    channel_id=YOUR_CHANNEL_ID
)

# Запускаем бота (в отдельном потоке)
bot.run()

# Отправляем алерт
await bot.send_alert("🚀 Новый сигнал!")
```

### Интегрированная система мониторинга

```python
from web_interface.services.stream_processor import RealTimeMonitoringSystem

# Создаем систему
monitoring = RealTimeMonitoringSystem(
    exchange_name='binance',
    api_key='YOUR_API_KEY',
    secret='YOUR_SECRET'
)

# Callback для алертов
def on_alert(anomaly):
    print(f"Алерт: {anomaly['message']}")
    # Можно отправить в Discord
    # await bot.send_anomaly_alert(anomaly)

monitoring.processor.alert_callback = on_alert

# Начинаем мониторинг
monitoring.start_monitoring(['BTC/USDT', 'ETH/USDT'])

# Статус
status = monitoring.get_status()
print(status)
```

## ⚙️ Конфигурация

### .env файл

```env
# Discord Bot (опционально)
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id

# Exchange API
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=your_api_key
EXCHANGE_API_SECRET=your_secret
```

### Параметры Anomaly Detector

```python
detector = PriceAnomalyDetector(
    z_score_threshold=3.0,        # Порог Z-score (стандартные отклонения)
    price_change_threshold=5.0,   # Порог % изменения цены
    volume_spike_threshold=2.0,   # Порог всплеска объема
    window_size=100              # Размер окна для анализа
)
```

## 📊 Использование в Dashboard

Интеграция с существующим dashboard:

```python
from web_interface.services import RealTimeMonitoringSystem, create_discord_bot

# Инициализация
monitoring = RealTimeMonitoringSystem(exchange_name='binance')
discord_bot = create_discord_bot()

# Callback для обновления dashboard
def update_dashboard_with_price(price_data):
    # Обновляем графики в реальном времени
    pass

def send_alert_to_discord(anomaly):
    if discord_bot:
        # Отправляем в Discord
        asyncio.create_task(discord_bot.send_anomaly_alert(anomaly))

monitoring.processor.alert_callback = send_alert_to_discord
monitoring.start_monitoring(['BTC/USDT'])
```

## 🔔 Discord Команды

- `!status` - Проверить статус системы
- `!help` - Показать доступные команды
- `!alerts` - Показать последние алерты

## 📈 Типы аномалий

1. **Z-score Anomaly** - Статистическая аномалия (выход за пределы стандартных отклонений)
2. **Price Change Anomaly** - Резкое изменение цены (%)
3. **Volume Spike** - Всплеск объема торгов
4. **Price Spike** - Резкое ценовое движение (широкий диапазон свечи)

## 🛠️ Troubleshooting

### WebSocket не подключается
- Проверьте интернет соединение
- Убедитесь что API ключ правильный
- Проверьте что биржа доступна

### Discord бот не отвечает
- Проверьте токен бота
- Убедитесь что бот добавлен в сервер
- Проверьте права бота в канале

### Нет аномалий
- Уменьшите пороги (thresholds)
- Убедитесь что достаточно данных (минимум 50 свечей)
- Проверьте настройки детектора

## 📚 Дополнительно

- [Crypto Price Monitoring System](https://github.com/soheil-mp/Crypto-Price-Monitoring-System) - Исходный проект
- [CCXT Documentation](https://docs.ccxt.com/) - Библиотека для бирж
- [Discord.py Documentation](https://discordpy.readthedocs.io/) - Discord API


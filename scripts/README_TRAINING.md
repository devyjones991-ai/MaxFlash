# Инструкция по обучению модели с калибровкой

## Обзор

Скрипт `train_model_with_calibration.py` обучает модель LightGBM на историческом датасете (365 дней) с калибровкой вероятностей через confusion matrix.

### Особенности:
- ✅ Обучение на 365 днях исторических данных
- ✅ Confusion matrix калибровка (Isotonic Regression)
- ✅ Метрики качества: Accuracy, Precision, Recall, F1
- ✅ Интеграция с EnhancedSignalGenerator

## Запуск на сервере

### 1. Подготовка

```bash
cd /path/to/MaxFlash
python3 -m venv venv  # Если виртуальное окружение еще не создано
source venv/bin/activate  # Или venv\Scripts\activate на Windows
pip install -r requirements.txt
```

### 2. Запуск обучения

```bash
# Базовая команда (использует настройки по умолчанию)
python scripts/train_model_with_calibration.py

# С параметрами
python scripts/train_model_with_calibration.py \
    --days 365 \
    --timeframe 15m \
    --output models/lightgbm_calibrated.pkl
```

### 3. Результаты

После обучения будут созданы файлы:
- `models/lightgbm_calibrated.pkl` - обученная модель
- `models/calibration_meta.pkl` - параметры калибровки
- `models/training_history.json` - история обучения с метриками

### 4. Использование обученной модели

```python
from ml.lightgbm_model import LightGBMSignalGenerator

# Загрузить модель с калибровкой
model = LightGBMSignalGenerator(model_path='models/lightgbm_calibrated.pkl')
model.load_calibration('models/calibration_meta.pkl')

# Использовать для предсказаний
prediction = model.predict(ohlcv_df)
```

## Интеграция с EnhancedSignalGenerator

Используйте `SignalIntegrator` для комбинирования ML и rule-based сигналов:

```python
from utils.signal_integrator import SignalIntegrator
from ml.lightgbm_model import LightGBMSignalGenerator

# Загрузить модель
ml_model = LightGBMSignalGenerator(model_path='models/lightgbm_calibrated.pkl')
ml_model.load_calibration('models/calibration_meta.pkl')

# Создать интегратор
integrator = SignalIntegrator(
    ml_model=ml_model,
    ml_weight=0.35,      # 35% ML
    enhanced_weight=0.65  # 65% Rule-based
)

# Получить интегрированный сигнал
integrated = integrator.integrate_signals(
    symbol="BTC/USDT",
    ticker=ticker_data,
    ohlcv_df=ohlcv_df
)

# Оценить качество
quality = integrator.summarize_signal_quality(integrated)
print(quality['summary'])  # 🟢 HIGH quality (85.3/100) - BUY
```

## Метрики обучения

После обучения проверьте `models/training_history.json`:

```json
{
  "timestamp": "2025-12-16T...",
  "training_samples": 50000,
  "validation_samples": 10000,
  "validation_metrics": {
    "accuracy": 0.6234,
    "precision": {
      "SELL": 0.65,
      "HOLD": 0.61,
      "BUY": 0.67
    },
    "recall": {
      "SELL": 0.58,
      "HOLD": 0.72,
      "BUY": 0.59
    }
  },
  "calibration_result": {
    "log_loss_before": 0.8234,
    "log_loss_after": 0.7891,
    "improvement": 0.0343
  }
}
```

## Автоматическое переобучение

Используйте `auto_retrain_v2.py` для автоматического переобучения:

```bash
# Настроить cron для ежедневного запуска в 3:00
0 3 * * * cd /path/to/MaxFlash && /path/to/venv/bin/python scripts/auto_retrain_v2.py >> logs/retrain.log 2>&1
```

Или через systemd service (уже настроен в `infra/maxflash-retrain.service`):

```bash
sudo systemctl status maxflash-retrain
sudo systemctl start maxflash-retrain
```

## Устранение неполадок

### Недостаточно данных
Если `Insufficient data: X < 10000`:
- Увеличьте `training_days` или уменьшите `min_samples` в CONFIG
- Проверьте подключение к бирже (Binance API)

### Ошибка калибровки
Если `sklearn not available`:
```bash
pip install scikit-learn
```

### Медленное обучение
- Уменьшите `num_boost_round` (по умолчанию 500)
- Используйте меньше монет в CONFIG['coins']
- Обучайте ночью когда рынок менее активен

## Конфигурация

Отредактируйте `CONFIG` в `scripts/train_model_with_calibration.py`:

```python
CONFIG = {
    'training_days': 365,      # Дней исторических данных
    'min_samples': 10000,      # Минимум samples
    'timeframe': '15m',        # Таймфрейм
    'calibration_method': 'isotonic',  # 'isotonic' или 'sigmoid'
    # ...
}
```



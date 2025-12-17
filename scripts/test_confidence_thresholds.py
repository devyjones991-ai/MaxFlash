"""
Тест разных порогов confidence для выбора оптимального.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from ml.lightgbm_model import LightGBMSignalGenerator
from ml.labeling import calculate_atr
import numpy as np

# Загружаем модель
model = LightGBMSignalGenerator(model_path='models/lightgbm_latest.pkl')

# Загружаем тестовые данные (BTC)
import ccxt
exchange = ccxt.binance({'enableRateLimit': True})
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=200)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

# Получаем предсказания с вероятностями
predictions, probs = model.predict_batch_with_probs(df)

print("=" * 60)
print("АНАЛИЗ CONFIDENCE РАСПРЕДЕЛЕНИЯ")
print("=" * 60)
print()

# Анализируем распределение confidence для каждого класса
buy_probs = []
sell_probs = []
hold_probs = []

for i, (pred, prob) in enumerate(zip(predictions, probs)):
    sell_prob, hold_prob, buy_prob = prob
    buy_probs.append(buy_prob)
    sell_probs.append(sell_prob)
    hold_probs.append(hold_prob)

buy_probs = np.array(buy_probs)
sell_probs = np.array(sell_probs)
hold_probs = np.array(hold_probs)

print(f"BUY signals: {np.sum(predictions == 2)}")
print(f"SELL signals: {np.sum(predictions == 0)}")
print(f"HOLD signals: {np.sum(predictions == 1)}")
print()

print("BUY probabilities:")
print(f"  Mean: {buy_probs.mean():.3f}")
print(f"  Median: {np.median(buy_probs):.3f}")
print(f"  Max: {buy_probs.max():.3f}")
print(f"  Min: {buy_probs.min():.3f}")
print(f"  > 0.5: {np.sum(buy_probs > 0.5)} ({np.sum(buy_probs > 0.5)/len(buy_probs)*100:.1f}%)")
print(f"  > 0.48: {np.sum(buy_probs > 0.48)} ({np.sum(buy_probs > 0.48)/len(buy_probs)*100:.1f}%)")
print(f"  > 0.45: {np.sum(buy_probs > 0.45)} ({np.sum(buy_probs > 0.45)/len(buy_probs)*100:.1f}%)")
print()

print("SELL probabilities:")
print(f"  Mean: {sell_probs.mean():.3f}")
print(f"  Median: {np.median(sell_probs):.3f}")
print(f"  Max: {sell_probs.max():.3f}")
print(f"  > 0.5: {np.sum(sell_probs > 0.5)} ({np.sum(sell_probs > 0.5)/len(sell_probs)*100:.1f}%)")
print(f"  > 0.48: {np.sum(sell_probs > 0.48)} ({np.sum(sell_probs > 0.48)/len(sell_probs)*100:.1f}%)")
print(f"  > 0.45: {np.sum(sell_probs > 0.45)} ({np.sum(sell_probs > 0.45)/len(sell_probs)*100:.1f}%)")
print()

# Тестируем разные пороги
print("=" * 60)
print("РЕКОМЕНДУЕМЫЕ ПОРОГИ")
print("=" * 60)
print()

thresholds = [0.45, 0.48, 0.50, 0.52, 0.55, 0.60]

for threshold in thresholds:
    buy_count = np.sum((predictions == 2) & (buy_probs >= threshold))
    sell_count = np.sum((predictions == 0) & (sell_probs >= threshold))
    total = buy_count + sell_count
    print(f"Threshold {threshold:.2f}: {total} сигналов (BUY: {buy_count}, SELL: {sell_count})")


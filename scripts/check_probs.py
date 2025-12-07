"""Check model probability distribution."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from ml.lightgbm_model import LightGBMSignalGenerator
from utils.market_data_manager import MarketDataManager
from ml.feature_engineering import create_all_features

OUTPUT = 'probs_output.txt'

with open(OUTPUT, 'w') as f:
    f.write("Loading model...\n")

m = LightGBMSignalGenerator()
m.load_model('models/lightgbm_latest.pkl')

with open(OUTPUT, 'a') as f:
    f.write(f"Model loaded. Features: {len(m.feature_names)}\n")

dm = MarketDataManager()
df = dm.get_ohlcv('BTC/USDT', '15m', limit=200)

with open(OUTPUT, 'a') as f:
    f.write(f"Data loaded: {len(df)} candles\n")

X = create_all_features(df, None, True).values

with open(OUTPUT, 'a') as f:
    f.write(f"Features created: {X.shape}\n")

X_scaled = m.scaler.transform(X)
probs = m.model.predict(X_scaled)

with open(OUTPUT, 'a') as f:
    f.write(f"\nProbability distribution:\n")
    f.write(f"Shape: {probs.shape}\n")
    f.write(f"Columns: [SELL, HOLD, BUY]\n\n")
    
    # Stats
    f.write(f"SELL probs - min: {probs[:, 0].min():.4f}, max: {probs[:, 0].max():.4f}, mean: {probs[:, 0].mean():.4f}\n")
    f.write(f"HOLD probs - min: {probs[:, 1].min():.4f}, max: {probs[:, 1].max():.4f}, mean: {probs[:, 1].mean():.4f}\n")
    f.write(f"BUY probs  - min: {probs[:, 2].min():.4f}, max: {probs[:, 2].max():.4f}, mean: {probs[:, 2].mean():.4f}\n")
    
    f.write(f"\nLast 10 predictions:\n")
    for i, p in enumerate(probs[-10:]):
        f.write(f"  {i}: SELL={p[0]:.4f}, HOLD={p[1]:.4f}, BUY={p[2]:.4f}\n")
    
    # Count by argmax
    argmax_preds = np.argmax(probs, axis=1)
    unique, counts = np.unique(argmax_preds, return_counts=True)
    labels = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
    f.write(f"\nArgmax distribution:\n")
    for u, c in zip(unique, counts):
        f.write(f"  {labels.get(u, u)}: {c} ({c/len(probs)*100:.1f}%)\n")
    
    f.write("\nDONE\n")


"""Quick test of LightGBM model predictions."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# UTF-8 for Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

import numpy as np
from ml.lightgbm_model import LightGBMSignalGenerator
from utils.market_data_manager import MarketDataManager

def main():
    import sys
    print("=" * 60, flush=True)
    print("QUICK MODEL TEST", flush=True)
    print("=" * 60, flush=True)
    
    # Load model
    model = LightGBMSignalGenerator()
    model.load_model('models/lightgbm_latest.pkl')
    print(f"Model loaded. Features: {len(model.feature_names) if model.feature_names else 'N/A'}")
    
    # Get data
    dm = MarketDataManager()
    df = dm.get_ohlcv('BTC/USDT', '15m', limit=500)
    
    if df is None:
        print("ERROR: Failed to load data")
        return
    
    print(f"Data loaded: {len(df)} candles")
    
    # Predict
    preds = model.predict_batch(df)
    
    # Distribution
    unique, counts = np.unique(preds, return_counts=True)
    labels = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
    
    print("\nPredictions distribution:")
    for u, c in zip(unique, counts):
        pct = c / len(preds) * 100
        print(f"  {labels.get(u, u)}: {c} ({pct:.1f}%)")
    
    # Show recent predictions
    print("\nLast 20 predictions:")
    recent = preds[-20:]
    for i, p in enumerate(recent):
        print(f"  {i+1}: {labels.get(p, p)}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

"""Quick test of model predictions."""
import sys
import os
import traceback

sys.path.insert(0, 'D:\\MaxFlash')
os.chdir('D:\\MaxFlash')

# Write to file for Windows compatibility
OUTPUT_FILE = 'D:\\MaxFlash\\test_output.txt'

def p(msg=''):
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

# Clear file
with open(OUTPUT_FILE, 'w') as f:
    f.write('Starting...\n')

try:
    from ml.lightgbm_model import LightGBMSignalGenerator
    from utils.market_data_manager import MarketDataManager
    import numpy as np
    
    p("Imports OK")
    
    p("Loading model...")
    m = LightGBMSignalGenerator()
    m.load_model('models/lightgbm_latest.pkl')
    p(f"Model loaded. Features: {len(m.feature_names)}")
    
    p("\nFetching data...")
    dm = MarketDataManager()
    df = dm.get_ohlcv('BTC/USDT', '15m', limit=500)
    p(f"Data: {len(df)} candles")
    
    p("\nGenerating predictions...")
    preds = m.predict_batch(df)
    u, c = np.unique(preds, return_counts=True)
    labels = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
    
    p("\n=== PREDICTION DISTRIBUTION ===")
    for label, count in zip(u, c):
        pct = count/len(preds)*100
        p(f"  {labels.get(label, label)}: {count} ({pct:.1f}%)")
    
    # Show probabilities distribution
    p("\n=== PROBABILITY STATS ===")
    features = m.feature_engineering.create_all_features(df).dropna()
    probs = m.model.predict(m.scaler.transform(features.values))
    p(f"BUY prob range: {probs[:, 2].min():.3f} - {probs[:, 2].max():.3f} (mean: {probs[:, 2].mean():.3f})")
    p(f"SELL prob range: {probs[:, 0].min():.3f} - {probs[:, 0].max():.3f} (mean: {probs[:, 0].mean():.3f})")
    p(f"HOLD prob range: {probs[:, 1].min():.3f} - {probs[:, 1].max():.3f} (mean: {probs[:, 1].mean():.3f})")
    
    p("\nDONE!")

except Exception as e:
    p(f"\nERROR: {e}")
    p(traceback.format_exc())

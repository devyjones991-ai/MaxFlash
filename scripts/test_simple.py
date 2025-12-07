"""Simplest test."""
import sys
import os

sys.path.insert(0, 'D:\\MaxFlash')
os.chdir('D:\\MaxFlash')

OUT = 'D:\\MaxFlash\\test_out.txt'

def w(s):
    with open(OUT, 'a') as f:
        f.write(str(s) + '\n')

with open(OUT, 'w') as f:
    f.write('TEST START\n')

try:
    import numpy as np
    from ml.lightgbm_model import LightGBMSignalGenerator
    from utils.market_data_manager import MarketDataManager
    w('Imports OK')
    
    m = LightGBMSignalGenerator()
    m.load_model('models/lightgbm_latest.pkl')
    w(f'Model: {len(m.feature_names)} features')
    
    dm = MarketDataManager()
    df = dm.get_ohlcv('BTC/USDT', '15m', limit=500)
    w(f'Data: {len(df)} candles')
    
    preds = m.predict_batch(df)
    
    unique, counts = np.unique(preds, return_counts=True)
    w('')
    w('=== PREDICTION DISTRIBUTION ===')
    labels = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
    for u, c in zip(unique, counts):
        w(f'  {labels.get(u, u)}: {c} ({c*100/len(preds):.1f}%)')
    
    # Quick backtest
    w('')
    w('=== QUICK BACKTEST ===')
    wins = 0
    losses = 0
    for i in range(50, len(df)-10):
        if preds[i] == 2:  # BUY
            entry = df['close'].iloc[i]
            exit = df['close'].iloc[i+10]
            if exit > entry:
                wins += 1
            else:
                losses += 1
        elif preds[i] == 0:  # SELL
            entry = df['close'].iloc[i]
            exit = df['close'].iloc[i+10]
            if exit < entry:
                wins += 1
            else:
                losses += 1
    
    total = wins + losses
    if total > 0:
        w(f'  Trades: {total}')
        w(f'  Wins: {wins}, Losses: {losses}')
        w(f'  Win Rate: {wins*100/total:.1f}%')
    else:
        w('  No trades!')
    
    w('')
    w('DONE!')
    
except Exception as e:
    import traceback
    w(f'ERROR: {e}')
    w(traceback.format_exc())

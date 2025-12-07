"""Quick model training on limited data."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import ccxt
from datetime import datetime, timedelta
from ml.lightgbm_model import LightGBMSignalGenerator

OUTPUT = 'train_output.txt'

def log(msg):
    print(msg)
    with open(OUTPUT, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

# Clear output
open(OUTPUT, 'w').close()

log(f"Starting quick training at {datetime.now()}")

# Load data from 3 coins
coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
exchange = ccxt.binance({'enableRateLimit': True})

all_data = []
for symbol in coins:
    log(f"Loading {symbol}...")
    try:
        # 30 days of 15m data
        since = exchange.parse8601((datetime.now() - timedelta(days=30)).isoformat())
        ohlcv = exchange.fetch_ohlcv(symbol, '15m', since=since, limit=2880)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        all_data.append(df)
        log(f"  Loaded {len(df)} candles")
    except Exception as e:
        log(f"  Error: {e}")

if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    log(f"\nTotal data: {len(combined_df)} candles")
    
    # Train model
    log("\nTraining model...")
    model = LightGBMSignalGenerator()
    
    try:
        metrics = model.train(
            combined_df,
            use_new_features=True,
            num_boost_round=500,
            early_stopping_rounds=50
        )
        
        log(f"\nTraining complete!")
        log(f"Accuracy: {metrics['accuracy']:.4f}")
        log(f"Iterations: {metrics['num_iterations']}")
        log(f"Top features: {[f[0] for f in metrics['top_features'][:5]]}")
        
        # Save model
        model.save_model('models/lightgbm_quick.pkl')
        log(f"\nModel saved to models/lightgbm_quick.pkl")
        
    except Exception as e:
        log(f"Training error: {e}")
        import traceback
        log(traceback.format_exc())
else:
    log("No data loaded!")

log("\nDONE")


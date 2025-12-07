"""Simple backtest for model evaluation."""
import sys
import os
import traceback

# Use hardcoded path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else 'D:\\MaxFlash\\scripts'
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_FILE = os.path.join(ROOT_DIR, 'backtest_output.txt')

def log(msg=''):
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

try:
    # Clear output file first
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('Starting backtest...\n')
    
    sys.path.insert(0, ROOT_DIR)
    os.chdir(ROOT_DIR)
    
    import numpy as np
    from datetime import datetime
    log(f"Numpy imported at {datetime.now()}")
    
    from ml.lightgbm_model import LightGBMSignalGenerator
    log("LightGBM imported")
    
    from utils.market_data_manager import MarketDataManager
    log("MarketDataManager imported")
    
    def run_backtest(symbol='BTC/USDT', days=30):
        log(f"\n{'='*60}")
        log(f"BACKTEST: {symbol} ({days} days)")
        log(f"{'='*60}")
        
        # Load model
        model = LightGBMSignalGenerator()
        model.load_model('models/lightgbm_quick.pkl')
        log(f"Model loaded. Features: {len(model.feature_names)}")
        
        # Get data
        dm = MarketDataManager()
        candles = days * 24 * 4  # 15m candles
        df = dm.get_ohlcv(symbol, '15m', limit=min(candles, 2880))
        
        if df is None or len(df) < 100:
            log("ERROR: Not enough data")
            return None
        
        log(f"Data: {len(df)} candles")
        
        # Generate predictions
        preds = model.predict_batch(df)
        
        # Simple backtest simulation
        initial_balance = 10000
        balance = initial_balance
        position = 0  # 0 = no position, 1 = long, -1 = short
        entry_price = 0
        trades = []
        wins = 0
        losses = 0
        
        for i in range(1, len(df)):
            price = df['close'].iloc[i]
            pred = preds[i]
            
            # Exit current position
            if position != 0:
                # Calculate P&L
                if position == 1:  # Long
                    pnl_pct = (price - entry_price) / entry_price
                else:  # Short
                    pnl_pct = (entry_price - price) / entry_price
                
                # Apply simple TP/SL
                tp_pct = 0.02  # 2% take profit
                sl_pct = -0.01  # 1% stop loss
                
                if pnl_pct >= tp_pct or pnl_pct <= sl_pct:
                    pnl = balance * 0.1 * pnl_pct  # 10% position size
                    balance += pnl
                    trades.append(pnl)
                    if pnl > 0:
                        wins += 1
                    else:
                        losses += 1
                    position = 0
            
            # Enter new position
            if position == 0:
                if pred == 2:  # BUY
                    position = 1
                    entry_price = price
                elif pred == 0:  # SELL
                    position = -1
                    entry_price = price
        
        # Calculate metrics
        total_trades = len(trades)
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0
        total_return = (balance - initial_balance) / initial_balance * 100
        
        gross_profit = sum(t for t in trades if t > 0)
        gross_loss = abs(sum(t for t in trades if t < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
        
        # Predictions distribution
        u, c = np.unique(preds, return_counts=True)
        labels = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        
        log(f"\n--- PREDICTIONS ---")
        for label, count in zip(u, c):
            log(f"  {labels.get(label, label)}: {count} ({count/len(preds)*100:.1f}%)")
        
        log(f"\n--- RESULTS ---")
        log(f"Total Trades: {total_trades}")
        log(f"Wins: {wins}, Losses: {losses}")
        log(f"Win Rate: {win_rate:.1f}%")
        log(f"Profit Factor: {profit_factor:.2f}")
        log(f"Return: {total_return:.2f}%")
        log(f"Final Balance: ${balance:.2f}")
        log(f"{'='*60}\n")
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'return': total_return,
            'trades': total_trades
        }
    
    log("Starting backtests...")
    
    # Test on BTC only for quick result
    coins = ['BTC/USDT']
    
    results = []
    for coin in coins:
        try:
            r = run_backtest(coin, days=30)
            if r:
                results.append(r)
        except Exception as e:
            log(f"Error with {coin}: {e}")
            log(traceback.format_exc())
    
    if results:
        log("\n" + "="*60)
        log("FINAL RESULTS")
        log("="*60)
        for r in results:
            log(f"Win Rate: {r['win_rate']:.1f}%")
            log(f"Profit Factor: {r['profit_factor']:.2f}")
            log(f"Return: {r['return']:.2f}%")
            log(f"Trades: {r['trades']}")
    
    log("\nDONE")

except Exception as e:
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(f"\nFATAL ERROR: {e}\n")
        f.write(traceback.format_exc())

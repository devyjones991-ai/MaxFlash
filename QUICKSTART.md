# MaxFlash Trading System - Quick Start Guide

## 🚀 Quick Installation

```bash
# 1. Clone the repository
git clone https://github.com/devyjones991-ai/MaxFlash
cd MaxFlash

# 2. Install dependencies
pip install -e ".[dev,ml]"

# Alternative: Install specific components
pip install "ccxt[async]" tensorflow scikit-learn pandas numpy

# 3. Copy environment configuration
cp .env.example .env

# 4. Edit .env with your settings (optional for testnet)
```

## 📋 Prerequisites

- Python 3.9+
- 4GB+ RAM (for ML model training)
- Internet connection for exchange API access

## 🎯 Usage

### 1. Train ML Model (Optional but Recommended)

```bash
# Train on historical data (this may take 20-30 minutes)
python scripts/train_ml_model.py --days 365 --epochs 50

# Quick training for testing
python scripts/train_ml_model.py --days 30 --epochs 10
```

**Model will be saved to:** `models/lstm_model.h5`

### 2. Backtest Strategy

```bash
# Backtest with trained model
python scripts/backtest_strategy.py --symbol BTC/USDT --days 90 --model models/lstm_model.h5

# Backtest without model (random baseline)
python scripts/backtest_strategy.py --symbol ETH/USDT --days 30
```

### 3. Start API Server

```bash
# Development mode (with auto-reload)
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Or use the runner script
python run_api.py
```

**API will be available at:** `http://localhost:8000`
**Documentation:** `http://localhost:8000/docs`

### 4. Get Trading Signals

```bash
# Using curl
curl "http://localhost:8000/api/v1/signals?limit=5"

# Using browser
# Open: http://localhost:8000/docs
# Try the /api/v1/signals endpoint
```

### 5. Execute Trades (Testnet)

```python
import requests

# Place a market buy order
response = requests.post(
    "http://localhost:8000/api/v1/trades",
    json={
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.001,
        "order_type": "market"
    }
)

print(response.json())
```

## ⚙️ Configuration

### Testnet Mode (Default - SAFE)

In `.env`:

```bash
USE_TESTNET=true
ACCOUNT_BALANCE=10000  # Virtual balance for testing
```

### Live Trading (⚠️ Real Money)

1. Get API keys from your exchange (Binance, Bybit, etc.)
2. Update `.env`:

```bash
USE_TESTNET=false
EXCHANGE_API_KEY=your_actual_key
EXCHANGE_API_SECRET=your_actual_secret
ACCOUNT_BALANCE=100  # Start SMALL!
```

> **⚠️ WARNING:** Start with minimum balance (\$50-100) in live trading!

## 📊 Key Features

### ML-Based Signals

- LSTM neural network predictions
- Technical analysis alignment
- Confidence scoring (0.0-1.0)

### Risk Management

- Kelly Criterion position sizing
- Portfolio risk limits (5% default)
- Daily loss circuit breaker (2%)
- Correlation exposure checks

### Auto-Trading

- Automatic order placement
- Stop-loss & take-profit automation
- Order monitoring
- Balance validation

## 🧪 Testing Your Setup

```bash
# 1. Test exchange connection
python -c "from utils.async_exchange import *; import asyncio; asyncio.run(get_async_exchange('binance').fetch_ticker('BTC/USDT'))"

# 2. Test ML model (after training)
python -c "from ml.lstm_signal_generator import LSTMSignalGenerator; model = LSTMSignalGenerator('models/lstm_model.h5'); print('Model loaded successfully!')"

# 3. Run API health check
curl http://localhost:8000/health
```

## 📈 Expected Performance

After training on 1 year of data:

- **Win Rate:** 55-65% (good ML model)
- **Profit Factor:** 1.5-2.5
- **Max Drawdown:** < 15%
- **Sharpe Ratio:** > 1.5

> Results vary based on market conditions and training data quality.

## 🛡️ Safety Checklist

Before live trading:

- [ ] Tested in testnet mode for 30+ days
- [ ] Backtested on 2+ years historical data
- [ ] Win rate > 55% in backtests
- [ ] Max drawdown < 15%
- [ ] API keys have withdrawal restrictions
- [ ] IP whitelisting enabled on exchange
- [ ] 2FA enabled on exchange account
- [ ] Starting with < \$100 capital
- [ ] Daily loss limit enabled (2%)
- [ ] Risk per trade ≤ 1%

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'tensorflow'"

```bash
pip install tensorflow scikit-learn
```

### "No module named 'ccxt.async_support'"

```bash
pip install 'ccxt[async]' --upgrade
```

### "EXCHANGE_API_KEY not set"

- Testnet works without API keys
- For live trading, add keys to `.env`

### Model training is slow

- Reduce `--days` or `--epochs`
- Use GPU if available (TensorFlow will auto-detect)

## 📚 Next Steps

1. **Optimize Strategy:** Adjust parameters in `.env`
2. **Add More Indicators:** Edit `ml/feature_engineering.py`
3. **Improve Model:** Try different architectures in `ml/lstm_signal_generator.py`
4. **Monitor Performance:** Use `/api/v1/signals` to track signals
5. **Deploy:** Set up on cloud server for 24/7 operation

## 🔗 Resources

- **API Docs:** <http://localhost:8000/docs>
- **GitHub:** <https://github.com/devyjones991-ai/MaxFlash>
- **Freqtrade Docs:** <https://www.freqtrade.io/>
- **CCXT Docs:** <https://docs.ccxt.com/>

## ⚠️ Disclaimer

Trading cryptocurrencies involves significant risk. This software is for educational purposes only. Always test thoroughly in testnet mode before risking real money. Past performance does not guarantee future results.

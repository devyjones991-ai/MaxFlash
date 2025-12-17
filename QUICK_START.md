# MaxFlash - Quick Start Guide

## ⚡ Fast Track to Production

**Time**: ~30 minutes
**Goal**: Deploy working trading system with realistic signals

---

## 🚀 Step 1: Train Model (5 min)

```bash
# Quick training (5 coins, 50 rounds)
python scripts/train_lightgbm_fixed.py --quick
```

**Output**:
```
✅ TRAINING COMPLETE - NO LOOK-AHEAD BIAS!

📊 Expected realistic performance:
  - Win Rate: 45-55% (NOT 100%!)
  - Profit Factor: 1.2-2.0 (NOT 999!)

Model saved: models/lightgbm_quick_fixed.pkl
```

---

## 📊 Step 2: Verify with Backtest (10 min)

```bash
# Walk-forward backtest on 5 coins
python scripts/run_walk_forward_backtest.py --coins 5
```

**Expected Results**:
```
REALISTIC RESULTS (NO LOOK-AHEAD BIAS)

Tested Symbols: 5
Total Trades: 250
Average Metrics:
  Win Rate: 48.5% (realistic!)
  Profit Factor: 1.42 (realistic!)
  Return: +3.2%
```

✅ If you see these numbers, everything is working correctly!
❌ If you see 100% win rate, you're using the old broken code!

---

## 🧹 Step 3: Clean Up (2 min)

```bash
# Preview cleanup
python scripts/cleanup_project.py --dry-run

# Execute cleanup
python scripts/cleanup_project.py
```

**Removes**:
- Old backtest files
- Python cache
- Temporary files
- Old models (keeps latest 3)

---

## 📦 Step 4: Deploy to Server (10 min)

### Option A: Automatic (Recommended)

```bash
python scripts/deploy_to_server.py
```

### Option B: Manual

```bash
# 1. Sync files
python scripts/sync_to_server.py

# 2. SSH to server
ssh devyjones@192.168.0.203 -p 22

# 3. Install dependencies
cd /home/devyjones/MaxFlash
python3 -m pip install -r requirements.txt --user

# 4. Setup services
sudo cp infra/*.service /etc/systemd/system/
sudo cp infra/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# 5. Start services
sudo systemctl start maxflash-bot
sudo systemctl start maxflash-dashboard
sudo systemctl start maxflash-retrain.timer
```

---

## ✅ Step 5: Verify Deployment (3 min)

### Check Services

```bash
ssh devyjones@192.168.0.203 -p 22

# Check status
sudo systemctl status maxflash-bot
sudo systemctl status maxflash-dashboard

# Check logs
sudo journalctl -u maxflash-bot -n 50
```

**Expected**:
```
● maxflash-bot.service - MaxFlash Telegram Bot v2
   Active: active (running) since ...

[OK] Bot started successfully
[OK] LightGBM model loaded
```

### Test Dashboard

Open: http://192.168.0.203:8050

**You should see**:
- Trading signals for top 55 pairs
- Signal strengths (BUY/SELL/HOLD)
- Risk management info

### Test Telegram Bot

1. Open Telegram
2. Find your bot
3. Send: `/start`
4. Send: `/signal BTC/USDT`

**Expected Response**:
```
🎯 BTC/USDT Signal

Direction: BUY
Confidence: 62%
Entry: $42,350
TP: $43,500 (+2.7%)
SL: $41,800 (-1.3%)
```

---

## 🎯 Common Issues

### Issue: SSH Connection Failed

```bash
# Test connection
ssh devyjones@192.168.0.203 -p 22 'echo OK'

# If fails, setup SSH key
ssh-keygen -t rsa -b 4096
ssh-copy-id -p 22 devyjones@192.168.0.203
```

### Issue: Model Not Found

```bash
# Check if model exists
ls -lh models/

# If missing, train again
python scripts/train_lightgbm_fixed.py --quick
```

### Issue: Dashboard Not Accessible

```bash
# On server, check if port is open
sudo netstat -tulpn | grep 8050

# Allow port in firewall
sudo ufw allow 8050/tcp
```

### Issue: Telegram Bot Not Responding

```bash
# Check .env file has token
cat .env | grep TELEGRAM_BOT_TOKEN

# Check bot service logs
sudo journalctl -u maxflash-bot -n 100
```

---

## 📊 Understanding Results

### Realistic Metrics

| Metric | Good | Bad | Your Goal |
|--------|------|-----|-----------|
| Win Rate | 45-55% | 100% | ~50% |
| Profit Factor | 1.2-2.0 | 999 | >1.3 |
| Avg Trade | +0.5% | +5% | ~+0.8% |
| Drawdown | 10-20% | 0% | <25% |

**Remember**: 100% win rate in backtest = broken system!

### Signal Quality

```
High Confidence (>70%): Take the trade
Medium Confidence (50-70%): Consider the trade
Low Confidence (<50%): Skip the trade
```

---

## 🔄 Daily Operations

### Morning Check (2 min)

```bash
# Check service status
python scripts/deploy_to_server.py --status

# View recent signals
# Open dashboard: http://192.168.0.203:8050
```

### Weekly Maintenance (10 min)

```bash
# SSH to server
ssh devyjones@192.168.0.203 -p 22

# Check logs for errors
sudo journalctl -u maxflash-bot --since "1 week ago" | grep ERROR

# Check disk space
df -h

# Clean old logs if needed
sudo journalctl --vacuum-time=7d
```

### Monthly Retraining (automatic)

The system auto-retrains daily at 02:00 UTC.

**Manual retrain**:
```bash
ssh devyjones@192.168.0.203 -p 22
cd /home/devyjones/MaxFlash
python3 scripts/auto_retrain_v2.py
```

---

## 🎓 Learning Path

### Beginner (Week 1)

1. Deploy system ✅
2. Monitor signals daily
3. Paper trade (no real money)
4. Track win rate manually

### Intermediate (Week 2-4)

1. Start with small capital
2. Trade only high confidence signals (>70%)
3. Always use stop losses
4. Review performance weekly

### Advanced (Month 2+)

1. Analyze which pairs perform best
2. Adjust confidence thresholds
3. Optimize position sizing
4. Consider multiple timeframes

---

## 📚 Next Steps

### Read Full Documentation

- [`README_FIXES.md`](README_FIXES.md) - What was fixed and why
- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) - Complete deployment guide
- [`scripts/README_TRAINING.md`](scripts/README_TRAINING.md) - Training details

### Explore Features

```bash
# Run full training (20 coins)
python scripts/train_lightgbm_fixed.py --coins 20

# Run comprehensive backtest
python scripts/run_walk_forward_backtest.py --coins 20

# Check signal integrator
python -c "from utils.signal_integrator import test_integration; test_integration()"
```

### Monitor Performance

```bash
# View backtest results
ls -lht backtest_results/

# Analyze specific result
cat backtest_results/walk_forward_20241217_*.csv
```

---

## 💡 Tips for Success

### Do's ✅

- ✅ Start small (2% position size)
- ✅ Always use stop losses
- ✅ Trade high confidence signals
- ✅ Keep trading journal
- ✅ Review weekly performance
- ✅ Accept 40-60% win rate as normal

### Don'ts ❌

- ❌ Don't expect 100% win rate
- ❌ Don't trade without stop loss
- ❌ Don't increase position after losses
- ❌ Don't trade every signal
- ❌ Don't panic during drawdowns
- ❌ Don't ignore risk management

---

## 🆘 Getting Help

### Check Logs

```bash
# Bot logs
sudo journalctl -u maxflash-bot -f

# Dashboard logs
sudo journalctl -u maxflash-dashboard -f

# Retrain logs
sudo journalctl -u maxflash-retrain -f
```

### Debug Mode

```bash
# Run bot in debug mode
python run_bot_v2.py --debug

# Run dashboard in debug mode
python -m web_interface.dashboard_v2 --debug
```

### System Health

```bash
# Check server resources
ssh devyjones@192.168.0.203 -p 22
htop  # or: top

# Check service health
python -c "from services.monitoring.health_monitor import check_health; check_health()"
```

---

## 🎉 You're Ready!

### Checklist

- [ ] Model trained (no look-ahead bias)
- [ ] Backtest shows realistic results (45-55% WR)
- [ ] Project cleaned up
- [ ] Services deployed to server
- [ ] Dashboard accessible
- [ ] Telegram bot responding
- [ ] Logs showing no errors

### What's Running

```
Server: 192.168.0.203

✅ Telegram Bot (background)
   - Sends signals
   - Risk management
   - User commands

✅ Dashboard (http://192.168.0.203:8050)
   - 55 trading pairs
   - Live signals
   - Visual analysis

✅ Auto-retrain (daily 02:00 UTC)
   - Keeps model fresh
   - Adapts to market
   - Logs results
```

---

**Ready to trade? Remember: Consistent beats perfect!** 🚀

*For detailed info, see [README_FIXES.md](README_FIXES.md) and [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)*

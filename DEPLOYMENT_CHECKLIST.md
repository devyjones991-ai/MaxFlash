# MaxFlash Deployment Checklist

## 🎯 Pre-Deployment

### Local Machine Setup

- [ ] Python 3.9+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with API keys
- [ ] SSH access to server configured
- [ ] Git repository clean (no uncommitted changes)

### Code Verification

- [ ] All tests pass (if applicable)
- [ ] No look-ahead bias in labeling (`ml/labeling_fixed.py`)
- [ ] Walk-forward backtest implemented
- [ ] Model training uses realistic labels
- [ ] Code reviewed and approved

---

## 🧪 Local Testing

### 1. Train Model (Fixed Version)

```bash
python scripts/train_lightgbm_fixed.py --quick
```

**Expected Output**:
- [ ] Training completes without errors
- [ ] Model saved to `models/lightgbm_quick_fixed.pkl`
- [ ] Accuracy ~60-75% (not 100%)
- [ ] Class distribution shows BUY/SELL/HOLD all present

### 2. Run Walk-Forward Backtest

```bash
python scripts/run_walk_forward_backtest.py --coins 5
```

**Expected Output**:
- [ ] Backtest completes without errors
- [ ] Win Rate: 45-55% (REALISTIC!)
- [ ] Profit Factor: 1.2-2.0 (REALISTIC!)
- [ ] Results saved to `backtest_results/`

### 3. Cleanup Project

```bash
python scripts/cleanup_project.py
```

**Expected Output**:
- [ ] Old `__pycache__` removed
- [ ] Temporary files removed
- [ ] Old models removed (keep latest 3)
- [ ] Required directories created

---

## 🚀 Deployment to Server

### Server Information

```
Host: 192.168.0.203
Port: 22
User: devyjones
Password: 19Maxon91!
Remote Path: /home/devyjones/MaxFlash
```

### 1. Verify SSH Connection

```bash
ssh devyjones@192.168.0.203 -p 22 'echo Connection OK'
```

**Expected Output**:
- [ ] "Connection OK" printed
- [ ] No password prompt (if SSH key configured)

### 2. Deploy Files

#### Option A: Automatic Deployment (Recommended)

```bash
python scripts/deploy_to_server.py
```

**Expected Steps**:
- [ ] SSH connection verified
- [ ] Files synced to server
- [ ] Dependencies installed
- [ ] Services configured
- [ ] Services started
- [ ] Status check passed

#### Option B: Manual Deployment

```bash
# 1. Sync files
python scripts/sync_to_server.py

# 2. Install dependencies
ssh devyjones@192.168.0.203 -p 22
cd /home/devyjones/MaxFlash
python3 -m pip install -r requirements.txt --user

# 3. Setup services
sudo cp infra/*.service /etc/systemd/system/
sudo cp infra/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# 4. Start services
sudo systemctl start maxflash-bot
sudo systemctl start maxflash-dashboard
sudo systemctl start maxflash-retrain.timer
sudo systemctl enable maxflash-bot
sudo systemctl enable maxflash-dashboard
sudo systemctl enable maxflash-retrain.timer
```

---

## ✅ Verification

### 1. Check Services Running

```bash
# On server
ssh devyjones@192.168.0.203 -p 22
sudo systemctl status maxflash-bot
sudo systemctl status maxflash-dashboard
sudo systemctl status maxflash-retrain.timer
```

**Expected**:
- [ ] All services show `active (running)`
- [ ] No error messages in status

### 2. Check Logs

```bash
# Bot logs
sudo journalctl -u maxflash-bot -n 50

# Dashboard logs
sudo journalctl -u maxflash-dashboard -n 50
```

**Expected**:
- [ ] No ERROR level messages
- [ ] Bot started successfully
- [ ] Model loaded successfully
- [ ] Dashboard running on port 8050

### 3. Test Dashboard

Open browser: http://192.168.0.203:8050

**Checklist**:
- [ ] Dashboard loads successfully
- [ ] Trading pairs displayed (55 pairs)
- [ ] Signals shown (BUY/SELL/HOLD)
- [ ] No error messages
- [ ] Data updates (not stale)
- [ ] Mobile view works

### 4. Test Telegram Bot

#### Initial Test

1. Open Telegram
2. Find your bot
3. Send `/start`

**Expected**:
- [ ] Bot responds with welcome message
- [ ] Menu buttons appear
- [ ] No error messages

#### Signal Test

Send: `/signal BTC/USDT`

**Expected**:
- [ ] Signal generated
- [ ] Direction shown (BUY/SELL/HOLD)
- [ ] Confidence percentage shown
- [ ] Entry/TP/SL prices shown
- [ ] Reasonable values (not 100% confidence)

#### Settings Test

Send: `/settings`

**Expected**:
- [ ] Settings menu appears
- [ ] Options available:
  - Min confidence adjustment
  - Symbol selection
  - Notifications toggle

### 5. Test Auto-Retrain

```bash
# Check timer is active
sudo systemctl status maxflash-retrain.timer

# Manually trigger (optional)
sudo systemctl start maxflash-retrain.service

# Check logs
sudo journalctl -u maxflash-retrain -f
```

**Expected**:
- [ ] Timer scheduled (next run shown)
- [ ] Manual run completes successfully (if tested)
- [ ] Model retrained
- [ ] New model saved

---

## 🔍 Performance Monitoring

### Metrics to Watch (First Week)

| Metric | Target | Check |
|--------|--------|-------|
| Win Rate | 45-55% | [ ] |
| Profit Factor | >1.2 | [ ] |
| Avg Trade Return | 0.3-1.0% | [ ] |
| Max Drawdown | <25% | [ ] |
| Signals/Day | 10-30 | [ ] |

### Daily Checks

- [ ] Service status (all running)
- [ ] No errors in logs
- [ ] Dashboard accessible
- [ ] Bot responding
- [ ] Signal quality reasonable

### Weekly Review

- [ ] Review trading performance
- [ ] Check model accuracy
- [ ] Analyze worst performing pairs
- [ ] Adjust confidence threshold if needed
- [ ] Review and clear old logs

---

## 🚨 Troubleshooting

### Service Won't Start

```bash
# Full error log
sudo journalctl -u maxflash-bot -xe

# Common fixes:
# 1. Missing dependencies
python3 -m pip install -r requirements.txt --user

# 2. Permission issues
sudo chown -R devyjones:devyjones /home/devyjones/MaxFlash

# 3. Port in use
sudo lsof -i :8050
sudo kill -9 <PID>
```

**Checklist**:
- [ ] Dependencies installed
- [ ] Permissions correct
- [ ] Ports available
- [ ] .env file present
- [ ] Model files exist

### Dashboard Not Accessible

```bash
# Check port listening
sudo netstat -tulpn | grep 8050

# Check firewall
sudo ufw status
sudo ufw allow 8050/tcp
```

**Checklist**:
- [ ] Service running
- [ ] Port 8050 open
- [ ] Firewall allows access
- [ ] No network issues

### Bot Not Responding

```bash
# Check bot connection
python3 -c "import telegram; print(telegram.__version__)"

# Check token
cat .env | grep TELEGRAM_BOT_TOKEN

# Test manually
python3 -c "from bots.telegram.bot_v2 import test_bot; test_bot()"
```

**Checklist**:
- [ ] Token configured
- [ ] python-telegram-bot installed
- [ ] Network access to Telegram API
- [ ] Bot service running

### Model Not Found

```bash
# Check models directory
ls -lh /home/devyjones/MaxFlash/models/

# Retrain if missing
python3 scripts/train_lightgbm_fixed.py --quick
```

**Checklist**:
- [ ] Model file exists
- [ ] Model path correct in code
- [ ] Model not corrupted
- [ ] Metadata file exists

---

## 📊 Success Criteria

### Must Have ✅

- [x] No look-ahead bias in code
- [ ] Model trained successfully
- [ ] Backtest shows realistic metrics (45-55% WR)
- [ ] All services running on server
- [ ] Dashboard accessible
- [ ] Bot responding to commands
- [ ] Auto-retrain configured

### Should Have 💡

- [ ] SSH key authentication (not password)
- [ ] Firewall configured
- [ ] Logs rotating (not filling disk)
- [ ] Monitoring alerts (optional)
- [ ] Backup strategy

### Nice to Have 🎁

- [ ] API endpoint (FastAPI)
- [ ] Multiple exchange support
- [ ] Advanced analytics dashboard
- [ ] Performance tracking database
- [ ] Automated testing

---

## 🔄 Post-Deployment

### Day 1

- [ ] Monitor logs hourly
- [ ] Check service status every 4 hours
- [ ] Test bot functionality
- [ ] Review first signals generated
- [ ] Document any issues

### Week 1

- [ ] Daily service check
- [ ] Review signal quality
- [ ] Track win rate manually
- [ ] Adjust confidence if needed
- [ ] Review error logs

### Month 1

- [ ] Analyze performance metrics
- [ ] Compare backtest vs live results
- [ ] Identify best performing pairs
- [ ] Optimize parameters if needed
- [ ] Plan improvements

---

## 📝 Sign-Off

### Developer

- [ ] Code reviewed and tested
- [ ] Documentation complete
- [ ] No known critical issues
- [ ] Deployment tested locally

**Name**: _______________
**Date**: _______________
**Signature**: _______________

### DevOps/Admin

- [ ] Server configured correctly
- [ ] Services running
- [ ] Monitoring in place
- [ ] Backups configured

**Name**: _______________
**Date**: _______________
**Signature**: _______________

---

## 📚 Reference Documents

- [README_FIXES.md](README_FIXES.md) - What was fixed and why
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Detailed deployment guide
- [QUICK_START.md](QUICK_START.md) - Quick start guide

---

## 🆘 Emergency Contacts

### Support Channels

- GitHub Issues: (if applicable)
- Email: (if applicable)
- Telegram: (if applicable)

### Rollback Procedure

If deployment fails:

```bash
# 1. Stop services
sudo systemctl stop maxflash-bot
sudo systemctl stop maxflash-dashboard

# 2. Restore previous version
cd /home/devyjones/MaxFlash
git stash
git checkout <previous-commit>

# 3. Restart services
sudo systemctl daemon-reload
sudo systemctl start maxflash-bot
sudo systemctl start maxflash-dashboard
```

---

**Deployment Date**: _______________
**Version**: 2.0 (Fixed - No Look-Ahead Bias)
**Status**: [ ] Success [ ] Failed [ ] Partial

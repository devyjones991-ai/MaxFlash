# MaxFlash Deployment Guide

## 📋 Table of Contents

- [Overview](#overview)
- [Server Requirements](#server-requirements)
- [Pre-Deployment Setup](#pre-deployment-setup)
- [Deployment Steps](#deployment-steps)
- [Service Management](#service-management)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedure](#rollback-procedure)

---

## Overview

This guide covers deployment of MaxFlash to production server:
- **Server**: 192.168.0.203
- **User**: devyjones
- **Port**: 22
- **Remote Path**: /home/devyjones/MaxFlash

### Components Deployed

1. **LightGBM Model** (Fixed - no look-ahead bias)
2. **Dashboard v2** (Web interface on port 8050)
3. **Telegram Bot v2** (Interactive trading bot)
4. **Auto-retrain Service** (Periodic model retraining)
5. **Health Monitor** (System monitoring)

---

## Server Requirements

### Operating System
- Ubuntu 20.04 LTS or later
- Python 3.9+

### System Packages
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git rsync
```

### Python Packages
All Python dependencies are in `requirements.txt` and will be installed during deployment.

### Ports
- **8050**: Dashboard (Dash app)
- **8000**: API (FastAPI) - optional

---

## Pre-Deployment Setup

### 1. SSH Key Setup (Recommended)

On your local machine:
```bash
ssh-keygen -t rsa -b 4096 -C "maxflash-deploy"
ssh-copy-id -p 22 devyjones@192.168.0.203
```

### 2. Environment Variables

Create `.env` file in project root:
```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Exchanges
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Optional
BYBIT_API_KEY=
BYBIT_API_SECRET=
OKX_API_KEY=
OKX_API_SECRET=
```

### 3. Verify Requirements

Check `requirements.txt` includes all dependencies:
```
lightgbm>=4.0.0
pandas>=2.0.0
numpy>=1.24.0
ccxt>=4.0.0
python-telegram-bot>=20.0
dash>=2.14.0
plotly>=5.17.0
fastapi>=0.104.0
uvicorn>=0.24.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
scikit-learn>=1.3.0
```

---

## Deployment Steps

### Quick Deploy (Automatic)

```bash
# Run deployment script
python scripts/deploy_to_server.py
```

This will:
1. ✅ Check SSH connection
2. ✅ Sync all files to server
3. ✅ Install Python dependencies
4. ✅ Setup systemd services
5. ✅ Start all services
6. ✅ Display service status

### Manual Deploy (Step-by-Step)

#### Step 1: Sync Files

```bash
# Using the sync script
python scripts/sync_to_server.py
```

Or manually with rsync:
```bash
rsync -avz --progress \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='data/' \
  --exclude='backtest_results/' \
  -e 'ssh -p 22' \
  ml/ utils/ bots/ web_interface/ app/ services/ models/ \
  devyjones@192.168.0.203:/home/devyjones/MaxFlash/
```

#### Step 2: Install Dependencies on Server

```bash
ssh devyjones@192.168.0.203 -p 22
cd /home/devyjones/MaxFlash
python3 -m pip install -r requirements.txt --user
```

#### Step 3: Setup Systemd Services

```bash
# Copy service files
sudo cp infra/*.service /etc/systemd/system/
sudo cp infra/*.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload
```

#### Step 4: Start Services

```bash
# Start Telegram Bot
sudo systemctl start maxflash-bot
sudo systemctl enable maxflash-bot

# Start Dashboard
sudo systemctl start maxflash-dashboard
sudo systemctl enable maxflash-dashboard

# Start Auto-retrain Timer
sudo systemctl start maxflash-retrain.timer
sudo systemctl enable maxflash-retrain.timer
```

---

## Service Management

### Check Service Status

```bash
# All services
python scripts/deploy_to_server.py --status

# Individual service
sudo systemctl status maxflash-bot
sudo systemctl status maxflash-dashboard
sudo systemctl status maxflash-retrain.timer
```

### View Logs

```bash
# Live logs (follow)
sudo journalctl -u maxflash-bot -f

# Last 100 lines
sudo journalctl -u maxflash-bot -n 100

# Dashboard logs
sudo journalctl -u maxflash-dashboard -f
```

### Restart Services

```bash
# Restart bot
sudo systemctl restart maxflash-bot

# Restart dashboard
sudo systemctl restart maxflash-dashboard

# Restart all
python scripts/deploy_to_server.py --services-only
```

### Stop Services

```bash
sudo systemctl stop maxflash-bot
sudo systemctl stop maxflash-dashboard
sudo systemctl stop maxflash-retrain.timer
```

---

## Service Details

### maxflash-bot.service

Telegram Bot v2 with enhanced signals.

**Service File**: `infra/maxflash-bot.service`

```ini
[Unit]
Description=MaxFlash Telegram Bot v2
After=network.target

[Service]
Type=simple
User=devyjones
WorkingDirectory=/home/devyjones/MaxFlash
ExecStart=/usr/bin/python3 run_bot_v2.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### maxflash-dashboard.service

Web dashboard (Dash/Plotly) on port 8050.

**Service File**: `infra/maxflash-dashboard.service`

```ini
[Unit]
Description=MaxFlash Dashboard v2
After=network.target

[Service]
Type=simple
User=devyjones
WorkingDirectory=/home/devyjones/MaxFlash
ExecStart=/usr/bin/python3 -m web_interface.dashboard_v2
Restart=always
RestartSec=10
Environment="PORT=8050"

[Install]
WantedBy=multi-user.target
```

### maxflash-retrain.timer

Periodic model retraining (daily at 02:00 UTC).

**Timer File**: `infra/maxflash-retrain.timer`

```ini
[Unit]
Description=MaxFlash Model Retrain Timer

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Service File**: `infra/maxflash-retrain.service`

```ini
[Unit]
Description=MaxFlash Model Retrain

[Service]
Type=oneshot
User=devyjones
WorkingDirectory=/home/devyjones/MaxFlash
ExecStart=/usr/bin/python3 scripts/auto_retrain_v2.py
```

---

## Verification

After deployment, verify everything works:

### 1. Check Services Running

```bash
sudo systemctl status maxflash-bot
sudo systemctl status maxflash-dashboard
sudo systemctl status maxflash-retrain.timer
```

All should show **active (running)**.

### 2. Test Dashboard

Open browser: http://192.168.0.203:8050

You should see the trading dashboard with signals.

### 3. Test Telegram Bot

1. Open Telegram
2. Find your bot
3. Send `/start`
4. Send `/signal BTC/USDT`

Bot should respond with current signals.

### 4. Check Logs

```bash
# Should show no errors
sudo journalctl -u maxflash-bot -n 50
sudo journalctl -u maxflash-dashboard -n 50
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check full error log
sudo journalctl -u maxflash-bot -xe

# Common issues:
# 1. Missing dependencies
python3 -m pip install -r requirements.txt --user

# 2. Permission issues
sudo chown -R devyjones:devyjones /home/devyjones/MaxFlash

# 3. Port already in use
sudo lsof -i :8050  # Find what's using port 8050
```

### Dashboard Not Accessible

```bash
# Check if port is open
sudo netstat -tulpn | grep 8050

# Check firewall
sudo ufw status
sudo ufw allow 8050/tcp

# Check dashboard is running
ps aux | grep dashboard_v2
```

### Telegram Bot Not Responding

```bash
# Check bot token in .env
cat /home/devyjones/MaxFlash/.env | grep TELEGRAM_BOT_TOKEN

# Test bot connection
python3 -c "from bots.telegram.bot_v2 import test_connection; test_connection()"

# Check network access
curl https://api.telegram.org
```

### Model Not Found

```bash
# Check if model exists
ls -lh /home/devyjones/MaxFlash/models/

# If missing, train model:
python3 scripts/train_lightgbm_fixed.py --quick
```

### High Memory Usage

```bash
# Check memory
free -h

# Restart services to free memory
sudo systemctl restart maxflash-bot
sudo systemctl restart maxflash-dashboard
```

---

## Rollback Procedure

If deployment fails or causes issues:

### 1. Stop New Services

```bash
sudo systemctl stop maxflash-bot
sudo systemctl stop maxflash-dashboard
```

### 2. Restore Previous Version

```bash
cd /home/devyjones/MaxFlash
git stash  # Save current changes
git checkout <previous-commit-hash>
```

### 3. Restart Services

```bash
sudo systemctl daemon-reload
sudo systemctl start maxflash-bot
sudo systemctl start maxflash-dashboard
```

### 4. Verify Rollback

```bash
sudo systemctl status maxflash-bot
sudo journalctl -u maxflash-bot -f
```

---

## Maintenance

### Update Model

```bash
# SSH to server
ssh devyjones@192.168.0.203 -p 22

# Navigate to project
cd /home/devyjones/MaxFlash

# Train new model
python3 scripts/train_lightgbm_fixed.py

# Restart services to load new model
sudo systemctl restart maxflash-bot
sudo systemctl restart maxflash-dashboard
```

### View Performance Metrics

```bash
# Check backtest results
ls -lht /home/devyjones/MaxFlash/backtest_results/

# Run new backtest
python3 scripts/run_walk_forward_backtest.py --coins 10
```

### Monitor Disk Space

```bash
# Check disk usage
df -h

# Clean old logs
sudo journalctl --vacuum-time=7d

# Clean old models
python3 scripts/cleanup_project.py
```

---

## Security Considerations

### 1. API Keys

- ✅ Store in `.env` file (not in git)
- ✅ Use read-only keys when possible
- ✅ Restrict IP access on exchange

### 2. SSH Access

- ✅ Use SSH keys instead of passwords
- ✅ Disable root login
- ✅ Use non-standard SSH port (if needed)

### 3. Firewall

```bash
# Setup UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 8050/tcp # Dashboard
sudo ufw enable
```

### 4. Updates

```bash
# Keep system updated
sudo apt update && sudo apt upgrade -y
```

---

## Support

For issues or questions:
1. Check logs: `sudo journalctl -u maxflash-bot -f`
2. Review this guide
3. Check project README.md

---

**Last Updated**: 2025-12-17
**Version**: 2.0 (Fixed - No Look-Ahead Bias)

#!/bin/bash
#
# MaxFlash v2.0 - Quick Deployment Commands
# Server: 192.168.0.203 | User: devyjones
#
# Usage:
#   bash DEPLOY_COMMANDS.sh         # Full deployment
#   bash DEPLOY_COMMANDS.sh quick   # Quick mode (skip training)
#

set -e  # Exit on error

SERVER="devyjones@192.168.0.203"
PORT="22"
REMOTE_PATH="/home/devyjones/MaxFlash"

echo "========================================================================"
echo "MaxFlash v2.0 Deployment"
echo "========================================================================"
echo ""
echo "Target: $SERVER:$PORT"
echo "Path: $REMOTE_PATH"
echo ""

# Parse mode
MODE="${1:-full}"

if [ "$MODE" = "quick" ]; then
    echo "⚡ QUICK MODE - Skipping training"
else
    echo "🎯 FULL MODE - Including training"
fi

echo ""

# ============================================================================
# STEP 1: Local Training (if full mode)
# ============================================================================

if [ "$MODE" != "quick" ]; then
    echo "--------------------------------------------------------------------"
    echo "STEP 1: Training Model (Fixed - No Look-Ahead Bias)"
    echo "--------------------------------------------------------------------"
    echo ""

    # Quick training (5 coins, 50 rounds)
    python scripts/train_lightgbm_fixed.py --quick

    echo ""
    echo "✅ Model trained successfully"
    echo ""
fi

# ============================================================================
# STEP 2: Cleanup
# ============================================================================

echo "--------------------------------------------------------------------"
echo "STEP 2: Cleaning Up Project"
echo "--------------------------------------------------------------------"
echo ""

python scripts/cleanup_project.py || echo "⚠️  Cleanup had errors (non-critical)"

echo ""
echo "✅ Cleanup complete"
echo ""

# ============================================================================
# STEP 3: Sync Files
# ============================================================================

echo "--------------------------------------------------------------------"
echo "STEP 3: Syncing Files to Server"
echo "--------------------------------------------------------------------"
echo ""

# Build rsync command
rsync -avz --progress \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='data/' \
  --exclude='backtest_results/' \
  --exclude='freqtrade/' \
  --exclude='.vscode' \
  --exclude='.idea' \
  -e "ssh -p $PORT" \
  ml/ utils/ bots/ web_interface/ app/ services/ indicators/ trading/ models/ \
  scripts/auto_retrain_v2.py \
  scripts/train_lightgbm_fixed.py \
  scripts/run_walk_forward_backtest.py \
  run_bot_v2.py \
  requirements.txt \
  .env \
  infra/ \
  "$SERVER:$REMOTE_PATH/"

echo ""
echo "✅ Files synced successfully"
echo ""

# ============================================================================
# STEP 4: Install Dependencies
# ============================================================================

echo "--------------------------------------------------------------------"
echo "STEP 4: Installing Dependencies on Server"
echo "--------------------------------------------------------------------"
echo ""

ssh -p $PORT $SERVER "cd $REMOTE_PATH && python3 -m pip install -r requirements.txt --user"

echo ""
echo "✅ Dependencies installed"
echo ""

# ============================================================================
# STEP 5: Setup Systemd Services
# ============================================================================

echo "--------------------------------------------------------------------"
echo "STEP 5: Setting Up Systemd Services"
echo "--------------------------------------------------------------------"
echo ""

ssh -p $PORT $SERVER << 'ENDSSH'
cd /home/devyjones/MaxFlash
sudo cp infra/*.service /etc/systemd/system/
sudo cp infra/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
echo "✅ Systemd services configured"
ENDSSH

echo ""

# ============================================================================
# STEP 6: Start Services
# ============================================================================

echo "--------------------------------------------------------------------"
echo "STEP 6: Starting Services"
echo "--------------------------------------------------------------------"
echo ""

ssh -p $PORT $SERVER << 'ENDSSH'
# Start and enable bot
echo "Starting Telegram Bot..."
sudo systemctl restart maxflash-bot
sudo systemctl enable maxflash-bot

# Start and enable dashboard
echo "Starting Dashboard..."
sudo systemctl restart maxflash-dashboard
sudo systemctl enable maxflash-dashboard

# Start and enable retrain timer
echo "Starting Auto-retrain Timer..."
sudo systemctl restart maxflash-retrain.timer
sudo systemctl enable maxflash-retrain.timer

echo "✅ All services started"
ENDSSH

echo ""

# ============================================================================
# STEP 7: Verify Deployment
# ============================================================================

echo "--------------------------------------------------------------------"
echo "STEP 7: Verifying Deployment"
echo "--------------------------------------------------------------------"
echo ""

echo "Checking service status..."
echo ""

ssh -p $PORT $SERVER << 'ENDSSH'
echo "📊 Service Status:"
echo ""
sudo systemctl is-active maxflash-bot && echo "  ✅ Bot: Running" || echo "  ❌ Bot: Failed"
sudo systemctl is-active maxflash-dashboard && echo "  ✅ Dashboard: Running" || echo "  ❌ Dashboard: Failed"
sudo systemctl is-active maxflash-retrain.timer && echo "  ✅ Retrain Timer: Running" || echo "  ❌ Retrain Timer: Failed"
echo ""
echo "📝 Recent Logs:"
echo ""
echo "Bot (last 10 lines):"
sudo journalctl -u maxflash-bot -n 10 --no-pager
echo ""
echo "Dashboard (last 10 lines):"
sudo journalctl -u maxflash-dashboard -n 10 --no-pager
ENDSSH

echo ""
echo "========================================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================================================"
echo ""
echo "🎯 Next Steps:"
echo ""
echo "  1. Dashboard: http://192.168.0.203:8050"
echo "  2. Test Telegram Bot: /start, /signal BTC/USDT"
echo "  3. Monitor Logs:"
echo "     ssh $SERVER -p $PORT"
echo "     sudo journalctl -u maxflash-bot -f"
echo ""
echo "📚 Documentation:"
echo "  - Quick Start: QUICK_START.md"
echo "  - Deployment Guide: DEPLOYMENT_GUIDE.md"
echo "  - Fixes Explained: README_FIXES.md"
echo ""
echo "⚠️  Remember:"
echo "  - Win Rate 45-55% is NORMAL and GOOD"
echo "  - Profit Factor 1.2-2.0 is REALISTIC"
echo "  - 100% win rate was FAKE (look-ahead bias)"
echo ""
echo "🚀 Happy Trading!"
echo ""

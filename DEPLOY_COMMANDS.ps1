# MaxFlash v2.0 - Quick Deployment Commands (PowerShell)
# Server: 192.168.0.203 | User: devyjones
#
# Usage:
#   .\DEPLOY_COMMANDS.ps1         # Full deployment
#   .\DEPLOY_COMMANDS.ps1 -Quick  # Quick mode (skip training)
#

param(
    [switch]$Quick
)

$ErrorActionPreference = "Stop"

$SERVER = "devyjones@192.168.0.203"
$PORT = "22"
$REMOTE_PATH = "/home/devyjones/MaxFlash"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "MaxFlash v2.0 Deployment" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Target: $SERVER:$PORT"
Write-Host "Path: $REMOTE_PATH"
Write-Host ""

if ($Quick) {
    Write-Host "⚡ QUICK MODE - Skipping training" -ForegroundColor Yellow
} else {
    Write-Host "🎯 FULL MODE - Including training" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# STEP 1: Local Training (if full mode)
# ============================================================================

if (-not $Quick) {
    Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "STEP 1: Training Model (Fixed - No Look-Ahead Bias)" -ForegroundColor Cyan
    Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host ""

    python scripts/train_lightgbm_fixed.py --quick

    Write-Host ""
    Write-Host "✅ Model trained successfully" -ForegroundColor Green
    Write-Host ""
}

# ============================================================================
# STEP 2: Cleanup
# ============================================================================

Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "STEP 2: Cleaning Up Project" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

try {
    python scripts/cleanup_project.py
} catch {
    Write-Host "⚠️  Cleanup had errors (non-critical)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Cleanup complete" -ForegroundColor Green
Write-Host ""

# ============================================================================
# STEP 3: Sync Files (Using Python script - rsync alternative)
# ============================================================================

Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "STEP 3: Syncing Files to Server" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

# Check if rsync available (via WSL or Git Bash)
$hasRsync = (Get-Command rsync -ErrorAction SilentlyContinue)

if ($hasRsync) {
    Write-Host "Using rsync..." -ForegroundColor Green

    rsync -avz --progress `
      --exclude='__pycache__' `
      --exclude='*.pyc' `
      --exclude='.git' `
      --exclude='data/' `
      --exclude='backtest_results/' `
      --exclude='freqtrade/' `
      --exclude='.vscode' `
      --exclude='.idea' `
      -e "ssh -p $PORT" `
      ml/ utils/ bots/ web_interface/ app/ services/ indicators/ trading/ models/ `
      scripts/auto_retrain_v2.py `
      scripts/train_lightgbm_fixed.py `
      scripts/run_walk_forward_backtest.py `
      run_bot_v2.py `
      requirements.txt `
      .env `
      infra/ `
      "$($SERVER):$REMOTE_PATH/"
} else {
    Write-Host "Using Python sync script (rsync not available)..." -ForegroundColor Yellow

    # Use Python-based sync
    if (Test-Path "scripts/sync_to_server.py") {
        python scripts/sync_to_server.py
    } else {
        Write-Host "❌ Neither rsync nor sync_to_server.py found!" -ForegroundColor Red
        Write-Host "Install Git for Windows (includes rsync) or create sync_to_server.py" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "✅ Files synced successfully" -ForegroundColor Green
Write-Host ""

# ============================================================================
# STEP 4: Install Dependencies
# ============================================================================

Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "STEP 4: Installing Dependencies on Server" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

ssh -p $PORT $SERVER "cd $REMOTE_PATH && python3 -m pip install -r requirements.txt --user"

Write-Host ""
Write-Host "✅ Dependencies installed" -ForegroundColor Green
Write-Host ""

# ============================================================================
# STEP 5: Setup Systemd Services
# ============================================================================

Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "STEP 5: Setting Up Systemd Services" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

$setupScript = @'
cd /home/devyjones/MaxFlash
sudo cp infra/*.service /etc/systemd/system/
sudo cp infra/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
echo "✅ Systemd services configured"
'@

ssh -p $PORT $SERVER $setupScript

Write-Host ""

# ============================================================================
# STEP 6: Start Services
# ============================================================================

Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "STEP 6: Starting Services" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

$startScript = @'
echo "Starting Telegram Bot..."
sudo systemctl restart maxflash-bot
sudo systemctl enable maxflash-bot

echo "Starting Dashboard..."
sudo systemctl restart maxflash-dashboard
sudo systemctl enable maxflash-dashboard

echo "Starting Auto-retrain Timer..."
sudo systemctl restart maxflash-retrain.timer
sudo systemctl enable maxflash-retrain.timer

echo "✅ All services started"
'@

ssh -p $PORT $SERVER $startScript

Write-Host ""

# ============================================================================
# STEP 7: Verify Deployment
# ============================================================================

Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "STEP 7: Verifying Deployment" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking service status..." -ForegroundColor Yellow
Write-Host ""

$verifyScript = @'
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
'@

ssh -p $PORT $SERVER $verifyScript

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎯 Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Dashboard: http://192.168.0.203:8050"
Write-Host "  2. Test Telegram Bot: /start, /signal BTC/USDT"
Write-Host "  3. Monitor Logs:"
Write-Host "     ssh $SERVER -p $PORT"
Write-Host "     sudo journalctl -u maxflash-bot -f"
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Yellow
Write-Host "  - Quick Start: QUICK_START.md"
Write-Host "  - Deployment Guide: DEPLOYMENT_GUIDE.md"
Write-Host "  - Fixes Explained: README_FIXES.md"
Write-Host ""
Write-Host "⚠️  Remember:" -ForegroundColor Yellow
Write-Host "  - Win Rate 45-55% is NORMAL and GOOD"
Write-Host "  - Profit Factor 1.2-2.0 is REALISTIC"
Write-Host "  - 100% win rate was FAKE (look-ahead bias)"
Write-Host ""
Write-Host "🚀 Happy Trading!" -ForegroundColor Green
Write-Host ""

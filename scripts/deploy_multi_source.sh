#!/bin/bash
# Deploy Multi-Source Data Provider to server
# Run this on the server after git pull

set -e

cd /home/devyjones/MaxFlash

echo "=== MaxFlash Multi-Source Deploy ==="
echo ""

# 1. Stop running processes
echo "[1/5] Stopping running processes..."
pkill -9 -f 'run_bot_v2' 2>/dev/null || true
pkill -9 -f 'dashboard_v2' 2>/dev/null || true
pkill -9 -f 'background_updater' 2>/dev/null || true
rm -f /tmp/maxflash_bot.pid /tmp/maxflash_bg_updater.pid 2>/dev/null || true
sleep 2

# 2. Pull latest code
echo "[2/5] Pulling latest code..."
git stash 2>/dev/null || true
git fetch origin main
git reset --hard origin/main
echo "Git updated to: $(git log -1 --oneline)"

# 3. Activate venv and check dependencies
echo "[3/5] Checking dependencies..."
source venv/bin/activate
pip install --quiet requests pandas 2>/dev/null || true

# 4. Create data directory
echo "[4/5] Creating data directory..."
mkdir -p data
chmod 755 data

# 5. Start services
echo "[5/5] Starting services..."

# Start background updater
nohup python web_interface/background_updater.py > logs/updater.log 2>&1 &
echo "Background updater started (PID: $!)"
sleep 2

# Start dashboard
nohup python web_interface/dashboard_v2.py > logs/dashboard.log 2>&1 &
echo "Dashboard started (PID: $!)"

echo ""
echo "=== Deploy completed! ==="
echo ""
echo "Check logs:"
echo "  tail -f logs/updater.log"
echo "  tail -f logs/dashboard.log"
echo ""
echo "Dashboard URL: http://192.168.0.203:8050"

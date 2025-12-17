#!/bin/bash
#
# MaxFlash Server Deployment Script
# Usage: ./scripts/deploy_server.sh
#

set -e

# Configuration
SERVER_USER="devyjones"
SERVER_HOST="192.168.0.203"
SERVER_PATH="/home/devyjones/MaxFlash"
LOCAL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  MaxFlash Server Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if sshpass is available for password auth
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}Note: sshpass not found. You'll be prompted for password.${NC}"
    SSH_CMD="ssh"
    SCP_CMD="scp"
    RSYNC_CMD="rsync"
else
    echo -e "${YELLOW}Enter server password:${NC}"
    read -s SERVER_PASS
    SSH_CMD="sshpass -p '$SERVER_PASS' ssh"
    SCP_CMD="sshpass -p '$SERVER_PASS' scp"
    RSYNC_CMD="sshpass -p '$SERVER_PASS' rsync"
fi

SSH_TARGET="${SERVER_USER}@${SERVER_HOST}"

echo ""
echo -e "${YELLOW}Step 1: Stopping existing services...${NC}"
ssh ${SSH_TARGET} "sudo systemctl stop maxflash-dashboard maxflash-bot maxflash-retrain.timer 2>/dev/null || true"

echo ""
echo -e "${YELLOW}Step 2: Creating backup of existing installation...${NC}"
ssh ${SSH_TARGET} "if [ -d ${SERVER_PATH} ]; then mv ${SERVER_PATH} ${SERVER_PATH}_backup_\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true; fi"

echo ""
echo -e "${YELLOW}Step 3: Creating directory structure...${NC}"
ssh ${SSH_TARGET} "mkdir -p ${SERVER_PATH}"

echo ""
echo -e "${YELLOW}Step 4: Uploading files...${NC}"
rsync -avz --progress \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude 'venv' \
    --exclude '.venv' \
    --exclude 'node_modules' \
    --exclude '*.egg-info' \
    --exclude '.pytest_cache' \
    --exclude '.mypy_cache' \
    --exclude '*.db' \
    --exclude 'logs/*.log' \
    --exclude 'freqtrade' \
    "${LOCAL_PATH}/" "${SSH_TARGET}:${SERVER_PATH}/"

echo ""
echo -e "${YELLOW}Step 5: Setting up Python environment...${NC}"
ssh ${SSH_TARGET} << 'ENDSSH'
cd /home/devyjones/MaxFlash

# Install Python 3.11 if not present
if ! command -v python3.11 &> /dev/null; then
    echo "Installing Python 3.11..."
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3-pip
fi

# Create virtual environment
python3.11 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Python environment ready!"
ENDSSH

echo ""
echo -e "${YELLOW}Step 6: Setting up .env file...${NC}"
ssh ${SSH_TARGET} << 'ENDSSH'
cd /home/devyjones/MaxFlash

if [ ! -f .env ]; then
    # Create .env from template
    cat > .env << 'ENVFILE'
TELEGRAM_BOT_TOKEN=8274253718:AAGa8juUeXf1jXP7BUZ3o_t-fpK-3BADxew
DASHBOARD_PORT=8050
DATABASE_URL=sqlite+aiosqlite:///./maxflash.db
SECRET_KEY=$(openssl rand -hex 32)
USE_TESTNET=true
RISK_PROFILE=BALANCED
USE_ML_FILTER=true
SIGNAL_CONFIDENCE_THRESHOLD=0.7
ENVFILE
    echo ".env file created"
else
    echo ".env file already exists, keeping existing configuration"
fi
ENDSSH

echo ""
echo -e "${YELLOW}Step 7: Installing systemd services...${NC}"
ssh ${SSH_TARGET} << 'ENDSSH'
cd /home/devyjones/MaxFlash

# Copy service files
sudo cp infra/maxflash-dashboard.service /etc/systemd/system/
sudo cp infra/maxflash-bot.service /etc/systemd/system/
sudo cp infra/maxflash-retrain.service /etc/systemd/system/
sudo cp infra/maxflash-retrain.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable maxflash-dashboard
sudo systemctl enable maxflash-bot
sudo systemctl enable maxflash-retrain.timer

echo "Systemd services installed!"
ENDSSH

echo ""
echo -e "${YELLOW}Step 8: Starting services...${NC}"
ssh ${SSH_TARGET} << 'ENDSSH'
sudo systemctl start maxflash-dashboard
sudo systemctl start maxflash-bot
sudo systemctl start maxflash-retrain.timer

# Wait a moment for services to start
sleep 3

# Show status
echo ""
echo "=== Service Status ==="
sudo systemctl status maxflash-dashboard --no-pager -l || true
echo ""
sudo systemctl status maxflash-bot --no-pager -l || true
echo ""
sudo systemctl status maxflash-retrain.timer --no-pager -l || true
ENDSSH

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Dashboard: http://${SERVER_HOST}:8050"
echo -e "Logs: ssh ${SSH_TARGET} 'journalctl -u maxflash-dashboard -f'"
echo ""






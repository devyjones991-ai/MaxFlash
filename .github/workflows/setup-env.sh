#!/bin/bash
# Helper script for CI environment setup

set -e

echo "Setting up CI environment..."

# Install system dependencies
sudo apt-get update
sudo apt-get install -y build-essential wget curl

# Try to install TA-Lib (optional)
if [ "$INSTALL_TALIB" = "true" ]; then
    echo "Installing TA-Lib..."
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz || echo "TA-Lib download failed"
    if [ -f ta-lib-0.4.0-src.tar.gz ]; then
        tar -xzf ta-lib-0.4.0-src.tar.gz
        cd ta-lib/
        ./configure --prefix=/usr
        make
        sudo make install
        cd ..
        pip install TA-Lib || echo "TA-Lib Python package installation failed"
    fi
fi

# Upgrade pip
python -m pip install --upgrade pip setuptools wheel

echo "Environment setup complete!"


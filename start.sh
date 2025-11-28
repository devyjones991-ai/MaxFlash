#!/bin/bash

# MaxFlash Simple Launcher

# 1. Navigate to the script's directory
cd "$(dirname "$0")"

# 2. Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 3. Activate virtual environment
source venv/bin/activate

# 4. Install/Update dependencies (quietly) to ensure everything is ready
echo "Checking dependencies..."
pip install -r requirements.txt -q

# 5. Run the main application
echo "Starting MaxFlash..."
python run.py

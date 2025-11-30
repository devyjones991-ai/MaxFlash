#!/bin/bash
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
pkill -f "python web_interface/app.py"
nohup python web_interface/app.py > logs/dash_final.log 2>&1 &
echo "Dashboard started with PID $!"

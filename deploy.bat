@echo off
echo Deploying to server...
ssh -o StrictHostKeyChecking=no devyjones@192.168.0.204 "cd ~/MaxFlash && git pull origin main && pkill -f 'python.*app_simple' 2>/dev/null; sleep 2; nohup python3 web_interface/app_simple.py > dashboard.log 2>&1 &"
echo Deploy complete!
pause






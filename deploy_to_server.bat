@echo off
echo Deploying to server 192.168.0.204...
echo.

REM SSH connection details
set SERVER=192.168.0.204
set USER=devyjones
set PASS=19Maxon91!
set REMOTE_PATH=/home/devyjones/MaxFlash

echo Step 1: Pulling latest changes on server...
C:\Windows\System32\OpenSSH\ssh.exe %USER%@%SERVER% "cd %REMOTE_PATH% && git fetch origin && git reset --hard origin/main"

echo.
echo Step 2: Restarting dashboard service...
C:\Windows\System32\OpenSSH\ssh.exe %USER%@%SERVER% "cd %REMOTE_PATH% && pkill -f 'python.*app_simple' 2>/dev/null; sleep 1; nohup python3 web_interface/app_simple.py > dashboard.log 2>&1 &"

echo.
echo Step 3: Checking service status...
timeout /t 3 /nobreak >nul
C:\Windows\System32\OpenSSH\ssh.exe %USER%@%SERVER% "ps aux | grep app_simple | grep -v grep"

echo.
echo Deploy complete!
pause



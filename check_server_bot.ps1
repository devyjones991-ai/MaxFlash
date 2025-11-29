$password = ConvertTo-SecureString "19Maxon91!" -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential("devyjones", $password)

$session = New-SSHSession -ComputerName 192.168.0.204 -Port 22 -Credential $credential -AcceptKey

if ($session) {
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command "cd ~/MaxFlash && pwd && ls -la run_bot.py bots/telegram/bot.py 2>&1"
    Write-Host $result.Output
    
    $result2 = Invoke-SSHCommand -SessionId $session.SessionId -Command "cd ~/MaxFlash && ps aux | grep -i 'run_bot\|telegram\|python.*bot' | grep -v grep"
    Write-Host "Running processes:"
    Write-Host $result2.Output
    
    $result3 = Invoke-SSHCommand -SessionId $session.SessionId -Command "cd ~/MaxFlash && cat .env 2>/dev/null | grep TELEGRAM_BOT_TOKEN || echo 'No .env file or token not found'"
    Write-Host "Telegram token check:"
    Write-Host $result3.Output
    
    $result4 = Invoke-SSHCommand -SessionId $session.SessionId -Command "cd ~/MaxFlash && tail -50 logs/*.log 2>/dev/null | tail -20 || echo 'No logs found'"
    Write-Host "Recent logs:"
    Write-Host $result4.Output
    
    Remove-SSHSession -SessionId $session.SessionId
} else {
    Write-Host "Failed to connect"
}


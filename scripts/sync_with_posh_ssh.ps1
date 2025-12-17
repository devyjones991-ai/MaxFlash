# Скрипт синхронизации через Posh-SSH
# Требуется: Install-Module -Name Posh-SSH

param(
    [string]$Server = "192.168.0.203",
    [int]$Port = 22,
    [string]$User = "devyjones",
    [string]$Password = "19Maxon91!",
    [string]$RemotePath = "/home/devyjones/MaxFlash"
)

Import-Module Posh-SSH -ErrorAction Stop

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SYNC TO SERVER (Posh-SSH)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Список файлов для синхронизации
$FILES = @(
    # Новые файлы
    "ml/labeling.py",
    "trading/outcome_tracker.py",
    "utils/universe_selector.py",
    "utils/signal_integrator.py",
    "utils/advanced_signal_validator.py",
    "utils/enhanced_signal_generator.py",
    
    # Модифицированные файлы
    "ml/lightgbm_model.py",
    "bots/telegram/bot_v2.py",
    "scripts/train_lightgbm.py",
    "scripts/run_comprehensive_backtest.py",
    "scripts/auto_retrain_v2.py"
)

$BaseDir = Join-Path $PSScriptRoot ".." | Resolve-Path

# Создаем credential
$SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
$Credential = New-Object System.Management.Automation.PSCredential($User, $SecurePassword)

try {
    # Подключаемся к серверу
    Write-Host "Подключение к серверу..." -ForegroundColor Yellow
    $Session = New-SSHSession -ComputerName $Server -Port $Port -Credential $Credential -AcceptKey
    
    if (-not $Session) {
        Write-Host "ОШИБКА: Не удалось подключиться к серверу" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ Подключено" -ForegroundColor Green
    Write-Host ""
    
    # Создаем директории на сервере
    Write-Host "Создание директорий..." -ForegroundColor Yellow
    $Dirs = $FILES | ForEach-Object { Split-Path $_ -Parent } | Select-Object -Unique
    foreach ($Dir in $Dirs) {
        if ($Dir -ne ".") {
            $RemoteDir = "$RemotePath/$Dir"
            $Command = "mkdir -p `"$RemoteDir`""
            $Result = Invoke-SSHCommand -SessionId $Session.SessionId -Command $Command
            if ($Result.ExitStatus -eq 0) {
                Write-Host "  ✓ $Dir" -ForegroundColor Gray
            }
        }
    }
    Write-Host ""
    
    # Копируем файлы
    Write-Host "Копирование файлов..." -ForegroundColor Yellow
    $Success = 0
    $Failed = 0
    
    foreach ($File in $FILES) {
        $LocalFile = Join-Path $BaseDir $File
        
        if (Test-Path $LocalFile) {
            $RemoteFile = "$RemotePath/$File"
            Write-Host "  → $File" -ForegroundColor Gray
            
            try {
                Set-SCPFile -SessionId $Session.SessionId -LocalFile $LocalFile -RemotePath $RemoteFile
                Write-Host "    ✓ Успешно" -ForegroundColor Green
                $Success++
            }
            catch {
                Write-Host "    ✗ Ошибка: $_" -ForegroundColor Red
                $Failed++
            }
        }
        else {
            Write-Host "  ✗ $File (не найден локально)" -ForegroundColor Red
            $Failed++
        }
    }
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "РЕЗУЛЬТАТ" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Успешно: $Success" -ForegroundColor Green
    Write-Host "Ошибок:  $Failed" -ForegroundColor $(if ($Failed -eq 0) { "Green" } else { "Red" })
    Write-Host ""
    
    # Отключаемся
    Remove-SSHSession -SessionId $Session.SessionId | Out-Null
    Write-Host "✓ Отключено от сервера" -ForegroundColor Green
}
catch {
    Write-Host "ОШИБКА: $_" -ForegroundColor Red
    exit 1
}


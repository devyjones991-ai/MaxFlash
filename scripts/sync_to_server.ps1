# Скрипт синхронизации файлов на сервер
# Использование: .\scripts\sync_to_server.ps1

$SERVER = "192.168.0.203"
$PORT = "22"
$USER = "devyjones"
$PASSWORD = "19Maxon91!"
$REMOTE_PATH = "/home/devyjones/MaxFlash"

# Новые файлы для создания
$NEW_FILES = @(
    "ml/labeling.py",
    "trading/outcome_tracker.py",
    "utils/universe_selector.py",
    "utils/signal_integrator.py",
    "utils/advanced_signal_validator.py",
    "utils/enhanced_signal_generator.py"
)

# Модифицированные файлы
$MODIFIED_FILES = @(
    "ml/lightgbm_model.py",
    "bots/telegram/bot_v2.py",
    "scripts/train_lightgbm.py",
    "scripts/run_comprehensive_backtest.py",
    "scripts/auto_retrain_v2.py"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SYNC TO SERVER - MaxFlash Updates" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка наличия SSH
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: SSH not found. Install OpenSSH or use WSL." -ForegroundColor Red
    exit 1
}

# Создаем временный скрипт для передачи пароля через sshpass (если доступен)
# Или используем SSH ключи (рекомендуется)

Write-Host "Синхронизация файлов..." -ForegroundColor Yellow

# Используем scp с паролем через sshpass (если установлен) или интерактивно
foreach ($file in $NEW_FILES + $MODIFIED_FILES) {
    $localPath = Join-Path $PSScriptRoot "..\$file" | Resolve-Path -ErrorAction SilentlyContinue
    if ($localPath) {
        $remoteDir = "$REMOTE_PATH/$(Split-Path $file -Parent)"
        
        Write-Host "  → $file" -ForegroundColor Gray
        
        # Создаем директорию на сервере если нужно
        $dirScript = "mkdir -p $remoteDir"
        
        # Копируем файл
        $scpCommand = "scp -P $PORT `"$localPath`" ${USER}@${SERVER}:${REMOTE_PATH}/${file}"
        
        Write-Host "    Команда: $scpCommand" -ForegroundColor DarkGray
        
        # Пробуем с sshpass если доступен
        $sshpassCmd = "echo $PASSWORD | sshpass -p `"$PASSWORD`" $scpCommand"
        
        # Или используем expect/plink
        # Для PowerShell лучше использовать Posh-SSH модуль или интерактивный ввод
        
        Write-Host "    ⚠ Используйте вручную: $scpCommand" -ForegroundColor Yellow
        Write-Host "    Или установите Posh-SSH: Install-Module -Name Posh-SSH" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "РЕКОМЕНДУЕМЫЙ СПОСОБ:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Установите Posh-SSH модуль:" -ForegroundColor Yellow
Write-Host "   Install-Module -Name Posh-SSH -Force" -ForegroundColor White
Write-Host ""
Write-Host "2. Используйте скрипт sync_with_posh_ssh.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "ИЛИ используйте WinSCP / FileZilla для GUI синхронизации" -ForegroundColor Yellow
Write-Host ""


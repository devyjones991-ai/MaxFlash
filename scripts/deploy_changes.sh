#!/bin/bash
# Скрипт деплоя изменений на сервер
# Использование: ./scripts/deploy_changes.sh

SERVER="192.168.0.203"
PORT="22"
USER="devyjones"
PASSWORD="19Maxon91!"
REMOTE_PATH="/home/devyjones/MaxFlash"

echo "========================================"
echo "DEPLOY TO SERVER - MaxFlash Updates"
echo "========================================"
echo ""

# Список файлов для синхронизации
NEW_FILES=(
    "ml/labeling.py"
    "trading/outcome_tracker.py"
    "utils/universe_selector.py"
    "utils/signal_integrator.py"
    "utils/advanced_signal_validator.py"
    "utils/enhanced_signal_generator.py"
)

MODIFIED_FILES=(
    "ml/lightgbm_model.py"
    "bots/telegram/bot_v2.py"
    "scripts/train_lightgbm.py"
    "scripts/run_comprehensive_backtest.py"
    "scripts/auto_retrain_v2.py"
)

ALL_FILES=("${NEW_FILES[@]}" "${MODIFIED_FILES[@]}")

# Проверка наличия sshpass
if ! command -v sshpass &> /dev/null; then
    echo "⚠ sshpass не найден. Устанавливаем зависимости..."
    echo "  Для Ubuntu/Debian: sudo apt-get install sshpass"
    echo "  Для MacOS: brew install hudochenkov/sshpass/sshpass"
    echo ""
    echo "Или используйте ключи SSH (рекомендуется):"
    echo "  ssh-copy-id ${USER}@${SERVER}"
    echo ""
    USE_SSHPASS=false
else
    USE_SSHPASS=true
fi

# Функция для копирования файла
copy_file() {
    local_file="$1"
    remote_file="$2"
    
    if [ ! -f "$local_file" ]; then
        echo "  ✗ $remote_file (не найден локально)"
        return 1
    fi
    
    # Создаем директорию на сервере
    remote_dir=$(dirname "$remote_file")
    if [ "$USE_SSHPASS" = true ]; then
        sshpass -p "$PASSWORD" ssh -p "$PORT" -o StrictHostKeyChecking=no "${USER}@${SERVER}" "mkdir -p ${REMOTE_PATH}/${remote_dir}"
        sshpass -p "$PASSWORD" scp -P "$PORT" -o StrictHostKeyChecking=no "$local_file" "${USER}@${SERVER}:${REMOTE_PATH}/${remote_file}"
    else
        ssh -p "$PORT" "${USER}@${SERVER}" "mkdir -p ${REMOTE_PATH}/${remote_dir}"
        scp -P "$PORT" "$local_file" "${USER}@${SERVER}:${REMOTE_PATH}/${remote_file}"
    fi
    
    if [ $? -eq 0 ]; then
        echo "  ✓ $remote_file"
        return 0
    else
        echo "  ✗ $remote_file (ошибка копирования)"
        return 1
    fi
}

# Копируем файлы
echo "Синхронизация файлов..."
SUCCESS=0
FAILED=0

for file in "${ALL_FILES[@]}"; do
    copy_file "$file" "$file"
    if [ $? -eq 0 ]; then
        ((SUCCESS++))
    else
        ((FAILED++))
    fi
done

echo ""
echo "========================================"
echo "РЕЗУЛЬТАТ"
echo "========================================"
echo "Успешно: $SUCCESS"
echo "Ошибок:  $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✓ Все файлы успешно синхронизированы!"
    echo ""
    echo "Следующие шаги на сервере:"
    echo "  1. ssh ${USER}@${SERVER}"
    echo "  2. cd ${REMOTE_PATH}"
    echo "  3. pip install -r requirements.txt  # если нужно обновить зависимости"
    echo "  4. python scripts/train_lightgbm.py --coins 20  # переобучить модель"
    echo "  5. python scripts/run_comprehensive_backtest.py --coins 20  # проверить результаты"
    exit 0
else
    echo "✗ Некоторые файлы не были скопированы"
    exit 1
fi


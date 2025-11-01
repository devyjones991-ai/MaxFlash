#!/bin/bash
# Простой запуск MaxFlash Dashboard для Linux/Mac

echo "========================================"
echo "MaxFlash Trading Dashboard"
echo "========================================"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 не установлен!"
    exit 1
fi

echo "[1/3] Проверка зависимостей..."
if ! python3 -c "import dash" 2>/dev/null; then
    echo "[INFO] Установка зависимостей..."
    pip3 install dash dash-bootstrap-components dash-table requests --quiet
    if [ $? -ne 0 ]; then
        echo "[ERROR] Не удалось установить зависимости!"
        exit 1
    fi
    echo "[OK] Зависимости установлены"
else
    echo "[OK] Зависимости уже установлены"
fi

echo ""
echo "[2/3] Запуск dashboard..."
echo ""
echo "========================================"
echo "Dashboard будет доступен по адресу:"
echo "http://localhost:8050"
echo "========================================"
echo ""
echo "Нажмите Ctrl+C для остановки"
echo ""

cd "$(dirname "$0")"
python3 app.py


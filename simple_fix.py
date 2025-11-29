#!/usr/bin/env python3
import paramiko
import sys

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, 22, username, password, timeout=10)

# Команды выполняем по одной
# Остановка
print("\n[1] Остановка старых процессов...")
stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && pkill -f 'run_bot.py' || true", timeout=10)
stdout.channel.recv_exit_status()

# Установка
print("[2] Установка библиотеки...")
stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && source venv/bin/activate && pip install -q python-telegram-bot", timeout=60)
stdout.channel.recv_exit_status()

# Проверка импорта
print("[3] Проверка импорта...")
stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && source venv/bin/activate && python -c 'from bots.telegram.bot import TelegramBot; print(\"OK\")'", timeout=30)
output = stdout.read().decode('utf-8', errors='ignore')
print(output)

# Запуск через screen или просто в фоне
print("[4] Запуск бота...")
stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && source venv/bin/activate && python run_bot.py > logs/telegram_bot.log 2>&1 &", timeout=5)
# Не ждем вывода от фоновой команды
import time
time.sleep(3)

# Проверка
print("[5] Проверка процесса...")
stdin, stdout, stderr = ssh.exec_command("ps aux | grep 'run_bot.py' | grep -v grep", timeout=10)
output = stdout.read().decode('utf-8', errors='ignore')
if output:
    print("✅ Бот запущен:")
    print(output)
else:
    print("❌ Процесс не найден")

# Логи
print("\n[6] Последние логи:")
stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && tail -20 logs/telegram_bot.log 2>/dev/null || echo 'Логи пусты'", timeout=10)
output = stdout.read().decode('utf-8', errors='ignore')
print(output)

ssh.close()
print("\n✅ Готово!")


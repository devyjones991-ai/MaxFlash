# 🚀 Запуск MaxFlash Dashboard в фоне

## Проблема с фоновыми процессами

**Почему не работают фоновые процессы через инструменты Cursor?**
- Инструменты Cursor запускают процессы в ограниченном контексте
- Процессы могут завершаться при закрытии сессии
- Нет полного контроля над жизненным циклом процесса

## ✅ Решение: Production-ready скрипты

Созданы специальные скрипты для запуска в фоне:

### Windows

#### 1. Запуск в фоне:
```batch
run_background.bat
```
или
```bash
python run_background.py
```

**Что делает:**
- Создает VBS скрипт для скрытого запуска
- Использует `pythonw.exe` (без консоли)
- Сохраняет логи в `dashboard.log`
- Запускает процесс независимо от терминала

#### 2. Остановка:
```batch
stop_dashboard.bat
```
или
```bash
python stop_dashboard.py
```

### Linux/Mac

#### 1. Запуск в фоне:
```bash
chmod +x run_background.sh
./run_background.sh
```
или
```bash
python3 run_background.py
```

**Что делает:**
- Использует `subprocess.Popen` с `start_new_session=True`
- Сохраняет PID в `dashboard.pid`
- Сохраняет логи в `dashboard.log`
- Процесс работает независимо от терминала

#### 2. Остановка:
```bash
./stop_dashboard.sh
```
или
```bash
python3 stop_dashboard.py
```

## 🔧 Для Production сервера

### Linux (systemd)

1. **Установите service файл:**
```bash
sudo cp maxflash-dashboard.service /etc/systemd/system/
sudo nano /etc/systemd/system/maxflash-dashboard.service
# Отредактируйте пути
```

2. **Запустите:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable maxflash-dashboard
sudo systemctl start maxflash-dashboard
```

3. **Проверка:**
```bash
sudo systemctl status maxflash-dashboard
sudo journalctl -u maxflash-dashboard -f
```

### Windows (Task Scheduler)

1. Откройте Планировщик заданий
2. Создайте задачу:
   - Триггер: "При запуске компьютера"
   - Действие: Запустить `run_background.bat`
   - Параметры: "Запускать скрыто"

## 📝 Логирование

- **Windows:** `dashboard.log` в корне проекта
- **Linux/Mac:** `dashboard.log` в корне проекта
- **Systemd:** `journalctl -u maxflash-dashboard`

## 🐛 Troubleshooting

### Процесс не запускается

1. **Проверьте зависимости:**
```bash
pip install -r requirements.txt
```

2. **Проверьте Python версию:**
```bash
python --version  # Должно быть 3.9+
```

3. **Запустите в foreground для отладки:**
```bash
python run_background.py --foreground
```

### Порт занят

```bash
# Windows
netstat -ano | findstr :8050
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8050
kill -9 <PID>
```

### Проверка работы

```bash
# Проверка порта
curl http://localhost:8050

# Проверка процесса
# Windows
tasklist | findstr python

# Linux/Mac
ps aux | grep app_simple.py
```

## 💡 Рекомендации

1. **Используйте systemd на Linux** для production
2. **Настройте автозапуск** через планировщик задач
3. **Мониторьте логи** регулярно
4. **Используйте reverse proxy** (nginx) для HTTPS
5. **Настройте firewall** для безопасности


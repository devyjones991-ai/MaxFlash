# 🚀 MaxFlash Dashboard - Production Deployment Guide

## Запуск в фоне (Background Mode)

### Windows

#### Вариант 1: Через скрипт (Рекомендуется)
```batch
run_background.bat
```

#### Вариант 2: Через Python
```bash
python run_background.py
```

#### Вариант 3: Через VBS (Скрытый запуск)
Скрипт автоматически создаст `start_hidden.vbs` и запустит сервер без окна консоли.

#### Остановка:
```batch
stop_dashboard.bat
```

### Linux/Mac

#### Вариант 1: Через скрипт (Рекомендуется)
```bash
chmod +x run_background.sh
./run_background.sh
```

#### Вариант 2: Через Python
```bash
python3 run_background.py
```

#### Вариант 3: Через systemd (Production)
1. Скопируйте `maxflash-dashboard.service` в `/etc/systemd/system/`
2. Отредактируйте пути в файле:
   ```bash
   sudo nano /etc/systemd/system/maxflash-dashboard.service
   ```
3. Замените `/path/to/MaxFlash` на реальный путь
4. Запустите:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable maxflash-dashboard
   sudo systemctl start maxflash-dashboard
   ```
5. Проверка статуса:
   ```bash
   sudo systemctl status maxflash-dashboard
   ```
6. Просмотр логов:
   ```bash
   sudo journalctl -u maxflash-dashboard -f
   ```

#### Остановка:
```bash
./stop_dashboard.sh
# или
python3 stop_dashboard.py
```

## Docker Deployment

### Запуск через Docker Compose
```bash
docker-compose up -d
```

### Сборка образа
```bash
docker build -t maxflash-dashboard -f Dockerfile.dashboard .
docker run -d -p 8050:8050 --name maxflash maxflash-dashboard
```

## Проверка работы

После запуска проверьте:
```bash
# Проверка порта
netstat -an | grep 8050  # Linux/Mac
netstat -an | findstr 8050  # Windows

# Проверка процесса
ps aux | grep app_simple.py  # Linux/Mac
tasklist | findstr python  # Windows

# Проверка через браузер
curl http://localhost:8050  # Linux/Mac
```

## Логирование

### Windows
- Логи процесса можно увидеть в диспетчере задач
- Или запустите с `--foreground` для просмотра логов

### Linux/Mac
- Логи сохраняются в `dashboard.log` в корне проекта
- PID сохраняется в `dashboard.pid`

### Systemd
- Логи доступны через `journalctl -u maxflash-dashboard`

## Troubleshooting

### Порт занят
```bash
# Linux/Mac
lsof -i :8050
kill -9 <PID>

# Windows
netstat -ano | findstr :8050
taskkill /PID <PID> /F
```

### Процесс не запускается
1. Проверьте зависимости: `pip install -r requirements.txt`
2. Проверьте Python версию: `python --version` (требуется 3.9+)
3. Проверьте права доступа к файлам
4. Запустите с `--foreground` для отладки

### Автозапуск при перезагрузке

#### Windows
Создайте задачу в Планировщике заданий:
1. Откройте Планировщик заданий
2. Создайте задачу
3. Триггер: "При запуске компьютера"
4. Действие: Запустить программу `run_background.bat`

#### Linux (systemd)
```bash
sudo systemctl enable maxflash-dashboard
```

## Production Best Practices

1. **Используйте reverse proxy** (nginx/apache) для HTTPS
2. **Настройте firewall** для ограничения доступа
3. **Используйте systemd** на Linux для автозапуска
4. **Настройте логирование** в отдельный файл
5. **Мониторинг**: используйте healthcheck endpoints
6. **Backup**: регулярно сохраняйте конфигурацию


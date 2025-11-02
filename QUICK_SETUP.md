# ⚡ Быстрая настройка MaxFlash

## 🚀 Быстрый старт (5 минут)

### Вариант 1: Docker (рекомендуется)

```bash
# Клонировать репозиторий
git clone https://github.com/devyjones991-ai/MaxFlash.git
cd MaxFlash

# Запустить все сервисы
make docker-up

# Или вручную
docker-compose up -d
```

Доступно:
- Dashboard: http://localhost:8050
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Вариант 2: Локальная установка

```bash
# Установка
python setup_dev.py

# Или вручную
pip install -e ".[dev]"
pre-commit install

# Запуск dashboard
cd web_interface
python app_modern.py

# Запуск API (в другом терминале)
cd api
uvicorn main:app --reload
```

## 📋 Полезные команды

```bash
# Через Makefile
make install      # Установить зависимости
make dev          # Настроить dev окружение
make test         # Запустить тесты
make lint         # Проверить код
make format       # Форматировать код
make docker-up    # Запустить Docker
make clean        # Очистить кэш

# Напрямую
ruff check .      # Линтинг
ruff format .     # Форматирование
pytest tests/     # Тесты
pre-commit run --all-files  # Все проверки
```

## 🔧 Pre-commit hooks

Автоматические проверки перед каждым коммитом:

```bash
# Установить hooks
pre-commit install

# Запустить вручную для всех файлов
pre-commit run --all-files

# Для конкретного файла
pre-commit run --files indicators/order_blocks.py
```

## 🐳 Docker команды

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Логи
docker-compose logs -f

# Пересборка
docker-compose build --no-cache

# Статус
docker-compose ps
```

## 📚 API документация

После запуска API:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Тестирование

```bash
# Все тесты
make test

# Быстрые тесты
make test-fast

# С покрытием
pytest tests/ --cov=indicators --cov=utils --cov=strategies

# Конкретный тест
pytest tests/test_order_blocks.py -v
```

## 🎯 Что дальше?

1. **Настройте API ключи** в `.env`:
   ```env
   EXCHANGE_NAME=binance
   EXCHANGE_API_KEY=your_key
   EXCHANGE_API_SECRET=your_secret
   ```

2. **Запустите dashboard** и посмотрите интерфейс

3. **Попробуйте API** через Swagger UI

4. **Настройте стратегию** под ваши нужды

## 📖 Документация

- [README_IMPROVEMENTS.md](README_IMPROVEMENTS.md) - Все новые возможности
- [docs/](docs/) - Детальная документация
- [QUICK_START_PARTNER.md](QUICK_START_PARTNER.md) - Для партнеров


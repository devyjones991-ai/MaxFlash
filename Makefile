.PHONY: help install dev test lint format docker-up docker-down clean

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install --upgrade pip
	pip install -r requirements-core.txt
	pip install -r requirements-test.txt

dev: ## Установить dev зависимости
	pip install -e ".[dev]"
	pre-commit install

test: ## Запустить тесты
	pytest tests/ -v --cov=indicators --cov=utils --cov=strategies --cov-report=term-missing

test-fast: ## Быстрые тесты (без coverage)
	pytest tests/ -v -x

lint: ## Проверить код линтером
	ruff check indicators/ utils/ strategies/ tests/
	mypy indicators/ utils/ strategies/ --ignore-missing-imports

format: ## Форматировать код
	ruff format indicators/ utils/ strategies/ tests/
	ruff check --fix indicators/ utils/ strategies/ tests/

lint-fix: ## Исправить ошибки линтера
	ruff check --fix indicators/ utils/ strategies/ tests/
	ruff format indicators/ utils/ strategies/ tests/

docker-up: ## Запустить Docker Compose
	docker-compose up -d
	@echo "Dashboard: http://localhost:8050"
	@echo "API: http://localhost:8000"

docker-down: ## Остановить Docker Compose
	docker-compose down

docker-build: ## Собрать Docker образы
	docker-compose build

docker-logs: ## Показать логи Docker
	docker-compose logs -f

clean: ## Очистить кэш и временные файлы
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/

ci: lint test ## Запустить все проверки (как в CI)

all: clean install dev lint test ## Полная установка и проверка


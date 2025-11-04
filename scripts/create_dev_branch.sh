#!/bin/bash
# Скрипт для создания dev ветки и настройки workflow

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🌿 Создание dev ветки${NC}"
echo "================================"

# Проверяем что мы в git репозитории
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Ошибка: не найдена git директория${NC}"
    exit 1
fi

# Проверяем текущую ветку
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${YELLOW}📦 Текущая ветка: ${CURRENT_BRANCH}${NC}"

# Проверяем есть ли незакоммиченные изменения
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${YELLOW}⚠️  Обнаружены незакоммиченные изменения${NC}"
    read -p "Продолжить? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Переключаемся на main если нужно
if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
    echo -e "${YELLOW}🔄 Переключение на main...${NC}"
    git checkout main 2>/dev/null || git checkout master 2>/dev/null || {
        echo -e "${RED}❌ Не удалось переключиться на main/master${NC}"
        exit 1
    }
fi

# Обновляем main
echo -e "${YELLOW}⬇️  Обновление main...${NC}"
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || echo "⚠️  Предупреждение: не удалось обновить main"

# Проверяем существует ли dev ветка
if git show-ref --verify --quiet refs/heads/dev; then
    echo -e "${YELLOW}⚠️  Ветка dev уже существует${NC}"
    read -p "Переключиться на dev? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git checkout dev
        git pull origin dev 2>/dev/null || echo "⚠️  Предупреждение: не удалось обновить dev"
        echo -e "${GREEN}✅ Переключились на dev${NC}"
    fi
else
    # Создаем dev ветку
    echo -e "${YELLOW}🌿 Создание dev ветки...${NC}"
    git checkout -b dev
    
    # Пушим dev ветку
    echo -e "${YELLOW}🚀 Отправка dev ветки...${NC}"
    git push -u origin dev || {
        echo -e "${RED}❌ Не удалось отправить dev ветку${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✅ Dev ветка создана и отправлена${NC}"
fi

echo "================================"
echo -e "${GREEN}✅ Готово!${NC}"
echo ""
echo "Теперь вы можете:"
echo "  - Работать в dev ветке для разработки"
echo "  - Использовать main для стабильных релизов"
echo "  - Использовать scripts/auto_commit_push.sh для коммитов"


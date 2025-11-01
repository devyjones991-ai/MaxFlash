# Инструкция по загрузке на GitHub

## Шаги для загрузки проекта на GitHub

### 1. Создайте репозиторий на GitHub

1. Перейдите на [GitHub.com](https://github.com)
2. Нажмите кнопку **"+"** в правом верхнем углу → **"New repository"**
3. Заполните форму:
   - **Repository name**: `MaxFlash` (или любое другое имя)
   - **Description**: "Integrated Crypto Trading System with Smart Money Concepts, Footprint, Volume Profile, Market Profile and TPO"
   - Выберите **Public** или **Private**
   - **НЕ** инициализируйте с README, .gitignore или лицензией (у нас уже есть эти файлы)
4. Нажмите **"Create repository"**

### 2. Подключите локальный репозиторий к GitHub

После создания репозитория GitHub покажет инструкции. Выполните:

```bash
# Если репозиторий еще не инициализирован (уже сделано)
# git init

# Добавить все файлы (уже сделано)
# git add .

# Создать коммит (уже сделано)
# git commit -m "Initial commit"

# Добавить remote (ЗАМЕНИТЕ yourusername на ваш GitHub username)
git remote add origin https://github.com/yourusername/MaxFlash.git

# Переименовать ветку в main (если нужно)
git branch -M main

# Загрузить код на GitHub
git push -u origin main
```

### 3. Альтернативный способ (SSH)

Если вы используете SSH ключи:

```bash
git remote add origin git@github.com:yourusername/MaxFlash.git
git branch -M main
git push -u origin main
```

### 4. Проверка

После успешной загрузки:
1. Обновите страницу репозитория на GitHub
2. Вы должны увидеть все файлы проекта
3. README.md автоматически отобразится на главной странице

### 5. Настройка GitHub Actions (опционально)

Файл `.github/workflows/tests.yml` уже создан. GitHub Actions автоматически запустится при следующем push, если:
- У вас есть публичный репозиторий
- Или вы включили GitHub Actions для приватного репозитория

### 6. Настройка README badge

В файле `README.md` замените `yourusername` на ваш реальный GitHub username в строке:

```markdown
[![Tests](https://github.com/yourusername/MaxFlash/actions/workflows/tests.yml/badge.svg)](https://github.com/yourusername/MaxFlash/actions/workflows/tests.yml)
```

### 7. Дополнительные файлы для GitHub

Не забудьте создать (если нужно):

#### LICENSE файл
```bash
# Создайте MIT License файл
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2024 [Your Name]

Permission is hereby granted...
EOF
git add LICENSE
git commit -m "Add MIT License"
git push
```

### 8. Теги и релизы

После первого успешного тестирования создайте релиз:

```bash
# Создать тег
git tag -a v1.0.0 -m "First release: Integrated Trading System"

# Загрузить тег
git push origin v1.0.0

# На GitHub: Releases → Create a new release → выберите тег v1.0.0
```

## Важные замечания

⚠️ **Не загружайте секретные данные:**
- API ключи бирж
- Приватные ключи
- Пароли
- Личные данные

Файл `.gitignore` уже настроен для исключения таких файлов.

⚠️ **Freqtrade репозиторий:**
Папка `freqtrade/` исключена из git (в .gitignore), так как это отдельный репозиторий.
Пользователи должны клонировать Freqtrade отдельно согласно инструкциям.

## Быстрая команда

Если репозиторий уже создан на GitHub:

```bash
git remote add origin https://github.com/YOUR_USERNAME/MaxFlash.git
git branch -M main
git push -u origin main
```

Замените `YOUR_USERNAME` на ваш GitHub username!

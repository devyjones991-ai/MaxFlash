# Документация стратегии

## Обзор

Интегрированная торговая стратегия объединяет Smart Money Concepts, Footprint Analysis, Volume Profile, Market Profile и TPO в единую многоуровневую систему анализа.

## Архитектура анализа

### Top-Down подход

Стратегия использует трехуровневый анализ:

1. **Макроуровень (Daily/4H)**: Определение общего тренда и ключевых зон
2. **Промежуточный уровень (1H)**: Фильтрация через Market Profile
3. **Микроуровень (5-15min)**: Точный вход на основе Footprint

## Компоненты

### Smart Money Concepts

- **Order Blocks**: Зоны консолидации перед импульсными движениями
- **Fair Value Gaps**: Ценовые разрывы, указывающие на дисбаланс
- **Market Structure**: BOS, ChoCH, определение тренда

### Volume Profile

- **POC**: Уровень максимального объема
- **HVN**: Зоны высокого объема
- **LVN**: Зоны низкого объема
- **Value Area**: 70% объема торговли

### Market Profile & TPO

- **Value Area**: VAH, VAL, POC
- **TPO Distribution**: Анализ распределения времени и цены
- **Single Prints**: Импульсные зоны

### Footprint Analysis

- **Delta**: Дисбаланс между покупками и продажами
- **Order Flow**: Анализ потока ордеров
- **Absorption**: Детекция поглощения на ключевых уровнях

## Правила входа

### Long Entry

1. Макро: Цена находится в bullish Order Block
2. Макро: Общий тренд bullish или range
3. Промежуточный: Цена в Value Area или отскок от VAL
4. Микро: Положительный Delta
5. Микро: Детекция absorption
6. Confluence: Минимум 3 сигнала сходятся

### Short Entry

1. Макро: Цена находится в bearish Order Block
2. Макро: Общий тренд bearish или range
3. Промежуточный: Цена в Value Area или отскок от VAH
4. Микро: Отрицательный Delta
5. Микро: Детекция absorption
6. Confluence: Минимум 3 сигнала сходятся

## Управление рисками

- **Stop Loss**: Ниже Order Block low (для long) или выше Order Block high (для short)
- **Take Profit 1**: Ближайший HVN или FVG
- **Take Profit 2**: Противоположный Order Block или FVG
- **Position Sizing**: 1-2% риска на сделку
- **Max Drawdown**: Защита от превышения лимита

## Фильтры

- Избегать торговли во время важных новостей
- Минимальный ATR для фильтрации маловолатильных рынков
- Проверка ликвидности перед входом

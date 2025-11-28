# Cython Extensions

Cython модули для ускорения критичных участков кода.

## Компиляция

```bash
python cython_ext/setup.py build_ext --inplace
```

Или через pip:

```bash
pip install -e .
```

## Использование

После компиляции модули можно импортировать:

```python
from cython_ext.feature_calc import calculate_moving_average, calculate_volatility
from cython_ext.scoring import calculate_scam_score, calculate_signal_score

# Использование
prices = np.array([100.0, 101.0, 102.0, 103.0, 104.0])
ma = calculate_moving_average(prices, window=3)
vol = calculate_volatility(prices, window=3)
```

## Модули

- `feature_calc.pyx`: Расчёт технических индикаторов (MA, волатильность, RSI)
- `scoring.pyx`: Быстрый расчёт scam score и signal score


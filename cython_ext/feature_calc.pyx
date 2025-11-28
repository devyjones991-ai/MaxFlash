"""
Cython модуль для быстрого расчёта фич.
"""
import numpy as np
cimport numpy as np
cimport cython

@cython.boundscheck(False)
@cython.wraparound(False)
def calculate_moving_average(double[:] prices, int window):
    """
    Рассчитать скользящее среднее.
    
    Args:
        prices: Массив цен
        window: Размер окна
    """
    cdef int n = prices.shape[0]
    cdef np.ndarray[double] result = np.zeros(n - window + 1, dtype=np.float64)
    cdef int i, j
    cdef double sum_val
    
    for i in range(n - window + 1):
        sum_val = 0.0
        for j in range(window):
            sum_val += prices[i + j]
        result[i] = sum_val / window
    
    return result

@cython.boundscheck(False)
@cython.wraparound(False)
def calculate_volatility(double[:] prices, int window):
    """
    Рассчитать волатильность.
    
    Args:
        prices: Массив цен
        window: Размер окна
    """
    cdef int n = prices.shape[0]
    cdef np.ndarray[double] returns = np.zeros(n - 1, dtype=np.float64)
    cdef np.ndarray[double] volatility = np.zeros(n - window, dtype=np.float64)
    cdef int i, j
    cdef double mean_return, sum_sq
    
    # Рассчитываем returns
    for i in range(n - 1):
        returns[i] = (prices[i + 1] - prices[i]) / prices[i]
    
    # Рассчитываем волатильность
    for i in range(n - window):
        mean_return = 0.0
        for j in range(window - 1):
            mean_return += returns[i + j]
        mean_return /= (window - 1)
        
        sum_sq = 0.0
        for j in range(window - 1):
            sum_sq += (returns[i + j] - mean_return) ** 2
        
        volatility[i] = np.sqrt(sum_sq / (window - 2))
    
    return volatility

@cython.boundscheck(False)
@cython.wraparound(False)
def calculate_rsi(double[:] prices, int period):
    """
    Рассчитать RSI (Relative Strength Index).
    
    Args:
        prices: Массив цен
        period: Период
    """
    cdef int n = prices.shape[0]
    cdef np.ndarray[double] deltas = np.zeros(n - 1, dtype=np.float64)
    cdef np.ndarray[double] gains = np.zeros(n - 1, dtype=np.float64)
    cdef np.ndarray[double] losses = np.zeros(n - 1, dtype=np.float64)
    cdef np.ndarray[double] rsi = np.zeros(n - period, dtype=np.float64)
    cdef int i, j
    cdef double avg_gain, avg_loss, rs
    
    # Рассчитываем изменения цен
    for i in range(n - 1):
        deltas[i] = prices[i + 1] - prices[i]
        if deltas[i] > 0:
            gains[i] = deltas[i]
            losses[i] = 0.0
        else:
            gains[i] = 0.0
            losses[i] = -deltas[i]
    
    # Рассчитываем RSI
    for i in range(n - period):
        avg_gain = 0.0
        avg_loss = 0.0
        
        for j in range(period):
            avg_gain += gains[i + j]
            avg_loss += losses[i + j]
        
        avg_gain /= period
        avg_loss /= period
        
        if avg_loss == 0.0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
    
    return rsi


"""
Cython модуль для быстрого скоринга.
"""
import numpy as np
cimport numpy as np
cimport cython

@cython.boundscheck(False)
@cython.wraparound(False)
def calculate_scam_score(
    double[:] features,
    double[:] weights
):
    """
    Рассчитать scam score на основе фич и весов.
    
    Args:
        features: Массив фич
        weights: Массив весов
    """
    cdef int n = features.shape[0]
    cdef double score = 0.0
    cdef int i
    
    for i in range(n):
        score += features[i] * weights[i]
    
    return min(1.0, max(0.0, score))

@cython.boundscheck(False)
@cython.wraparound(False)
def calculate_signal_score(
    double safety_score,
    double liquidity_score,
    double volume_score,
    double lp_score
):
    """
    Рассчитать signal score.
    
    Args:
        safety_score: Score безопасности (0.0 - 1.0)
        liquidity_score: Score ликвидности (0.0 - 1.0)
        volume_score: Score объёма (0.0 - 1.0)
        lp_score: Score блокировки LP (0.0 - 1.0)
    """
    cdef double score = (
        safety_score * 0.4 +
        liquidity_score * 0.3 +
        volume_score * 0.2 +
        lp_score * 0.1
    )
    
    return min(1.0, max(0.0, score))

@cython.boundscheck(False)
@cython.wraparound(False)
def batch_score_signals(
    double[:, :] features_matrix,
    double[:] weights
):
    """
    Пакетный расчёт scores для множества сигналов.
    
    Args:
        features_matrix: Матрица фич (n_signals x n_features)
        weights: Массив весов
    """
    cdef int n_signals = features_matrix.shape[0]
    cdef np.ndarray[double] scores = np.zeros(n_signals, dtype=np.float64)
    cdef int i, j
    cdef double score
    
    for i in range(n_signals):
        score = 0.0
        for j in range(features_matrix.shape[1]):
            score += features_matrix[i, j] * weights[j]
        scores[i] = min(1.0, max(0.0, score))
    
    return scores


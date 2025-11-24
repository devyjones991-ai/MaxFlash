"""
Обработка ошибок и исключений для торговой системы.
"""

import logging
import traceback
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


def handle_errors(default_return: Any = None, log_error: bool = True, re_raise: bool = False):
    """
    Декоратор для обработки ошибок.

    Args:
        default_return: Значение по умолчанию при ошибке
        log_error: Логировать ли ошибку
        re_raise: Переподнять исключение после логирования
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {e!s}\nTraceback: {traceback.format_exc()}")

                if re_raise:
                    raise

                return default_return

        return wrapper

    return decorator


class TradingSystemError(Exception):
    """Базовое исключение для торговой системы."""

    pass


class DataValidationError(TradingSystemError):
    """Ошибка валидации данных."""

    pass


class IndicatorCalculationError(TradingSystemError):
    """Ошибка расчета индикатора."""

    pass


class StrategyExecutionError(TradingSystemError):
    """Ошибка выполнения стратегии."""

    pass

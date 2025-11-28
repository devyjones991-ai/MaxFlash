"""
Контекстные бандиты для онлайн-обучения параметров торговли.
"""
from typing import Dict, List, Optional
import numpy as np
import structlog
from datetime import datetime
import json

logger = structlog.get_logger()


class ThompsonSamplingBandit:
    """Thompson Sampling бандит для выбора параметров."""
    
    def __init__(self, arms: List[Dict]):
        """
        Инициализация бандита.
        
        Args:
            arms: Список "рук" (вариантов параметров)
                Пример: [
                    {"position_size": 0.01, "stop_loss": 0.02, "take_profit": 0.05},
                    {"position_size": 0.02, "stop_loss": 0.03, "take_profit": 0.06},
                ]
        """
        self.arms = arms
        self.n_arms = len(arms)
        
        # Инициализация параметров Beta распределения для каждой руки
        # alpha = успехи, beta = неудачи
        self.alpha = np.ones(self.n_arms)  # Начинаем с 1 успехом
        self.beta = np.ones(self.n_arms)   # Начинаем с 1 неудачей
        
        # Статистика
        self.pulls = np.zeros(self.n_arms, dtype=int)
        self.rewards = np.zeros(self.n_arms)
    
    def select_arm(self) -> int:
        """
        Выбрать руку используя Thompson Sampling.
        
        Returns:
            Индекс выбранной руки
        """
        # Генерируем случайные значения из Beta распределения для каждой руки
        samples = np.random.beta(self.alpha, self.beta)
        
        # Выбираем руку с максимальным значением
        selected_arm = np.argmax(samples)
        
        self.pulls[selected_arm] += 1
        
        logger.debug(
            "Arm selected",
            arm_index=selected_arm,
            arm_params=self.arms[selected_arm],
            samples=samples.tolist()
        )
        
        return selected_arm
    
    def update(self, arm_index: int, reward: float):
        """
        Обновить параметры бандита на основе полученной награды.
        
        Args:
            arm_index: Индекс руки
            reward: Награда (0.0 - 1.0, где 1.0 = максимальная прибыль)
        """
        if arm_index < 0 or arm_index >= self.n_arms:
            logger.warning("Invalid arm index", arm_index=arm_index)
            return
        
        # Нормализуем reward в [0, 1]
        normalized_reward = max(0.0, min(1.0, reward))
        
        # Обновляем параметры Beta распределения
        # Если reward > 0.5, считаем успехом, иначе неудачей
        if normalized_reward > 0.5:
            self.alpha[arm_index] += 1
        else:
            self.beta[arm_index] += 1
        
        self.rewards[arm_index] += normalized_reward
        
        logger.info(
            "Bandit updated",
            arm_index=arm_index,
            reward=normalized_reward,
            alpha=self.alpha[arm_index],
            beta=self.beta[arm_index]
        )
    
    def get_best_arm(self) -> int:
        """Получить лучшую руку на основе текущих оценок."""
        # Используем среднее значение Beta распределения
        means = self.alpha / (self.alpha + self.beta)
        return int(np.argmax(means))
    
    def get_statistics(self) -> Dict:
        """Получить статистику бандита."""
        means = self.alpha / (self.alpha + self.beta)
        
        return {
            "arms": self.arms,
            "pulls": self.pulls.tolist(),
            "means": means.tolist(),
            "total_pulls": int(np.sum(self.pulls)),
            "best_arm": int(self.get_best_arm()),
        }


class ContextualBandit:
    """Контекстный бандит для адаптации к разным условиям рынка."""
    
    def __init__(self, context_features: List[str]):
        """
        Инициализация контекстного бандита.
        
        Args:
            context_features: Список названий фич контекста
                Пример: ["volatility", "trend", "volume"]
        """
        self.context_features = context_features
        self.n_features = len(context_features)
        
        # Бандиты для разных контекстов (упрощённо - один бандит)
        # В реальности можно использовать LinUCB или другие алгоритмы
        self.bandits: Dict[str, ThompsonSamplingBandit] = {}
    
    def _get_context_key(self, context: Dict) -> str:
        """Получить ключ контекста для выбора бандита."""
        # Упрощённо - используем категоризацию по волатильности
        volatility = context.get("volatility", 0.0)
        
        if volatility < 0.1:
            return "low_vol"
        elif volatility < 0.3:
            return "medium_vol"
        else:
            return "high_vol"
    
    def initialize_bandit(self, context_key: str, arms: List[Dict]):
        """Инициализировать бандит для контекста."""
        self.bandits[context_key] = ThompsonSamplingBandit(arms)
    
    def select_arm(self, context: Dict) -> tuple:
        """
        Выбрать руку на основе контекста.
        
        Args:
            context: Словарь с фичами контекста
        
        Returns:
            (context_key, arm_index, arm_params)
        """
        context_key = self._get_context_key(context)
        
        if context_key not in self.bandits:
            # Инициализируем бандит с дефолтными руками
            default_arms = [
                {"position_size": 0.01, "stop_loss": 0.02, "take_profit": 0.05},
                {"position_size": 0.02, "stop_loss": 0.03, "take_profit": 0.06},
                {"position_size": 0.015, "stop_loss": 0.025, "take_profit": 0.055},
            ]
            self.initialize_bandit(context_key, default_arms)
        
        bandit = self.bandits[context_key]
        arm_index = bandit.select_arm()
        arm_params = bandit.arms[arm_index]
        
        return (context_key, arm_index, arm_params)
    
    def update(self, context: Dict, arm_index: int, reward: float):
        """Обновить бандит на основе контекста и награды."""
        context_key = self._get_context_key(context)
        
        if context_key in self.bandits:
            self.bandits[context_key].update(arm_index, reward)
    
    def get_statistics(self) -> Dict:
        """Получить статистику всех бандитов."""
        return {
            context_key: bandit.get_statistics()
            for context_key, bandit in self.bandits.items()
        }


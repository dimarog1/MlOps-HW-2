"""Базовый класс для ML моделей."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


class BaseMLModel(ABC):
    """
    Абстрактный базовый класс для всех ML моделей.

    Определяет интерфейс, который должны реализовать все модели.
    """

    def __init__(self, hyperparameters: Optional[Dict[str, Any]] = None):
        """
        Инициализация модели.

        Args:
            hyperparameters: Словарь с гиперпараметрами модели
        """
        self.hyperparameters = hyperparameters or {}
        self.model = None
        self.is_trained = False

    @abstractmethod
    def train(
        self, X: pd.DataFrame, y: pd.Series, clearml_task_id: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Обучение модели.

        Args:
            X: Признаки для обучения
            y: Целевая переменная
            clearml_task_id: ID задачи ClearML для логирования прогресса (опционально)

        Returns:
            Словарь с метриками обучения
        """
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Получение предсказаний.

        Args:
            X: Признаки для предсказания

        Returns:
            Массив предсказаний
        """
        pass

    @abstractmethod
    def get_default_hyperparameters(self) -> Dict[str, Any]:
        """
        Получение гиперпараметров по умолчанию.

        Returns:
            Словарь с гиперпараметрами по умолчанию
        """
        pass

    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """
        Получение описания модели.

        Returns:
            Описание модели
        """
        pass

    def save(self, path: str):
        """
        Сохранение модели.

        Args:
            path: Путь для сохранения
        """
        import joblib

        if not self.is_trained:
            raise ValueError("Модель не обучена")

        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "BaseMLModel":
        """
        Загрузка модели.

        Args:
            path: Путь к сохраненной модели

        Returns:
            Загруженная модель
        """
        from typing import cast

        import joblib

        return cast("BaseMLModel", joblib.load(path))

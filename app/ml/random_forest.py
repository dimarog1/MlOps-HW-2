"""Random Forest классификатор."""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier as SKRandomForest
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from app.logger import log
from app.ml.base import BaseMLModel


class RandomForest(BaseMLModel):
    """
    Обертка над sklearn RandomForestClassifier.

    Поддерживает настройку гиперпараметров и вычисление метрик.
    """

    def __init__(self, hyperparameters: Optional[Dict[str, Any]] = None):
        """
        Инициализация Random Forest.

        Args:
            hyperparameters: Гиперпараметры модели
        """
        super().__init__(hyperparameters)
        self.model = SKRandomForest(**self._get_model_params())

    def _get_model_params(self) -> Dict[str, Any]:
        """
        Формирует словарь параметров для инициализации sklearn модели.

        Объединяет параметры по умолчанию с переданными гиперпараметрами.

        Returns:
            Словарь параметров для передачи в конструктор sklearn RandomForestClassifier
        """
        defaults = self.get_default_hyperparameters()
        defaults.update(self.hyperparameters)
        return defaults

    def train(
        self, X: pd.DataFrame, y: pd.Series, clearml_task_id: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Обучает модель Random Forest на предоставленных данных.

        Процесс включает:
        - Разделение данных на обучающую (80%) и тестовую (20%) выборки
        - Обучение ансамбля деревьев решений на обучающей выборке
        - Логирование прогресса обучения деревьев в ClearML (для больших ансамблей)
        - Вычисление метрик качества на тестовой выборке

        Args:
            X: DataFrame с признаками для обучения
            y: Series с целевой переменной
            clearml_task_id: Опциональный ID задачи ClearML для логирования прогресса обучения

        Returns:
            Словарь с метриками качества:
            - accuracy: Точность классификации
            - precision: Прецизионность (weighted average)
            - recall: Полнота (weighted average)
            - f1: F1-мера (weighted average)
        """
        log.info(f"Начало обучения RandomForest с параметрами: {self.hyperparameters}")

        if clearml_task_id:
            try:
                from app.services.clearml_service import ClearMLService

                clearml_service = ClearMLService()
                clearml_service.log_training_progress(
                    clearml_task_id,
                    f"Инициализация RandomForest с параметрами: {self.hyperparameters}",
                )
            except Exception:
                pass

        if clearml_task_id:
            try:
                from app.services.clearml_service import ClearMLService

                clearml_service = ClearMLService()
                train_size = len(X) * 0.8
                test_size = len(X) * 0.2
                clearml_service.log_training_progress(
                    clearml_task_id,
                    f"Разделение данных: train={train_size:.0f} samples, "
                    f"test={test_size:.0f} samples",
                )
            except Exception:
                pass

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        n_estimators = self.hyperparameters.get("n_estimators", 100)
        if clearml_task_id and n_estimators > 10:
            try:
                from app.services.clearml_service import ClearMLService

                clearml_service = ClearMLService()
                for i in range(0, n_estimators, max(1, n_estimators // 10)):
                    if i == 0:
                        clearml_service.log_training_progress(
                            clearml_task_id,
                            f"Начало обучения RandomForest ({n_estimators} деревьев)...",
                        )
                    elif i < n_estimators:
                        progress = (i / n_estimators) * 100
                        clearml_service.log_training_progress(
                            clearml_task_id,
                            f"Обучение прогресс: {progress:.0f}% ({i}/{n_estimators} деревьев)",
                            iteration=i,
                        )
            except Exception:
                pass

        if self.model is None:
            raise ValueError("Модель не инициализирована")
        self.model.fit(X_train, y_train)
        self.is_trained = True

        if clearml_task_id:
            try:
                from app.services.clearml_service import ClearMLService

                clearml_service = ClearMLService()
                clearml_service.log_training_progress(
                    clearml_task_id,
                    "Обучение завершено. Вычисление метрик на тестовом наборе...",
                )
            except Exception:
                pass

        if self.model is None:
            raise ValueError("Модель не инициализирована")
        y_pred = self.model.predict(X_test)

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(
                precision_score(y_test, y_pred, average="weighted", zero_division=0)
            ),
            "recall": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
        }

        log.info(f"Обучение завершено. Метрики: {metrics}")
        return metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Выполняет предсказания для новых данных с помощью обученной модели.

        Args:
            X: DataFrame с признаками для предсказания

        Returns:
            NumPy массив с предсказанными классами

        Raises:
            ValueError: Если модель не была обучена
        """
        if not self.is_trained:
            raise ValueError("Модель не обучена")

        if self.model is None:
            raise ValueError("Модель не инициализирована")
        log.info(f"Предсказание для {len(X)} записей")
        return self.model.predict(X)

    def get_default_hyperparameters(self) -> Dict[str, Any]:
        """
        Возвращает гиперпараметры модели по умолчанию.

        Returns:
            Словарь с параметрами по умолчанию:
            - n_estimators: Количество деревьев в ансамбле (100)
            - max_depth: Максимальная глубина дерева (None - без ограничений)
            - min_samples_split: Минимальное количество образцов для разделения узла (2)
            - min_samples_leaf: Минимальное количество образцов в листе (1)
            - random_state: Seed для воспроизводимости (42)
        """
        return {
            "n_estimators": 100,
            "max_depth": None,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "random_state": 42,
        }

    @classmethod
    def get_description(cls) -> str:
        """
        Возвращает краткое описание модели.

        Returns:
            Строка с описанием Random Forest классификатора
        """
        return "Random Forest классификатор - ансамбль деревьев решений"

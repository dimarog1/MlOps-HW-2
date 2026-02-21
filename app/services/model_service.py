"""Сервис для работы с моделями."""

import json
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from app.config import settings
from app.logger import log
from app.ml import MODEL_REGISTRY, BaseMLModel
from app.models.schemas import ModelInfo, ModelType
from app.services.clearml_service import ClearMLService


class ModelService:
    """Сервис управления ML моделями."""

    def __init__(self):
        """Инициализация сервиса моделей."""
        self.models_dir = settings.models_dir
        self.metadata_file = self.models_dir / "metadata.json"
        self._metadata = self._load_metadata()
        self.clearml_service = ClearMLService()

    def _load_metadata(self) -> Dict:
        """
        Загружает метаданные моделей из JSON файла.

        Returns:
            Словарь с метаданными моделей или пустой словарь, если файл не существует
        """
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return dict(json.load(f))
        return {}

    def _save_metadata(self):
        """
        Сохраняет метаданные моделей в JSON файл.
        """
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, indent=2, ensure_ascii=False)

    def get_available_model_types(self) -> List[ModelType]:
        """
        Возвращает список всех доступных типов моделей из реестра.

        Для каждого типа модели возвращает его название, описание и гиперпараметры по умолчанию.

        Returns:
            Список объектов ModelType с информацией о каждом доступном типе модели
        """
        log.info("Получение списка доступных моделей")

        model_types = []
        for name, model_class in MODEL_REGISTRY.items():
            instance = model_class()
            model_types.append(
                ModelType(
                    name=name,
                    description=model_class.get_description(),
                    hyperparameters=instance.get_default_hyperparameters(),
                )
            )

        return model_types

    def train_model(
        self,
        model_type: str,
        model_name: str,
        X: pd.DataFrame,
        y: pd.Series,
        hyperparameters: Optional[Dict] = None,
    ) -> tuple[BaseMLModel, Dict[str, float], Optional[str]]:
        """
        Обучает модель машинного обучения на предоставленных данных.

        Процесс обучения включает:
        - Создание задачи в ClearML для отслеживания прогресса (если ClearML включен)
        - Разделение данных на обучающую и тестовую выборки
        - Обучение модели с указанными гиперпараметрами
        - Вычисление метрик качества на тестовой выборке
        - Сохранение обученной модели в файл
        - Регистрацию модели в ClearML и загрузку весов в S3
        - Сохранение метаданных модели

        Args:
            model_type: Тип модели из MODEL_REGISTRY
                (например, "LogisticRegression", "RandomForest")
            model_name: Уникальное имя для сохранения модели
            X: DataFrame с признаками для обучения
            y: Series с целевой переменной
            hyperparameters: Опциональный словарь с гиперпараметрами модели.
                            Если не указан, используются значения по умолчанию.

        Returns:
            Кортеж из трех элементов:
            - Обученная модель (BaseMLModel)
            - Словарь с метриками качества (accuracy, precision, recall, f1)
            - ID задачи ClearML (str) или None, если ClearML отключен

        Raises:
            ValueError: Если указанный тип модели не найден в MODEL_REGISTRY
        """
        log.info(f"Начало обучения модели {model_name} типа {model_type}")

        if model_type not in MODEL_REGISTRY:
            raise ValueError(
                f"Неизвестный тип модели: {model_type}. "
                f"Доступные: {list(MODEL_REGISTRY.keys())}"
            )

        clearml_task_id = None
        if self.clearml_service.enabled:
            try:
                clearml_task_id = self.clearml_service.create_training_task(
                    project_name="MLOps",
                    task_name=f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    model_type=model_type,
                    hyperparameters=hyperparameters or {},
                )

                if clearml_task_id:
                    self.clearml_service.log_training_progress(
                        clearml_task_id,
                        f"Начало обучения модели {model_name} типа {model_type}",
                    )
                    log.info(
                        f"ClearML задача создана для отслеживания прогресса: {clearml_task_id}"
                    )
            except Exception as e:
                log.warning(f"Ошибка при создании ClearML задачи (продолжаем без него): {e}")

        model_class = MODEL_REGISTRY[model_type]
        model = model_class(hyperparameters=hyperparameters)

        if clearml_task_id:
            self.clearml_service.log_training_progress(
                clearml_task_id,
                "Разделение данных на train/test наборы",
            )

        metrics = model.train(X, y, clearml_task_id=clearml_task_id)

        model_path = self.models_dir / f"{model_name}.joblib"

        if clearml_task_id:
            self.clearml_service.log_training_progress(
                clearml_task_id,
                f"Сохранение модели в {model_path}",
            )

        model.save(str(model_path))

        if clearml_task_id:
            try:
                self.clearml_service.log_metrics(clearml_task_id, metrics)

                self.clearml_service.log_training_progress(
                    clearml_task_id,
                    f"Обучение завершено. Метрики: {metrics}",
                )

                model_metadata = {
                    "model_name": model_name,
                    "model_type": model_type,
                    "metrics": metrics,
                    "hyperparameters": hyperparameters or {},
                }
                clearml_model_id = self.clearml_service.upload_model(
                    task_id=clearml_task_id,
                    model_path=str(model_path),
                    model_name=model_name,
                    metadata=model_metadata,
                )
                if clearml_model_id:
                    log.info(
                        f"Модель {model_name} загружена в ClearML как отдельная модель "
                        f"(ID: {clearml_model_id})"
                    )

                try:
                    from clearml import Task

                    task = Task.get_task(task_id=clearml_task_id)
                    task.close()
                except Exception:
                    pass

            except Exception as e:
                log.warning(f"Ошибка при работе с ClearML (продолжаем без него): {e}")

        self._metadata[model_name] = {
            "type": model_type,
            "created_at": datetime.now().isoformat(),
            "metrics": metrics,
            "hyperparameters": hyperparameters or {},
            "clearml_task_id": clearml_task_id,
        }
        self._save_metadata()

        log.info(f"Модель {model_name} успешно обучена и сохранена")
        return model, metrics, clearml_task_id

    def load_model(self, model_name: str) -> BaseMLModel:
        """
        Загружает ранее обученную модель из файла.

        Args:
            model_name: Имя модели для загрузки

        Returns:
            Загруженный объект модели, готовый для использования

        Raises:
            FileNotFoundError: Если файл модели с указанным именем не найден
        """
        log.info(f"Загрузка модели: {model_name}")

        model_path = self.models_dir / f"{model_name}.joblib"
        if not model_path.exists():
            raise FileNotFoundError(f"Модель {model_name} не найдена")

        model = BaseMLModel.load(str(model_path))
        log.info(f"Модель {model_name} успешно загружена")
        return model

    def list_models(self) -> List[ModelInfo]:
        """
        Возвращает список всех обученных моделей с их метаданными.

        Returns:
            Список объектов ModelInfo, содержащих информацию о каждой модели:
            название, тип, дату создания и метрики качества
        """
        log.info("Получение списка моделей")

        models = []
        for model_name, metadata in self._metadata.items():
            models.append(
                ModelInfo(
                    name=model_name,
                    type=metadata["type"],
                    created_at=metadata["created_at"],
                    metrics=metadata.get("metrics"),
                )
            )

        log.info(f"Найдено моделей: {len(models)}")
        return models

    def delete_model(self, model_name: str) -> bool:
        """
        Удаляет обученную модель и её метаданные.

        Args:
            model_name: Имя модели для удаления

        Returns:
            True если удаление выполнено успешно

        Raises:
            FileNotFoundError: Если модель с указанным именем не найдена
        """
        log.info(f"Удаление модели: {model_name}")

        model_path = self.models_dir / f"{model_name}.joblib"
        if not model_path.exists():
            raise FileNotFoundError(f"Модель {model_name} не найдена")

        model_path.unlink()

        if model_name in self._metadata:
            del self._metadata[model_name]
            self._save_metadata()

        log.info(f"Модель {model_name} успешно удалена")
        return True

    def retrain_model(
        self,
        model_name: str,
        X: pd.DataFrame,
        y: pd.Series,
        hyperparameters: Optional[Dict] = None,
    ) -> tuple[BaseMLModel, Dict[str, float], Optional[str]]:
        """
        Переобучает существующую модель на новых данных.

        Использует тип модели и гиперпараметры из метаданных существующей модели,
        если новые гиперпараметры не указаны.

        Args:
            model_name: Имя существующей модели для переобучения
            X: Новые данные признаков для обучения
            y: Новая целевая переменная
            hyperparameters: Опциональные новые гиперпараметры.
                           Если не указаны, используются гиперпараметры из метаданных модели.

        Returns:
            Кортеж из трех элементов:
            - Переобученная модель (BaseMLModel)
            - Словарь с метриками качества
            - ID задачи ClearML (str) или None

        Raises:
            FileNotFoundError: Если модель с указанным именем не найдена
        """
        log.info(f"Переобучение модели: {model_name}")

        if model_name not in self._metadata:
            raise FileNotFoundError(f"Модель {model_name} не найдена")

        model_type = self._metadata[model_name]["type"]

        if hyperparameters is None:
            hyperparameters = self._metadata[model_name].get("hyperparameters", {})

        return self.train_model(model_type, model_name, X, y, hyperparameters)

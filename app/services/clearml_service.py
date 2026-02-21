"""Сервис для интеграции с ClearML."""

from typing import Any, Dict, Optional

from app.config import settings
from app.logger import log

try:
    from clearml import Model, Task

    CLEARML_AVAILABLE = True
except ImportError:
    log.warning("ClearML не установлен. Интеграция отключена.")
    CLEARML_AVAILABLE = False


class ClearMLService:
    """Сервис для работы с ClearML."""

    def __init__(self):
        """
        Инициализирует сервис интеграции с ClearML.

        Проверяет доступность ClearML и наличие необходимых credentials.
        Настраивает переменные окружения для работы с S3 через boto3.
        """
        self.enabled = CLEARML_AVAILABLE and self._is_configured()

        if not self.enabled:
            log.warning("ClearML интеграция отключена")
        else:
            import os

            os.environ["AWS_ACCESS_KEY_ID"] = settings.s3_access_key
            os.environ["AWS_SECRET_ACCESS_KEY"] = settings.s3_secret_key
            os.environ["AWS_ENDPOINT_URL"] = settings.s3_endpoint

            log.info("ClearML интеграция активна")

    def _is_configured(self) -> bool:
        """
        Проверяет наличие всех необходимых настроек для работы с ClearML.

        Returns:
            True если все необходимые credentials настроены, False иначе
        """
        return bool(
            settings.clearml_api_host
            and settings.clearml_access_key
            and settings.clearml_secret_key
        )

    def create_training_task(
        self,
        project_name: str,
        task_name: str,
        model_type: str,
        hyperparameters: Dict,
    ) -> Optional[str]:
        """
        Создает новую задачу обучения в ClearML для отслеживания эксперимента.

        Закрывает предыдущую активную задачу (если есть) и создает новую.
        Сохраняет гиперпараметры и тип модели в задаче.

        Args:
            project_name: Название проекта в ClearML
            task_name: Уникальное имя задачи
            model_type: Тип модели машинного обучения
            hyperparameters: Словарь с гиперпараметрами модели

        Returns:
            ID созданной задачи (str) или None, если ClearML отключен или произошла ошибка
        """
        if not self.enabled:
            return None

        try:
            current_task = Task.current_task()
            if current_task:
                current_task.close()

            task = Task.init(
                project_name=project_name,
                task_name=task_name,
                task_type=Task.TaskTypes.training,
                reuse_last_task_id=False,
            )

            task.connect(hyperparameters)
            task.set_parameter("model_type", model_type)

            log.info(f"ClearML задача создана: {task.id}")
            return str(task.id)

        except Exception as e:
            log.error(f"Ошибка при создании ClearML задачи: {e}")
            return None

    def get_task_logger(self, task_id: str):
        """
        Получает объект logger для логирования в задачу ClearML.

        Args:
            task_id: ID задачи ClearML

        Returns:
            Logger объект для задачи или None, если ClearML отключен или произошла ошибка
        """
        if not self.enabled:
            return None

        try:
            task = Task.get_task(task_id=task_id)
            return task.get_logger()
        except Exception as e:
            log.error(f"Ошибка при получении logger: {e}")
            return None

    def log_metrics(self, task_id: str, metrics: Dict[str, float], iteration: Optional[int] = None):
        """
        Логирует метрики качества модели в задачу ClearML.

        Если указана итерация, метрики логируются как скалярные значения с привязкой к итерации
        (для отображения графиков прогресса). Иначе логируются как финальные значения.

        Args:
            task_id: ID задачи ClearML
            metrics: Словарь с метриками (ключ - название метрики, значение - числовое значение)
            iteration: Опциональный номер итерации для логирования прогресса обучения
        """
        if not self.enabled:
            return

        try:
            task = Task.get_task(task_id=task_id)
            logger = task.get_logger()

            for metric_name, metric_value in metrics.items():
                if iteration is not None:
                    logger.report_scalar(
                        title="Metrics",
                        series=metric_name,
                        value=metric_value,
                        iteration=iteration,
                    )
                else:
                    logger.report_single_value(metric_name, metric_value)

            log.info(f"Метрики залогированы в ClearML задачу {task_id} (iteration={iteration})")

        except Exception as e:
            log.error(f"Ошибка при логировании метрик: {e}")

    def log_training_progress(self, task_id: str, message: str, iteration: Optional[int] = None):
        """
        Логирует текстовое сообщение о прогрессе обучения в задачу ClearML.

        Args:
            task_id: ID задачи ClearML
            message: Текстовое сообщение о текущем этапе обучения
            iteration: Опциональный номер итерации для привязки сообщения к конкретной итерации
        """
        if not self.enabled:
            return

        try:
            task = Task.get_task(task_id=task_id)
            logger = task.get_logger()

            if iteration is not None:
                logger.report_text(f"[Iteration {iteration}] {message}")
            else:
                logger.report_text(message)

            log.info(f"ClearML progress logged: {message}")

        except Exception as e:
            log.error(f"Ошибка при логировании прогресса: {e}")

    def upload_model(
        self,
        task_id: str,
        model_path: str,
        model_name: str,
        metadata: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        Загружает обученную модель в ClearML Model Registry и S3 хранилище.

        Выполняет следующие действия:
        1. Загружает файл модели в S3 через boto3
        2. Создает OutputModel в ClearML для регистрации модели в Model Registry
        3. Добавляет метаданные модели (метрики, гиперпараметры)

        Модель становится доступной в ClearML независимо от задачи обучения.

        Args:
            task_id: ID задачи обучения, к которой привязана модель
            model_path: Путь к файлу модели на диске
            model_name: Уникальное имя модели для регистрации
            metadata: Опциональный словарь с метаданными (метрики, гиперпараметры и т.д.)

        Returns:
            ID зарегистрированной модели в ClearML (str) или None при ошибке
        """
        if not self.enabled:
            return None

        try:
            from pathlib import Path

            import boto3
            from clearml import OutputModel

            task = Task.get_task(task_id=task_id)

            s3_client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name="us-east-1",
            )

            model_filename = Path(model_path).name
            s3_key = f"clearml/models/{model_name}/{model_filename}"
            s3_uri = f"s3://{settings.s3_bucket}/{s3_key}"

            s3_client.upload_file(model_path, settings.s3_bucket, s3_key)
            log.info(f"Модель загружена в S3: {s3_uri}")

            output_model = OutputModel(
                task=task,
                name=model_name,
                tags=["trained", "production-ready"],
                comment=f"Модель обучена в задаче {task_id}. Веса в S3: {s3_uri}",
            )

            output_model.update_weights(
                weights_filename=model_path,
                auto_delete_file=False,
            )

            if metadata:
                for key, value in metadata.items():
                    output_model.set_metadata(key, str(value))

            model_id = output_model.id
            log.info(
                f"Модель {model_name} загружена в ClearML как отдельная модель (ID: {model_id})"
            )
            log.info(f"Веса модели сохранены в S3: {s3_uri}")
            return str(model_id)

        except Exception as e:
            log.error(f"Ошибка при загрузке модели в ClearML: {e}")
            import traceback

            log.error(traceback.format_exc())
            return None

    def get_model(self, model_name: str) -> Optional[str]:
        """
        Загружает модель из ClearML Model Registry на локальный диск.

        Args:
            model_name: Название модели в ClearML

        Returns:
            Путь к локальной копии модели или None при ошибке
        """
        if not self.enabled:
            return None

        try:
            model = Model(model_name=model_name)
            model_path = model.get_local_copy()

            log.info(f"Модель получена из ClearML: {model_path}")
            return str(model_path) if model_path is not None else None

        except Exception as e:
            log.error(f"Ошибка при получении модели: {e}")
            return None

    def list_models(self, project_name: str = "MLOps") -> list[Any]:
        """
        Возвращает список всех моделей из указанного проекта в ClearML.

        Args:
            project_name: Название проекта в ClearML (по умолчанию "MLOps")

        Returns:
            Список объектов Model из ClearML или пустой список при ошибке
        """
        if not self.enabled:
            return []

        try:
            from clearml import Model as ClearMLModel

            models = ClearMLModel.query_models(
                project_name=project_name,
                only_published=False,
            )

            log.info(f"Получено {len(models)} моделей из ClearML")
            return list(models)  # type: ignore[no-any-return]

        except Exception as e:
            log.error(f"Ошибка при получении списка моделей: {e}")
            return []

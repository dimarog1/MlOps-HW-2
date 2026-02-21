"""gRPC сервер для ML сервиса."""

import json
from concurrent import futures

import grpc

from app import __version__
from app.config import settings
from app.logger import log
from app.services import DatasetService, ModelService

# Импортируем сгенерированные protobuf файлы
try:
    from app.grpc_service import ml_service_pb2, ml_service_pb2_grpc
except ImportError:
    log.warning("gRPC protobuf файлы не сгенерированы. Запустите: python -m grpc_tools.protoc")
    ml_service_pb2 = None  # type: ignore[assignment]
    ml_service_pb2_grpc = None  # type: ignore[assignment]


class MLServiceServicer:
    """
    Реализация gRPC сервиса для машинного обучения.

    Предоставляет методы для:
    - Обучения и переобучения ML моделей
    - Получения предсказаний от обученных моделей
    - Управления моделями и датасетами
    - Проверки статуса сервиса
    """

    def __init__(self):
        """
        Инициализирует gRPC сервис.

        Создает экземпляры ModelService и DatasetService для работы с моделями и датасетами.
        """
        self.model_service = ModelService()
        self.dataset_service = DatasetService()

    def HealthCheck(self, request, context):
        """
        Проверяет работоспособность gRPC сервиса.

        Args:
            request: HealthRequest (пустой запрос)
            context: gRPC контекст

        Returns:
            HealthResponse со статусом "ok" и версией приложения
        """
        log.debug("gRPC HealthCheck запрос")
        return ml_service_pb2.HealthResponse(
            status="ok",
            version=__version__,
        )

    def GetModelTypes(self, request, context):
        """
        Возвращает список всех доступных типов моделей для обучения.

        Для каждого типа модели возвращает название, описание и гиперпараметры по умолчанию.

        Args:
            request: ModelTypesRequest (пустой запрос)
            context: gRPC контекст

        Returns:
            ModelTypesResponse со списком доступных типов моделей
        """
        log.info("gRPC GetModelTypes запрос")
        try:
            model_types = self.model_service.get_available_model_types()

            response_types = []
            for mt in model_types:
                response_types.append(
                    ml_service_pb2.ModelType(
                        name=mt.name,
                        description=mt.description,
                        hyperparameters_json=json.dumps(mt.hyperparameters),
                    )
                )

            return ml_service_pb2.ModelTypesResponse(model_types=response_types)
        except Exception as e:
            log.error(f"Ошибка в GetModelTypes: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ml_service_pb2.ModelTypesResponse()

    def TrainModel(self, request, context):
        """
        Обучает новую модель машинного обучения на указанном датасете.

        Загружает датасет, разделяет данные на признаки и целевую переменную,
        обучает модель с указанными гиперпараметрами и возвращает метрики качества.

        Args:
            request: TrainModelRequest с параметрами:
                - model_type: Тип модели для обучения
                - model_name: Уникальное имя модели
                - dataset_name: Имя датасета для обучения
                - target_column: Название целевой колонки
                - hyperparameters_json: JSON строка с гиперпараметрами (опционально)
            context: gRPC контекст

        Returns:
            TrainModelResponse с информацией об обученной модели:
            - model_name: Имя модели
            - model_type: Тип модели
            - metrics_json: JSON строка с метриками качества
            - clearml_task_id: ID задачи ClearML (если ClearML включен)
        """
        log.info(f"gRPC TrainModel запрос для {request.model_name}")
        try:
            dataset = self.dataset_service.load_dataset(request.dataset_name)

            if request.target_column not in dataset.columns:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Колонка {request.target_column} не найдена")
                return ml_service_pb2.TrainModelResponse()

            X = dataset.drop(columns=[request.target_column])
            y = dataset[request.target_column]

            hyperparameters = None
            if request.hyperparameters_json:
                hyperparameters = json.loads(request.hyperparameters_json)

            model, metrics, clearml_task_id = self.model_service.train_model(
                model_type=request.model_type,
                model_name=request.model_name,
                X=X,
                y=y,
                hyperparameters=hyperparameters,
            )

            return ml_service_pb2.TrainModelResponse(
                model_name=request.model_name,
                model_type=request.model_type,
                metrics_json=json.dumps(metrics),
                clearml_task_id=clearml_task_id or "",
            )

        except FileNotFoundError as e:
            log.error(f"Датасет не найден: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return ml_service_pb2.TrainModelResponse()
        except Exception as e:
            log.error(f"Ошибка при обучении: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ml_service_pb2.TrainModelResponse()

    def Predict(self, request, context):
        """
        Выполняет предсказания с помощью обученной модели.

        Загружает модель по имени и выполняет предсказания для предоставленных данных.

        Args:
            request: PredictRequest с параметрами:
                - model_name: Имя обученной модели
                - data_json: JSON строка с данными для предсказания (список словарей)
            context: gRPC контекст

        Returns:
            PredictResponse с результатами:
            - predictions_json: JSON строка с массивом предсказаний
            - model_name: Имя использованной модели
        """
        log.info(f"gRPC Predict запрос для {request.model_name}")
        try:
            model = self.model_service.load_model(request.model_name)

            import pandas as pd

            data = json.loads(request.data_json)
            df = pd.DataFrame(data)

            predictions = model.predict(df)

            return ml_service_pb2.PredictResponse(
                predictions_json=json.dumps(predictions.tolist()),
                model_name=request.model_name,
            )

        except FileNotFoundError as e:
            log.error(f"Модель не найдена: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return ml_service_pb2.PredictResponse()
        except Exception as e:
            log.error(f"Ошибка при предсказании: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ml_service_pb2.PredictResponse()

    def ListModels(self, request, context):
        """
        Возвращает список всех обученных моделей с их метаданными.

        Args:
            request: ListModelsRequest (пустой запрос)
            context: gRPC контекст

        Returns:
            ListModelsResponse со списком моделей, включая:
            - name: Имя модели
            - type: Тип модели
            - created_at: Дата создания
            - metrics_json: JSON строка с метриками качества
        """
        log.info("gRPC ListModels запрос")
        try:
            models = self.model_service.list_models()

            response_models = []
            for model in models:
                response_models.append(
                    ml_service_pb2.ModelInfo(
                        name=model.name,
                        type=model.type,
                        created_at=model.created_at,
                        metrics_json=json.dumps(model.metrics) if model.metrics else "{}",
                    )
                )

            return ml_service_pb2.ListModelsResponse(models=response_models)
        except Exception as e:
            log.error(f"Ошибка в ListModels: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ml_service_pb2.ListModelsResponse()

    def DeleteModel(self, request, context):
        """
        Удаляет обученную модель и её метаданные.

        Args:
            request: DeleteModelRequest с параметрами:
                - model_name: Имя модели для удаления
            context: gRPC контекст

        Returns:
            DeleteModelResponse с результатом операции:
            - success: True если удаление успешно
            - message: Сообщение о результате операции
        """
        log.info(f"gRPC DeleteModel запрос для {request.model_name}")
        try:
            self.model_service.delete_model(request.model_name)
            return ml_service_pb2.DeleteModelResponse(
                success=True,
                message=f"Модель {request.model_name} успешно удалена",
            )
        except FileNotFoundError as e:
            log.error(f"Модель не найдена: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return ml_service_pb2.DeleteModelResponse(success=False, message=str(e))
        except Exception as e:
            log.error(f"Ошибка при удалении: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ml_service_pb2.DeleteModelResponse(success=False, message=str(e))

    def RetrainModel(self, request, context):
        """
        Переобучает существующую модель на новых данных.

        Использует тип модели из метаданных существующей модели.
        Если новые гиперпараметры не указаны, используются гиперпараметры из метаданных.

        Args:
            request: RetrainModelRequest с параметрами:
                - model_name: Имя существующей модели для переобучения
                - dataset_name: Имя датасета для переобучения
                - target_column: Название целевой колонки
                - hyperparameters_json: JSON строка с новыми гиперпараметрами (опционально)
            context: gRPC контекст

        Returns:
            TrainModelResponse с информацией о переобученной модели:
            - model_name: Имя модели
            - model_type: Тип модели
            - metrics_json: JSON строка с новыми метриками качества
            - clearml_task_id: ID задачи ClearML (если ClearML включен)
        """
        log.info(f"gRPC RetrainModel запрос для {request.model_name}")
        try:
            dataset = self.dataset_service.load_dataset(request.dataset_name)

            if request.target_column not in dataset.columns:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Колонка {request.target_column} не найдена")
                return ml_service_pb2.TrainModelResponse()

            X = dataset.drop(columns=[request.target_column])
            y = dataset[request.target_column]

            hyperparameters = None
            if request.hyperparameters_json:
                hyperparameters = json.loads(request.hyperparameters_json)

            model, metrics, clearml_task_id = self.model_service.retrain_model(
                model_name=request.model_name,
                X=X,
                y=y,
                hyperparameters=hyperparameters,
            )

            model_metadata = self.model_service._metadata.get(request.model_name, {})
            model_type = model_metadata.get("type", "Unknown")

            return ml_service_pb2.TrainModelResponse(
                model_name=request.model_name,
                model_type=model_type,
                metrics_json=json.dumps(metrics),
                clearml_task_id=clearml_task_id or "",
            )

        except FileNotFoundError as e:
            log.error(f"Модель или датасет не найдены: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return ml_service_pb2.TrainModelResponse()
        except Exception as e:
            log.error(f"Ошибка при переобучении: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ml_service_pb2.TrainModelResponse()

    def ListDatasets(self, request, context):
        """
        Возвращает список всех загруженных датасетов с их метаданными.

        Args:
            request: ListDatasetsRequest (пустой запрос)
            context: gRPC контекст

        Returns:
            ListDatasetsResponse со списком датасетов, включая:
            - name: Имя датасета
            - size: Размер файла в байтах
            - rows: Количество строк
            - columns_json: JSON строка с названиями колонок
            - uploaded_at: Дата загрузки
        """
        log.info("gRPC ListDatasets запрос")
        try:
            datasets = self.dataset_service.list_datasets()

            response_datasets = []
            for ds in datasets:
                response_datasets.append(
                    ml_service_pb2.DatasetInfo(
                        name=ds.name,
                        size=ds.size,
                        rows=ds.rows or 0,
                        columns_json=json.dumps(ds.columns) if ds.columns else "[]",
                        uploaded_at=ds.uploaded_at,
                    )
                )

            return ml_service_pb2.ListDatasetsResponse(datasets=response_datasets)
        except Exception as e:
            log.error(f"Ошибка в ListDatasets: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ml_service_pb2.ListDatasetsResponse()


def serve():
    """
    Запускает gRPC сервер для ML сервиса.

    Создает gRPC сервер с пулом потоков и регистрирует MLServiceServicer.
    Сервер слушает на адресе, указанном в настройках (grpc_host:grpc_port).

    Raises:
        SystemExit: Если protobuf файлы не сгенерированы
    """
    if ml_service_pb2 is None or ml_service_pb2_grpc is None:
        log.error("Невозможно запустить gRPC сервер: protobuf файлы не сгенерированы")
        return

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ml_service_pb2_grpc.add_MLServiceServicer_to_server(MLServiceServicer(), server)

    address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(address)

    log.info(f"Запуск gRPC сервера на {address}")
    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        log.info("Остановка gRPC сервера")
        server.stop(0)


if __name__ == "__main__":
    serve()

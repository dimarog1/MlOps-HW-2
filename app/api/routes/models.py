"""Эндпоинты для работы с моделями."""

from typing import List

from fastapi import APIRouter, HTTPException, status

from app.logger import log
from app.models.schemas import (
    DeleteResponse,
    ModelInfo,
    ModelType,
    PredictRequest,
    PredictResponse,
    TrainRequest,
    TrainResponse,
)
from app.services import DatasetService, ModelService

router = APIRouter()
model_service = ModelService()
dataset_service = DatasetService()


@router.get("/types", response_model=List[ModelType])
async def get_model_types():
    """
    Получение списка доступных типов моделей.

    Returns:
        Список доступных моделей с описанием и гиперпараметрами
    """
    log.info("Запрос списка типов моделей")
    try:
        return model_service.get_available_model_types()
    except Exception as e:
        log.error(f"Ошибка при получении типов моделей: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/train", response_model=TrainResponse, status_code=status.HTTP_201_CREATED)
async def train_model(request: TrainRequest):
    """
    Обучает новую модель машинного обучения на указанном датасете.

    Загружает датасет, разделяет данные на признаки и целевую переменную,
    обучает модель с указанными гиперпараметрами и возвращает метрики качества.

    Args:
        request: Параметры обучения, включающие:
            - model_type: Тип модели для обучения
            - model_name: Уникальное имя модели
            - dataset_name: Имя датасета для обучения
            - target_column: Название целевой колонки
            - hyperparameters: Опциональные гиперпараметры модели

    Returns:
        TrainResponse с информацией об обученной модели:
        - model_name: Имя модели
        - model_type: Тип модели
        - metrics: Словарь с метриками качества
        - clearml_task_id: ID задачи ClearML (если ClearML включен)

    Raises:
        HTTPException: При ошибках загрузки датасета, отсутствии целевой колонки
                      или ошибках обучения модели
    """
    log.info(f"Запрос на обучение модели {request.model_name} типа {request.model_type}")

    try:
        dataset = dataset_service.load_dataset(request.dataset_name)

        if request.target_column not in dataset.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Колонка {request.target_column} не найдена в датасете",
            )

        X = dataset.drop(columns=[request.target_column])
        y = dataset[request.target_column]

        model, metrics, clearml_task_id = model_service.train_model(
            model_type=request.model_type,
            model_name=request.model_name,
            X=X,
            y=y,
            hyperparameters=request.hyperparameters,
        )

        return TrainResponse(
            model_name=request.model_name,
            model_type=request.model_type,
            metrics=metrics,
            clearml_task_id=clearml_task_id,
        )

    except FileNotFoundError as e:
        log.error(f"Датасет не найден: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        log.error(f"Ошибка валидации: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        log.error(f"Ошибка при обучении модели: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Получение предсказаний модели.

    Args:
        request: Имя модели и данные для предсказания

    Returns:
        Предсказания модели

    Raises:
        HTTPException: При ошибках загрузки модели или предсказания
    """
    log.info(f"Запрос на предсказание с помощью модели {request.model_name}")

    try:
        model = model_service.load_model(request.model_name)

        import pandas as pd

        df = pd.DataFrame(request.data)

        predictions = model.predict(df)

        return PredictResponse(
            predictions=predictions.tolist(),
            model_name=request.model_name,
        )

    except FileNotFoundError as e:
        log.error(f"Модель не найдена: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        error_msg = str(e)
        log.error(f"Ошибка валидации при предсказании: {error_msg}")

        if "feature names" in error_msg.lower() or "feature" in error_msg.lower():
            if "unseen at fit time" in error_msg:
                detail = "Ошибка: Неправильные названия признаков в данных для предсказания.\n\n"
                detail += "Модель ожидает другие названия колонок, чем те, что вы предоставили.\n"
                detail += f"Детали: {error_msg}"
            else:
                detail = f"Ошибка валидации данных: {error_msg}"
        else:
            detail = f"Ошибка валидации: {error_msg}"

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
    except Exception as e:
        error_msg = str(e)
        log.error(f"Ошибка при предсказании: {error_msg}")

        if len(error_msg) > 500:
            detail = (
                f"Ошибка при предсказании: {error_msg[:500]}...\n\n"
                "(Полное сообщение в логах сервера)"
            )
        else:
            detail = f"Ошибка при предсказании: {error_msg}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


@router.get("/", response_model=List[ModelInfo])
async def list_models():
    """
    Получение списка всех обученных моделей.

    Returns:
        Список информации о моделях
    """
    log.info("Запрос списка моделей")
    try:
        return model_service.list_models()
    except Exception as e:
        log.error(f"Ошибка при получении списка моделей: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{model_name}", response_model=DeleteResponse)
async def delete_model(model_name: str):
    """
    Удаление модели.

    Args:
        model_name: Имя модели для удаления

    Returns:
        Результат удаления

    Raises:
        HTTPException: Если модель не найдена
    """
    log.info(f"Запрос на удаление модели {model_name}")

    try:
        model_service.delete_model(model_name)
        return DeleteResponse(
            success=True,
            message=f"Модель {model_name} успешно удалена",
        )
    except FileNotFoundError as e:
        log.error(f"Модель не найдена: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        log.error(f"Ошибка при удалении модели: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{model_name}/retrain", response_model=TrainResponse)
async def retrain_model(model_name: str, request: TrainRequest):
    """
    Переобучение существующей модели.

    Args:
        model_name: Имя модели для переобучения
        request: Параметры обучения

    Returns:
        Информация об обученной модели и новые метрики
    """
    log.info(f"Запрос на переобучение модели {model_name}")

    try:
        dataset = dataset_service.load_dataset(request.dataset_name)

        if request.target_column not in dataset.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Колонка {request.target_column} не найдена в датасете",
            )

        X = dataset.drop(columns=[request.target_column])
        y = dataset[request.target_column]

        model, metrics, clearml_task_id = model_service.retrain_model(
            model_name=model_name,
            X=X,
            y=y,
            hyperparameters=request.hyperparameters,
        )

        return TrainResponse(
            model_name=model_name,
            model_type=request.model_type,
            metrics=metrics,
            clearml_task_id=clearml_task_id,
        )

    except FileNotFoundError as e:
        log.error(f"Ресурс не найден: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        log.error(f"Ошибка при переобучении модели: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

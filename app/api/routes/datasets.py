"""Эндпоинты для работы с датасетами."""

from typing import List

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.logger import log
from app.models.schemas import DatasetInfo, DeleteResponse
from app.services import DatasetService

router = APIRouter()
dataset_service = DatasetService()


@router.get("/", response_model=List[DatasetInfo])
async def list_datasets():
    """
    Получение списка всех датасетов.

    Returns:
        Список информации о датасетах
    """
    log.info("Запрос списка датасетов")
    try:
        return dataset_service.list_datasets()
    except Exception as e:
        log.error(f"Ошибка при получении списка датасетов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/upload", response_model=DatasetInfo, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Загрузка датасета.

    Args:
        file: Файл датасета (CSV или JSON)

    Returns:
        Информация о загруженном датасете

    Raises:
        HTTPException: При ошибках чтения или сохранения файла
    """
    log.info(f"Загрузка датасета: {file.filename}")

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя файла не указано",
        )

    if not (file.filename.endswith(".csv") or file.filename.endswith(".json")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только CSV и JSON файлы",
        )

    try:
        content = await file.read()

        if file.filename.endswith(".json"):
            import json

            data = pd.DataFrame(json.loads(content))
        else:
            from io import StringIO

            data = pd.read_csv(StringIO(content.decode("utf-8")))

        dataset_info = dataset_service.save_dataset(file.filename, data)

        log.info(f"Датасет {file.filename} успешно загружен")
        return dataset_info

    except Exception as e:
        log.error(f"Ошибка при загрузке датасета: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обработке файла: {str(e)}",
        )


@router.get("/{dataset_name}", response_model=DatasetInfo)
async def get_dataset_info(dataset_name: str):
    """
    Получение информации о датасете.

    Args:
        dataset_name: Имя датасета

    Returns:
        Информация о датасете
    """
    log.info(f"Запрос информации о датасете {dataset_name}")

    try:
        return dataset_service.get_dataset_info(dataset_name)
    except FileNotFoundError as e:
        log.error(f"Датасет не найден: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        log.error(f"Ошибка при получении информации о датасете: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/sync-s3", response_model=DeleteResponse)
async def sync_datasets_to_s3():
    """
    Синхронизация всех существующих датасетов в S3.

    Returns:
        Результат синхронизации
    """
    log.info("Запрос на синхронизацию датасетов в S3")

    try:
        dataset_service.sync_existing_to_s3()
        return DeleteResponse(
            success=True,
            message="Датасеты успешно синхронизированы с S3",
        )
    except Exception as e:
        log.error(f"Ошибка при синхронизации: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{dataset_name}", response_model=DeleteResponse)
async def delete_dataset(dataset_name: str):
    """
    Удаление датасета.

    Args:
        dataset_name: Имя датасета для удаления

    Returns:
        Результат удаления
    """
    log.info(f"Запрос на удаление датасета {dataset_name}")

    try:
        dataset_service.delete_dataset(dataset_name)
        return DeleteResponse(
            success=True,
            message=f"Датасет {dataset_name} успешно удален",
        )
    except FileNotFoundError as e:
        log.error(f"Датасет не найден: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        log.error(f"Ошибка при удалении датасета: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

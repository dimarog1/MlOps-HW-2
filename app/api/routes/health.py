"""Эндпоинты для проверки здоровья сервиса."""

from fastapi import APIRouter

from app import __version__
from app.logger import log
from app.models.schemas import HealthResponse, ReadyResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Проверка состояния сервиса.

    Returns:
        Статус сервиса и версия приложения
    """
    log.debug("Health check запрос")
    return HealthResponse(
        status="ok",
        version=__version__,
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready_check():
    """
    Проверка готовности сервиса (readiness).

    Returns:
        ready: true если сервис готов принимать запросы
    """
    log.debug("Ready check запрос")
    return ReadyResponse(ready=True)

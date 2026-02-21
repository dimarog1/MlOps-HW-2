"""Настройка логирования."""

import sys

from loguru import logger

from app.config import settings


def setup_logger():
    """
    Настраивает логгер с ротацией файлов и форматированием.

    Настраивает два хендлера:
    - Консольный вывод с цветным форматированием (уровень INFO)
    - Файловый вывод с ротацией при достижении 10MB, сжатием и хранением 1 неделю (уровень DEBUG)

    Returns:
        Настроенный logger объект
    """
    logger.remove()

    logger.add(
        sys.stdout,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        level="INFO",
    )

    log_file = settings.logs_dir / "app.log"
    logger.add(
        log_file,
        rotation="10 MB",
        retention="1 week",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
    )

    logger.info("Логгер инициализирован")
    return logger


log = setup_logger()

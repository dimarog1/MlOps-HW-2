"""Конфигурация приложения."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    # Основные настройки
    app_name: str = "ML Model Training API"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051

    # Пути
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    models_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "models")
    datasets_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "datasets")
    logs_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "logs")

    # S3/MinIO настройки
    s3_endpoint: str = os.getenv("S3_ENDPOINT", "http://minio:9000")
    s3_access_key: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    s3_secret_key: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    s3_bucket: str = os.getenv("S3_BUCKET", "mlops")
    s3_region: str = os.getenv("S3_REGION", "us-east-1")

    # ClearML настройки
    clearml_api_host: Optional[str] = os.getenv("CLEARML_API_HOST")
    clearml_web_host: Optional[str] = os.getenv("CLEARML_WEB_HOST")
    clearml_files_host: Optional[str] = os.getenv("CLEARML_FILES_HOST")
    clearml_access_key: Optional[str] = os.getenv("CLEARML_ACCESS_KEY")
    clearml_secret_key: Optional[str] = os.getenv("CLEARML_SECRET_KEY")

    # DVC настройки
    dvc_remote: str = "s3storage"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        """Инициализация настроек с созданием необходимых директорий."""
        super().__init__(**kwargs)
        try:
            self.models_dir.mkdir(parents=True, exist_ok=True)
            self.datasets_dir.mkdir(parents=True, exist_ok=True)
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            pass


settings = Settings()

"""Сервис для работы с DVC."""

import os
import subprocess
from typing import List, Optional

from app.config import settings
from app.logger import log


class DVCService:
    """
    Сервис для версионирования датасетов через DVC.

    Требование 9: Датасеты версионируются через DVC
    Требование 11: Кэш DVC хранится на S3 (MinIO)

    DVC конфигурация (см. .dvc/config):
    - remote = s3storage (настроен на MinIO S3)
    - url = s3://mlops/dvc
    """

    def __init__(self):
        """Инициализация DVC сервиса."""
        self.datasets_dir = settings.datasets_dir
        self.enabled = self._check_dvc_available()

    def _check_dvc_available(self) -> bool:
        """Проверка доступности DVC."""
        try:
            result = subprocess.run(
                ["dvc", "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                log.info("DVC доступен")
                return True
            return False
        except Exception as e:
            log.warning(f"DVC недоступен: {e}")
            return False

    def add_dataset(self, dataset_name: str) -> bool:
        """
        Добавление датасета под версионный контроль DVC.

        Args:
            dataset_name: Имя файла датасета

        Returns:
            True если успешно
        """
        if not self.enabled:
            log.warning("DVC недоступен, пропуск add")
            return False

        try:
            dataset_path = self.datasets_dir / dataset_name

            if not dataset_path.exists():
                log.error(f"Датасет не найден: {dataset_path}")
                return False

            env = os.environ.copy()
            env.update(
                {
                    "S3_ENDPOINT": settings.s3_endpoint,
                    "S3_ACCESS_KEY": settings.s3_access_key,
                    "S3_SECRET_KEY": settings.s3_secret_key,
                }
            )

            result = subprocess.run(
                ["dvc", "add", str(dataset_path)],
                capture_output=True,
                text=True,
                cwd=settings.base_dir,
                env=env,
                timeout=30,
            )

            if result.returncode == 0:
                log.info(f"Датасет {dataset_name} добавлен в DVC")

                dvc_file = dataset_path.with_suffix(dataset_path.suffix + ".dvc")
                if dvc_file.exists():
                    log.info(f"Создан DVC файл: {dvc_file}")

                return True
            else:
                log.error(f"Ошибка DVC add: {result.stderr}")
                return False

        except Exception as e:
            log.error(f"Ошибка при добавлении в DVC: {e}")
            return False

    def push_dataset(self, dataset_name: Optional[str] = None) -> bool:
        """
        Загрузка датасета в удаленное хранилище.

        Args:
            dataset_name: Имя датасета (или None для всех)

        Returns:
            True если успешно
        """
        if not self.enabled:
            log.warning("DVC недоступен, пропуск push")
            return False

        try:
            env = os.environ.copy()
            env.update(
                {
                    "S3_ENDPOINT": settings.s3_endpoint,
                    "S3_ACCESS_KEY": settings.s3_access_key,
                    "S3_SECRET_KEY": settings.s3_secret_key,
                }
            )

            cmd = ["dvc", "push"]

            if dataset_name:
                dataset_path = self.datasets_dir / dataset_name
                cmd.append(str(dataset_path.with_suffix(dataset_path.suffix + ".dvc")))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=settings.base_dir,
                env=env,
                timeout=120,
            )

            if result.returncode == 0:
                log.info("DVC push выполнен успешно")
                return True
            else:
                log.error(f"Ошибка DVC push: {result.stderr}")
                return False

        except Exception as e:
            log.error(f"Ошибка при DVC push: {e}")
            return False

    def pull_dataset(self, dataset_name: Optional[str] = None) -> bool:
        """
        Загрузка датасета из удаленного хранилища.

        Args:
            dataset_name: Имя датасета (или None для всех)

        Returns:
            True если успешно
        """
        if not self.enabled:
            log.warning("DVC недоступен, пропуск pull")
            return False

        try:
            cmd = ["dvc", "pull"]

            if dataset_name:
                dataset_path = self.datasets_dir / dataset_name
                cmd.append(str(dataset_path.with_suffix(dataset_path.suffix + ".dvc")))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=settings.base_dir,
                timeout=120,
            )

            if result.returncode == 0:
                log.info("DVC pull выполнен успешно")
                return True
            else:
                log.error(f"Ошибка DVC pull: {result.stderr}")
                return False

        except Exception as e:
            log.error(f"Ошибка при DVC pull: {e}")
            return False

    def list_tracked_files(self) -> List[str]:
        """
        Список файлов под контролем DVC.

        Returns:
            Список имен файлов
        """
        if not self.enabled:
            return []

        try:
            result = subprocess.run(
                ["dvc", "list", ".", "datasets"],
                capture_output=True,
                text=True,
                cwd=settings.base_dir,
                timeout=10,
            )

            if result.returncode == 0:
                files = result.stdout.strip().split("\n")
                return [f for f in files if f]
            return []

        except Exception as e:
            log.error(f"Ошибка при получении списка DVC файлов: {e}")
            return []

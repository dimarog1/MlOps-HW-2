"""Сервис для работы с датасетами."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from app.config import settings
from app.logger import log
from app.models.schemas import DatasetInfo
from app.services.dvc_service import DVCService


class DatasetService:
    """Сервис управления датасетами."""

    def __init__(self):
        """Инициализация сервиса датасетов."""
        self.datasets_dir = settings.datasets_dir
        self.dvc_service = DVCService()

    def save_dataset(self, name: str, data: pd.DataFrame) -> DatasetInfo:
        """
        Сохраняет датасет в файл и загружает его в S3 через DVC.

        Определяет формат файла по расширению имени (CSV или JSON).
        Если расширение не указано, используется CSV.
        После сохранения датасет версионируется через DVC и загружается в S3.

        Args:
            name: Имя датасета (может включать расширение .csv или .json)
            data: DataFrame для сохранения

        Returns:
            DatasetInfo с информацией о сохраненном датасете
        """
        log.info(f"Сохранение датасета: {name}")

        if name.endswith(".json"):
            file_path = self.datasets_dir / name
            data.to_json(file_path, orient="records", indent=2)
        else:
            if not name.endswith(".csv"):
                name = f"{name}.csv"
            file_path = self.datasets_dir / name
            data.to_csv(file_path, index=False)

        log.info(f"Датасет сохранен: {file_path}")

        self._upload_to_s3_via_dvc(file_path, name)

        return self.get_dataset_info(name)

    def _upload_to_s3_via_dvc(self, file_path: Path, dataset_name: str):
        """
        Загружает датасет в S3 через DVC для версионирования и хранения.

        Добавляет датасет в DVC для версионирования и затем загружает его в S3
        через команду DVC push. Это обеспечивает версионирование датасетов
        и хранение кэша DVC в S3 хранилище.

        Args:
            file_path: Путь к файлу датасета на диске
            dataset_name: Имя датасета для добавления в DVC
        """
        if not self.dvc_service.enabled:
            log.warning("DVC недоступен, датасет не будет загружен в S3")
            return

        try:
            if self.dvc_service.add_dataset(dataset_name):
                if self.dvc_service.push_dataset(dataset_name):
                    log.info(f"Датасет {dataset_name} версионирован через DVC и загружен в S3")
                else:
                    log.warning(f"Не удалось загрузить {dataset_name} в S3 через DVC push")
            else:
                log.warning(f"Не удалось добавить {dataset_name} в DVC")
        except Exception as e:
            log.error(f"Ошибка при загрузке в S3 через DVC: {e}")

    def load_dataset(self, name: str) -> pd.DataFrame:
        """
        Загрузка датасета.

        Args:
            name: Имя датасета

        Returns:
            DataFrame с данными

        Raises:
            FileNotFoundError: Если датасет не найден
        """
        log.info(f"Загрузка датасета: {name}")

        file_path = self._find_dataset_file(name)
        if not file_path:
            raise FileNotFoundError(f"Датасет {name} не найден")

        if file_path.suffix == ".json":
            data = pd.read_json(file_path)
        else:
            data = pd.read_csv(file_path)

        log.info(f"Датасет загружен: {len(data)} строк, {len(data.columns)} колонок")
        return data

    def list_datasets(self) -> List[DatasetInfo]:
        """
        Получение списка всех датасетов.

        Returns:
            Список информации о датасетах
        """
        log.info("Получение списка датасетов")

        datasets = []
        for file_path in self.datasets_dir.glob("*"):
            if file_path.suffix in [".csv", ".json"]:
                try:
                    info = self.get_dataset_info(file_path.name)
                    datasets.append(info)
                except Exception as e:
                    log.error(f"Ошибка при чтении информации о датасете {file_path.name}: {e}")

        log.info(f"Найдено датасетов: {len(datasets)}")
        return datasets

    def delete_dataset(self, name: str) -> bool:
        """
        Удаление датасета.

        Args:
            name: Имя датасета

        Returns:
            True если удаление успешно

        Raises:
            FileNotFoundError: Если датасет не найден
        """
        log.info(f"Удаление датасета: {name}")

        file_path = self._find_dataset_file(name)
        if not file_path:
            raise FileNotFoundError(f"Датасет {name} не найден")

        file_path.unlink()

        dvc_file = file_path.with_suffix(file_path.suffix + ".dvc")
        if dvc_file.exists():
            dvc_file.unlink()
            log.info(f"DVC файл удален: {dvc_file}")

        log.info(f"Датасет удален: {file_path}")
        return True

    def get_dataset_info(self, name: str) -> DatasetInfo:
        """
        Получение информации о датасете.

        Args:
            name: Имя датасета

        Returns:
            Информация о датасете
        """
        file_path = self._find_dataset_file(name)
        if not file_path:
            raise FileNotFoundError(f"Датасет {name} не найден")

        stat = file_path.stat()

        try:
            if file_path.suffix == ".json":
                df = pd.read_json(file_path)
            else:
                df = pd.read_csv(file_path)

            rows = len(df)
            columns = df.columns.tolist()
        except Exception:
            rows = None
            columns = None

        return DatasetInfo(
            name=file_path.name,
            size=stat.st_size,
            rows=rows,
            columns=columns,
            uploaded_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        )

    def _find_dataset_file(self, name: str) -> Optional[Path]:
        """
        Поиск файла датасета.

        Args:
            name: Имя датасета (с расширением или без)

        Returns:
            Path к файлу или None, если файл не найден
        """
        from pathlib import Path

        file_path: Path = self.datasets_dir / name
        if file_path.exists():
            return file_path

        for ext in [".csv", ".json"]:
            if not name.endswith(ext):
                file_path = self.datasets_dir / f"{name}{ext}"
                if file_path.exists():
                    return file_path

        return None

    def sync_existing_to_s3(self):
        """
        Синхронизация всех существующих датасетов в S3 через DVC.

        Загружает все датасеты из локальной директории в S3 через DVC.
        """
        if not self.dvc_service.enabled:
            log.warning("DVC недоступен, пропуск синхронизации")
            return

        log.info("Начало синхронизации датасетов в S3 через DVC")

        for file_path in self.datasets_dir.glob("*"):
            if file_path.suffix in [".csv", ".json"]:
                try:
                    self._upload_to_s3_via_dvc(file_path, file_path.name)
                except Exception as e:
                    log.error(f"Ошибка при синхронизации {file_path.name}: {e}")

        log.info("Синхронизация датасетов завершена")

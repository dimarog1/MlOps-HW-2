"""
Пример клиента для тестирования gRPC сервиса машинного обучения.

Демонстрирует использование всех основных методов gRPC API:
- Health Check
- Получение списка типов моделей
- Получение списка датасетов
- Обучение модели
- Получение списка обученных моделей
- Выполнение предсказаний

Демонстрирует полный цикл работы с ML моделями:
1. Загрузка датасета через REST API
2. Обучение модели через gRPC
3. Выполнение предсказаний с обученной моделью
4. Удаление модели
"""

import json
import sys
from pathlib import Path

import grpc
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.grpc_service import ml_service_pb2, ml_service_pb2_grpc
except ImportError:
    print("Ошибка: gRPC файлы не сгенерированы")
    print("Запустите: python scripts/generate_grpc.py")
    sys.exit(1)


def upload_dataset_via_api(api_url: str, dataset_path: Path) -> str:
    """
    Загружает датасет через REST API.

    Args:
        api_url: URL REST API (например, http://localhost:8000)
        dataset_path: Путь к файлу датасета

    Returns:
        Имя загруженного датасета
    """
    print(f"\nЗагрузка датасета {dataset_path.name} через REST API...")

    with open(dataset_path, "rb") as f:
        files = {"file": (dataset_path.name, f, "text/csv")}
        response = requests.post(f"{api_url}/api/datasets/upload", files=files, timeout=30)

    if response.status_code == 201:
        dataset_info = response.json()
        print(f"✓ Датасет успешно загружен: {dataset_info['name']}")
        print(f"  Размер: {dataset_info['rows']} строк, {len(dataset_info['columns'])} колонок")
        return dataset_info["name"]
    else:
        raise Exception(f"Ошибка загрузки датасета: {response.status_code} - {response.text}")


def get_dataset_info_for_prediction(dataset_path: Path) -> tuple:
    """
    Получает информацию о датасете для создания тестовых данных для предсказания.

    Args:
        dataset_path: Путь к файлу датасета

    Returns:
        Кортеж (columns, target_column, sample_data)
    """
    df = pd.read_csv(dataset_path)
    columns = df.columns.tolist()
    target_column = columns[-1]
    feature_columns = columns[:-1]

    sample_row = df.iloc[0]
    sample_data = [{col: float(sample_row[col]) for col in feature_columns}]

    return columns, target_column, sample_data


def run_client(host: str = "localhost", grpc_port: int = 50051, api_port: int = 8000):
    """
    Запускает тестовый клиент для проверки работы gRPC сервиса.

    Выполняет полный цикл:
    1. Health Check
    2. Получение списка типов моделей
    3. Загрузка датасета через REST API
    4. Обучение модели через gRPC
    5. Выполнение предсказания с обученной моделью
    6. Удаление модели

    Args:
        host: Хост сервера
        grpc_port: Порт gRPC сервера
        api_port: Порт REST API
    """
    grpc_address = f"{host}:{grpc_port}"
    api_url = f"http://{host}:{api_port}"

    print(f"Подключение к gRPC серверу: {grpc_address}")
    print(f"REST API URL: {api_url}")

    dataset_path = Path(__file__).parent.parent / "datasets" / "iris.csv"
    if not dataset_path.exists():
        print(f"Ошибка: Датасет не найден: {dataset_path}")
        print("Убедитесь, что файл datasets/iris.csv существует")
        sys.exit(1)

    columns, target_column, sample_data = get_dataset_info_for_prediction(dataset_path)
    model_name = "test_grpc_demo_model"

    with grpc.insecure_channel(grpc_address) as channel:
        stub = ml_service_pb2_grpc.MLServiceStub(channel)

        try:
            print("\n" + "=" * 50)
            print("1. Health Check")
            print("=" * 50)
            response = stub.HealthCheck(ml_service_pb2.HealthRequest())
            print(f"Status: {response.status}")
            print(f"Version: {response.version}")

            print("\n" + "=" * 50)
            print("2. Get Model Types")
            print("=" * 50)
            response = stub.GetModelTypes(ml_service_pb2.ModelTypesRequest())
            print(f"Found {len(response.model_types)} model types:")
            for model_type in response.model_types:
                print(f"  - {model_type.name}: {model_type.description}")

            print("\n" + "=" * 50)
            print("3. Upload Dataset via REST API")
            print("=" * 50)
            try:
                dataset_name = upload_dataset_via_api(api_url, dataset_path)
            except Exception as e:
                print(f"Ошибка загрузки датасета: {e}")
                print("Проверьте, что REST API доступен по адресу:", api_url)
                sys.exit(1)

            print("\n" + "=" * 50)
            print("4. Train Model via gRPC")
            print("=" * 50)
            print(f"Обучение модели '{model_name}' на датасете '{dataset_name}'...")
            print(f"Целевая колонка: {target_column}")

            train_request = ml_service_pb2.TrainModelRequest(
                model_type="LogisticRegression",
                model_name=model_name,
                dataset_name=dataset_name,
                target_column=target_column,
                hyperparameters_json=json.dumps({"C": 1.0, "max_iter": 100}),
            )

            try:
                response = stub.TrainModel(train_request)
                print(f"\n✓ Модель успешно обучена!")
                print(f"  Имя модели: {response.model_name}")
                print(f"  Тип модели: {response.model_type}")
                metrics = json.loads(response.metrics_json)
                print(f"  Метрики:")
                for key, value in metrics.items():
                    print(f"    - {key}: {value:.4f}")
                if response.clearml_task_id:
                    print(f"  ClearML Task ID: {response.clearml_task_id}")
            except grpc.RpcError as e:
                print(f"✗ Ошибка обучения модели: {e.code()} - {e.details()}")
                sys.exit(1)

            print("\n" + "=" * 50)
            print("5. Predict with Trained Model")
            print("=" * 50)
            print(f"Выполнение предсказания с моделью '{model_name}'...")
            print(f"Тестовые данные: {sample_data[0]}")

            predict_request = ml_service_pb2.PredictRequest(
                model_name=model_name, data_json=json.dumps(sample_data)
            )

            try:
                response = stub.Predict(predict_request)
                predictions = json.loads(response.predictions_json)
                print(f"\n✓ Предсказание выполнено!")
                print(f"  Модель: {response.model_name}")
                print(f"  Предсказания: {predictions}")
            except grpc.RpcError as e:
                print(f"✗ Ошибка предсказания: {e.code()} - {e.details()}")
                print("Возможно, модель ожидает другие признаки. Продолжаем...")

            print("\n" + "=" * 50)
            print("6. Delete Model")
            print("=" * 50)
            print(f"Удаление модели '{model_name}'...")

            delete_request = ml_service_pb2.DeleteModelRequest(model_name=model_name)
            try:
                response = stub.DeleteModel(delete_request)
                if response.success:
                    print(f"✓ Модель '{model_name}' успешно удалена")
                    print(f"  Сообщение: {response.message}")
                else:
                    print(f"✗ Ошибка удаления: {response.message}")
            except grpc.RpcError as e:
                print(f"✗ Ошибка удаления модели: {e.code()} - {e.details()}")

            print("\n" + "=" * 50)
            print("7. Verify Deletion")
            print("=" * 50)
            response = stub.ListModels(ml_service_pb2.ListModelsRequest())
            model_names = [model.name for model in response.models]
            if model_name in model_names:
                print(f"⚠ Модель '{model_name}' все еще в списке!")
            else:
                print(f"✓ Модель '{model_name}' успешно удалена (не найдена в списке)")
                print(f"Всего моделей в системе: {len(response.models)}")

            print("\n" + "=" * 50)
            print("✓ Тестирование завершено успешно!")
            print("=" * 50)

        except grpc.RpcError as e:
            print(f"\n[ERROR] gRPC error: {e.code()} - {e.details()}")
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


def main():
    """
    Главная функция для запуска клиента из командной строки.

    Парсит аргументы командной строки и запускает тестовый клиент.
    """
    import argparse

    parser = argparse.ArgumentParser(description="gRPC client example")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--grpc-port", type=int, default=50051, help="gRPC server port")
    parser.add_argument("--api-port", type=int, default=8000, help="REST API port")

    args = parser.parse_args()
    run_client(args.host, args.grpc_port, args.api_port)


if __name__ == "__main__":
    main()

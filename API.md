# REST API

Базовый URL: `http://localhost:8000` (или адрес сервиса).

Интерактивная документация: `/docs` (Swagger).

## Общие эндпоинты

### GET /

Корневой эндпоинт.

**Ответ:** `{ "message": "...", "version": "...", "docs": "/docs" }`

### GET /health

Проверка состояния сервиса (liveness).

**Ответ:** `{ "status": "ok", "version": "0.1.0" }`

### GET /ready

Проверка готовности принимать трафик (readiness).

**Ответ:** `{ "ready": true }`

## Модели — /api/models

### GET /api/models/types

Список типов моделей (LogisticRegression, RandomForest и т.д.).

**Ответ:** массив объектов с полями `name`, `description`, `hyperparameters`.

### POST /api/models/train

Обучение модели. Тело: `model_type`, `model_name`, `dataset_name`, `target_column`, опционально `hyperparameters`.

**Ответ:** `model_name`, `model_type`, `metrics`, `clearml_task_id`.

### GET /api/models

Список обученных моделей.

### POST /api/models/predict

Предсказание. Тело: `model_name`, `features` (список списков или массив).

**Ответ:** `predictions` (список).

### DELETE /api/models/{model_name}

Удаление модели.

## Датасеты — /api/datasets

### GET /api/datasets

Список датасетов.

**Ответ:** массив объектов с полями `name`, `path`, `size_bytes`, `rows`, `columns`.

### POST /api/datasets/upload

Загрузка файла (CSV/JSON). Form-data: `file`.

**Ответ:** информация о загруженном датасете.

### DELETE /api/datasets/{name}

Удаление датасета по имени.

# MLOps Homework 1

Система для обучения и инференса ML моделей с REST API, gRPC сервисом, интерактивным дашбордом и интеграцией с DVC и ClearML.

## Оглавление

- [Возможности](#возможности)
- [Требования](#требования)
- [Быстрый запуск](#быстрый-запуск)
- [Запуск в Minikube](#запуск-в-minikube)
- [Структура проекта](#структура-проекта)
- [Архитектура](#архитектура)
- [Доступ к сервисам](#доступ-к-сервисам)
- [API документация](#api-документация)
- [gRPC сервис](#grpc-сервис)
- [DVC и версионирование данных](#dvc-и-версионирование-данных)
- [ClearML интеграция](#clearml-интеграция)
- [Тестирование и разработка](#тестирование-и-разработка)
- [Управление Minikube](#управление-minikube)
- [Make команды](#make-команды)
- [Устранение неполадок](#устранение-неполадок)

## Возможности

- **ML Модели**: Logistic Regression, Random Forest с настройкой гиперпараметров
- **REST API**: FastAPI с Swagger документацией
- **gRPC API**: Высокопроизводительный gRPC сервис
- **Дашборд**: Streamlit интерфейс для управления моделями и датасетами
- **DVC**: Версионирование датасетов с хранением в S3
- **ClearML**: Трекинг экспериментов и моделей
- **Kubernetes**: Развертывание в Minikube

## Требования

- Python 3.10+
- Poetry
- Docker & Docker Compose
- Minikube
- kubectl

## Быстрый запуск

**Основная команда для запуска всего проекта:**

```bash
make quickstart-minikube-with-clearml
```

Эта команда автоматически выполнит:
1. Запуск ClearML в Docker Compose
2. Запуск Minikube
3. Сборку и загрузку Docker образов
4. Развертывание всех сервисов в Kubernetes
5. Применение ClearML credentials из `.env` в Kubernetes (если они настроены)
6. Настройку port-forward для доступа к сервисам

После выполнения команды все сервисы будут доступны:
- **API**: http://localhost:8000
- **Swagger docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8501
- **gRPC**: localhost:50051
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **ClearML Web UI**: http://localhost:8080

**Примечание**: Для полной функциональности ClearML рекомендуется настроить credentials перед запуском (см. раздел "Запуск в Minikube"). Если credentials не настроены, команда выполнится, но ClearML интеграция будет отключена.

## Запуск в Minikube

Поэтапная инструкция для ручного запуска (если нужен больший контроль над процессом):

### 1. Установка зависимостей

```bash
# Установка Poetry (если не установлен)
curl -sSL https://install.python-poetry.org | python3 -

# Установка зависимостей проекта
make install
```

### 2. Запуск ClearML (Docker Compose)

ClearML должен быть запущен отдельно в Docker Compose:

```bash
make clearml-up
```

Дождитесь запуска сервисов (обычно 30-60 секунд). Проверьте доступность:
- ClearML Web UI: http://localhost:8080
- ClearML API: http://localhost:8008

### 3. Настройка ClearML credentials

Получите credentials из ClearML Web UI:

1. Откройте http://localhost:8080
2. Зарегистрируйтесь или войдите
3. Перейдите в Settings -> Workspace Configuration
4. Нажмите "Create new credentials"
5. Скопируйте `access_key` и `secret_key`

Сохраните credentials в `.env` файл:

```bash
make clearml-setup
```

Или создайте `.env` вручную:

```bash
CLEARML_ACCESS_KEY=your_access_key
CLEARML_SECRET_KEY=your_secret_key
```

### 4. Запуск Minikube

```bash
# Запуск Minikube (4 CPU, 6GB RAM)
make minikube-start
```

### 5. Сборка и загрузка образов

```bash
# Сборка Docker образов и загрузка в Minikube
make minikube-build
```

### 6. Развертывание в Kubernetes

```bash
# Развертывание всех сервисов
make minikube-deploy
```

### 7. Применение ClearML credentials в Kubernetes

```bash
# Применение credentials из .env в Kubernetes secret
make clearml-apply-secret
```

Эта команда:
- Читает credentials из `.env` файла
- Создает или обновляет Kubernetes secret `clearml-secret`
- Перезапускает API deployment для применения новых credentials

**Важно**: Credentials никогда не хранятся в `k8s/clearml-secret.yaml` - они всегда загружаются из `.env` файла.

### 8. Настройка port-forward

```bash
# Проброс портов для доступа с хоста
make minikube-port-forward
```

### 9. Проверка статуса

```bash
# Проверка статуса подов
make minikube-status

# Просмотр URL сервисов
make minikube-services
```

### 10. Тестирование gRPC сервиса

```bash
# Запуск тестового gRPC клиента
make grpc-test
```

Тестовый клиент выполнит:
- Health Check
- Получение типов моделей
- Загрузку датасета через REST API
- Обучение модели через gRPC
- Предсказание с обученной моделью
- Удаление модели

## Структура проекта

```
.
├── app/                      # Основной код приложения
│   ├── api/                  # REST API (FastAPI)
│   │   ├── main.py          # Главное приложение FastAPI
│   │   └── routes/          # API роуты
│   ├── grpc_service/        # gRPC сервис
│   │   ├── ml_service.proto # Protobuf определения
│   │   └── server.py        # gRPC сервер
│   ├── ml/                  # ML модели
│   ├── models/              # Pydantic схемы
│   └── services/            # Бизнес-логика
├── dashboard/               # Streamlit дашборд
├── k8s/                     # Kubernetes манифесты
├── scripts/                 # Утилитарные скрипты
├── tests/                   # Тесты
├── datasets/                # Датасеты
├── models/                  # Обученные модели
├── docker-compose.yml       # Docker Compose конфигурация
├── Dockerfile               # Dockerfile для API
├── Dockerfile.grpc          # Dockerfile для gRPC
├── Dockerfile.dashboard      # Dockerfile для Dashboard
├── Makefile                 # Make команды
└── pyproject.toml           # Poetry зависимости
```

## Архитектура

```
┌─────────────────┐
│   Dashboard     │  ← Streamlit UI
│   (Streamlit)   │
└────────┬────────┘
         │ HTTP
    ┌────▼────────────────────┐
    │                         │
┌───▼─────┐           ┌──────▼────┐
│ REST API│           │ gRPC API  │
│(FastAPI)│           │ (Python)  │
└───┬─────┘           └──────┬────┘
    │                        │
    └────────┬───────────────┘
             │
    ┌────────▼────────┐
    │  Model Service  │
    │ Dataset Service │
    └────────┬────────┘
             │
    ┌────────┼────────────┐
    │        │            │
┌───▼──┐  ┌──▼───┐  ┌────▼──┐
│ DVC  │  │MinIO │  │ClearML│
│(Data)│  │(S3)  │  │(MLOps)│
└──────┘  └──────┘  └───────┘
```

## Доступ к сервисам

После настройки port-forward:

- **API**: http://localhost:8000
- **Swagger docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8501
- **gRPC**: localhost:50051
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **ClearML Web UI**: http://localhost:8080

## API документация

Полная интерактивная документация API доступна после запуска сервиса:

**http://localhost:8000/docs**

Swagger UI содержит все эндпоинты, схемы запросов/ответов и возможность тестирования API прямо из браузера.

## gRPC сервис

### Генерация protobuf файлов

```bash
make grpc-generate
```

### Тестирование gRPC

```bash
# Полный тест gRPC сервиса (загрузка датасета, обучение, предсказание, удаление)
make grpc-test
```

### Доступные gRPC методы

- `HealthCheck` - проверка состояния сервиса
- `GetModelTypes` - получение списка типов моделей
- `TrainModel` - обучение новой модели
- `RetrainModel` - переобучение существующей модели
- `Predict` - получение предсказаний
- `ListModels` - список всех обученных моделей
- `DeleteModel` - удаление модели
- `ListDatasets` - список всех датасетов

## DVC и версионирование данных

Датасеты автоматически версионируются через DVC и хранятся в S3 (MinIO). При загрузке датасета через API (`POST /api/datasets/upload`) он автоматически добавляется в DVC и загружается в S3.

Для ручного управления используйте команды:
- `make dvc-init` - инициализация DVC
- `make dvc-push` - загрузка в S3
- `make dvc-pull` - скачивание из S3

## ClearML интеграция

ClearML автоматически логирует все эксперименты обучения моделей. При обучении создается ClearML Task с метриками и гиперпараметрами, а также модель регистрируется в Model Registry.

**Настройка:**
1. Запустите ClearML: `make clearml-up`
2. Получите credentials из Web UI (http://localhost:8080)
3. Сохраните в `.env`: `make clearml-setup`
4. Примените в Kubernetes: `make clearml-apply-secret`

Просмотр экспериментов: http://localhost:8080

## Тестирование и разработка

### Запуск тестов

```bash
make test
```

Тесты покрывают REST API эндпоинты и ML модели (обучение, предсказание, гиперпараметры).

### Линтинг и форматирование

```bash
# Проверка кода (flake8, mypy)
make lint

# Форматирование кода (black, isort)
make format
```

## Управление Minikube

```bash
# Проверка статуса
make minikube-status

# Просмотр логов
kubectl logs -n mlops -l app=mlops-api --tail=50

# Остановка
make minikube-stop

# Очистка
make minikube-clean

# Полное удаление
make minikube-delete
```

## Make команды

Для просмотра всех доступных команд используйте:

```bash
make help
```

или просто:

```bash
make
```

## Устранение неполадок

### Проблемы с gRPC

Если gRPC файлы не сгенерированы:
```bash
make grpc-generate
```

### Проблемы с ClearML

Проверьте credentials:
```bash
# Проверка secret в Kubernetes
kubectl get secret clearml-secret -n mlops -o yaml

# Применение credentials заново
make clearml-apply-secret
```

### Проблемы с Minikube

```bash
# Проверка статуса
minikube status

# Просмотр логов подов
kubectl logs -n mlops -l app=mlops-api --tail=50

# Перезапуск
make minikube-reset
make minikube-deploy
```

### Проблемы с port-forward

```bash
# Остановка старого port-forward
make minikube-port-forward-stop

# Запуск нового
make minikube-port-forward
```

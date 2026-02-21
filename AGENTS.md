# AGENTS.md

Описание правил, команд и стиля для AI-агентов и разработчиков проекта.

## О проекте

MLOps Homework 1 — система обучения и инференса ML моделей. Стек: FastAPI, gRPC, Streamlit, DVC, ClearML, Minikube.

## Структура

- `app/` — основной код (API, gRPC, ML модели, сервисы)
- `dashboard/` — Streamlit дашборд
- `k8s/` — Kubernetes манифесты
- `scripts/` — утилиты (grpc-generate, grpc_client_example)
- `tests/` — тесты

## Правила

- Python 3.10+, менеджер зависимостей — Poetry.
- После изменений в `ml_service.proto` обязательно запускать `make grpc-generate`.
- Перед коммитом: `make lint` и `make test`.
- Не коммитить секреты; для ClearML использовать `.env` и `make clearml-setup`.

## Команды

**Разработка:**

- `make install` — установка зависимостей
- `make test` — запуск тестов
- `make lint` — проверка кода (flake8, mypy)
- `make format` — форматирование (black, isort)
- `make grpc-generate` — генерация gRPC из proto
- `make grpc-test` — тест gRPC (API на 8000, gRPC на 50051)
- `make env` — создать `.env` из `.env.example`

**Локальный запуск:**

- `make quickstart` — Docker Compose (API, Dashboard, MinIO)
- `make quickstart-minikube` — развёртывание в Minikube
- `make quickstart-minikube-with-clearml` — Minikube + ClearML в Docker

**Minikube:**

- `make minikube-start` — старт кластера (4 CPU, 6GB RAM)
- `make minikube-deploy` — сборка образов и деплой
- `make minikube-port-forward` — проброс портов на localhost
- `make minikube-services` — вывод URL сервисов
- `make minikube-status` — статус подов
- `make minikube-stop` / `make minikube-reset` — стоп или сброс

**DVC:**

- `make dvc-init` — инициализация DVC и remote S3
- `make dvc-add FILE=path/to/file` — добавить файл в DVC
- `make dvc-push` / `make dvc-pull` — выгрузка/загрузка данных

**ClearML:**

- `make clearml-up` / `make clearml-down` — запуск/остановка сервисов
- `make clearml-setup` — интерактивная настройка учётных данных
- `make clearml-apply-secret` — применить креды из `.env` в k8s

## Стиль кода

- **Форматирование:** black (длина строки 100), isort (profile black).
- **Линтинг:** flake8 (max-line-length=100, extend-ignore E203,W503), mypy (ignore-missing-imports).
- **Области:** линт и формат применяются к `app/`, `scripts/`, `dashboard/`.
- Файлы должны заканчиваться переводом строки (LF), без пробелов в конце строк.

## Для разработки

- После правок кода: `make format` затем `make lint` и `make test`.
- Справка по всем командам: `make help`.

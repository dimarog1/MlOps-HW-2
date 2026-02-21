# AGENTS.md

Инструкции для AI-агентов, работающих с этим проектом.

## О проекте

MLOps Homework 1 — система обучения и инференса ML моделей. Стек: FastAPI, gRPC, Streamlit, DVC, ClearML, Minikube.

## Структура

- `app/` — основной код (API, gRPC, ML модели, сервисы)
- `dashboard/` — Streamlit дашборд
- `k8s/` — Kubernetes манифесты
- `scripts/` — утилиты (grpc-generate, grpc_client_example)
- `tests/` — тесты

## Основные команды

- `make install` — установка зависимостей
- `make test` — запуск тестов
- `make lint` / `make format` — линтинг и форматирование
- `make grpc-generate` — генерация gRPC файлов
- `make quickstart-minikube` — полный запуск в Minikube (ClearML при необходимости: `make clearml-up` отдельно)

## Для разработки

- Python 3.10+, Poetry
- После изменений в `ml_service.proto` — запускать `make grpc-generate`
- Тесты: `make test`
- Линтер: `make lint`


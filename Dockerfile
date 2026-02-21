# Multi-stage build для API сервиса

FROM python:3.10-slim as base

# Устанавливаем только необходимые системные зависимости
# gcc/g++ нужны для компиляции некоторых Python пакетов (scikit-learn, numpy и т.д.)
# git нужен для DVC
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry
RUN pip install poetry==1.7.1

# Рабочая директория
WORKDIR /app

# Копируем только файлы зависимостей (для лучшего кэширования)
COPY pyproject.toml ./

# Устанавливаем зависимости без dev-пакетов
# Это самый долгий шаг, поэтому он должен быть отдельным слоем
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main \
    && poetry cache clear pypi --all -n || true

# Копируем код приложения (этот слой пересобирается чаще)
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY clearml.conf ./

# Создаем необходимые директории
RUN mkdir -p /app/models /app/datasets /app/logs

# Инициализируем git репозиторий для DVC (делаем один раз)
RUN git config --global user.email "mlops@example.com" && \
    git config --global user.name "MLOps" && \
    git config --global init.defaultBranch main

# Инициализируем DVC (делаем один раз, кэшируется)
RUN cd /app && \
    git init && \
    dvc init && \
    dvc remote add -d -f s3storage s3://mlops/dvc && \
    dvc remote modify s3storage endpointurl http://minio:9000 && \
    dvc config core.autostage true || true

# Генерируем gRPC файлы (если нужно)
RUN python scripts/generate_grpc.py || echo "gRPC generation failed, continuing..."

# Устанавливаем права на скрипты
RUN chmod +x scripts/*.sh 2>/dev/null || true

# Порты
EXPOSE 8000 50051

# Запуск через entrypoint скрипт
ENTRYPOINT ["/app/scripts/entrypoint_api.sh"]


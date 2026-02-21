#!/bin/bash
# Entrypoint скрипт для API контейнера: инициализирует окружение и запускает API

echo "Starting API service..."

cd /app

if [ ! -d .git ]; then
    echo "Initializing git repository for DVC..."
    git config --global user.email "mlops@example.com"
    git config --global user.name "MLOps"
    git config --global init.defaultBranch main
    git init
    git add -A
    git commit -m "Initial commit" || true
    echo "Git repository initialized"
fi

if [ -f .dvc/config ]; then
    echo "Updating DVC remote configuration..."
    dvc remote modify s3storage endpointurl "${S3_ENDPOINT}" 2>/dev/null || true
    dvc remote modify s3storage access_key_id "${S3_ACCESS_KEY}" 2>/dev/null || true
    dvc remote modify s3storage secret_access_key "${S3_SECRET_KEY}" 2>/dev/null || true
fi

if [ -f .dvc/config ]; then
    echo "Pulling datasets from S3..."
    dvc pull || echo "Warning: Dataset pull failed, continuing..."
fi

exec python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000


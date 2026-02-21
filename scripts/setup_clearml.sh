#!/bin/bash
# Проверяет статус ClearML сервисов и помогает настроить credentials

set -e

echo "=========================================="
echo "Настройка ClearML Credentials"
echo "=========================================="
echo ""

echo "Проверка статуса ClearML сервисов..."

if ! docker compose ps clearml-webserver clearml-apiserver clearml-fileserver 2>/dev/null | grep -q "Up"; then
    echo "[WARN] ClearML сервисы не запущены или недоступны"
    echo "Запустите сервисы:"
    echo "  docker compose up -d clearml-webserver clearml-apiserver clearml-fileserver"
    echo ""
    echo "После запуска откройте ClearML Web UI в браузере:"
    echo "  http://localhost:8080 (или IP вашего Docker хоста)"
    echo ""
else
    echo "[OK] ClearML сервисы запущены"
    echo ""
    
    if docker compose exec -T clearml-webserver curl -s -f http://localhost > /dev/null 2>&1; then
        echo "[OK] ClearML Web UI доступен внутри Docker сети"
    else
        echo "[INFO] Проверка доступности через Docker сеть не удалась"
        echo "       Это нормально, если сервисы только что запустились"
    fi
    echo ""
fi

echo "Попытка получить credentials из базы данных ClearML..."
echo ""

if [ -f .env ]; then
    if grep -q "CLEARML_ACCESS_KEY=" .env && grep -q "CLEARML_SECRET_KEY=" .env; then
        ACCESS_KEY=$(grep "CLEARML_ACCESS_KEY=" .env | cut -d'=' -f2)
        SECRET_KEY=$(grep "CLEARML_SECRET_KEY=" .env | cut -d'=' -f2)
        
        if [ -n "$ACCESS_KEY" ] && [ -n "$SECRET_KEY" ] && [ "$ACCESS_KEY" != "" ] && [ "$SECRET_KEY" != "" ]; then
            echo "[OK] Credentials уже настроены в .env"
            echo "Access Key: ${ACCESS_KEY:0:10}..."
            echo ""
            echo "Для обновления credentials отредактируйте файл .env"
            exit 0
        fi
    fi
fi

echo "[INFO] Credentials не найдены в .env"
echo ""
echo "Добавьте credentials в файл .env:"
echo ""
echo "CLEARML_ACCESS_KEY=your_access_key_here"
echo "CLEARML_SECRET_KEY=your_secret_key_here"
echo ""
echo "Или выполните интерактивную настройку:"
echo "  python scripts/setup_clearml_interactive.py"
echo ""





#!/bin/bash
# Применяет ClearML credentials из .env файла в Kubernetes secret

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}Применение ClearML credentials в Kubernetes${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

if [ ! -f .env ]; then
    echo -e "${RED}[ERROR] Файл .env не найден!${NC}"
    echo -e "${YELLOW}Создайте файл .env или запустите: make clearml-setup${NC}"
    exit 1
fi

if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -E '^CLEARML_' | xargs)
fi

if [ -z "$CLEARML_ACCESS_KEY" ] || [ -z "$CLEARML_SECRET_KEY" ]; then
    echo -e "${RED}[ERROR] CLEARML_ACCESS_KEY или CLEARML_SECRET_KEY не найдены в .env${NC}"
    echo -e "${YELLOW}Запустите: make clearml-setup${NC}"
    exit 1
fi

echo -e "${BLUE}Найдены credentials в .env:${NC}"
echo -e "  CLEARML_ACCESS_KEY: ${CLEARML_ACCESS_KEY:0:10}...${NC}"
echo -e "  CLEARML_SECRET_KEY: ${CLEARML_SECRET_KEY:0:10}...${NC}"
echo ""

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}[ERROR] kubectl не найден!${NC}"
    exit 1
fi

if ! kubectl get namespace mlops &> /dev/null; then
    echo -e "${YELLOW}[WARN] Namespace mlops не найден. Создаю...${NC}"
    kubectl create namespace mlops
fi

echo -e "${BLUE}Применение secret в Kubernetes...${NC}"
kubectl create secret generic clearml-secret \
    --from-literal=CLEARML_ACCESS_KEY="$CLEARML_ACCESS_KEY" \
    --from-literal=CLEARML_SECRET_KEY="$CLEARML_SECRET_KEY" \
    -n mlops \
    --dry-run=client -o yaml | kubectl apply -f -

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[OK] Secret успешно применен в Kubernetes${NC}"
else
    echo -e "${RED}[ERROR] Не удалось применить secret${NC}"
    exit 1
fi

if kubectl get deployment mlops-api -n mlops &> /dev/null; then
    echo ""
    echo -e "${BLUE}Перезапуск deployment mlops-api для применения новых credentials...${NC}"
    kubectl rollout restart deployment/mlops-api -n mlops
    
    echo -e "${BLUE}Ожидание перезапуска...${NC}"
    kubectl rollout status deployment/mlops-api -n mlops --timeout=60s || true
    
    echo -e "${GREEN}[OK] Deployment перезапущен${NC}"
else
    echo -e "${YELLOW}[WARN] Deployment mlops-api не найден. Secret применен, но перезапуск не выполнен.${NC}"
fi

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}Готово! ClearML credentials применены в Kubernetes${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${BLUE}Проверка подключения ClearML:${NC}"
echo -e "  kubectl logs -n mlops deployment/mlops-api --tail=20 | grep -i clearml"
echo ""


.PHONY: help install build up down logs clean test lint format minikube-start minikube-deploy minikube-stop grpc-generate grpc-test

DOCKER_COMPOSE = docker compose
MINIKUBE = minikube
KUBECTL = kubectl
POETRY = poetry

BLUE = \033[0;34m
GREEN = \033[0;32m
RED = \033[0;31m
YELLOW = \033[1;33m
NC = \033[0m

help: ## Show help
	@echo "$(BLUE)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ============ Local Development ============

env: ## Create .env file from .env.example
	@if [ -f .env ]; then \
		echo "$(YELLOW).env already exists.$(NC)"; \
		echo "$(BLUE)To recreate, delete .env first: rm .env$(NC)"; \
	else \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "$(GREEN).env created from .env.example$(NC)"; \
			echo "$(BLUE)Edit .env to configure your settings$(NC)"; \
		else \
			echo "$(RED)Error: .env.example not found$(NC)"; \
			exit 1; \
		fi; \
	fi

install: ## Install dependencies via Poetry
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(POETRY) install

grpc-generate: ## Generate gRPC files
	@echo "$(BLUE)Generating gRPC files...$(NC)"
	$(POETRY) run python scripts/generate_grpc.py

grpc-test: ## Test gRPC service (upload dataset, train, predict, delete)
	@echo "$(BLUE)Testing gRPC service...$(NC)"
	@echo "$(BLUE)Make sure REST API is available on port 8000 and gRPC on port 50051$(NC)"
	$(POETRY) run python scripts/grpc_client_example.py --host localhost --grpc-port 50051 --api-port 8000

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(POETRY) run pytest -v

lint: ## Check code (flake8, mypy)
	@echo "$(BLUE)Checking code...$(NC)"
	$(POETRY) run flake8 app/ --max-line-length=100 --extend-ignore=E203,W503
	$(POETRY) run mypy app/ --ignore-missing-imports

format: ## Format code (black, isort)
	@echo "$(BLUE)Formatting code...$(NC)"
	$(POETRY) run black app/ scripts/ dashboard/
	$(POETRY) run isort app/ scripts/ dashboard/

# ============ Minikube ============

minikube-start: ## Start Minikube with Docker driver (4 CPUs, 6GB RAM)
	@echo "$(BLUE)Starting Minikube with 4 CPUs and 6GB RAM...$(NC)"
	@if minikube status > /dev/null 2>&1; then \
		echo "$(BLUE)Minikube is already running$(NC)"; \
		minikube status; \
		echo "$(BLUE)To apply new resources, stop and restart: make minikube-reset$(NC)"; \
	else \
		echo "$(BLUE)Starting new Minikube cluster...$(NC)"; \
		if ! minikube start --driver=docker --cpus=4 --memory=6144 2>&1; then \
			echo "$(BLUE)Failed to start with existing profile. Deleting and starting fresh...$(NC)"; \
			minikube delete || true; \
			minikube start --driver=docker --cpus=4 --memory=6144; \
		fi; \
		echo "$(GREEN)Minikube started with 4 CPUs and 6GB RAM!$(NC)"; \
		minikube status; \
	fi

minikube-build-local:
	@echo "$(BLUE)Building images locally...$(NC)"
	@for image in mlops-api:latest mlops-grpc:latest mlops-dashboard:latest; do \
		IMAGE_NAME=$$(echo $$image | cut -d: -f1); \
		DOCKERFILE=$$(if [ "$$IMAGE_NAME" = "mlops-api" ]; then echo "Dockerfile"; elif [ "$$IMAGE_NAME" = "mlops-grpc" ]; then echo "Dockerfile.grpc"; else echo "Dockerfile.dashboard"; fi); \
		echo "$(BLUE)Building $$image locally...$(NC)"; \
		docker build -t "$$image" -f $$DOCKERFILE .; \
	done
	@echo "$(GREEN)Local images built!$(NC)"

minikube-build: ## Build images locally and load into Minikube
	@echo "$(BLUE)Checking Minikube status...$(NC)"
	@if ! minikube status > /dev/null 2>&1; then \
		echo "$(RED)Minikube is not running! Starting Minikube...$(NC)"; \
		$(MAKE) minikube-start; \
	fi
	@echo "$(BLUE)Waiting for Minikube to be ready...$(NC)"
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if minikube status > /dev/null 2>&1; then \
			break; \
		fi; \
		if [ $$i -eq 10 ]; then \
			echo "$(RED)Minikube is not responding after 20 seconds.$(NC)"; \
			echo "$(BLUE)Try: make minikube-reset$(NC)"; \
			exit 1; \
		fi; \
		sleep 2; \
	done
	@echo "$(BLUE)Step 1: Building images locally...$(NC)"
	@$(MAKE) minikube-build-local
	@echo "$(BLUE)Step 2: Loading images into Minikube...$(NC)"
	@for image in mlops-api:latest mlops-grpc:latest mlops-dashboard:latest; do \
		if ! minikube docker-env > /dev/null 2>&1; then \
			echo "$(RED)Failed to get Minikube docker-env. Minikube may be stuck.$(NC)"; \
			echo "$(BLUE)Try: make minikube-reset$(NC)"; \
			exit 1; \
		fi; \
		eval $$(minikube docker-env) && \
		if docker image inspect "$$image" >/dev/null 2>&1; then \
			echo "$(BLUE)Removing old $$image from Minikube...$(NC)"; \
			docker rmi "$$image" 2>/dev/null || true; \
		fi; \
		echo "$(BLUE)Loading $$image into Minikube...$(NC)"; \
		if minikube image load "$$image" 2>&1; then \
			eval $$(minikube docker-env) && \
			if docker image inspect "$$image" >/dev/null 2>&1; then \
				echo "$(GREEN)✓ Image $$image loaded and verified in Minikube$(NC)"; \
			else \
				echo "$(RED)✗ Image $$image load reported success but not found in Minikube!$(NC)"; \
				exit 1; \
			fi; \
		else \
			echo "$(RED)✗ Failed to load $$image into Minikube!$(NC)"; \
			exit 1; \
		fi; \
	done
	@echo "$(GREEN)Images ready in Minikube!$(NC)"

minikube-deploy: ## Deploy to Minikube
	@echo "$(BLUE)Checking if images need to be built...$(NC)"
	@$(MAKE) minikube-build
	@echo "$(BLUE)Deploying to Minikube...$(NC)"
	@kubectl apply -f k8s/namespace.yaml
	@echo "$(BLUE)Creating ClearML Secret and ConfigMap...$(NC)"
	@echo "$(BLUE)Creating ClearML secret from .env...$(NC)"
	@$(MAKE) minikube-create-clearml-secret
	@kubectl apply -f k8s/clearml-configmap.yaml
	@echo "$(BLUE)Deploying MinIO...$(NC)"
	@kubectl apply -f k8s/minio-deployment.yaml
	@echo "$(BLUE)Waiting for MinIO to be ready...$(NC)"
	@kubectl wait --for=condition=available --timeout=120s deployment/minio -n mlops || true
	@echo "$(BLUE)Initializing MinIO bucket...$(NC)"
	@kubectl delete job minio-init -n mlops --ignore-not-found=true
	@kubectl apply -f k8s/minio-init-job.yaml
	@echo "$(BLUE)Waiting for MinIO init job to complete...$(NC)"
	@kubectl wait --for=condition=complete --timeout=60s job/minio-init -n mlops || true
	@echo "$(BLUE)Verifying images are in Minikube before deployment...$(NC)"
	@for img in mlops-api:latest mlops-grpc:latest mlops-dashboard:latest; do \
		echo "$(BLUE)Checking $$img...$(NC)"; \
		eval $$(minikube docker-env) && \
		if docker image inspect "$$img" >/dev/null 2>&1; then \
			echo "$(GREEN)✓ $$img found in Minikube$(NC)"; \
		else \
			echo "$(YELLOW)✗ $$img not in Minikube, loading from local...$(NC)"; \
			eval $$(minikube docker-env -u) && \
			if docker image inspect "$$img" >/dev/null 2>&1; then \
				echo "$(BLUE)Loading $$img into Minikube...$(NC)"; \
				minikube image load "$$img" && echo "$(GREEN)✓ Loaded$(NC)" || echo "$(RED)✗ Load failed$(NC)"; \
			else \
				echo "$(RED)✗ $$img not found locally! Need to build it.$(NC)"; \
				echo "$(BLUE)Building $$img in Minikube...$(NC)"; \
				eval $$(minikube docker-env) && \
				IMG_NAME=$$(echo $$img | cut -d: -f1); \
				DOCKERFILE=$$(if [ "$$IMG_NAME" = "mlops-api" ]; then echo "Dockerfile"; elif [ "$$IMG_NAME" = "mlops-grpc" ]; then echo "Dockerfile.grpc"; else echo "Dockerfile.dashboard"; fi); \
				docker build -t "$$img" -f $$DOCKERFILE .; \
			fi; \
		fi; \
	done
	@echo "$(BLUE)Final verification...$(NC)"
	@eval $$(minikube docker-env) && docker images | grep -E "mlops-(api|grpc|dashboard)" || echo "$(YELLOW)Warning: Some images may be missing$(NC)"
	@echo "$(BLUE)Deploying API...$(NC)"
	@kubectl apply -f k8s/api-deployment.yaml
	@echo "$(BLUE)Deploying gRPC...$(NC)"
	@kubectl apply -f k8s/grpc-deployment.yaml
	@echo "$(BLUE)Deploying Dashboard...$(NC)"
	@kubectl apply -f k8s/dashboard-deployment.yaml
	@echo "$(BLUE)Waiting for deployments to be ready...$(NC)"
	@kubectl wait --for=condition=available --timeout=180s deployment/mlops-api -n mlops || \
		(echo "$(RED)API deployment failed. Checking pod status...$(NC)" && \
		kubectl get pods -n mlops -l app=mlops-api && \
		kubectl describe pod -n mlops -l app=mlops-api | tail -40 && \
		echo "$(BLUE)Checking if image exists in Minikube...$(NC)" && \
		eval $$(minikube docker-env) && docker images mlops-api:latest)
	@kubectl wait --for=condition=available --timeout=180s deployment/mlops-grpc -n mlops || \
		(echo "$(RED)gRPC deployment failed. Checking pod status...$(NC)" && \
		kubectl get pods -n mlops -l app=mlops-grpc && \
		kubectl describe pod -n mlops -l app=mlops-grpc | tail -40)
	@kubectl wait --for=condition=available --timeout=180s deployment/mlops-dashboard -n mlops || \
		(echo "$(RED)Dashboard deployment failed. Checking pod status...$(NC)" && \
		kubectl get pods -n mlops -l app=mlops-dashboard && \
		kubectl describe pod -n mlops -l app=mlops-dashboard | tail -40)
	@echo "$(GREEN)Deployment complete!$(NC)"
	@echo ""
	@echo "$(BLUE)Pod status:$(NC)"
	@kubectl get pods -n mlops
	@echo ""
	@echo "To access services use:"
	@echo "  make minikube-services"

minikube-services: ## Get Minikube service URLs
	@echo "$(BLUE)Minikube Service URLs (via port-forward):$(NC)"
	@echo ""
	@echo "API: http://localhost:8000"
	@echo "Dashboard: http://localhost:8501"
	@echo "gRPC: localhost:50051"
	@echo "MinIO API: http://localhost:9000"
	@echo "MinIO Console: http://localhost:9001"
	@echo ""
	@echo "$(GREEN)Note: Run 'make minikube-port-forward' to start port forwarding$(NC)"
	@echo ""
	@echo "$(BLUE)ClearML Service URLs (Docker Compose):$(NC)"
	@echo "  ClearML Web UI: http://localhost:8080"
	@echo "  ClearML API: http://localhost:8008"
	@echo "  ClearML Fileserver: http://localhost:8081"

minikube-port-forward: ## Forward ports to localhost
	@echo "$(BLUE)Starting port forwarding...$(NC)"
	@make minikube-port-forward-stop > /dev/null 2>&1 || true
	@echo "$(BLUE)Waiting a moment for services to be fully ready...$(NC)"
	@sleep 2
	@nohup kubectl port-forward -n mlops service/mlops-api 8000:8000 > /tmp/k8s-api-pf.log 2>&1 & \
	nohup kubectl port-forward -n mlops service/mlops-dashboard 8501:8501 > /tmp/k8s-dashboard-pf.log 2>&1 & \
	nohup kubectl port-forward -n mlops service/mlops-grpc 50051:50051 > /tmp/k8s-grpc-pf.log 2>&1 & \
	nohup kubectl port-forward -n mlops service/minio 9000:9000 9001:9001 > /tmp/k8s-minio-pf.log 2>&1 & \
	sleep 3 && \
	echo "$(BLUE)Verifying port forwarding...$(NC)" && \
	for i in 1 2 3 4 5; do \
		if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
			echo "$(GREEN)✓ API port-forward is working$(NC)"; \
			break; \
		fi; \
		if [ $$i -eq 5 ]; then \
			echo "$(YELLOW)⚠ API port-forward may not be ready yet, check logs: tail -f /tmp/k8s-api-pf.log$(NC)"; \
		fi; \
		sleep 1; \
	done && \
	echo "$(GREEN)Port forwarding started!$(NC)" && \
	echo "" && \
	echo "API: http://localhost:8000" && \
	echo "Dashboard: http://localhost:8501" && \
	echo "gRPC: localhost:50051" && \
	echo "MinIO API: http://localhost:9000" && \
	echo "MinIO Console: http://localhost:9001" && \
	echo "" && \
	echo "$(BLUE)To stop port forwarding, run: make minikube-port-forward-stop$(NC)"

minikube-port-forward-stop: ## Stop port forwarding
	@echo "$(BLUE)Stopping port forwarding...$(NC)"
	@pkill -f "kubectl port-forward.*mlops" || true
	@echo "$(GREEN)Port forwarding stopped$(NC)"

minikube-status: ## Check pod status in Minikube
	@echo "$(BLUE)Service status:$(NC)"
	@kubectl get all -n mlops
	@echo ""
	@echo "$(BLUE)MinIO init job status:$(NC)"
	@kubectl get job minio-init -n mlops 2>/dev/null || echo "MinIO init job not found"

minikube-stop: ## Stop Minikube
	@echo "$(BLUE)Stopping Minikube...$(NC)"
	@minikube stop

minikube-delete: ## Delete Minikube cluster
	@echo "$(RED)Deleting Minikube cluster...$(NC)"
	@minikube delete || true

minikube-reset: ## Reset Minikube (delete and start fresh)
	@echo "$(BLUE)Resetting Minikube...$(NC)"
	@minikube delete || true
	@$(MAKE) minikube-start

minikube-create-clearml-secret: ## Create ClearML secret from .env file and restart API
	@echo "$(BLUE)Creating ClearML secret from .env...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)Error: .env file not found$(NC)"; \
		echo "$(YELLOW)Run: make clearml-setup$(NC)"; \
		exit 1; \
	fi
	@if ! grep -q "CLEARML_ACCESS_KEY=" .env || ! grep -q "CLEARML_SECRET_KEY=" .env; then \
		echo "$(RED)Error: CLEARML_ACCESS_KEY or CLEARML_SECRET_KEY not found in .env$(NC)"; \
		echo "$(YELLOW)Run: make clearml-setup$(NC)"; \
		exit 1; \
	fi
	@kubectl create secret generic clearml-secret -n mlops \
		--from-literal=CLEARML_ACCESS_KEY=$$(grep CLEARML_ACCESS_KEY .env | cut -d'=' -f2) \
		--from-literal=CLEARML_SECRET_KEY=$$(grep CLEARML_SECRET_KEY .env | cut -d'=' -f2) \
		--dry-run=client -o yaml | kubectl apply -f - || \
		kubectl create secret generic clearml-secret -n mlops \
		--from-literal=CLEARML_ACCESS_KEY=$$(grep CLEARML_ACCESS_KEY .env | cut -d'=' -f2) \
		--from-literal=CLEARML_SECRET_KEY=$$(grep CLEARML_SECRET_KEY .env | cut -d'=' -f2)
	@if kubectl get deployment mlops-api -n mlops &>/dev/null; then \
		echo "$(BLUE)Restarting mlops-api deployment...$(NC)"; \
		kubectl rollout restart deployment/mlops-api -n mlops; \
		echo "$(GREEN)Secret applied and deployment restarted$(NC)"; \
	else \
		echo "$(GREEN)Secret applied$(NC)"; \
	fi

minikube-clean: ## Clean Minikube resources
	@echo "$(BLUE)Cleaning resources...$(NC)"
	@kubectl delete namespace mlops --ignore-not-found=true

# ============ DVC ============

dvc-init: ## Initialize DVC
	@echo "$(BLUE)Initializing DVC...$(NC)"
	dvc init
	dvc remote add -d s3storage s3://mlops/dvc
	dvc remote modify s3storage endpointurl http://localhost:9000

dvc-add: ## Add datasets to DVC (usage: make dvc-add FILE=datasets/mydata.csv)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: specify FILE=path/to/file$(NC)"; \
		exit 1; \
	fi
	dvc add $(FILE)
	@echo "$(GREEN)File added to DVC$(NC)"

dvc-push: ## Upload data to S3
	@echo "$(BLUE)Uploading data to S3...$(NC)"
	dvc push

dvc-pull: ## Download data from S3
	@echo "$(BLUE)Downloading data from S3...$(NC)"
	dvc pull

# ============ ClearML ============

clearml-up: ## Start ClearML services in Docker Compose
	@echo "$(BLUE)Starting ClearML services...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.clearml.yml up -d
	@echo "$(GREEN)ClearML services started!$(NC)"
	@echo "ClearML Web UI: http://localhost:8080"
	@echo "ClearML API: http://localhost:8008"
	@echo "ClearML Fileserver: http://localhost:8081"
	@echo ""
	@echo "$(BLUE)Waiting for services to be ready...$(NC)"
	@sleep 5
	@echo "$(GREEN)ClearML is ready!$(NC)"

clearml-down: ## Stop ClearML services
	@echo "$(BLUE)Stopping ClearML services...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.clearml.yml down

clearml-setup: ## Setup ClearML credentials (interactive)
	@echo "$(BLUE)Setting up ClearML credentials...$(NC)"
	@python3 scripts/setup_clearml_interactive.py

clearml-apply-secret: minikube-create-clearml-secret ## Apply ClearML credentials from .env to Kubernetes secret

# ============ Quick Start ============

quickstart: ## Quick start in Docker Compose
	@echo "$(BLUE)Quick start project...$(NC)"
	@$(MAKE) build
	@$(MAKE) up
	@echo ""
	@echo "$(BLUE)Waiting for services to start...$(NC)"
	@sleep 10
	@echo "$(BLUE)Syncing datasets with S3 (uploading local datasets)...$(NC)"
	@docker compose exec -T api dvc push || echo "$(RED)Warning: Dataset push failed (this is OK if datasets already exist in S3)$(NC)"
	@echo ""
	@echo "$(GREEN)Project started!$(NC)"
	@echo ""
	@echo "API Documentation: http://localhost:8000/docs"
	@echo "Dashboard: http://localhost:8501"
	@echo "MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
	@echo ""
	@echo "$(BLUE)Note: Datasets are automatically synced with S3 on startup$(NC)"

quickstart-minikube: ## Quick start in Minikube
	@echo "$(BLUE)Quick start in Minikube...$(NC)"
	@$(MAKE) minikube-start
	@$(MAKE) minikube-deploy
	@echo ""
	@echo "$(GREEN)Project deployed to Minikube!$(NC)"
	@echo ""
	@$(MAKE) minikube-services

quickstart-minikube-with-clearml: ## Quick start Minikube + ClearML in Docker
	@echo "$(BLUE)Starting Minikube with ClearML...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(BLUE)Step 0: Creating .env file from .env.example...$(NC)"; \
		$(MAKE) env; \
		echo ""; \
	fi
	@echo "$(BLUE)Step 1: Starting ClearML in Docker Compose...$(NC)"
	@$(MAKE) clearml-up
	@echo ""
	@echo "$(BLUE)Step 2: Starting Minikube...$(NC)"
	@$(MAKE) minikube-start
	@echo ""
	@echo "$(BLUE)Step 3: Deploying to Minikube...$(NC)"
	@$(MAKE) minikube-deploy
	@echo ""
	@echo "$(BLUE)Step 4: Applying ClearML credentials...$(NC)"
	@if kubectl get secret clearml-secret -n mlops > /dev/null 2>&1; then \
		echo "$(GREEN)ClearML credentials already applied in Kubernetes, skipping...$(NC)"; \
	else \
		ACCESS_KEY=$$(grep "^CLEARML_ACCESS_KEY=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' '); \
		SECRET_KEY=$$(grep "^CLEARML_SECRET_KEY=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' '); \
		if [ -f .env ] && [ -n "$$ACCESS_KEY" ] && [ -n "$$SECRET_KEY" ]; then \
			echo "$(BLUE)Found ClearML credentials in .env, applying to Kubernetes...$(NC)"; \
			$(MAKE) clearml-apply-secret; \
		else \
			echo "$(YELLOW)ClearML credentials not found in .env$(NC)"; \
			echo "$(BLUE)Setting up ClearML credentials interactively...$(NC)"; \
			$(MAKE) clearml-setup || (echo "$(YELLOW)Credentials setup cancelled or failed. Continuing without ClearML integration.$(NC)" && exit 0); \
			ACCESS_KEY=$$(grep "^CLEARML_ACCESS_KEY=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' '); \
			SECRET_KEY=$$(grep "^CLEARML_SECRET_KEY=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' '); \
			if [ -n "$$ACCESS_KEY" ] && [ -n "$$SECRET_KEY" ]; then \
				echo "$(BLUE)Applying credentials to Kubernetes...$(NC)"; \
				$(MAKE) clearml-apply-secret; \
			else \
				echo "$(YELLOW)Credentials not configured. ClearML integration will be disabled.$(NC)"; \
			fi; \
		fi; \
	fi
	@echo ""
	@echo "$(BLUE)Step 5: Waiting for pods to be ready...$(NC)"
	@echo "$(BLUE)Waiting for API pod to be ready...$(NC)"
	@kubectl wait --for=condition=ready --timeout=60s pod -n mlops -l app=mlops-api || \
		(echo "$(YELLOW)Warning: API pod not ready, continuing anyway...$(NC)")
	@echo "$(BLUE)Waiting for Dashboard pod to be ready...$(NC)"
	@kubectl wait --for=condition=ready --timeout=60s pod -n mlops -l app=mlops-dashboard || \
		(echo "$(YELLOW)Warning: Dashboard pod not ready, continuing anyway...$(NC)")
	@echo "$(BLUE)Waiting for gRPC pod to be ready...$(NC)"
	@kubectl wait --for=condition=ready --timeout=60s pod -n mlops -l app=mlops-grpc || \
		(echo "$(YELLOW)Warning: gRPC pod not ready, continuing anyway...$(NC)")
	@echo "$(BLUE)Step 6: Setting up port forwarding...$(NC)"
	@$(MAKE) minikube-port-forward
	@echo ""
	@echo "$(GREEN)All services started!$(NC)"
	@echo ""
	@echo "$(BLUE)Minikube services (via port-forward):$(NC)"
	@echo "  API: http://localhost:8000"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  gRPC: localhost:50051"
	@echo "  MinIO API: http://localhost:9000"
	@echo "  MinIO Console: http://localhost:9001"
	@echo ""
	@echo "$(BLUE)ClearML services (Docker Compose):$(NC)"
	@echo "  ClearML Web UI: http://localhost:8080"
	@echo "  ClearML API: http://localhost:8008"
	@echo "  ClearML Fileserver: http://localhost:8081"
	@echo ""
	@echo "$(GREEN)Everything is ready!$(NC)"
	@echo "$(BLUE)Note: To stop port forwarding, run 'make minikube-port-forward-stop'$(NC)"

.DEFAULT_GOAL := help

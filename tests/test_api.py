"""Тесты для REST API."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import app


@pytest.fixture
def client():
    """Фикстура для тестового клиента."""
    return TestClient(app)


def test_read_root(client):
    """Тест корневого эндпоинта."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_check(client):
    """Тест health check."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_ready_check(client):
    """Тест readiness check."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


def test_get_model_types(client):
    """Тест получения типов моделей."""
    response = client.get("/api/models/types")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # Минимум 2 модели
    
    # Проверяем структуру
    for model_type in data:
        assert "name" in model_type
        assert "description" in model_type
        assert "hyperparameters" in model_type


def test_list_models(client):
    """Тест получения списка моделей."""
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_datasets(client):
    """Тест получения списка датасетов."""
    response = client.get("/api/datasets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


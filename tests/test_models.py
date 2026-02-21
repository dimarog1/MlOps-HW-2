"""Тесты для ML моделей."""

import numpy as np
import pandas as pd
import pytest

from app.ml import LogisticRegression, RandomForest


@pytest.fixture
def sample_data():
    """Фикстура с примерными данными."""
    np.random.seed(42)
    X = pd.DataFrame(np.random.randn(100, 4), columns=[f"feature_{i}" for i in range(4)])
    y = pd.Series(np.random.randint(0, 2, 100))
    return X, y


def test_logistic_regression_train(sample_data):
    """Тест обучения логистической регрессии."""
    X, y = sample_data
    
    model = LogisticRegression()
    metrics = model.train(X, y)
    
    assert model.is_trained
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert 0 <= metrics["accuracy"] <= 1


def test_logistic_regression_predict(sample_data):
    """Тест предсказания логистической регрессии."""
    X, y = sample_data
    
    model = LogisticRegression()
    model.train(X, y)
    
    predictions = model.predict(X[:10])
    assert len(predictions) == 10
    assert all(pred in [0, 1] for pred in predictions)


def test_random_forest_train(sample_data):
    """Тест обучения Random Forest."""
    X, y = sample_data
    
    model = RandomForest(hyperparameters={"n_estimators": 10})
    metrics = model.train(X, y)
    
    assert model.is_trained
    assert "accuracy" in metrics
    assert 0 <= metrics["accuracy"] <= 1


def test_random_forest_predict(sample_data):
    """Тест предсказания Random Forest."""
    X, y = sample_data
    
    model = RandomForest(hyperparameters={"n_estimators": 10})
    model.train(X, y)
    
    predictions = model.predict(X[:10])
    assert len(predictions) == 10


def test_model_hyperparameters():
    """Тест гиперпараметров моделей."""
    lr_model = LogisticRegression()
    rf_model = RandomForest()
    
    lr_params = lr_model.get_default_hyperparameters()
    rf_params = rf_model.get_default_hyperparameters()
    
    assert "C" in lr_params
    assert "n_estimators" in rf_params


def test_model_description():
    """Тест описания моделей."""
    lr_desc = LogisticRegression.get_description()
    rf_desc = RandomForest.get_description()
    
    assert isinstance(lr_desc, str)
    assert isinstance(rf_desc, str)
    assert len(lr_desc) > 0
    assert len(rf_desc) > 0


"""ML модели."""

from app.ml.base import BaseMLModel
from app.ml.logistic_regression import LogisticRegression
from app.ml.random_forest import RandomForest

MODEL_REGISTRY = {
    "LogisticRegression": LogisticRegression,
    "RandomForest": RandomForest,
}

__all__ = [
    "BaseMLModel",
    "LogisticRegression",
    "RandomForest",
    "MODEL_REGISTRY",
]

"""Model interface and registry for backtest pipeline.

Provides the ``BaseModel`` abstract interface, a ``DummyModel`` for
pipeline testing, and a ``ModelRegistry`` for registering and
instantiating model factories.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

import numpy as np


class BaseModel(ABC):
    """Abstract interface for backtest models."""

    @abstractmethod
    def fit(self, features: np.ndarray, labels: np.ndarray) -> None:
        """Train the model on feature matrix and labels."""

    @abstractmethod
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Return probability predictions, shape (n, n_classes)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable model name."""


class DummyModel(BaseModel):
    """Dummy model returning random probabilities.

    Used for end-to-end pipeline testing without real ML dependencies.
    Predictions are seeded for reproducibility.
    """

    def __init__(self, model_name: str = "DummyModel", seed: int = 42) -> None:
        self._name = model_name
        self._rng = np.random.default_rng(seed)
        self._n_classes = 3

    def fit(self, features: np.ndarray, labels: np.ndarray) -> None:
        """No-op fit; records the number of classes from labels."""
        unique_classes = len(np.unique(labels))
        if unique_classes > 1:
            self._n_classes = unique_classes

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Return random probabilities that sum to 1 per row."""
        raw = self._rng.random((len(features), self._n_classes))
        result: np.ndarray = raw / raw.sum(axis=1, keepdims=True)
        return result

    @property
    def name(self) -> str:
        return self._name


class ModelRegistry:
    """Registry of available model factories.

    Register a factory via ``register`` and instantiate via ``create``.
    The ``DummyModel`` is pre-registered under ``"dummy"``.
    """

    _factories: ClassVar[dict[str, type[BaseModel]]] = {}

    @classmethod
    def register(cls, key: str, factory: type[BaseModel]) -> None:
        """Register a model factory under a string key."""
        cls._factories[key] = factory

    @classmethod
    def create(cls, key: str, **kwargs: object) -> BaseModel:
        """Instantiate a registered model by key.

        Raises:
            KeyError: If the key is not registered.
        """
        if key not in cls._factories:
            available = list(cls._factories.keys())
            msg = f"Model '{key}' not registered. Available: {available}"
            raise KeyError(msg)
        return cls._factories[key](**kwargs)

    @classmethod
    def available(cls) -> list[str]:
        """Return list of registered model keys."""
        return list(cls._factories.keys())


ModelRegistry.register("dummy", DummyModel)

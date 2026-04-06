"""Tests for the model registry and individual model wrappers."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.models.ensemble.registry import (
    MODEL_REGISTRY,
    DummyModel,
    LightGBMModel,
    PredictionModel,
    TabPFNModel,
    XGBoostModel,
    create_model,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rng() -> np.random.Generator:
    """Seeded random generator for reproducibility."""
    return np.random.default_rng(42)


@pytest.fixture
def binary_dataset(rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray]:
    """Small synthetic binary classification dataset.

    100 samples, 5 features, 2 classes.
    """
    n_samples, n_features = 100, 5
    X = pd.DataFrame(
        rng.standard_normal((n_samples, n_features)),
        columns=[f"f{i}" for i in range(n_features)],
    )
    y = rng.integers(0, 2, size=n_samples)
    return X, y


@pytest.fixture
def multiclass_dataset(rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray]:
    """Small synthetic 3-class (1X2) dataset.

    150 samples, 8 features, 3 classes.
    """
    n_samples, n_features = 150, 8
    X = pd.DataFrame(
        rng.standard_normal((n_samples, n_features)),
        columns=[f"f{i}" for i in range(n_features)],
    )
    y = rng.integers(0, 3, size=n_samples)
    return X, y


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_valid_probabilities(proba: np.ndarray, n_samples: int, n_classes: int) -> None:
    """Assert that a probability matrix has the correct shape and values."""
    assert proba.shape == (n_samples, n_classes)
    assert np.all(proba >= 0.0), "Probabilities must be non-negative"
    assert np.all(proba <= 1.0), "Probabilities must be at most 1.0"
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-6, err_msg="Rows must sum to 1.0")


# ---------------------------------------------------------------------------
# DummyModel
# ---------------------------------------------------------------------------


class TestDummyModel:
    """Tests for DummyModel random-prediction baseline."""

    def test_fit_predict_binary_shape(
        self, binary_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """fit + predict_proba returns correct shape for binary."""
        X, y = binary_dataset
        model = DummyModel(seed=123)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=2)

    def test_fit_predict_multiclass_shape(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """fit + predict_proba returns correct shape for multiclass."""
        X, y = multiclass_dataset
        model = DummyModel(seed=123)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

    def test_reproducibility(self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]) -> None:
        """Same seed + same input produces identical output."""
        X, y = multiclass_dataset
        model_a = DummyModel(seed=99)
        model_a.fit(X, y)
        proba_a = model_a.predict_proba(X)

        model_b = DummyModel(seed=99)
        model_b.fit(X, y)
        proba_b = model_b.predict_proba(X)

        np.testing.assert_array_equal(proba_a, proba_b)

    def test_different_seeds_differ(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """Different seeds produce different output."""
        X, y = multiclass_dataset
        model_a = DummyModel(seed=1)
        model_a.fit(X, y)

        model_b = DummyModel(seed=2)
        model_b.fit(X, y)

        assert not np.allclose(model_a.predict_proba(X), model_b.predict_proba(X))

    def test_predict_before_fit_raises(self) -> None:
        """predict_proba before fit raises RuntimeError."""
        model = DummyModel()
        X = pd.DataFrame({"a": [1.0, 2.0]})
        with pytest.raises(RuntimeError, match="fitted before predict_proba"):
            model.predict_proba(X)

    def test_n_classes_inferred_from_y(self) -> None:
        """n_classes comes from y, not the constructor default."""
        X = pd.DataFrame({"a": range(20)})
        y = np.array([0, 1, 2, 3] * 5)  # 4 classes
        model = DummyModel(n_classes=2)  # constructor says 2
        model.fit(X, y)
        proba = model.predict_proba(X)
        assert proba.shape[1] == 4  # inferred from y


# ---------------------------------------------------------------------------
# LightGBMModel
# ---------------------------------------------------------------------------


class TestLightGBMModel:
    """Tests for LightGBM wrapper."""

    def test_fit_predict_binary(self, binary_dataset: tuple[pd.DataFrame, np.ndarray]) -> None:
        """LightGBM fit + predict_proba on binary data."""
        X, y = binary_dataset
        model = LightGBMModel(n_estimators=10)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=2)

    def test_fit_predict_multiclass(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """LightGBM fit + predict_proba on 3-class data."""
        X, y = multiclass_dataset
        model = LightGBMModel(n_estimators=10)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

    def test_predict_before_fit_raises(self) -> None:
        """predict_proba before fit raises RuntimeError."""
        model = LightGBMModel()
        X = pd.DataFrame({"a": [1.0, 2.0]})
        with pytest.raises(RuntimeError, match="fitted before predict_proba"):
            model.predict_proba(X)

    def test_conforms_to_protocol(self) -> None:
        """LightGBMModel is a PredictionModel at runtime."""
        model = LightGBMModel()
        assert isinstance(model, PredictionModel)


# ---------------------------------------------------------------------------
# XGBoostModel
# ---------------------------------------------------------------------------


class TestXGBoostModel:
    """Tests for XGBoost wrapper."""

    def test_fit_predict_binary(self, binary_dataset: tuple[pd.DataFrame, np.ndarray]) -> None:
        """XGBoost fit + predict_proba on binary data."""
        X, y = binary_dataset
        model = XGBoostModel(n_estimators=10)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=2)

    def test_fit_predict_multiclass(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """XGBoost fit + predict_proba on 3-class data."""
        X, y = multiclass_dataset
        model = XGBoostModel(n_estimators=10)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

    def test_predict_before_fit_raises(self) -> None:
        """predict_proba before fit raises RuntimeError."""
        model = XGBoostModel()
        X = pd.DataFrame({"a": [1.0, 2.0]})
        with pytest.raises(RuntimeError, match="fitted before predict_proba"):
            model.predict_proba(X)

    def test_conforms_to_protocol(self) -> None:
        """XGBoostModel is a PredictionModel at runtime."""
        model = XGBoostModel()
        assert isinstance(model, PredictionModel)


# ---------------------------------------------------------------------------
# TabPFNModel
# ---------------------------------------------------------------------------


class TestTabPFNModelImportGuard:
    """Tests for TabPFN import-error handling when package is missing."""

    def test_import_error_when_not_installed(self) -> None:
        """TabPFNModel raises ImportError when tabpfn is missing."""
        with (
            patch.dict("sys.modules", {"tabpfn": None}),
            pytest.raises(ImportError, match="TabPFN is not installed"),
        ):
            from ml_in_sports.models.ensemble.registry import TabPFNModel as _TabPFN

            _TabPFN()


# The remaining TabPFN tests require the optional tabpfn package.
# pytest.importorskip will skip them cleanly when tabpfn is not installed.
tabpfn = pytest.importorskip("tabpfn", reason="tabpfn not installed (optional dep)")


class TestTabPFNModel:
    """Tests for TabPFN wrapper when the package IS installed."""

    def test_fit_predict_multiclass(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """TabPFN fit + predict_proba on 3-class data."""
        X, y = multiclass_dataset
        model = TabPFNModel(n_estimators=4)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

    def test_fit_predict_binary(
        self, binary_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """TabPFN fit + predict_proba on binary data."""
        X, y = binary_dataset
        model = TabPFNModel(n_estimators=4)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=2)

    def test_predict_before_fit_raises(self) -> None:
        """predict_proba before fit raises RuntimeError."""
        model = TabPFNModel(n_estimators=4)
        X = pd.DataFrame({"a": [1.0, 2.0]})
        with pytest.raises(RuntimeError, match="fitted before predict_proba"):
            model.predict_proba(X)

    def test_conforms_to_protocol(self) -> None:
        """TabPFNModel is a PredictionModel at runtime."""
        model = TabPFNModel(n_estimators=4)
        assert isinstance(model, PredictionModel)

    def test_subsample_large_dataset(self, rng: np.random.Generator) -> None:
        """TabPFN subsamples when train set exceeds max_train_samples."""
        n_samples, n_features = 500, 5
        X = pd.DataFrame(
            rng.standard_normal((n_samples, n_features)),
            columns=[f"f{i}" for i in range(n_features)],
        )
        y = rng.integers(0, 3, size=n_samples)

        # Set a very low limit to force subsampling
        model = TabPFNModel(max_train_samples=50, n_estimators=4)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=n_samples, n_classes=3)

    def test_subsample_preserves_all_classes(self, rng: np.random.Generator) -> None:
        """Stratified subsample keeps at least 1 sample per class."""
        n_samples, n_features = 300, 3
        X = pd.DataFrame(
            rng.standard_normal((n_samples, n_features)),
            columns=[f"f{i}" for i in range(n_features)],
        )
        # Imbalanced: class 2 has very few samples
        y = np.array([0] * 140 + [1] * 140 + [2] * 20)

        model = TabPFNModel(max_train_samples=30, n_estimators=4)
        model.fit(X, y)
        proba = model.predict_proba(X)
        # All 3 classes should be represented in predictions
        assert proba.shape[1] == 3

    def test_no_subsample_below_limit(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """No subsampling when dataset is within the limit."""
        X, y = multiclass_dataset  # 150 samples
        model = TabPFNModel(max_train_samples=10_000, n_estimators=4)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

    def test_probabilities_sum_to_one(self, rng: np.random.Generator) -> None:
        """TabPFN probabilities sum to 1.0 for every row."""
        n_samples, n_features = 80, 4
        X = pd.DataFrame(
            rng.standard_normal((n_samples, n_features)),
            columns=[f"f{i}" for i in range(n_features)],
        )
        y = rng.integers(0, 3, size=n_samples)

        model = TabPFNModel(n_estimators=4)
        model.fit(X, y)
        proba = model.predict_proba(X)

        np.testing.assert_allclose(
            proba.sum(axis=1),
            np.ones(n_samples),
            atol=1e-5,
            err_msg="TabPFN probabilities must sum to 1.0",
        )

    def test_via_create_model_factory(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """TabPFN created via create_model works end-to-end."""
        X, y = multiclass_dataset
        model = create_model("tabpfn", n_estimators=4)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

    def test_numpy_conversion_from_dataframe(self, rng: np.random.Generator) -> None:
        """TabPFN correctly converts DataFrame to numpy arrays."""
        X = pd.DataFrame(
            {"a": rng.standard_normal(50), "b": rng.standard_normal(50)},
        )
        y = rng.integers(0, 2, size=50)

        model = TabPFNModel(n_estimators=4)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=50, n_classes=2)


# ---------------------------------------------------------------------------
# create_model factory
# ---------------------------------------------------------------------------


class TestCreateModel:
    """Tests for the create_model factory function."""

    def test_valid_type_returns_model(self) -> None:
        """create_model with a valid type returns an instance."""
        model = create_model("dummy", seed=7)
        assert isinstance(model, DummyModel)

    def test_invalid_type_raises_key_error(self) -> None:
        """create_model with an unknown type raises KeyError."""
        with pytest.raises(KeyError, match="Unknown model type"):
            create_model("nonexistent_model")

    def test_all_registry_keys_are_constructible(self) -> None:
        """Every key in MODEL_REGISTRY can be instantiated (except tabpfn)."""
        for name, cls in MODEL_REGISTRY.items():
            if name == "tabpfn":
                continue  # optional dependency, tested separately
            instance = cls()
            assert isinstance(instance, PredictionModel)

    def test_params_forwarded(self) -> None:
        """Constructor params are forwarded correctly."""
        model = create_model("dummy", seed=999, n_classes=5)
        assert isinstance(model, DummyModel)
        assert model._seed == 999
        assert model._n_classes == 5

    def test_lightgbm_via_factory(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """LightGBM created via factory works end-to-end."""
        X, y = multiclass_dataset
        model = create_model("lightgbm", n_estimators=5)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

    def test_xgboost_via_factory(self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]) -> None:
        """XGBoost created via factory works end-to-end."""
        X, y = multiclass_dataset
        model = create_model("xgboost", n_estimators=5)
        model.fit(X, y)
        proba = model.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

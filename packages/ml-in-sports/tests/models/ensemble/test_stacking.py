"""Tests for the StackingEnsemble meta-learner."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.models.ensemble.registry import (
    DummyModel,
    LightGBMModel,
    XGBoostModel,
    create_model,
)
from ml_in_sports.models.ensemble.stacking import StackingEnsemble

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rng() -> np.random.Generator:
    """Seeded random generator for reproducibility."""
    return np.random.default_rng(42)


@pytest.fixture
def multiclass_dataset(rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray]:
    """Synthetic 3-class dataset with 200 samples and 6 features.

    Feature correlations with classes ensure learnable signal.
    """
    n_samples, n_features = 200, 6
    y = rng.integers(0, 3, size=n_samples)

    # Create features with class-dependent signal
    X_arr = rng.standard_normal((n_samples, n_features))
    for class_idx in range(3):
        mask = y == class_idx
        X_arr[mask, class_idx % n_features] += 1.5
    X = pd.DataFrame(X_arr, columns=[f"f{i}" for i in range(n_features)])
    return X, y


@pytest.fixture
def binary_dataset(rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray]:
    """Synthetic binary dataset with 120 samples and 5 features."""
    n_samples, n_features = 120, 5
    y = rng.integers(0, 2, size=n_samples)
    X_arr = rng.standard_normal((n_samples, n_features))
    X_arr[y == 1, 0] += 2.0
    X = pd.DataFrame(X_arr, columns=[f"f{i}" for i in range(n_features)])
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
# StackingEnsemble with DummyModel bases
# ---------------------------------------------------------------------------


class TestStackingEnsembleDummy:
    """Tests using DummyModel base models (fast, no real training)."""

    def test_fit_predict_works(self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]) -> None:
        """Stacking with dummy bases fits and predicts without error."""
        X, y = multiclass_dataset
        base_models = [DummyModel(seed=i) for i in range(3)]
        ensemble = StackingEnsemble(base_models=base_models, n_folds=3)
        ensemble.fit(X, y)
        proba = ensemble.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

    def test_binary_classification(self, binary_dataset: tuple[pd.DataFrame, np.ndarray]) -> None:
        """Stacking works on binary (2-class) data."""
        X, y = binary_dataset
        base_models = [DummyModel(seed=i) for i in range(2)]
        ensemble = StackingEnsemble(base_models=base_models, n_folds=3)
        ensemble.fit(X, y)
        proba = ensemble.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=2)

    def test_predict_before_fit_raises(self) -> None:
        """predict_proba before fit raises RuntimeError."""
        base_models = [DummyModel(seed=0)]
        ensemble = StackingEnsemble(base_models=base_models)
        X = pd.DataFrame({"a": [1.0, 2.0]})
        with pytest.raises(RuntimeError, match="fitted before predict_proba"):
            ensemble.predict_proba(X)


# ---------------------------------------------------------------------------
# StackingEnsemble with real models
# ---------------------------------------------------------------------------


class TestStackingEnsembleReal:
    """Tests using LightGBM + XGBoost base models."""

    def test_lgb_xgb_stacking_produces_valid_proba(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """LightGBM + XGBoost stacking produces valid probabilities."""
        X, y = multiclass_dataset
        base_models = [
            LightGBMModel(n_estimators=10),
            XGBoostModel(n_estimators=10),
        ]
        ensemble = StackingEnsemble(base_models=base_models, n_folds=3)
        ensemble.fit(X, y)
        proba = ensemble.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

    def test_ensemble_does_not_break_individual_predictions(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """Ensemble predictions are in a reasonable range vs. individuals.

        We check that the ensemble produces probabilities (not NaN/Inf)
        and that its log-loss is finite.  We do NOT assert it beats
        individual models on 200 samples -- that requires larger data.
        """
        X, y = multiclass_dataset
        lgb = LightGBMModel(n_estimators=10)
        xgb = XGBoostModel(n_estimators=10)
        base_models = [lgb, xgb]

        ensemble = StackingEnsemble(base_models=base_models, n_folds=3)
        ensemble.fit(X, y)

        proba_ensemble = ensemble.predict_proba(X)
        assert not np.any(np.isnan(proba_ensemble))
        assert not np.any(np.isinf(proba_ensemble))

        # All base models are also refitted on full data
        proba_lgb = lgb.predict_proba(X)
        proba_xgb = xgb.predict_proba(X)
        assert proba_lgb.shape == proba_ensemble.shape
        assert proba_xgb.shape == proba_ensemble.shape


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestStackingEnsembleEdgeCases:
    """Edge cases and validation tests."""

    def test_single_base_model(self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]) -> None:
        """Stacking with a single base model still works."""
        X, y = multiclass_dataset
        ensemble = StackingEnsemble(
            base_models=[DummyModel(seed=42)],
            n_folds=3,
        )
        ensemble.fit(X, y)
        proba = ensemble.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

    def test_empty_base_models_raises(self) -> None:
        """Empty base_models list raises ValueError."""
        with pytest.raises(ValueError, match="at least one base model"):
            StackingEnsemble(base_models=[])

    def test_n_folds_less_than_two_raises(self) -> None:
        """n_folds < 2 raises ValueError."""
        with pytest.raises(ValueError, match="n_folds must be >= 2"):
            StackingEnsemble(base_models=[DummyModel()], n_folds=1)

    def test_invalid_meta_learner_type_raises(self) -> None:
        """Unknown meta_learner_type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown meta_learner_type"):
            StackingEnsemble(
                base_models=[DummyModel()],
                meta_learner_type="random_forest",
            )

    def test_oof_shape_internal(self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]) -> None:
        """Verify the internal OOF prediction matrix has correct dimensions.

        This is a white-box test: we monkey-patch to capture the OOF
        matrix shape during fit.
        """
        X, y = multiclass_dataset
        n_base = 2
        n_classes = 3
        base_models = [DummyModel(seed=i) for i in range(n_base)]
        ensemble = StackingEnsemble(base_models=base_models, n_folds=3)

        # After fit, the meta_learner is fitted on (n_samples, n_base * n_classes)
        ensemble.fit(X, y)
        assert ensemble._meta_learner is not None
        assert ensemble._n_classes == n_classes

        # Meta-learner should have seen features of width n_base * n_classes
        n_features_seen = ensemble._meta_learner.n_features_in_
        assert n_features_seen == n_base * n_classes

    def test_create_model_factory_for_ensemble(
        self, multiclass_dataset: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        """Models created via create_model work as stacking base models."""
        X, y = multiclass_dataset
        lgb = create_model("lightgbm", n_estimators=5)
        xgb = create_model("xgboost", n_estimators=5)
        ensemble = StackingEnsemble(base_models=[lgb, xgb], n_folds=3)
        ensemble.fit(X, y)
        proba = ensemble.predict_proba(X)
        _assert_valid_probabilities(proba, n_samples=len(X), n_classes=3)

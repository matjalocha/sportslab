"""Stacking ensemble: combines base model predictions with a meta-learner.

Uses out-of-fold (OOF) predictions from base models as features for
the meta-learner.  This prevents the meta-learner from overfitting
to the base models' training-set predictions.

Training workflow:
    1. Generate OOF predictions from each base model using K-fold CV.
    2. Stack OOF predictions into a feature matrix
       ``(n_samples, n_base_models * n_classes)``.
    3. Train a meta-learner (default: ``LogisticRegression``) on
       stacked features.
    4. Refit each base model on the full training set for prediction.

Prediction workflow:
    1. Get predictions from each (fully-trained) base model.
    2. Stack into the same feature layout.
    3. Predict with the fitted meta-learner.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
import structlog
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold

from ml_in_sports.models.ensemble.registry import PredictionModel

logger = structlog.get_logger(__name__)

_META_LEARNER_REGISTRY: dict[str, type] = {
    "logistic_regression": LogisticRegression,
}


class StackingEnsemble:
    """Stacking meta-learner over base models.

    Combines OOF predictions from multiple base models via a
    second-level classifier.  Conforms to :class:`PredictionModel`
    so it can itself be used as a model in the backtest runner.

    Args:
        base_models: List of fitted-or-unfitted models implementing
            :class:`PredictionModel`.  At least one is required.
        meta_learner_type: Key into the meta-learner registry.
            Currently only ``"logistic_regression"`` is supported.
        n_folds: Number of cross-validation folds for generating
            OOF predictions.  Must be >= 2.
        meta_learner_params: Extra keyword arguments forwarded to
            the meta-learner constructor.
    """

    def __init__(
        self,
        base_models: Sequence[PredictionModel],
        meta_learner_type: str = "logistic_regression",
        n_folds: int = 5,
        meta_learner_params: dict[str, Any] | None = None,
    ) -> None:
        if len(base_models) == 0:
            raise ValueError("StackingEnsemble requires at least one base model.")
        if n_folds < 2:
            raise ValueError(f"n_folds must be >= 2, got {n_folds}.")
        if meta_learner_type not in _META_LEARNER_REGISTRY:
            available = ", ".join(sorted(_META_LEARNER_REGISTRY.keys()))
            raise ValueError(
                f"Unknown meta_learner_type {meta_learner_type!r}. Available: {available}"
            )

        self._base_models: Sequence[PredictionModel] = base_models
        self._meta_learner_type: str = meta_learner_type
        self._n_folds: int = n_folds
        self._meta_learner_params: dict[str, Any] = meta_learner_params or {}
        self._meta_learner: LogisticRegression | None = None
        self._n_classes: int = 0
        self._fitted: bool = False

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> None:
        """Train the stacking ensemble.

        1. Generate OOF predictions from each base model via K-fold.
        2. Train the meta-learner on stacked OOF features.
        3. Refit every base model on the full training set.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.
            y: Target labels, shape ``(n_samples,)``.
                Integer class indices.
        """
        y_arr = np.asarray(y).ravel()
        self._n_classes = len(np.unique(y_arr))
        n_samples = len(X)
        n_base = len(self._base_models)

        logger.info(
            "stacking_ensemble_fit_start",
            n_samples=n_samples,
            n_features=X.shape[1],
            n_base_models=n_base,
            n_classes=self._n_classes,
            n_folds=self._n_folds,
        )

        # --- Step 1: Generate OOF predictions ---
        oof_predictions = np.zeros(
            (n_samples, n_base * self._n_classes),
            dtype=np.float64,
        )

        kf = KFold(n_splits=self._n_folds, shuffle=False)

        for model_idx, model in enumerate(self._base_models):
            col_start = model_idx * self._n_classes
            col_end = col_start + self._n_classes

            for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X)):
                X_train_fold = X.iloc[train_idx]
                y_train_fold = y_arr[train_idx]
                X_val_fold = X.iloc[val_idx]

                # Create a fresh copy of the model for this fold to avoid
                # contamination between folds. We reconstruct from the same
                # class with no params (the base_models list provides the
                # template configuration, but for OOF we need fresh instances).
                fold_model = _clone_model(model)
                fold_model.fit(X_train_fold, y_train_fold)

                fold_proba = fold_model.predict_proba(X_val_fold)
                oof_predictions[val_idx, col_start:col_end] = fold_proba

                logger.debug(
                    "stacking_oof_fold_done",
                    model_idx=model_idx,
                    fold_idx=fold_idx,
                    val_size=len(val_idx),
                )

        # --- Step 2: Train meta-learner on OOF features ---
        defaults: dict[str, Any] = {
            "max_iter": 1000,
            "solver": "lbfgs",
        }
        merged_params = {**defaults, **self._meta_learner_params}
        meta_cls = _META_LEARNER_REGISTRY[self._meta_learner_type]
        self._meta_learner = meta_cls(**merged_params)
        self._meta_learner.fit(oof_predictions, y_arr)

        logger.debug("stacking_meta_learner_fitted", meta_type=self._meta_learner_type)

        # --- Step 3: Refit all base models on full training data ---
        for model_idx, model in enumerate(self._base_models):
            model.fit(X, y_arr)
            logger.debug("stacking_base_model_refitted", model_idx=model_idx)

        self._fitted = True
        logger.info("stacking_ensemble_fit_done", n_base_models=n_base)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class probabilities using the stacking ensemble.

        Gets predictions from each base model, stacks them, and
        passes through the meta-learner.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.

        Returns:
            Probability array, shape ``(n_samples, n_classes)``.

        Raises:
            RuntimeError: If called before ``fit()``.
        """
        if not self._fitted or self._meta_learner is None:
            raise RuntimeError("StackingEnsemble must be fitted before predict_proba.")

        n_samples = len(X)
        n_base = len(self._base_models)
        stacked = np.zeros(
            (n_samples, n_base * self._n_classes),
            dtype=np.float64,
        )

        for model_idx, model in enumerate(self._base_models):
            col_start = model_idx * self._n_classes
            col_end = col_start + self._n_classes
            stacked[:, col_start:col_end] = model.predict_proba(X)

        result: np.ndarray = self._meta_learner.predict_proba(stacked)
        return result


def _clone_model(model: PredictionModel) -> PredictionModel:
    """Create a fresh (unfitted) copy of a model.

    Uses ``sklearn.base.clone`` if the model is sklearn-compatible,
    otherwise falls back to constructing a new instance of the same
    class with no arguments.

    Args:
        model: Model instance to clone.

    Returns:
        Fresh unfitted model of the same type.
    """
    try:
        from sklearn.base import clone

        return clone(model)  # type: ignore[no-any-return]
    except TypeError:
        # Model is not sklearn-compatible; reconstruct from class.
        return model.__class__()

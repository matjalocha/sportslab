"""Model registry: maps config names to model classes.

All models implement the :class:`PredictionModel` protocol with
``fit()`` and ``predict_proba()``.  The registry allows the backtest
runner to instantiate models by name from YAML/JSON experiment configs.

Wrappers are deliberately thin: they delegate to the underlying
scikit-learn-compatible classifier, adding only the type-safe
protocol interface and graceful optional-dependency handling (TabPFN).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


@runtime_checkable
class PredictionModel(Protocol):
    """Protocol for all models in the backtest framework.

    Every model must implement ``fit`` and ``predict_proba`` with
    the signatures below.  The protocol is runtime-checkable so
    the registry can validate instances.
    """

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> None:
        """Train the model.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.
            y: Target labels, shape ``(n_samples,)``.
                Integer class indices (0, 1, ..., n_classes-1).
        """
        ...

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class probabilities.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.

        Returns:
            Probability array, shape ``(n_samples, n_classes)``.
        """
        ...


class LightGBMModel:
    """LightGBM wrapper conforming to :class:`PredictionModel` protocol.

    Wraps ``lightgbm.LGBMClassifier``. The number of classes is
    inferred from ``y`` during ``fit()``, not hardcoded.

    Args:
        **params: Keyword arguments forwarded to ``LGBMClassifier``.
            Defaults are set for multiclass classification with
            suppressed verbosity.
    """

    def __init__(self, **params: Any) -> None:
        import lightgbm as lgb

        defaults: dict[str, Any] = {
            "objective": "multiclass",
            "verbosity": -1,
            "n_jobs": 1,
        }
        merged = {**defaults, **params}
        self._model: lgb.LGBMClassifier = lgb.LGBMClassifier(**merged)
        self._fitted: bool = False

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> None:
        """Train on feature DataFrame and integer target labels.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.
            y: Target labels, shape ``(n_samples,)``.
        """
        y_arr = np.asarray(y).ravel()
        n_classes = len(np.unique(y_arr))
        self._model.set_params(num_class=n_classes)
        self._model.fit(X, y_arr)
        self._fitted = True
        logger.debug(
            "lightgbm_model_fitted",
            n_samples=len(y_arr),
            n_features=X.shape[1],
            n_classes=n_classes,
        )

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return class probabilities.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.

        Returns:
            Probability array, shape ``(n_samples, n_classes)``.

        Raises:
            RuntimeError: If called before ``fit()``.
        """
        if not self._fitted:
            raise RuntimeError("LightGBMModel must be fitted before predict_proba.")
        result: np.ndarray = self._model.predict_proba(X)
        return result


class XGBoostModel:
    """XGBoost wrapper conforming to :class:`PredictionModel` protocol.

    Wraps ``xgboost.XGBClassifier``. The number of classes is
    inferred from ``y`` during ``fit()``.

    Args:
        **params: Keyword arguments forwarded to ``XGBClassifier``.
            Defaults are set for multiclass soft-probability output
            with suppressed verbosity.
    """

    def __init__(self, **params: Any) -> None:
        import xgboost as xgb

        defaults: dict[str, Any] = {
            "objective": "multi:softprob",
            "eval_metric": "mlogloss",
            "use_label_encoder": False,
            "verbosity": 0,
            "n_jobs": 1,
        }
        merged = {**defaults, **params}
        self._model: xgb.XGBClassifier = xgb.XGBClassifier(**merged)
        self._fitted: bool = False

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> None:
        """Train on feature DataFrame and integer target labels.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.
            y: Target labels, shape ``(n_samples,)``.
        """
        y_arr = np.asarray(y).ravel()
        n_classes = len(np.unique(y_arr))
        self._model.set_params(num_class=n_classes)
        self._model.fit(X, y_arr)
        self._fitted = True
        logger.debug(
            "xgboost_model_fitted",
            n_samples=len(y_arr),
            n_features=X.shape[1],
            n_classes=n_classes,
        )

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return class probabilities.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.

        Returns:
            Probability array, shape ``(n_samples, n_classes)``.

        Raises:
            RuntimeError: If called before ``fit()``.
        """
        if not self._fitted:
            raise RuntimeError("XGBoostModel must be fitted before predict_proba.")
        result: np.ndarray = self._model.predict_proba(X)
        return result


_TABPFN_DEFAULT_MAX_TRAIN_SAMPLES: int = 10_000
"""Default maximum training samples for TabPFN.

TabPFN is an in-context learner that stores the entire training set for
prediction.  Performance degrades and memory usage grows linearly with
train size.  On CPU, TabPFN v6 enforces a 1000-sample hard limit by
default.  We subsample to ``max_train_samples`` before calling ``fit()``
and pass ``ignore_pretraining_limits=True`` to avoid the hard-coded guard.
"""


class TabPFNModel:
    """TabPFN wrapper conforming to :class:`PredictionModel` protocol.

    TabPFN is an optional heavy dependency (requires PyTorch).  If the
    ``tabpfn`` package is not installed, construction raises
    ``ImportError`` with a helpful message.

    When the training set exceeds ``max_train_samples``, a stratified
    random subsample is taken to keep fit time and memory bounded.
    The subsample is reproducible via ``random_state``.

    Args:
        max_train_samples: Maximum number of training samples.
            If the training set is larger, a stratified subsample is
            used.  Defaults to 10,000.
        random_state: Seed for both TabPFN internals and the
            subsampling RNG.  Defaults to 0 (TabPFN default).
        **params: Additional keyword arguments forwarded to
            ``TabPFNClassifier``.  Note: TabPFN v6 uses
            ``n_estimators`` (not ``n_ensemble_configurations``).
    """

    def __init__(
        self,
        max_train_samples: int = _TABPFN_DEFAULT_MAX_TRAIN_SAMPLES,
        random_state: int = 0,
        **params: Any,
    ) -> None:
        try:
            from tabpfn import TabPFNClassifier
        except ImportError as exc:
            raise ImportError(
                "TabPFN is not installed. Install it with: "
                "uv sync --extra ml  "
                "(requires PyTorch and ~1 GB model download on first use)."
            ) from exc

        self._max_train_samples: int = max_train_samples
        self._random_state: int = random_state
        self._model: Any = TabPFNClassifier(
            random_state=random_state,
            ignore_pretraining_limits=True,
            **params,
        )
        self._fitted: bool = False

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> None:
        """Train on feature DataFrame and integer target labels.

        Note: TabPFN is a prior-fitted model and does not learn from
        the training data in the traditional sense.  It stores the
        training set for in-context learning at prediction time.

        If the dataset exceeds ``max_train_samples``, a stratified
        random subsample is used.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.
            y: Target labels, shape ``(n_samples,)``.
        """
        X_arr = np.asarray(X, dtype=np.float64)
        y_arr = np.asarray(y).ravel()
        n_samples = len(y_arr)

        if n_samples > self._max_train_samples:
            X_arr, y_arr = self._stratified_subsample(X_arr, y_arr)
            logger.warning(
                "tabpfn_train_subsampled",
                original_samples=n_samples,
                subsampled_to=len(y_arr),
                max_train_samples=self._max_train_samples,
            )

        self._model.fit(X_arr, y_arr)
        self._fitted = True
        logger.debug(
            "tabpfn_model_fitted",
            n_samples=len(y_arr),
            n_features=X_arr.shape[1],
        )

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return class probabilities.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.

        Returns:
            Probability array, shape ``(n_samples, n_classes)``.

        Raises:
            RuntimeError: If called before ``fit()``.
        """
        if not self._fitted:
            raise RuntimeError("TabPFNModel must be fitted before predict_proba.")
        X_arr = np.asarray(X, dtype=np.float64)
        result: np.ndarray = self._model.predict_proba(X_arr)
        return result

    def _stratified_subsample(
        self, X: np.ndarray, y: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Subsample training data while preserving class distribution.

        Args:
            X: Feature array, shape ``(n_samples, n_features)``.
            y: Target labels, shape ``(n_samples,)``.

        Returns:
            Tuple of subsampled ``(X, y)`` with at most
            ``max_train_samples`` rows.
        """
        rng = np.random.default_rng(self._random_state)
        classes, counts = np.unique(y, return_counts=True)
        n_target = self._max_train_samples

        indices: list[int] = []
        for cls, count in zip(classes, counts, strict=True):
            cls_indices = np.where(y == cls)[0]
            # Proportional allocation, at least 1 per class
            n_cls = max(1, round(count / len(y) * n_target))
            n_cls = min(n_cls, len(cls_indices))
            chosen = rng.choice(cls_indices, size=n_cls, replace=False)
            indices.extend(chosen.tolist())

        idx_arr = np.array(sorted(indices))
        return X[idx_arr], y[idx_arr]


class DummyModel:
    """Random predictions for testing the pipeline end-to-end.

    Produces reproducible random Dirichlet-distributed probabilities,
    ignoring input features entirely.  Useful for verifying that
    the backtest pipeline handles model outputs correctly without
    depending on real training.

    Args:
        n_classes: Number of output classes (overridden by ``fit()``
            if ``y`` contains a different number of unique values).
        seed: Random seed for reproducibility.
    """

    def __init__(self, n_classes: int = 3, seed: int = 42) -> None:
        self._n_classes: int = n_classes
        self._seed: int = seed
        self._fitted: bool = False

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> None:
        """Store the number of classes from the target labels.

        Args:
            X: Feature DataFrame (ignored).
            y: Target labels, shape ``(n_samples,)``.
        """
        y_arr = np.asarray(y).ravel()
        self._n_classes = len(np.unique(y_arr))
        self._fitted = True
        logger.debug(
            "dummy_model_fitted",
            n_classes=self._n_classes,
            seed=self._seed,
        )

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return random Dirichlet-distributed probabilities.

        The random state is derived from both the stored seed and the
        input shape, making outputs deterministic for the same input.

        Args:
            X: Feature DataFrame, shape ``(n_samples, n_features)``.

        Returns:
            Probability array, shape ``(n_samples, n_classes)``.
                Each row sums to 1.0.

        Raises:
            RuntimeError: If called before ``fit()``.
        """
        if not self._fitted:
            raise RuntimeError("DummyModel must be fitted before predict_proba.")
        rng = np.random.default_rng(self._seed)
        alpha = np.ones(self._n_classes)
        result: np.ndarray = rng.dirichlet(alpha, size=len(X))
        return result


MODEL_REGISTRY: dict[str, type] = {
    "lightgbm": LightGBMModel,
    "xgboost": XGBoostModel,
    "tabpfn": TabPFNModel,
    "dummy": DummyModel,
}


def create_model(model_type: str, **params: Any) -> PredictionModel:
    """Create a model instance from the registry.

    Looks up the model class by name and instantiates it with the
    given parameters.

    Args:
        model_type: Model type name.  Must be a key in
            :data:`MODEL_REGISTRY` (``"lightgbm"``, ``"xgboost"``,
            ``"tabpfn"``, ``"dummy"``).
        **params: Model-specific keyword arguments forwarded to the
            constructor.

    Returns:
        Model instance conforming to :class:`PredictionModel`.

    Raises:
        KeyError: If ``model_type`` is not in the registry.
    """
    if model_type not in MODEL_REGISTRY:
        available = ", ".join(sorted(MODEL_REGISTRY.keys()))
        raise KeyError(f"Unknown model type {model_type!r}. Available: {available}")
    model_class = MODEL_REGISTRY[model_type]
    instance = model_class(**params)
    logger.info("model_created", model_type=model_type, params=params)
    return instance  # type: ignore[no-any-return]

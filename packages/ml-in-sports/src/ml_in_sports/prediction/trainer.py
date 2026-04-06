"""Model training, prediction, and calibration for daily pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.models.calibration.selector import CalibrationSelector
from ml_in_sports.prediction.models import ProbabilityModel

logger = structlog.get_logger(__name__)


def train_lightgbm(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    model_type: str,
    model_dir: Path,
) -> ProbabilityModel | None:
    """Train a LightGBM model for 1x2 classification.

    Args:
        x_train: Feature matrix.
        y_train: Encoded target labels (0=H, 1=D, 2=A).
        model_type: Model type key for the ensemble registry.
        model_dir: Directory for model persistence (logged only).

    Returns:
        Fitted model, or ``None`` if training data has fewer than 3 classes.
    """
    if len(np.unique(y_train)) < 3:
        logger.warning("trainer_requires_three_classes")
        return None

    from ml_in_sports.models.ensemble.registry import create_model

    model = create_model(
        model_type,
        n_estimators=50,
        learning_rate=0.05,
        num_leaves=15,
        min_child_samples=5,
        random_state=42,
    )
    model.fit(x_train, y_train)
    logger.info(
        "trainer_model_trained",
        rows=len(x_train),
        features=x_train.shape[1],
        model_dir=str(model_dir),
    )
    return model


def predict_probabilities(
    model: ProbabilityModel,
    x_upcoming: pd.DataFrame,
) -> np.ndarray:
    """Produce normalized 1x2 probability predictions.

    Args:
        model: A fitted probability model.
        x_upcoming: Feature matrix for upcoming matches.

    Returns:
        Array of shape ``(n_samples, 3)`` with normalized probabilities.

    Raises:
        ValueError: If the model output shape is not ``(n, 3)``.
    """
    probabilities = np.asarray(model.predict_proba(x_upcoming), dtype=np.float64)
    if probabilities.ndim != 2 or probabilities.shape[1] != 3:
        raise ValueError(
            "DailyPredictor expects 1x2 probabilities with shape (n_samples, 3)."
        )
    return _normalize_probabilities(probabilities)


def calibrate_probabilities(
    model: ProbabilityModel,
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    prediction_probs: np.ndarray,
) -> np.ndarray:
    """Apply calibration to raw model probabilities.

    Uses walk-forward cross-validation to select the best calibration method
    (temperature scaling or Platt scaling), then transforms prediction
    probabilities.

    Args:
        model: Fitted model (used to generate training probabilities).
        x_train: Training feature matrix.
        y_train: Training labels.
        prediction_probs: Raw probabilities to calibrate.

    Returns:
        Calibrated and normalized probability array.
    """
    if len(y_train) < 30:
        logger.info("trainer_calibration_skipped", reason="insufficient_rows")
        return prediction_probs

    try:
        train_probs = _normalize_probabilities(
            np.asarray(model.predict_proba(x_train), dtype=np.float64)
        )
        selector = CalibrationSelector(methods=["temperature", "platt"])
        method_name, calibrator = selector.select(y_train, train_probs, n_folds=3)
        calibrated = calibrator.transform(prediction_probs)
        logger.info("trainer_calibrated", method=method_name)
        return _normalize_probabilities(np.asarray(calibrated, dtype=np.float64))
    except (ValueError, np.linalg.LinAlgError):
        logger.warning("trainer_calibration_failed", exc_info=True)
        return prediction_probs


def _normalize_probabilities(probabilities: np.ndarray) -> np.ndarray:
    """Clip and row-normalize a probability matrix.

    Args:
        probabilities: Raw probability array of shape ``(n, k)``.

    Returns:
        Normalized array where each row sums to 1.
    """
    clipped = np.clip(probabilities, 1e-6, 1.0)
    row_sums = clipped.sum(axis=1, keepdims=True)
    normalized = clipped / np.where(row_sums == 0.0, 1.0, row_sums)
    return cast(np.ndarray, normalized)

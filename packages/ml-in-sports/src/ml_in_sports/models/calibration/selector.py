"""Auto-selection of the best calibration method via walk-forward CV.

Tries all configured calibration methods, picks the one with lowest
Expected Calibration Error (ECE) on held-out validation folds.

Usage::

    selector = CalibrationSelector()
    method_name, calibrator = selector.select(y_true, y_prob, n_folds=3)
    calibrated = calibrator.transform(new_probs)
"""

from __future__ import annotations

import itertools
from typing import Protocol

import numpy as np
import structlog

from ml_in_sports.models.calibration.isotonic import IsotonicScaler
from ml_in_sports.models.calibration.platt import PlattScaler
from ml_in_sports.models.calibration.temperature import TemperatureScaler

logger = structlog.get_logger(__name__)


class Calibrator(Protocol):
    """Protocol defining the calibrator interface."""

    def fit(self, y_true: np.ndarray, y_prob: np.ndarray) -> None:
        """Fit calibrator on validation data."""
        ...

    def transform(self, y_prob: np.ndarray) -> np.ndarray:
        """Transform probabilities to calibrated probabilities."""
        ...

    def fit_transform(self, y_true: np.ndarray, y_prob: np.ndarray) -> np.ndarray:
        """Fit and transform in one step."""
        ...


CalibratorInstance = TemperatureScaler | PlattScaler | IsotonicScaler

_METHOD_REGISTRY: dict[str, type[CalibratorInstance]] = {
    "temperature": TemperatureScaler,
    "platt": PlattScaler,
    "isotonic": IsotonicScaler,
}


def _compute_ece(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 15,
) -> float:
    """Compute Expected Calibration Error.

    For binary (1D probs), computes standard ECE. For multiclass (2D probs),
    computes classwise ECE averaged over classes.

    Args:
        y_true: Ground truth labels. Shape (n,) for binary/multiclass indices,
            or (n, k) one-hot.
        y_prob: Predicted probabilities. Shape (n,) for binary or (n, k) for
            multiclass.
        n_bins: Number of equal-width bins for calibration.

    Returns:
        ECE as a float in [0, 1].

    .. todo:: Replace with ``ml_in_sports.backtesting.metrics.compute_ece``
       once that module is available (SPO-TBD).
    """
    y_true_arr = np.asarray(y_true, dtype=np.float64)
    y_prob_arr = np.asarray(y_prob, dtype=np.float64)

    if y_prob_arr.ndim == 1:
        return _compute_ece_binary(y_true_arr.ravel(), y_prob_arr, n_bins)

    if y_prob_arr.ndim == 2 and y_prob_arr.shape[1] == 2:
        return _compute_ece_binary(y_true_arr.ravel(), y_prob_arr[:, 1], n_bins)

    return _compute_ece_multiclass(y_true_arr, y_prob_arr, n_bins)


def _compute_ece_binary(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int,
) -> float:
    """ECE for binary classification."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n_total = len(y_true)

    if n_total == 0:
        return 0.0

    for bin_lower, bin_upper in itertools.pairwise(bin_edges):
        if bin_lower == bin_edges[0]:
            mask = (y_prob >= bin_lower) & (y_prob <= bin_upper)
        else:
            mask = (y_prob > bin_lower) & (y_prob <= bin_upper)

        n_in_bin = int(np.sum(mask))
        if n_in_bin == 0:
            continue

        avg_confidence = float(np.mean(y_prob[mask]))
        avg_accuracy = float(np.mean(y_true[mask]))
        ece += (n_in_bin / n_total) * abs(avg_accuracy - avg_confidence)

    return ece


def _compute_ece_multiclass(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int,
) -> float:
    """Classwise ECE averaged over classes."""
    n_classes = y_prob.shape[1]

    labels_int = np.argmax(y_true, axis=1) if y_true.ndim == 2 else y_true.astype(int).ravel()

    total_ece = 0.0
    for class_idx in range(n_classes):
        binary_labels = (labels_int == class_idx).astype(float)
        total_ece += _compute_ece_binary(binary_labels, y_prob[:, class_idx], n_bins)

    return float(total_ece / n_classes)


def _create_walk_forward_folds(
    n_samples: int,
    n_folds: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Create walk-forward (expanding window) cross-validation folds.

    Each fold uses all data up to a split point for training and the
    next chunk for validation. This respects temporal ordering, which
    is critical for sports data where time leakage must be avoided.

    Args:
        n_samples: Total number of samples.
        n_folds: Number of validation folds.

    Returns:
        List of (train_indices, val_indices) tuples.
    """
    fold_size = n_samples // (n_folds + 1)
    folds: list[tuple[np.ndarray, np.ndarray]] = []

    if fold_size == 0:
        return folds

    for fold_idx in range(n_folds):
        train_end = fold_size * (fold_idx + 1)
        val_start = train_end
        val_end = min(val_start + fold_size, n_samples)

        if val_start >= n_samples or val_end <= val_start:
            break

        train_idx = np.arange(train_end)
        val_idx = np.arange(val_start, val_end)
        folds.append((train_idx, val_idx))

    return folds


class CalibrationSelector:
    """Auto-select best calibration method via walk-forward cross-validation.

    Tries all configured methods, picks the one with lowest ECE on
    held-out validation folds. Designed for sports prediction where
    temporal ordering matters.

    Args:
        methods: List of method names to try. Defaults to all three:
            ``["temperature", "platt", "isotonic"]``.
    """

    def __init__(self, methods: list[str] | None = None) -> None:
        if methods is None:
            methods = ["temperature", "platt", "isotonic"]

        unknown = set(methods) - set(_METHOD_REGISTRY)
        if unknown:
            raise ValueError(
                f"Unknown calibration methods: {unknown}. "
                f"Available: {list(_METHOD_REGISTRY)}"
            )

        self.methods: list[str] = methods

    def select(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        n_folds: int = 3,
    ) -> tuple[str, CalibratorInstance]:
        """Select best calibrator via walk-forward cross-validation.

        Splits data chronologically into expanding training windows with
        held-out validation chunks. Fits each method on training data,
        measures ECE on validation data, and picks the method with lowest
        mean ECE across folds.

        After selection, refits the chosen method on all data.

        Args:
            y_true: Ground truth labels, shape (n,) or (n, k).
            y_prob: Predicted probabilities, shape (n,) or (n, k).
            n_folds: Number of walk-forward folds.

        Returns:
            Tuple of (method_name, fitted_calibrator). The calibrator
            is fitted on the full dataset.
        """
        y_true_arr = np.asarray(y_true, dtype=np.float64)
        y_prob_arr = np.asarray(y_prob, dtype=np.float64)

        folds = _create_walk_forward_folds(len(y_true_arr), n_folds)

        if len(folds) == 0:
            logger.warning(
                "calibration_selector_insufficient_data",
                n_samples=len(y_true_arr),
                n_folds=n_folds,
            )
            best_method = self.methods[0]
            calibrator = _METHOD_REGISTRY[best_method]()
            calibrator.fit(y_true_arr, y_prob_arr)
            return best_method, calibrator

        method_scores: dict[str, list[float]] = {m: [] for m in self.methods}

        for fold_idx, (train_idx, val_idx) in enumerate(folds):
            y_true_train = y_true_arr[train_idx]
            y_prob_train = y_prob_arr[train_idx]
            y_true_val = y_true_arr[val_idx]
            y_prob_val = y_prob_arr[val_idx]

            for method_name in self.methods:
                calibrator = _METHOD_REGISTRY[method_name]()
                try:
                    calibrator.fit(y_true_train, y_prob_train)
                    calibrated_val = calibrator.transform(y_prob_val)
                    ece = _compute_ece(y_true_val, calibrated_val)
                    method_scores[method_name].append(ece)
                except Exception:
                    logger.warning(
                        "calibration_fold_failed",
                        method=method_name,
                        fold=fold_idx,
                        exc_info=True,
                    )
                    method_scores[method_name].append(1.0)

        mean_eces = {
            m: float(np.mean(scores)) if scores else 1.0
            for m, scores in method_scores.items()
        }

        best_method = min(mean_eces, key=lambda m: mean_eces[m])

        logger.info(
            "calibration_selector_result",
            mean_eces=mean_eces,
            best_method=best_method,
            n_folds=len(folds),
        )

        final_calibrator = _METHOD_REGISTRY[best_method]()
        final_calibrator.fit(y_true_arr, y_prob_arr)

        return best_method, final_calibrator

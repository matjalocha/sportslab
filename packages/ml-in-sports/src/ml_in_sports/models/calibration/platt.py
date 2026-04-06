"""Platt scaling calibration via logistic regression on logits.

Fits a logistic regression model on the logits of a base classifier,
learning parameters A and B such that:

    calibrated = sigmoid(A * logit + B)

For multiclass, applies one-vs-rest: each class gets its own logistic
regression, and outputs are renormalized to sum to 1.

Reference: Platt (1999), "Probabilistic Outputs for Support Vector
Machines and Comparisons to Regularized Likelihood Methods".
"""

from __future__ import annotations

import numpy as np
import structlog
from sklearn.linear_model import LogisticRegression

logger = structlog.get_logger(__name__)

_EPSILON = 1e-15
_LOGIT_CLIP = 15.0


def _clip_probabilities(probs: np.ndarray) -> np.ndarray:
    """Clip probabilities away from 0 and 1 for numerical stability."""
    result: np.ndarray = np.clip(probs, _EPSILON, 1.0 - _EPSILON)
    return result


def _probs_to_logits(probs: np.ndarray) -> np.ndarray:
    """Convert probabilities to logits: log(p / (1-p))."""
    clipped = _clip_probabilities(probs)
    logits: np.ndarray = np.log(clipped / (1.0 - clipped))
    result: np.ndarray = np.clip(logits, -_LOGIT_CLIP, _LOGIT_CLIP)
    return result


class PlattScaler:
    """Platt scaling calibrator using logistic regression on logits.

    For binary classification, fits a single logistic regression.
    For multiclass, fits one-vs-rest logistic regressions and
    renormalizes outputs to sum to 1.

    Attributes:
        models: Fitted LogisticRegression instances (one per class for
            multiclass, one for binary).
    """

    def __init__(self) -> None:
        self.models: list[LogisticRegression] = []
        self._fitted: bool = False
        self._n_classes: int = 0

    def fit(self, y_true: np.ndarray, y_prob: np.ndarray) -> None:
        """Fit Platt scaling on validation data.

        Args:
            y_true: Ground truth labels. For binary: shape (n,) with values
                in {0, 1}. For multiclass: shape (n,) with integer class
                indices, or shape (n, k) one-hot encoded.
            y_prob: Predicted probabilities. For binary: shape (n,) or (n, 2).
                For multiclass: shape (n, k) where k >= 3.
        """
        y_true_arr = np.asarray(y_true, dtype=np.float64)
        y_prob_arr = np.asarray(y_prob, dtype=np.float64)

        is_binary = y_prob_arr.ndim == 1 or (y_prob_arr.ndim == 2 and y_prob_arr.shape[1] == 2)

        if is_binary:
            self._fit_binary(y_true_arr, y_prob_arr)
        else:
            self._fit_multiclass(y_true_arr, y_prob_arr)

        self._fitted = True
        logger.info(
            "platt_scaler_fitted",
            n_samples=len(y_true_arr),
            n_classes=self._n_classes,
        )

    def _fit_binary(self, y_true: np.ndarray, y_prob: np.ndarray) -> None:
        """Fit Platt scaling for binary classification."""
        self._n_classes = 2
        probs_positive = y_prob[:, 1] if y_prob.ndim == 2 else y_prob

        logits = _probs_to_logits(probs_positive).reshape(-1, 1)
        labels = y_true.ravel().astype(int)

        model = LogisticRegression(
            solver="lbfgs",
            max_iter=1000,
            C=1e10,  # near-zero regularization for pure Platt fit
        )
        model.fit(logits, labels)
        self.models = [model]

    def _fit_multiclass(self, y_true: np.ndarray, y_prob: np.ndarray) -> None:
        """Fit one-vs-rest Platt scaling for multiclass."""
        self._n_classes = y_prob.shape[1]

        labels_int = np.argmax(y_true, axis=1) if y_true.ndim == 2 else y_true.astype(int).ravel()

        self.models = []
        for class_idx in range(self._n_classes):
            binary_labels = (labels_int == class_idx).astype(int)
            logits = _probs_to_logits(y_prob[:, class_idx]).reshape(-1, 1)

            model = LogisticRegression(
                solver="lbfgs",
                max_iter=1000,
                C=1e10,
            )
            model.fit(logits, binary_labels)
            self.models.append(model)

    def transform(self, y_prob: np.ndarray) -> np.ndarray:
        """Apply fitted Platt scaling to new probabilities.

        Args:
            y_prob: Predicted probabilities, same format as fit input.

        Returns:
            Calibrated probabilities. Multiclass outputs are renormalized
            to sum to 1.

        Raises:
            RuntimeError: If transform is called before fit.
        """
        if not self._fitted:
            raise RuntimeError("PlattScaler must be fitted before transform.")

        y_prob_arr = np.asarray(y_prob, dtype=np.float64)
        is_binary = y_prob_arr.ndim == 1 or (y_prob_arr.ndim == 2 and y_prob_arr.shape[1] == 2)

        if is_binary:
            return self._transform_binary(y_prob_arr)
        return self._transform_multiclass(y_prob_arr)

    def _transform_binary(self, y_prob: np.ndarray) -> np.ndarray:
        """Apply Platt scaling to binary probabilities."""
        was_1d = y_prob.ndim == 1
        probs_positive = y_prob if was_1d else y_prob[:, 1]

        logits = _probs_to_logits(probs_positive).reshape(-1, 1)
        calibrated: np.ndarray = np.asarray(self.models[0].predict_proba(logits)[:, 1])

        if was_1d:
            return calibrated
        result: np.ndarray = np.column_stack([1.0 - calibrated, calibrated])
        return result

    def _transform_multiclass(self, y_prob: np.ndarray) -> np.ndarray:
        """Apply one-vs-rest Platt scaling and renormalize."""
        n_samples = y_prob.shape[0]
        calibrated = np.zeros((n_samples, self._n_classes), dtype=np.float64)

        for class_idx in range(self._n_classes):
            logits = _probs_to_logits(y_prob[:, class_idx]).reshape(-1, 1)
            calibrated[:, class_idx] = self.models[class_idx].predict_proba(logits)[:, 1]

        row_sums: np.ndarray = calibrated.sum(axis=1, keepdims=True)
        row_sums = np.maximum(row_sums, _EPSILON)
        normalized: np.ndarray = calibrated / row_sums

        return normalized

    def fit_transform(self, y_true: np.ndarray, y_prob: np.ndarray) -> np.ndarray:
        """Fit on validation data and return calibrated probabilities.

        Args:
            y_true: Ground truth labels.
            y_prob: Predicted probabilities.

        Returns:
            Calibrated probabilities.
        """
        self.fit(y_true, y_prob)
        return self.transform(y_prob)

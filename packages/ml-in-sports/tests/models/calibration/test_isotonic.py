"""Tests for IsotonicScaler calibration."""

from __future__ import annotations

import numpy as np
import pytest
from ml_in_sports.models.calibration.isotonic import IsotonicScaler


@pytest.fixture
def rng() -> np.random.Generator:
    """Seeded random generator for reproducibility."""
    return np.random.default_rng(42)


@pytest.fixture
def binary_well_calibrated(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic binary data where probabilities are already well-calibrated."""
    n = 500
    probs = rng.uniform(0.1, 0.9, size=n)
    labels = (rng.random(n) < probs).astype(float)
    return labels, probs


@pytest.fixture
def binary_overconfident(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic binary data with overconfident probabilities."""
    n = 1000
    true_probs = rng.uniform(0.2, 0.8, size=n)
    labels = (rng.random(n) < true_probs).astype(float)
    overconfident_probs = np.where(
        true_probs > 0.5,
        0.5 + (true_probs - 0.5) * 2.0,
        0.5 - (0.5 - true_probs) * 2.0,
    )
    overconfident_probs = np.clip(overconfident_probs, 0.01, 0.99)
    return labels, overconfident_probs


@pytest.fixture
def multiclass_1x2(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic 1X2 (home/draw/away) multiclass data."""
    n = 600
    raw = rng.dirichlet([2.0, 1.5, 1.5], size=n)
    labels = np.array([rng.choice(3, p=p) for p in raw])
    overconfident = raw**0.5
    overconfident = overconfident / overconfident.sum(axis=1, keepdims=True)
    return labels, overconfident


class TestIsotonicScalerBinary:
    """Tests for binary classification isotonic calibration."""

    def test_perfect_calibration_stays_close(
        self, binary_well_calibrated: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Well-calibrated probs should not be significantly distorted."""
        labels, probs = binary_well_calibrated
        scaler = IsotonicScaler()
        calibrated = scaler.fit_transform(labels, probs)

        # Isotonic should not shift well-calibrated data too much
        assert np.mean(np.abs(calibrated - probs)) < 0.15

    def test_output_valid_probabilities(
        self, binary_overconfident: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Output must be valid probabilities in [0, 1]."""
        labels, probs = binary_overconfident
        scaler = IsotonicScaler()
        calibrated = scaler.fit_transform(labels, probs)

        assert np.all(calibrated >= 0.0)
        assert np.all(calibrated <= 1.0)

    def test_fit_transform_equals_fit_then_transform(
        self, binary_overconfident: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """fit_transform should produce same result as fit + transform."""
        labels, probs = binary_overconfident

        scaler_a = IsotonicScaler()
        result_a = scaler_a.fit_transform(labels, probs)

        scaler_b = IsotonicScaler()
        scaler_b.fit(labels, probs)
        result_b = scaler_b.transform(probs)

        np.testing.assert_allclose(result_a, result_b)

    def test_2d_binary_input(
        self, binary_overconfident: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Should handle (n, 2) binary probability arrays."""
        labels, probs_1d = binary_overconfident
        probs_2d = np.column_stack([1 - probs_1d, probs_1d])

        scaler = IsotonicScaler()
        calibrated = scaler.fit_transform(labels, probs_2d)

        assert calibrated.shape == probs_2d.shape
        np.testing.assert_allclose(calibrated[:, 0] + calibrated[:, 1], 1.0, atol=1e-10)

    def test_transform_before_fit_raises(self) -> None:
        """Calling transform before fit should raise RuntimeError."""
        scaler = IsotonicScaler()
        with pytest.raises(RuntimeError, match="fitted before transform"):
            scaler.transform(np.array([0.5, 0.6]))

    def test_monotonicity(
        self, binary_overconfident: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Isotonic output should be monotone with respect to input."""
        labels, probs = binary_overconfident
        scaler = IsotonicScaler()
        scaler.fit(labels, probs)

        sorted_probs = np.sort(probs)
        calibrated_sorted = scaler.transform(sorted_probs)

        # Monotone non-decreasing
        diffs = np.diff(calibrated_sorted)
        assert np.all(diffs >= -1e-10)


class TestIsotonicScalerMulticlass:
    """Tests for multiclass (1X2) isotonic calibration."""

    def test_output_sums_to_one(
        self, multiclass_1x2: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Multiclass calibrated probabilities must sum to 1."""
        labels, probs = multiclass_1x2
        scaler = IsotonicScaler()
        calibrated = scaler.fit_transform(labels, probs)

        np.testing.assert_allclose(calibrated.sum(axis=1), 1.0, atol=1e-10)

    def test_output_shape_preserved(
        self, multiclass_1x2: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Output shape must match input shape."""
        labels, probs = multiclass_1x2
        scaler = IsotonicScaler()
        calibrated = scaler.fit_transform(labels, probs)

        assert calibrated.shape == probs.shape

    def test_output_valid_probabilities(
        self, multiclass_1x2: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """All outputs must be valid probabilities in [0, 1]."""
        labels, probs = multiclass_1x2
        scaler = IsotonicScaler()
        calibrated = scaler.fit_transform(labels, probs)

        assert np.all(calibrated >= 0.0)
        assert np.all(calibrated <= 1.0)

    def test_onehot_labels_accepted(
        self, multiclass_1x2: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """One-hot encoded labels should produce valid output."""
        labels_int, probs = multiclass_1x2
        labels_onehot = np.zeros((len(labels_int), 3))
        labels_onehot[np.arange(len(labels_int)), labels_int] = 1.0

        scaler = IsotonicScaler()
        calibrated = scaler.fit_transform(labels_onehot, probs)

        np.testing.assert_allclose(calibrated.sum(axis=1), 1.0, atol=1e-10)


class TestIsotonicScalerEdgeCases:
    """Edge case tests for IsotonicScaler."""

    def test_extreme_probabilities(self) -> None:
        """Probabilities at near-0 and near-1 should not cause NaN."""
        labels = np.array([0, 0, 1, 1, 0, 1, 0, 1, 0, 0])
        probs = np.array([0.001, 0.01, 0.99, 0.999, 0.05, 0.95, 0.1, 0.9, 0.02, 0.03])
        scaler = IsotonicScaler()
        calibrated = scaler.fit_transform(labels, probs)

        assert not np.any(np.isnan(calibrated))
        assert not np.any(np.isinf(calibrated))

    def test_small_sample(self) -> None:
        """Should work with few samples."""
        labels = np.array([0, 1, 1])
        probs = np.array([0.3, 0.8, 0.7])
        scaler = IsotonicScaler()
        calibrated = scaler.fit_transform(labels, probs)

        assert calibrated.shape == probs.shape
        assert np.all(calibrated >= 0.0)
        assert np.all(calibrated <= 1.0)

    def test_all_same_probability(self) -> None:
        """All samples have the same predicted probability."""
        labels = np.array([0, 1, 0, 1, 1])
        probs = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        scaler = IsotonicScaler()
        calibrated = scaler.fit_transform(labels, probs)

        assert not np.any(np.isnan(calibrated))

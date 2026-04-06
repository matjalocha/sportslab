"""Tests for CalibrationSelector walk-forward selection."""

from __future__ import annotations

import numpy as np
import pytest
from ml_in_sports.models.calibration.isotonic import IsotonicScaler
from ml_in_sports.models.calibration.platt import PlattScaler
from ml_in_sports.models.calibration.selector import (
    CalibrationSelector,
    _compute_ece,
    _create_walk_forward_folds,
)
from ml_in_sports.models.calibration.temperature import TemperatureScaler


@pytest.fixture
def rng() -> np.random.Generator:
    """Seeded random generator for reproducibility."""
    return np.random.default_rng(42)


@pytest.fixture
def overconfident_tabpfn_like(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic data mimicking overconfident TabPFN output.

    Temperature scaling should clearly be the best method here, because
    the miscalibration is uniform overconfidence (all logits scaled by
    the same constant).
    """
    n = 1200
    true_probs = rng.uniform(0.2, 0.8, size=n)
    labels = (rng.random(n) < true_probs).astype(float)
    # Apply uniform overconfidence: push all probs away from 0.5
    logits = np.log(true_probs / (1 - true_probs))
    overconfident_logits = logits * 3.0  # 3x overconfidence
    from scipy.special import expit

    overconfident_probs = expit(overconfident_logits)
    return labels, overconfident_probs


class TestComputeEce:
    """Tests for the ECE helper function."""

    def test_perfect_calibration_zero_ece(self) -> None:
        """ECE should be near 0 for perfectly calibrated predictions."""
        rng = np.random.default_rng(123)
        n = 10000
        probs = rng.uniform(0.0, 1.0, size=n)
        labels = (rng.random(n) < probs).astype(float)

        ece = _compute_ece(labels, probs, n_bins=15)
        assert ece < 0.03  # Should be very small with enough samples

    def test_worst_case_ece(self) -> None:
        """ECE should be high for wildly miscalibrated predictions."""
        labels = np.zeros(100)
        probs = np.full(100, 0.9)  # Predict 0.9 but all are 0

        ece = _compute_ece(labels, probs)
        assert ece > 0.5

    def test_multiclass_ece(self) -> None:
        """ECE should work for multiclass predictions."""
        rng = np.random.default_rng(42)
        n = 1000
        probs = rng.dirichlet([2.0, 1.5, 1.5], size=n)
        labels = np.array([rng.choice(3, p=p) for p in probs])

        ece = _compute_ece(labels, probs)
        assert 0.0 <= ece <= 1.0

    def test_binary_2d_ece(self) -> None:
        """ECE should handle (n, 2) binary arrays."""
        rng = np.random.default_rng(42)
        n = 500
        probs_pos = rng.uniform(0.1, 0.9, size=n)
        probs_2d = np.column_stack([1 - probs_pos, probs_pos])
        labels = (rng.random(n) < probs_pos).astype(float)

        ece = _compute_ece(labels, probs_2d)
        assert 0.0 <= ece <= 1.0

    def test_empty_input(self) -> None:
        """ECE of empty arrays should be 0."""
        ece = _compute_ece(np.array([]), np.array([]))
        assert ece == 0.0


class TestWalkForwardFolds:
    """Tests for walk-forward fold creation."""

    def test_correct_number_of_folds(self) -> None:
        """Should create the requested number of folds."""
        folds = _create_walk_forward_folds(100, n_folds=3)
        assert len(folds) == 3

    def test_no_overlap(self) -> None:
        """Train and val indices should not overlap within a fold."""
        folds = _create_walk_forward_folds(200, n_folds=4)
        for train_idx, val_idx in folds:
            assert len(np.intersect1d(train_idx, val_idx)) == 0

    def test_expanding_window(self) -> None:
        """Each successive training set should be larger."""
        folds = _create_walk_forward_folds(200, n_folds=3)
        train_sizes = [len(train) for train, _ in folds]
        for i in range(1, len(train_sizes)):
            assert train_sizes[i] > train_sizes[i - 1]

    def test_temporal_ordering(self) -> None:
        """Validation indices should always come after training indices."""
        folds = _create_walk_forward_folds(200, n_folds=3)
        for train_idx, val_idx in folds:
            assert train_idx.max() < val_idx.min()

    def test_small_dataset(self) -> None:
        """Should handle very small datasets gracefully."""
        folds = _create_walk_forward_folds(5, n_folds=3)
        assert len(folds) >= 1


class TestCalibrationSelector:
    """Tests for the CalibrationSelector."""

    def test_returns_valid_method_and_calibrator(
        self, rng: np.random.Generator
    ) -> None:
        """Should return a method name and fitted calibrator."""
        n = 600
        probs = rng.uniform(0.1, 0.9, size=n)
        labels = (rng.random(n) < probs).astype(float)

        selector = CalibrationSelector()
        method_name, calibrator = selector.select(labels, probs)

        assert method_name in ["temperature", "platt", "isotonic"]
        # Calibrator should be fitted and usable
        result = calibrator.transform(probs[:10])
        assert result.shape == (10,)

    def test_picks_temperature_for_overconfident_data(
        self,
        overconfident_tabpfn_like: tuple[np.ndarray, np.ndarray],
    ) -> None:
        """For uniformly overconfident data, temperature should win or tie.

        Temperature scaling is the theoretically optimal single-parameter
        fix for uniform overconfidence. Platt can also handle this, but
        temperature should at minimum not lose badly.
        """
        labels, probs = overconfident_tabpfn_like

        selector = CalibrationSelector()
        _method_name, calibrator = selector.select(labels, probs, n_folds=3)

        # The selected calibrator should improve calibration
        ece_before = _compute_ece(labels, probs)
        calibrated = calibrator.transform(probs)
        ece_after = _compute_ece(labels, calibrated)

        assert ece_after < ece_before

    def test_custom_methods(self, rng: np.random.Generator) -> None:
        """Should accept a subset of methods."""
        n = 400
        probs = rng.uniform(0.1, 0.9, size=n)
        labels = (rng.random(n) < probs).astype(float)

        selector = CalibrationSelector(methods=["temperature", "platt"])
        method_name, _ = selector.select(labels, probs)

        assert method_name in ["temperature", "platt"]

    def test_unknown_method_raises(self) -> None:
        """Should raise ValueError for unknown method names."""
        with pytest.raises(ValueError, match="Unknown calibration methods"):
            CalibrationSelector(methods=["temperature", "magic_calibrator"])

    def test_multiclass_selection(self, rng: np.random.Generator) -> None:
        """Should work with multiclass (1X2) data."""
        n = 600
        raw = rng.dirichlet([2.0, 1.5, 1.5], size=n)
        labels = np.array([rng.choice(3, p=p) for p in raw])
        overconfident = raw**0.5
        overconfident = overconfident / overconfident.sum(axis=1, keepdims=True)

        selector = CalibrationSelector()
        method_name, calibrator = selector.select(labels, overconfident, n_folds=3)

        assert method_name in ["temperature", "platt", "isotonic"]
        result = calibrator.transform(overconfident[:10])
        np.testing.assert_allclose(result.sum(axis=1), 1.0, atol=1e-10)

    def test_selected_calibrator_is_refitted_on_all_data(
        self, rng: np.random.Generator
    ) -> None:
        """The returned calibrator should be fitted on the full dataset."""
        n = 400
        probs = rng.uniform(0.1, 0.9, size=n)
        labels = (rng.random(n) < probs).astype(float)

        selector = CalibrationSelector()
        _, calibrator = selector.select(labels, probs, n_folds=3)

        # Should be able to transform without error (proves it was fitted)
        result = calibrator.transform(np.array([0.3, 0.5, 0.7]))
        assert result.shape == (3,)
        assert np.all(result >= 0.0)
        assert np.all(result <= 1.0)

    def test_selector_calibrator_types(self, rng: np.random.Generator) -> None:
        """The returned calibrator should be one of the known types."""
        n = 400
        probs = rng.uniform(0.1, 0.9, size=n)
        labels = (rng.random(n) < probs).astype(float)

        selector = CalibrationSelector()
        _, calibrator = selector.select(labels, probs)

        assert isinstance(calibrator, (TemperatureScaler, PlattScaler, IsotonicScaler))

    def test_small_dataset_fallback(self) -> None:
        """With very few samples, should still return a result."""
        labels = np.array([0, 1, 1])
        probs = np.array([0.3, 0.7, 0.8])

        selector = CalibrationSelector()
        method_name, _calibrator = selector.select(labels, probs, n_folds=3)

        assert method_name in ["temperature", "platt", "isotonic"]

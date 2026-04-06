"""Tests for feature drift detection using Population Stability Index."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.models.monitoring.drift import (
    compute_feature_drift,
    compute_psi,
    detect_drift_alerts,
)


class TestComputePsi:
    """Tests for compute_psi."""

    def test_identical_distributions_returns_near_zero(self) -> None:
        """Same data as reference and current gives PSI approximately 0."""
        rng = np.random.default_rng(42)
        data = rng.normal(0, 1, size=5000)
        psi = compute_psi(data, data, n_bins=10)
        assert psi == pytest.approx(0.0, abs=1e-6)

    def test_same_distribution_different_samples_low_psi(self) -> None:
        """Two independent draws from the same distribution give low PSI."""
        rng = np.random.default_rng(42)
        reference = rng.normal(0, 1, size=5000)
        current = rng.normal(0, 1, size=5000)
        psi = compute_psi(reference, current, n_bins=10)
        assert psi < 0.1

    def test_shifted_distribution_moderate_psi(self) -> None:
        """A moderate mean shift produces noticeable PSI."""
        rng = np.random.default_rng(42)
        reference = rng.normal(0, 1, size=5000)
        current = rng.normal(0.5, 1, size=5000)
        psi = compute_psi(reference, current, n_bins=10)
        assert psi > 0.0

    def test_large_shift_high_psi(self) -> None:
        """A 3-sigma mean shift produces PSI > 0.25 (significant)."""
        rng = np.random.default_rng(42)
        reference = rng.normal(0, 1, size=5000)
        current = rng.normal(3, 1, size=5000)
        psi = compute_psi(reference, current, n_bins=10)
        assert psi > 0.25

    def test_psi_is_non_negative(self) -> None:
        """PSI is always >= 0 by construction."""
        rng = np.random.default_rng(123)
        reference = rng.uniform(0, 10, size=1000)
        current = rng.uniform(2, 8, size=1000)
        psi = compute_psi(reference, current, n_bins=10)
        assert psi >= 0.0

    def test_single_value_reference_same_current_returns_zero(self) -> None:
        """Constant reference and constant current at same value gives 0."""
        reference = np.array([5.0, 5.0, 5.0, 5.0])
        current = np.array([5.0, 5.0, 5.0])
        psi = compute_psi(reference, current, n_bins=10)
        assert psi == 0.0

    def test_single_value_reference_different_current_returns_inf(self) -> None:
        """Constant reference but different current gives inf."""
        reference = np.array([5.0, 5.0, 5.0])
        current = np.array([7.0, 7.0, 7.0])
        psi = compute_psi(reference, current, n_bins=10)
        assert psi == float("inf")

    def test_empty_reference_raises(self) -> None:
        """Empty reference array raises ValueError."""
        with pytest.raises(ValueError, match="reference must not be empty"):
            compute_psi(np.array([]), np.array([1.0, 2.0]))

    def test_empty_current_raises(self) -> None:
        """Empty current array raises ValueError."""
        with pytest.raises(ValueError, match="current must not be empty"):
            compute_psi(np.array([1.0, 2.0]), np.array([]))

    def test_n_bins_too_small_raises(self) -> None:
        """n_bins < 2 raises ValueError."""
        with pytest.raises(ValueError, match="n_bins must be >= 2"):
            compute_psi(np.array([1.0, 2.0]), np.array([1.0, 2.0]), n_bins=1)

    def test_different_sample_sizes(self) -> None:
        """PSI works with reference and current of different lengths."""
        rng = np.random.default_rng(42)
        reference = rng.normal(0, 1, size=10000)
        current = rng.normal(0, 1, size=500)
        psi = compute_psi(reference, current, n_bins=10)
        assert psi < 0.1


class TestComputeFeatureDrift:
    """Tests for compute_feature_drift."""

    def test_stable_features_all_ok(self) -> None:
        """Features drawn from the same distribution are classified ok."""
        rng = np.random.default_rng(42)
        n = 3000
        ref_df = pd.DataFrame({
            "feat_a": rng.normal(0, 1, n),
            "feat_b": rng.uniform(0, 10, n),
        })
        cur_df = pd.DataFrame({
            "feat_a": rng.normal(0, 1, n),
            "feat_b": rng.uniform(0, 10, n),
        })
        result = compute_feature_drift(ref_df, cur_df)
        assert len(result) == 2
        assert (result["status"] == "ok").all()

    def test_mixed_drift_some_alert(self) -> None:
        """One stable feature and one heavily drifted feature."""
        rng = np.random.default_rng(42)
        n = 3000
        ref_df = pd.DataFrame({
            "stable": rng.normal(0, 1, n),
            "drifted": rng.normal(0, 1, n),
        })
        cur_df = pd.DataFrame({
            "stable": rng.normal(0, 1, n),
            "drifted": rng.normal(5, 1, n),
        })
        result = compute_feature_drift(ref_df, cur_df)
        drifted_row = result[result["feature"] == "drifted"].iloc[0]
        stable_row = result[result["feature"] == "stable"].iloc[0]
        assert drifted_row["status"] == "alert"
        assert stable_row["status"] == "ok"

    def test_features_arg_filters_columns(self) -> None:
        """Only specified features are checked."""
        rng = np.random.default_rng(42)
        n = 500
        ref_df = pd.DataFrame({
            "a": rng.normal(0, 1, n),
            "b": rng.normal(0, 1, n),
            "c": rng.normal(0, 1, n),
        })
        cur_df = pd.DataFrame({
            "a": rng.normal(0, 1, n),
            "b": rng.normal(0, 1, n),
            "c": rng.normal(0, 1, n),
        })
        result = compute_feature_drift(ref_df, cur_df, features=["a", "c"])
        assert list(result["feature"]) == ["a", "c"] or set(result["feature"]) == {"a", "c"}
        assert len(result) == 2

    def test_auto_selects_numeric_columns(self) -> None:
        """Without features arg, only numeric columns are selected."""
        rng = np.random.default_rng(42)
        n = 500
        ref_df = pd.DataFrame({
            "num_feat": rng.normal(0, 1, n),
            "str_feat": ["cat"] * n,
        })
        cur_df = pd.DataFrame({
            "num_feat": rng.normal(0, 1, n),
            "str_feat": ["dog"] * n,
        })
        result = compute_feature_drift(ref_df, cur_df)
        assert len(result) == 1
        assert result.iloc[0]["feature"] == "num_feat"

    def test_sorted_by_psi_descending(self) -> None:
        """Result is sorted by PSI descending."""
        rng = np.random.default_rng(42)
        n = 3000
        ref_df = pd.DataFrame({
            "low_drift": rng.normal(0, 1, n),
            "high_drift": rng.normal(0, 1, n),
        })
        cur_df = pd.DataFrame({
            "low_drift": rng.normal(0.1, 1, n),
            "high_drift": rng.normal(5, 1, n),
        })
        result = compute_feature_drift(ref_df, cur_df)
        assert result.iloc[0]["feature"] == "high_drift"

    def test_nan_values_are_dropped(self) -> None:
        """NaN values in features are dropped before PSI computation."""
        rng = np.random.default_rng(42)
        ref_data = rng.normal(0, 1, 500)
        cur_data = rng.normal(0, 1, 500)
        cur_data_with_nan = np.concatenate([cur_data, [np.nan] * 50])

        ref_df = pd.DataFrame({"feat": ref_data})
        cur_df = pd.DataFrame({"feat": cur_data_with_nan})

        result = compute_feature_drift(ref_df, cur_df)
        assert len(result) == 1
        assert result.iloc[0]["status"] == "ok"


class TestDetectDriftAlerts:
    """Tests for detect_drift_alerts."""

    def test_no_alerts_when_all_ok(self) -> None:
        """No alerts when all features are below warning threshold."""
        drift_results = pd.DataFrame({
            "feature": ["a", "b", "c"],
            "psi": [0.01, 0.05, 0.09],
            "status": ["ok", "ok", "ok"],
        })
        alerts = detect_drift_alerts(drift_results)
        assert len(alerts) == 0

    def test_warning_severity(self) -> None:
        """PSI between warning and alert threshold gives warning severity."""
        drift_results = pd.DataFrame({
            "feature": ["a", "b"],
            "psi": [0.15, 0.05],
            "status": ["warning", "ok"],
        })
        alerts = detect_drift_alerts(drift_results)
        assert len(alerts) == 1
        assert alerts[0]["feature"] == "a"
        assert alerts[0]["severity"] == "warning"

    def test_alert_severity(self) -> None:
        """PSI above alert threshold gives alert severity."""
        drift_results = pd.DataFrame({
            "feature": ["x"],
            "psi": [0.50],
            "status": ["alert"],
        })
        alerts = detect_drift_alerts(drift_results)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "alert"

    def test_mixed_severities_sorted_by_psi(self) -> None:
        """Multiple alerts sorted by PSI descending."""
        drift_results = pd.DataFrame({
            "feature": ["low", "high", "mid"],
            "psi": [0.12, 0.50, 0.20],
            "status": ["warning", "alert", "warning"],
        })
        alerts = detect_drift_alerts(drift_results)
        assert len(alerts) == 3
        assert alerts[0]["feature"] == "high"
        assert alerts[0]["severity"] == "alert"
        assert alerts[1]["feature"] == "mid"
        assert alerts[1]["severity"] == "warning"
        assert alerts[2]["feature"] == "low"
        assert alerts[2]["severity"] == "warning"

    def test_custom_thresholds(self) -> None:
        """Custom thresholds change severity classification."""
        drift_results = pd.DataFrame({
            "feature": ["a"],
            "psi": [0.08],
            "status": ["ok"],
        })
        # Default thresholds: no alert
        assert len(detect_drift_alerts(drift_results)) == 0
        # Lower warning threshold: now it's a warning
        alerts = detect_drift_alerts(drift_results, warning_threshold=0.05)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "warning"

    def test_empty_dataframe(self) -> None:
        """Empty drift results produce no alerts."""
        drift_results = pd.DataFrame(columns=["feature", "psi", "status"])
        alerts = detect_drift_alerts(drift_results)
        assert len(alerts) == 0

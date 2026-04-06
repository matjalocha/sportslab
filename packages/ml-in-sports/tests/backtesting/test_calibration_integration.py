"""Integration tests for calibration wired into the walk-forward runner.

Verifies that CalibrationSelector is called during backtest runs,
that the chosen method is recorded in FoldResult, and that edge
cases (disabled calibration, small cal set) fall back gracefully.
"""

from __future__ import annotations

import numpy as np
import pytest
from ml_in_sports.backtesting.config import ExperimentConfig, ModelConfig
from ml_in_sports.backtesting.report.generator import build_report_data
from ml_in_sports.backtesting.report.terminal import render_terminal_string
from ml_in_sports.backtesting.runner import (
    BacktestResult,
    WalkForwardRunner,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def calibrated_config() -> ExperimentConfig:
    """Config with calibration enabled (default methods)."""
    return ExperimentConfig(
        name="Calibration Test",
        data={
            "leagues": ["ENG-Premier League"],
            "seasons": ["2122", "2223", "2324", "2425"],
            "markets": ["1x2"],
        },
        models=[ModelConfig(name="DummyModel", type="lightgbm")],
        calibration={"methods": ["temperature", "platt", "isotonic"]},
        evaluation={"walk_forward": {"train_seasons": 2, "test_seasons": 1}},
    )


@pytest.fixture
def no_calibration_config() -> ExperimentConfig:
    """Config with calibration explicitly disabled (empty methods)."""
    return ExperimentConfig(
        name="No Calibration Test",
        data={
            "leagues": ["ENG-Premier League"],
            "seasons": ["2122", "2223", "2324", "2425"],
            "markets": ["1x2"],
        },
        models=[ModelConfig(name="DummyModel", type="lightgbm")],
        calibration={"methods": []},
        evaluation={"walk_forward": {"train_seasons": 2, "test_seasons": 1}},
    )


@pytest.fixture
def small_data_config() -> ExperimentConfig:
    """Config that will produce a very small calibration set.

    With only 2 seasons for training and 200 matches/season, the cal set
    is 20% of 400 = 80 samples. This exceeds the 50-sample minimum so
    calibration should still run. We use this as a baseline.
    """
    return ExperimentConfig(
        name="Small Data Test",
        data={
            "leagues": ["ENG-Premier League"],
            "seasons": ["2122", "2223", "2324", "2425"],
            "markets": ["1x2"],
        },
        models=[ModelConfig(name="DummyModel", type="lightgbm")],
        calibration={"methods": ["temperature"]},
        evaluation={"walk_forward": {"train_seasons": 2, "test_seasons": 1}},
    )


@pytest.fixture
def multi_model_calibrated_config() -> ExperimentConfig:
    """Config with multiple models and calibration enabled."""
    return ExperimentConfig(
        name="Multi Model Calibration",
        data={
            "leagues": ["ENG-Premier League", "ESP-La Liga"],
            "seasons": ["2122", "2223", "2324", "2425"],
            "markets": ["1x2"],
        },
        models=[
            ModelConfig(name="ModelA", type="lightgbm"),
            ModelConfig(name="ModelB", type="xgboost"),
        ],
        calibration={"methods": ["temperature", "platt", "isotonic"]},
        evaluation={"walk_forward": {"train_seasons": 2, "test_seasons": 1}},
    )


# ---------------------------------------------------------------------------
# Tests: calibration applied in synthetic run
# ---------------------------------------------------------------------------


class TestCalibrationAppliedInSyntheticRun:
    """Verify calibration is applied and recorded during synthetic runs."""

    def test_calibration_method_recorded_in_fold_result(
        self,
        calibrated_config: ExperimentConfig,
    ) -> None:
        """Each fold result has a non-None calibration_method when enabled."""
        runner = WalkForwardRunner(calibrated_config)
        result = runner.run_synthetic(seed=42)

        assert len(result.fold_results) > 0
        for fold in result.fold_results:
            assert fold.calibration_method is not None, (
                f"Fold {fold.fold_idx} model {fold.model_name} "
                f"has calibration_method=None despite calibration being enabled"
            )

    def test_calibration_method_is_valid_name(
        self,
        calibrated_config: ExperimentConfig,
    ) -> None:
        """Calibration method is one of the configured methods."""
        runner = WalkForwardRunner(calibrated_config)
        result = runner.run_synthetic(seed=42)

        valid_methods = {"temperature", "platt", "isotonic"}
        for fold in result.fold_results:
            assert fold.calibration_method in valid_methods, (
                f"Unexpected calibration method: {fold.calibration_method}"
            )

    def test_predictions_are_valid_probabilities_after_calibration(
        self,
        calibrated_config: ExperimentConfig,
    ) -> None:
        """Calibrated predictions are still valid probability distributions."""
        runner = WalkForwardRunner(calibrated_config)
        result = runner.run_synthetic(seed=42)

        for fold in result.fold_results:
            assert fold.predictions.min() >= 0.0, "Negative probability detected"
            assert fold.predictions.max() <= 1.0, "Probability > 1 detected"
            np.testing.assert_allclose(
                fold.predictions.sum(axis=1),
                1.0,
                atol=1e-6,
                err_msg="Calibrated probabilities do not sum to 1",
            )

    def test_multi_model_each_has_calibration(
        self,
        multi_model_calibrated_config: ExperimentConfig,
    ) -> None:
        """Each model in a multi-model config gets calibrated independently."""
        runner = WalkForwardRunner(multi_model_calibrated_config)
        result = runner.run_synthetic(seed=42)

        models_with_cal = {
            fold.model_name for fold in result.fold_results if fold.calibration_method is not None
        }
        assert "ModelA" in models_with_cal
        assert "ModelB" in models_with_cal


# ---------------------------------------------------------------------------
# Tests: calibration disabled fallback
# ---------------------------------------------------------------------------


class TestCalibrationDisabledFallback:
    """Verify that calibration is skipped when methods list is empty."""

    def test_no_calibration_method_when_disabled(
        self,
        no_calibration_config: ExperimentConfig,
    ) -> None:
        """All fold results have calibration_method=None when disabled."""
        runner = WalkForwardRunner(no_calibration_config)
        result = runner.run_synthetic(seed=42)

        assert len(result.fold_results) > 0
        for fold in result.fold_results:
            assert fold.calibration_method is None, (
                f"Expected None calibration method but got {fold.calibration_method}"
            )

    def test_still_produces_valid_results_without_calibration(
        self,
        no_calibration_config: ExperimentConfig,
    ) -> None:
        """Runner produces valid BacktestResult even without calibration."""
        runner = WalkForwardRunner(no_calibration_config)
        result = runner.run_synthetic(seed=42)

        assert isinstance(result, BacktestResult)
        assert len(result.fold_results) > 0
        assert len(result.aggregate_metrics) > 0


# ---------------------------------------------------------------------------
# Tests: small calibration set fallback
# ---------------------------------------------------------------------------


class TestSmallCalibrationSetFallback:
    """Verify behavior when calibration set is too small."""

    def test_skips_calibration_when_cal_set_below_minimum(self) -> None:
        """Calibration is skipped when fewer than 50 samples in cal set.

        We configure a single short season so that 20% of the training
        data falls below the 50-sample threshold.
        """
        # With 1 season of 200 matches as train, cal_set = 40 (20% of 200)
        # That's below the _MIN_CALIBRATION_SAMPLES = 50
        config = ExperimentConfig(
            name="Tiny Cal Set",
            data={
                "leagues": ["ENG-Premier League"],
                "seasons": ["2122", "2223", "2324"],
                "markets": ["1x2"],
            },
            models=[ModelConfig(name="DummyModel", type="lightgbm")],
            calibration={"methods": ["temperature"]},
            evaluation={"walk_forward": {"train_seasons": 1, "test_seasons": 1}},
        )
        runner = WalkForwardRunner(config)
        result = runner.run_synthetic(seed=42)

        assert len(result.fold_results) > 0
        for fold in result.fold_results:
            assert fold.calibration_method is None, (
                "Calibration should be skipped when cal set is < 50 samples"
            )


# ---------------------------------------------------------------------------
# Tests: ECE behavior after calibration
# ---------------------------------------------------------------------------


class TestCalibrationEceEffect:
    """Verify calibration does not degrade ECE catastrophically."""

    def test_ece_metric_present_after_calibration(
        self,
        calibrated_config: ExperimentConfig,
    ) -> None:
        """ECE metric is still computed and finite after calibration."""
        runner = WalkForwardRunner(calibrated_config)
        result = runner.run_synthetic(seed=42)

        for fold in result.fold_results:
            assert "ece" in fold.metrics
            assert np.isfinite(fold.metrics["ece"]), f"ECE is not finite: {fold.metrics['ece']}"

    def test_ece_in_reasonable_range_after_calibration(
        self,
        calibrated_config: ExperimentConfig,
    ) -> None:
        """ECE remains in [0, 1] after calibration."""
        runner = WalkForwardRunner(calibrated_config)
        result = runner.run_synthetic(seed=42)

        for fold in result.fold_results:
            ece = fold.metrics["ece"]
            assert 0.0 <= ece <= 1.0, f"ECE out of range: {ece}"


# ---------------------------------------------------------------------------
# Tests: calibration method in terminal report
# ---------------------------------------------------------------------------


class TestCalibrationInTerminalReport:
    """Verify calibration info appears in terminal report output."""

    def test_terminal_report_shows_calibration_section(
        self,
        calibrated_config: ExperimentConfig,
    ) -> None:
        """Terminal report includes CALIBRATION section when enabled."""
        runner = WalkForwardRunner(calibrated_config)
        result = runner.run_synthetic(seed=42)
        report_data = build_report_data(result)
        output = render_terminal_string(report_data, backtest_result=result)

        assert "CALIBRATION" in output

    def test_terminal_report_shows_method_name(
        self,
        calibrated_config: ExperimentConfig,
    ) -> None:
        """Terminal report includes the name of the selected calibration method."""
        runner = WalkForwardRunner(calibrated_config)
        result = runner.run_synthetic(seed=42)
        report_data = build_report_data(result)
        output = render_terminal_string(report_data, backtest_result=result)

        # At least one of the method names should appear
        method_names = {"temperature", "platt", "isotonic"}
        found = any(name in output for name in method_names)
        assert found, f"No calibration method name found in terminal output:\n{output}"

    def test_terminal_report_no_calibration_section_when_disabled(
        self,
        no_calibration_config: ExperimentConfig,
    ) -> None:
        """Terminal report omits CALIBRATION section when disabled."""
        runner = WalkForwardRunner(no_calibration_config)
        result = runner.run_synthetic(seed=42)
        report_data = build_report_data(result)
        output = render_terminal_string(report_data, backtest_result=result)

        assert "CALIBRATION" not in output

    def test_terminal_report_backward_compatible_without_backtest_result(
        self,
        calibrated_config: ExperimentConfig,
    ) -> None:
        """Terminal report works without backtest_result (backward compat)."""
        runner = WalkForwardRunner(calibrated_config)
        result = runner.run_synthetic(seed=42)
        report_data = build_report_data(result)

        # Call without backtest_result (old API)
        output = render_terminal_string(report_data)
        assert "HERO METRICS" in output
        assert "CALIBRATION" not in output

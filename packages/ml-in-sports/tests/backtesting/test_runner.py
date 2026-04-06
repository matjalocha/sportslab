"""Tests for the walk-forward backtest runner and report generation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from ml_in_sports.backtesting.config import ExperimentConfig, ModelConfig
from ml_in_sports.backtesting.models import DummyModel, ModelRegistry
from ml_in_sports.backtesting.report.generator import (
    ReportData,
    build_report_data,
)
from ml_in_sports.backtesting.report.html import render_html_report
from ml_in_sports.backtesting.report.terminal import render_terminal_string
from ml_in_sports.backtesting.runner import (
    BacktestResult,
    WalkForwardRunner,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_config() -> ExperimentConfig:
    """Minimal experiment config with 4 seasons and 1 dummy model."""
    return ExperimentConfig(
        name="Test Experiment",
        data={
            "leagues": ["ENG-Premier League"],
            "seasons": ["2122", "2223", "2324", "2425"],
            "markets": ["1x2"],
        },
        models=[ModelConfig(name="DummyModel", type="lightgbm")],
        evaluation={"walk_forward": {"train_seasons": 2, "test_seasons": 1}},
    )


@pytest.fixture
def multi_model_config() -> ExperimentConfig:
    """Config with multiple models for comparison testing."""
    return ExperimentConfig(
        name="Multi Model Test",
        data={
            "leagues": ["ENG-Premier League", "ESP-La Liga"],
            "seasons": ["2122", "2223", "2324", "2425"],
            "markets": ["1x2"],
        },
        models=[
            ModelConfig(name="ModelA", type="lightgbm"),
            ModelConfig(name="ModelB", type="xgboost"),
        ],
        evaluation={"walk_forward": {"train_seasons": 2, "test_seasons": 1}},
    )


# ---------------------------------------------------------------------------
# DummyModel tests
# ---------------------------------------------------------------------------


class TestDummyModel:
    """Tests for the DummyModel used in synthetic testing."""

    def test_predict_proba_shape(self) -> None:
        """Predictions have correct shape (n_samples, n_classes)."""
        model = DummyModel(model_name="test", seed=0)
        features = np.random.default_rng(0).standard_normal((50, 10))
        labels = np.array([0, 1, 2] * 16 + [0, 1])
        model.fit(features, labels)
        preds = model.predict_proba(features)
        assert preds.shape == (50, 3)

    def test_predict_proba_sums_to_one(self) -> None:
        """Each row of predictions sums to 1.0."""
        model = DummyModel(seed=1)
        features = np.ones((20, 5))
        preds = model.predict_proba(features)
        np.testing.assert_allclose(preds.sum(axis=1), 1.0, atol=1e-10)

    def test_reproducibility(self) -> None:
        """Same seed produces identical predictions."""
        features = np.ones((10, 3))
        model_a = DummyModel(seed=42)
        model_b = DummyModel(seed=42)
        np.testing.assert_array_equal(
            model_a.predict_proba(features),
            model_b.predict_proba(features),
        )

    def test_name_property(self) -> None:
        """Model name is accessible via property."""
        model = DummyModel(model_name="TestModel")
        assert model.name == "TestModel"


# ---------------------------------------------------------------------------
# ModelRegistry tests
# ---------------------------------------------------------------------------


class TestModelRegistry:
    """Tests for the model registry."""

    def test_dummy_registered(self) -> None:
        """DummyModel is pre-registered under 'dummy'."""
        assert "dummy" in ModelRegistry.available()

    def test_create_dummy(self) -> None:
        """Can create a DummyModel via registry."""
        model = ModelRegistry.create("dummy", model_name="RegistryTest")
        assert model.name == "RegistryTest"

    def test_create_unknown_raises(self) -> None:
        """Creating an unregistered model raises KeyError."""
        with pytest.raises(KeyError, match="not registered"):
            ModelRegistry.create("nonexistent_model_type")


# ---------------------------------------------------------------------------
# WalkForwardRunner tests
# ---------------------------------------------------------------------------


class TestWalkForwardRunner:
    """Tests for the walk-forward backtest runner."""

    def test_synthetic_returns_backtest_result(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Synthetic run returns a BacktestResult dataclass."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        assert isinstance(result, BacktestResult)

    def test_synthetic_has_fold_results(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Synthetic run produces non-empty fold results."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        assert len(result.fold_results) > 0

    def test_fold_count_matches_seasons(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Number of folds = n_seasons - train_seasons."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        n_seasons = len(minimal_config.data.seasons)
        train_size = minimal_config.evaluation.walk_forward.train_seasons
        expected_folds = n_seasons - train_size
        unique_folds = {fr.fold_idx for fr in result.fold_results}
        assert len(unique_folds) == expected_folds

    def test_fold_train_test_seasons_correct(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Each fold has correct train and test season counts."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        train_size = minimal_config.evaluation.walk_forward.train_seasons
        test_size = minimal_config.evaluation.walk_forward.test_seasons
        for fr in result.fold_results:
            assert len(fr.train_seasons) == train_size
            assert len(fr.test_seasons) == test_size

    def test_fold_no_train_test_overlap(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Train and test seasons never overlap within a fold."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        for fr in result.fold_results:
            assert set(fr.train_seasons).isdisjoint(set(fr.test_seasons))

    def test_aggregate_metrics_populated(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Aggregate metrics are computed for each model."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        assert len(result.aggregate_metrics) > 0
        for _model_name, metrics in result.aggregate_metrics.items():
            assert "log_loss" in metrics
            assert "ece" in metrics

    def test_multi_model_results(
        self,
        multi_model_config: ExperimentConfig,
    ) -> None:
        """Multiple models produce separate fold results."""
        runner = WalkForwardRunner(multi_model_config)
        result = runner.run_synthetic(seed=42)
        model_names = {fr.model_name for fr in result.fold_results}
        assert "ModelA" in model_names
        assert "ModelB" in model_names

    def test_predictions_valid_probabilities(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """All predictions are valid probability distributions."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        for fr in result.fold_results:
            assert fr.predictions.min() >= 0.0
            assert fr.predictions.max() <= 1.0
            np.testing.assert_allclose(
                fr.predictions.sum(axis=1),
                1.0,
                atol=1e-10,
            )

    def test_duration_positive(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Backtest duration is a positive number."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        assert result.duration_seconds > 0

    def test_generated_at_populated(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Generated-at timestamp is set."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        assert result.generated_at is not None

    def test_insufficient_seasons_returns_empty(self) -> None:
        """Config with too few seasons returns empty fold results."""
        config = ExperimentConfig(
            name="Too Few Seasons",
            data={"leagues": ["ENG-Premier League"], "seasons": ["2324"], "markets": ["1x2"]},
            models=[ModelConfig(name="Dummy", type="lightgbm")],
            evaluation={"walk_forward": {"train_seasons": 3, "test_seasons": 1}},
        )
        runner = WalkForwardRunner(config)
        result = runner.run_synthetic(seed=42)
        assert len(result.fold_results) == 0


# ---------------------------------------------------------------------------
# ReportData generator tests
# ---------------------------------------------------------------------------


class TestReportDataGenerator:
    """Tests for the report data builder."""

    def test_build_report_data_structure(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """build_report_data returns a ReportData instance."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        assert isinstance(report, ReportData)

    def test_hero_metrics_present(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Hero metrics contain expected keys."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        expected_keys = {
            "clv",
            "roi",
            "sharpe",
            "ece",
            "log_loss",
            "brier_score",
            "n_bets",
            "max_drawdown",
        }
        assert expected_keys.issubset(report.hero_metrics.keys())

    def test_semaphore_valid_colors(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Semaphore values are valid traffic-light colors."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        for key, color in report.semaphore.items():
            assert color in {"green", "yellow", "red"}, f"{key}={color}"

    def test_verdict_text_non_empty(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Verdict text is generated and non-empty."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        assert len(report.verdict_text) > 10

    def test_cumulative_clv_has_entries(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Cumulative CLV is computed for at least one model."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        assert len(report.cumulative_clv) > 0

    def test_model_comparison_populated(
        self,
        multi_model_config: ExperimentConfig,
    ) -> None:
        """Model comparison table has rows for each model."""
        runner = WalkForwardRunner(multi_model_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        model_names = {row.model for row in report.model_comparison}
        assert "ModelA" in model_names
        assert "ModelB" in model_names


# ---------------------------------------------------------------------------
# HTML report tests
# ---------------------------------------------------------------------------


class TestHtmlReport:
    """Tests for HTML report generation."""

    def test_produces_valid_html(
        self,
        minimal_config: ExperimentConfig,
        tmp_path: Path,
    ) -> None:
        """HTML report is written and contains expected structure."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        output = tmp_path / "test_report.html"
        render_html_report(report, output)

        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Test Experiment" in content
        assert "plotly" in content.lower()

    def test_html_contains_sections(
        self,
        minimal_config: ExperimentConfig,
        tmp_path: Path,
    ) -> None:
        """HTML report contains key section headings."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        output = tmp_path / "sections_report.html"
        render_html_report(report, output)

        content = output.read_text(encoding="utf-8")
        assert "Executive Summary" in content
        assert "Closing Line Value" in content
        assert "Performance" in content

    def test_html_self_contained(
        self,
        minimal_config: ExperimentConfig,
        tmp_path: Path,
    ) -> None:
        """HTML report is self-contained (single file with inline CSS)."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        output = tmp_path / "self_contained.html"
        render_html_report(report, output)

        content = output.read_text(encoding="utf-8")
        assert "<style>" in content
        assert "fonts.googleapis.com" in content


# ---------------------------------------------------------------------------
# Terminal report tests
# ---------------------------------------------------------------------------


class TestTerminalReport:
    """Tests for Rich terminal report output."""

    def test_produces_non_empty_string(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Terminal report renders a non-empty string."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        output = render_terminal_string(report)
        assert len(output) > 50

    def test_contains_experiment_name(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Terminal output includes the experiment name."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        output = render_terminal_string(report)
        assert "Test Experiment" in output

    def test_contains_verdict(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Terminal output includes a VERDICT line."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        output = render_terminal_string(report)
        assert "VERDICT" in output

    def test_contains_hero_metrics(
        self,
        minimal_config: ExperimentConfig,
    ) -> None:
        """Terminal output includes HERO METRICS section."""
        runner = WalkForwardRunner(minimal_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        output = render_terminal_string(report)
        assert "HERO METRICS" in output

    def test_contains_model_comparison(
        self,
        multi_model_config: ExperimentConfig,
    ) -> None:
        """Terminal output includes MODEL COMPARISON section."""
        runner = WalkForwardRunner(multi_model_config)
        result = runner.run_synthetic(seed=42)
        report = build_report_data(result)
        output = render_terminal_string(report)
        assert "MODEL COMPARISON" in output

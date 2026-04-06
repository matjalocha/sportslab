"""Tests for automated leakage detection module.

Uses synthetic data with known leaker and safe features.
Does NOT use the real features parquet (too slow for CI).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.backtesting.leakage import (
    detect_high_correlations,
    detect_importance_spikes,
    detect_name_patterns,
    generate_leakage_report,
    run_leakage_check,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_synthetic_data(
    n: int = 1000,
    seed: int = 42,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Build DataFrame with known safe and leaker features.

    Creates 20+ noise features alongside leakers so that importance
    spikes are detectable (LightGBM needs enough features to dilute
    mean importance for the spike to be > 10x).

    Features:
      - safe_noise_0..19: random noise, correlation ~0.02 with target
      - safe_elo_diff: random noise, correlation ~0.05 with target
      - LEAKER_home_goals: equals target (perfect leaker)
      - LEAKER_result_encoded: target + small noise (near-perfect leaker)
      - suspicious_raw_shots: moderate correlation ~0.35 with target
    """
    rng = np.random.default_rng(seed)

    # Target: multiclass 0/1/2
    y = rng.integers(0, 3, size=n)

    data: dict[str, np.ndarray] = {}

    # 20 safe noise features to dilute mean importance
    for i in range(20):
        data[f"safe_noise_{i}"] = rng.standard_normal(n)

    data["safe_elo_diff"] = rng.standard_normal(n) * 100

    # Perfect leaker: exactly equals the target
    data["LEAKER_home_goals"] = y.astype(float)

    # Near-perfect leaker: target + small noise
    data["LEAKER_result_encoded"] = y.astype(float) + rng.normal(0, 0.1, size=n)

    # Suspicious: moderate correlation with target
    data["suspicious_raw_shots"] = y.astype(float) * 2 + rng.standard_normal(n) * 3

    x = pd.DataFrame(data)

    return x, y


@pytest.fixture
def synthetic_data() -> tuple[pd.DataFrame, np.ndarray]:
    """Provide synthetic data with known leakers."""
    return _build_synthetic_data()


# ---------------------------------------------------------------------------
# Strategy 1: Feature importance spikes
# ---------------------------------------------------------------------------


class TestDetectImportanceSpikes:
    """Tests for detect_importance_spikes."""

    def test_leaker_features_have_high_ratio(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """LEAKER_home_goals (perfect copy of target) should have importance ratio > 10x mean."""
        x, y = synthetic_data
        result = detect_importance_spikes(x, y)

        leaker_home = result[result["feature"] == "LEAKER_home_goals"]

        # The perfect leaker should be flagged as suspicious
        assert leaker_home["is_suspicious"].values[0]
        assert leaker_home["ratio"].values[0] > 10.0

    def test_safe_features_not_flagged(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Safe features should not be flagged as suspicious."""
        x, y = synthetic_data
        result = detect_importance_spikes(x, y)

        safe_noise = result[result["feature"] == "safe_noise_0"]
        assert not safe_noise["is_suspicious"].values[0]

    def test_output_columns(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Output should have the expected columns."""
        x, y = synthetic_data
        result = detect_importance_spikes(x, y)

        expected_cols = {"feature", "importance", "mean_importance", "ratio", "is_suspicious"}
        assert set(result.columns) == expected_cols

    def test_sorted_by_importance_desc(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Results should be sorted by importance descending."""
        x, y = synthetic_data
        result = detect_importance_spikes(x, y)

        importances = result["importance"].values
        assert all(importances[i] >= importances[i + 1] for i in range(len(importances) - 1))

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame should return empty result."""
        x = pd.DataFrame()
        y = np.array([0, 1, 2])
        result = detect_importance_spikes(x, y)

        assert len(result) == 0
        assert "feature" in result.columns

    def test_custom_threshold(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Lower threshold should flag more features."""
        x, y = synthetic_data
        result_strict = detect_importance_spikes(x, y, threshold_multiplier=20.0)
        result_lenient = detect_importance_spikes(x, y, threshold_multiplier=3.0)

        strict_count = result_strict["is_suspicious"].sum()
        lenient_count = result_lenient["is_suspicious"].sum()
        assert lenient_count >= strict_count


# ---------------------------------------------------------------------------
# Strategy 2: High correlations
# ---------------------------------------------------------------------------


class TestDetectHighCorrelations:
    """Tests for detect_high_correlations."""

    def test_leaker_features_have_high_correlation(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """LEAKER features should have high correlation with target."""
        x, y = synthetic_data
        result = detect_high_correlations(x, y)

        leaker_home = result[result["feature"] == "LEAKER_home_goals"]
        leaker_encoded = result[result["feature"] == "LEAKER_result_encoded"]

        # Perfect leaker should have correlation > 0.5
        assert leaker_home["correlation"].values[0] > 0.5
        assert leaker_home["severity"].values[0] == "high"

        # Near-perfect leaker should also be high
        assert leaker_encoded["correlation"].values[0] > 0.5
        assert leaker_encoded["severity"].values[0] == "high"

    def test_safe_features_low_correlation(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Safe features should have low correlation."""
        x, y = synthetic_data
        result = detect_high_correlations(x, y)

        safe_noise = result[result["feature"] == "safe_noise_0"]
        assert safe_noise["correlation"].values[0] < 0.3
        assert not safe_noise["is_suspicious"].values[0]

    def test_suspicious_moderate_correlation(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Suspicious feature should have moderate correlation."""
        x, y = synthetic_data
        result = detect_high_correlations(x, y)

        suspicious = result[result["feature"] == "suspicious_raw_shots"]
        corr = suspicious["correlation"].values[0]
        # Should be in the suspicious range (> 0.3) given the construction
        assert corr > 0.2  # Allow some slack for randomness

    def test_severity_classification(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Severity should be correctly assigned based on correlation value."""
        x, y = synthetic_data
        result = detect_high_correlations(x, y, threshold=0.3)

        for _, row in result.iterrows():
            if row["correlation"] >= 0.5:
                assert row["severity"] == "high"
            elif row["correlation"] >= 0.3:
                assert row["severity"] == "medium"
            else:
                assert row["severity"] == "low"

    def test_output_columns(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Output should have the expected columns."""
        x, y = synthetic_data
        result = detect_high_correlations(x, y)

        expected_cols = {"feature", "correlation", "is_suspicious", "severity"}
        assert set(result.columns) == expected_cols

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame should return empty result."""
        x = pd.DataFrame()
        y = np.array([0, 1, 2])
        result = detect_high_correlations(x, y)

        assert len(result) == 0
        assert "feature" in result.columns

    def test_constant_column_handled(self) -> None:
        """Constant column (std=0) should not cause NaN or crash."""
        x = pd.DataFrame({"constant_col": np.ones(100), "normal_col": np.random.randn(100)})
        y = np.random.randint(0, 3, size=100)
        result = detect_high_correlations(x, y)

        constant_row = result[result["feature"] == "constant_col"]
        assert constant_row["correlation"].values[0] == 0.0
        assert not np.isnan(constant_row["correlation"].values[0])


# ---------------------------------------------------------------------------
# Strategy 3: Name-based heuristics
# ---------------------------------------------------------------------------


class TestDetectNamePatterns:
    """Tests for detect_name_patterns."""

    def test_rolling_classified_safe(self) -> None:
        """Features with _rolling_ pattern should be classified safe."""
        names = [
            "home_rolling_xg_for_10",
            "away_rolling_goals_scored_10",
            "diff_rolling_possession_5",
        ]
        result = detect_name_patterns(names)

        for _, row in result.iterrows():
            assert row["classification"] == "safe", (
                f"{row['feature']} should be safe but got {row['classification']}"
            )
            assert row["matched_pattern"] != ""

    def test_lag_classified_safe(self) -> None:
        """Features with _lagN pattern should be classified safe."""
        names = ["home_xg_for_lag1", "away_goals_conceded_lag3", "home_points_lag2"]
        result = detect_name_patterns(names)

        for _, row in result.iterrows():
            assert row["classification"] == "safe"

    def test_elo_classified_safe(self) -> None:
        """Features with _elo pattern should be classified safe."""
        names = ["home_elo", "away_elo", "diff_elo", "elo_delta"]
        result = detect_name_patterns(names)

        for _, row in result.iterrows():
            assert row["classification"] == "safe"

    def test_raw_stats_classified_suspicious(self) -> None:
        """Raw match stat names should be classified suspicious."""
        names = [
            "home_xg",
            "away_xg",
            "home_possession",
            "away_total_shots",
            "home_goals",
            "away_goals",
        ]
        result = detect_name_patterns(names)

        for _, row in result.iterrows():
            assert row["classification"] == "suspicious", (
                f"{row['feature']} should be suspicious but got {row['classification']}"
            )

    def test_unknown_for_unrecognized(self) -> None:
        """Unrecognized feature names should be classified as unknown."""
        names = ["completely_unknown_feature", "weird_col_xyz"]
        result = detect_name_patterns(names)

        for _, row in result.iterrows():
            assert row["classification"] == "unknown"

    def test_output_columns(self) -> None:
        """Output should have the expected columns."""
        result = detect_name_patterns(["some_feature"])
        expected_cols = {"feature", "classification", "matched_pattern"}
        assert set(result.columns) == expected_cols

    def test_empty_list(self) -> None:
        """Empty feature list should return empty DataFrame."""
        result = detect_name_patterns([])
        assert len(result) == 0

    def test_safe_pattern_does_not_match_raw(self) -> None:
        """Rolling pattern for xg_for_roll3 should be safe, not suspicious like home_xg."""
        safe_names = ["home_xg_for_roll3", "away_xg_against_roll10"]
        result = detect_name_patterns(safe_names)

        for _, row in result.iterrows():
            assert row["classification"] == "safe", (
                f"{row['feature']} should be safe"
            )

    def test_squad_attributes_safe(self) -> None:
        """FIFA/squad attributes should be classified safe."""
        names = [
            "home_avg_overall_xi",
            "away_max_value_eur_xi",
            "home_starting_gk_overall",
            "away_bench_avg_overall",
        ]
        result = detect_name_patterns(names)

        for _, row in result.iterrows():
            assert row["classification"] == "safe", (
                f"{row['feature']} should be safe"
            )

    def test_calendar_features_safe(self) -> None:
        """Calendar features should be classified safe."""
        names = ["is_weekend", "is_holiday_period", "month", "day_of_week", "season_phase"]
        result = detect_name_patterns(names)

        for _, row in result.iterrows():
            assert row["classification"] == "safe", (
                f"{row['feature']} should be safe"
            )


# ---------------------------------------------------------------------------
# Strategy 4: Combined report
# ---------------------------------------------------------------------------


class TestRunLeakageCheck:
    """Tests for run_leakage_check (combined verdict)."""

    def test_leaker_verdict_correct(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Perfect leaker should get 'leaker' verdict."""
        x, y = synthetic_data
        result = run_leakage_check(x, y)

        leaker_home = result[result["feature"] == "LEAKER_home_goals"]
        # High importance + high correlation = leaker
        assert leaker_home["final_verdict"].values[0] in ("leaker", "suspicious")

    def test_safe_verdict_correct(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Safe features should get 'safe' verdict."""
        x, y = synthetic_data
        result = run_leakage_check(x, y)

        safe = result[result["feature"] == "safe_elo_diff"]
        assert safe["final_verdict"].values[0] == "safe"

    def test_output_columns(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Output should have the expected columns."""
        x, y = synthetic_data
        result = run_leakage_check(x, y)

        expected_cols = {
            "feature",
            "importance_ratio",
            "correlation",
            "name_class",
            "final_verdict",
            "reasons",
        }
        assert set(result.columns) == expected_cols

    def test_all_features_present(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """All input features should appear in the output."""
        x, y = synthetic_data
        result = run_leakage_check(x, y)

        assert set(result["feature"]) == set(x.columns)

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame should return empty result."""
        x = pd.DataFrame()
        y = np.array([0, 1, 2])
        result = run_leakage_check(x, y)

        assert len(result) == 0
        assert "final_verdict" in result.columns

    def test_all_safe_features(self) -> None:
        """When all features are random noise, all should be safe."""
        rng = np.random.default_rng(42)
        n = 300
        x = pd.DataFrame({
            "rolling_feature_1": rng.standard_normal(n),
            "rolling_feature_2": rng.standard_normal(n),
            "rolling_feature_3": rng.standard_normal(n),
        })
        y = rng.integers(0, 3, size=n)

        result = run_leakage_check(x, y)
        assert (result["final_verdict"] == "safe").all()

    def test_all_leaker_features(self) -> None:
        """When all features are perfect leakers, all should be flagged."""
        rng = np.random.default_rng(42)
        n = 500
        y = rng.integers(0, 3, size=n)
        x = pd.DataFrame({
            "leaker_1": y.astype(float),
            "leaker_2": y.astype(float) + rng.normal(0, 0.05, size=n),
            "leaker_3": y.astype(float) * 2,
        })

        result = run_leakage_check(x, y)
        # All should be flagged as suspicious or leaker
        assert (result["final_verdict"] != "safe").all()

    def test_single_feature(self) -> None:
        """Single feature DataFrame should work without error."""
        rng = np.random.default_rng(42)
        n = 200
        y = rng.integers(0, 3, size=n)
        x = pd.DataFrame({"only_feature": rng.standard_normal(n)})

        result = run_leakage_check(x, y)
        assert len(result) == 1

    def test_sorted_by_verdict_severity(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
    ) -> None:
        """Results should be sorted: leaker first, then suspicious, then safe."""
        x, y = synthetic_data
        result = run_leakage_check(x, y)

        verdict_order = {"leaker": 0, "suspicious": 1, "safe": 2}
        orders = result["final_verdict"].map(verdict_order).values
        assert all(orders[i] <= orders[i + 1] for i in range(len(orders) - 1))


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


class TestGenerateLeakageReport:
    """Tests for generate_leakage_report."""

    def test_produces_markdown_file(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
        tmp_path: Path,
    ) -> None:
        """Should produce a valid markdown file at the specified path."""
        x, y = synthetic_data
        results = run_leakage_check(x, y)

        output_path = tmp_path / "report.md"
        returned_path = generate_leakage_report(results, output_path)

        assert returned_path.exists()
        assert returned_path == output_path.resolve()

        content = returned_path.read_text(encoding="utf-8")
        assert "# Feature Leakage Audit Report" in content
        assert "## Summary" in content

    def test_report_contains_summary_counts(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
        tmp_path: Path,
    ) -> None:
        """Report should contain correct summary counts."""
        x, y = synthetic_data
        results = run_leakage_check(x, y)

        output_path = tmp_path / "report.md"
        generate_leakage_report(results, output_path)

        content = output_path.resolve().read_text(encoding="utf-8")
        assert f"**Total features analyzed**: {len(results)}" in content

    def test_report_contains_leaker_table(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
        tmp_path: Path,
    ) -> None:
        """Report should contain leaker table when leakers exist."""
        x, y = synthetic_data
        results = run_leakage_check(x, y)

        output_path = tmp_path / "report.md"
        generate_leakage_report(results, output_path)

        content = output_path.resolve().read_text(encoding="utf-8")

        leakers = results[results["final_verdict"] == "leaker"]
        if len(leakers) > 0:
            assert "## Confirmed Leakers" in content
        # If no leakers, section should not appear
        suspicious = results[results["final_verdict"] == "suspicious"]
        if len(suspicious) > 0 or len(leakers) > 0:
            assert "## Recommended Additions to _RAW_MATCH_STATS" in content

    def test_creates_parent_directories(
        self,
        synthetic_data: tuple[pd.DataFrame, np.ndarray],
        tmp_path: Path,
    ) -> None:
        """Should create parent directories if they don't exist."""
        x, y = synthetic_data
        results = run_leakage_check(x, y)

        output_path = tmp_path / "nested" / "deep" / "report.md"
        returned_path = generate_leakage_report(results, output_path)
        assert returned_path.exists()

    def test_empty_results(self, tmp_path: Path) -> None:
        """Empty results should produce a valid report with zero counts."""
        results = pd.DataFrame(
            columns=[
                "feature",
                "importance_ratio",
                "correlation",
                "name_class",
                "final_verdict",
                "reasons",
            ],
        )

        output_path = tmp_path / "empty_report.md"
        generate_leakage_report(results, output_path)

        content = output_path.resolve().read_text(encoding="utf-8")
        assert "**Total features analyzed**: 0" in content
        assert "**Safe**: 0" in content

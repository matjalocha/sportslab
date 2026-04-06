"""Tests for ECE monitoring: grouped, rolling, and alerting."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.models.monitoring.ece import (
    compute_ece_per_group,
    compute_rolling_ece,
    ece_alert,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_predictions_df(
    n: int = 500,
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Build a synthetic predictions DataFrame for testing.

    Generates well-calibrated predictions: actual outcomes are Bernoulli
    draws from model_prob, so ECE should be low.
    """
    rng = np.random.default_rng(seed)
    if leagues is None:
        leagues = ["EPL", "LaLiga"]
    if seasons is None:
        seasons = ["2324"]

    rows_per_combo = n // (len(leagues) * len(seasons))
    records: list[dict[str, object]] = []
    for league in leagues:
        for season in seasons:
            probs = rng.uniform(0.2, 0.8, rows_per_combo)
            actuals = (rng.uniform(0, 1, rows_per_combo) < probs).astype(int)
            for prob, actual in zip(probs, actuals, strict=True):
                records.append({
                    "league": league,
                    "season": season,
                    "model_prob": float(prob),
                    "actual": int(actual),
                })
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# compute_ece_per_group
# ---------------------------------------------------------------------------

class TestComputeEcePerGroup:
    """Tests for compute_ece_per_group."""

    def test_groups_computed_correctly(self) -> None:
        """Each league x season group gets its own ECE row."""
        df = _make_predictions_df(
            n=1000,
            leagues=["EPL", "LaLiga"],
            seasons=["2324", "2425"],
        )
        result = compute_ece_per_group(df)
        assert len(result) == 4  # 2 leagues x 2 seasons

    def test_well_calibrated_predictions_low_ece(self) -> None:
        """Well-calibrated predictions produce low ECE per group."""
        df = _make_predictions_df(n=2000, leagues=["EPL"], seasons=["2324"])
        result = compute_ece_per_group(df, n_bins=10)
        assert len(result) == 1
        assert result.iloc[0]["ece"] < 0.05

    def test_poorly_calibrated_predictions_high_ece(self) -> None:
        """Overconfident predictions produce higher ECE."""
        rng = np.random.default_rng(42)
        n = 1000
        # Predict 0.9 but actual rate is ~0.5
        df = pd.DataFrame({
            "league": ["EPL"] * n,
            "season": ["2324"] * n,
            "model_prob": [0.9] * n,
            "actual": rng.binomial(1, 0.5, n),
        })
        result = compute_ece_per_group(df, n_bins=10)
        assert result.iloc[0]["ece"] > 0.3

    def test_custom_group_cols(self) -> None:
        """Custom group columns work correctly."""
        df = pd.DataFrame({
            "market": ["1X2"] * 100 + ["OU25"] * 100,
            "model_prob": np.random.default_rng(42).uniform(0.3, 0.7, 200),
            "actual": np.random.default_rng(42).binomial(1, 0.5, 200),
        })
        result = compute_ece_per_group(df, group_cols=["market"])
        assert len(result) == 2
        assert "market" in result.columns

    def test_single_group(self) -> None:
        """Works with a single group."""
        df = _make_predictions_df(n=500, leagues=["EPL"], seasons=["2324"])
        result = compute_ece_per_group(df)
        assert len(result) == 1
        assert result.iloc[0]["n_bets"] > 0

    def test_n_bets_column_present(self) -> None:
        """Output includes n_bets count per group."""
        df = _make_predictions_df(n=600, leagues=["EPL", "LaLiga"], seasons=["2324"])
        result = compute_ece_per_group(df)
        assert "n_bets" in result.columns
        assert (result["n_bets"] > 0).all()

    def test_missing_column_raises(self) -> None:
        """Missing required column raises ValueError."""
        df = pd.DataFrame({"model_prob": [0.5], "actual": [1]})
        with pytest.raises(ValueError, match="Missing columns"):
            compute_ece_per_group(df, group_cols=["league"])

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty result with correct columns."""
        df = pd.DataFrame(columns=["league", "season", "model_prob", "actual"])
        result = compute_ece_per_group(df)
        assert len(result) == 0
        assert "ece" in result.columns
        assert "n_bets" in result.columns

    def test_sorted_by_ece_descending(self) -> None:
        """Result is sorted by ECE descending."""
        rng = np.random.default_rng(42)
        n = 500
        # EPL: well calibrated
        epl_probs = rng.uniform(0.3, 0.7, n)
        epl_actuals = (rng.uniform(0, 1, n) < epl_probs).astype(int)
        # LaLiga: poorly calibrated (constant 0.9, actual ~0.5)
        laliga_probs = np.full(n, 0.9)
        laliga_actuals = rng.binomial(1, 0.5, n)

        df = pd.DataFrame({
            "league": ["EPL"] * n + ["LaLiga"] * n,
            "season": ["2324"] * (2 * n),
            "model_prob": np.concatenate([epl_probs, laliga_probs]),
            "actual": np.concatenate([epl_actuals, laliga_actuals]),
        })
        result = compute_ece_per_group(df)
        assert result.iloc[0]["league"] == "LaLiga"


# ---------------------------------------------------------------------------
# compute_rolling_ece
# ---------------------------------------------------------------------------

class TestComputeRollingEce:
    """Tests for compute_rolling_ece."""

    def test_window_moves_correctly(self) -> None:
        """Number of output rows equals n_total - window + 1."""
        rng = np.random.default_rng(42)
        n = 300
        window = 100
        probs = rng.uniform(0.2, 0.8, n)
        df = pd.DataFrame({
            "model_prob": probs,
            "actual": (rng.uniform(0, 1, n) < probs).astype(int),
        })
        result = compute_rolling_ece(df, window=window)
        assert len(result) == n - window + 1

    def test_window_bounds_correct(self) -> None:
        """First and last window start/end indices are correct."""
        rng = np.random.default_rng(42)
        n = 150
        window = 50
        probs = rng.uniform(0.2, 0.8, n)
        df = pd.DataFrame({
            "model_prob": probs,
            "actual": (rng.uniform(0, 1, n) < probs).astype(int),
        })
        result = compute_rolling_ece(df, window=window)
        assert result.iloc[0]["window_start"] == 0
        assert result.iloc[0]["window_end"] == window - 1
        assert result.iloc[-1]["window_start"] == n - window
        assert result.iloc[-1]["window_end"] == n - 1

    def test_well_calibrated_rolling_ece_low(self) -> None:
        """Rolling ECE stays low for well-calibrated predictions.

        With a 200-sample window, sampling noise can push individual
        window ECE up to ~0.10 even for perfectly calibrated draws.
        We check the *median* ECE is below 0.08 as the stronger signal.
        """
        rng = np.random.default_rng(42)
        n = 2000
        probs = rng.uniform(0.2, 0.8, n)
        actuals = (rng.uniform(0, 1, n) < probs).astype(int)
        df = pd.DataFrame({"model_prob": probs, "actual": actuals})
        result = compute_rolling_ece(df, window=500)
        assert result["ece"].median() < 0.05

    def test_insufficient_data_returns_empty(self) -> None:
        """When n < window, returns empty DataFrame."""
        df = pd.DataFrame({
            "model_prob": [0.5, 0.6],
            "actual": [1, 0],
        })
        result = compute_rolling_ece(df, window=100)
        assert len(result) == 0

    def test_window_too_small_raises(self) -> None:
        """Window < 2 raises ValueError."""
        df = pd.DataFrame({"model_prob": [0.5], "actual": [1]})
        with pytest.raises(ValueError, match="window must be >= 2"):
            compute_rolling_ece(df, window=1)

    def test_n_bets_column_equals_window(self) -> None:
        """Every row has n_bets equal to the window size."""
        rng = np.random.default_rng(42)
        n = 200
        window = 50
        probs = rng.uniform(0.2, 0.8, n)
        df = pd.DataFrame({
            "model_prob": probs,
            "actual": (rng.uniform(0, 1, n) < probs).astype(int),
        })
        result = compute_rolling_ece(df, window=window)
        assert (result["n_bets"] == window).all()

    def test_missing_column_raises(self) -> None:
        """Missing probability column raises ValueError."""
        df = pd.DataFrame({"wrong_col": [0.5], "actual": [1]})
        with pytest.raises(ValueError, match="Missing columns"):
            compute_rolling_ece(df)


# ---------------------------------------------------------------------------
# ece_alert
# ---------------------------------------------------------------------------

class TestEceAlert:
    """Tests for ece_alert."""

    def test_above_threshold_triggers_alert(self) -> None:
        """ECE above threshold produces an alert."""
        ece_results = pd.DataFrame({
            "league": ["EPL"],
            "season": ["2324"],
            "ece": [0.05],
            "n_bets": [500],
        })
        alerts = ece_alert(ece_results, threshold=0.02)
        assert len(alerts) == 1
        assert alerts[0]["above_threshold"] is True
        assert alerts[0]["ece"] == 0.05

    def test_below_threshold_no_alerts(self) -> None:
        """ECE below threshold produces no alerts."""
        ece_results = pd.DataFrame({
            "league": ["EPL"],
            "season": ["2324"],
            "ece": [0.01],
            "n_bets": [500],
        })
        alerts = ece_alert(ece_results, threshold=0.02)
        assert len(alerts) == 0

    def test_mixed_results(self) -> None:
        """Some groups above threshold, some below."""
        ece_results = pd.DataFrame({
            "league": ["EPL", "LaLiga", "SerieA"],
            "season": ["2324", "2324", "2324"],
            "ece": [0.01, 0.05, 0.03],
            "n_bets": [500, 500, 500],
        })
        alerts = ece_alert(ece_results, threshold=0.02)
        assert len(alerts) == 2
        # Sorted by ECE descending
        assert alerts[0]["league"] == "LaLiga"
        assert alerts[1]["league"] == "SerieA"

    def test_custom_threshold(self) -> None:
        """Custom threshold changes alert sensitivity."""
        ece_results = pd.DataFrame({
            "league": ["EPL"],
            "ece": [0.015],
            "n_bets": [500],
        })
        # Default 2% threshold: below
        assert len(ece_alert(ece_results, threshold=0.02)) == 0
        # Lower threshold: above
        assert len(ece_alert(ece_results, threshold=0.01)) == 1

    def test_empty_dataframe_no_alerts(self) -> None:
        """Empty input produces no alerts."""
        ece_results = pd.DataFrame(columns=["ece", "n_bets"])
        alerts = ece_alert(ece_results)
        assert len(alerts) == 0

    def test_works_with_rolling_ece_output(self) -> None:
        """Alert function works with compute_rolling_ece output format."""
        ece_results = pd.DataFrame({
            "window_start": [0, 100],
            "window_end": [99, 199],
            "ece": [0.01, 0.05],
            "n_bets": [100, 100],
        })
        alerts = ece_alert(ece_results, threshold=0.02)
        assert len(alerts) == 1
        assert alerts[0]["window_start"] == 100

    def test_exact_threshold_not_triggered(self) -> None:
        """ECE exactly at threshold is NOT triggered (strict >)."""
        ece_results = pd.DataFrame({
            "league": ["EPL"],
            "ece": [0.02],
            "n_bets": [500],
        })
        alerts = ece_alert(ece_results, threshold=0.02)
        assert len(alerts) == 0

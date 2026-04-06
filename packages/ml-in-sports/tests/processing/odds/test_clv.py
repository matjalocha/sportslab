"""Tests for CLV tracking module."""

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.processing.odds.clv import (
    clv_summary,
    compute_match_clv,
    compute_rolling_clv,
    merge_closing_odds,
)

# ---------------------------------------------------------------------------
# Tests: compute_match_clv
# ---------------------------------------------------------------------------


class TestComputeMatchClv:
    """Tests for per-bet CLV computation."""

    def test_positive_clv_when_model_beats_market(self) -> None:
        """Model prob > market implied prob -> positive CLV."""
        # Market odds 2.0 -> implied prob 0.50; model says 0.55.
        model_probs = np.array([0.55])
        closing_odds = np.array([2.0])

        clv = compute_match_clv(model_probs, closing_odds)

        assert clv[0] == pytest.approx(0.05)

    def test_negative_clv_when_model_worse_than_market(self) -> None:
        """Model prob < market implied prob -> negative CLV."""
        # Market odds 2.0 -> implied 0.50; model says 0.45.
        model_probs = np.array([0.45])
        closing_odds = np.array([2.0])

        clv = compute_match_clv(model_probs, closing_odds)

        assert clv[0] == pytest.approx(-0.05)

    def test_zero_clv_when_model_equals_market(self) -> None:
        """Model prob == market implied prob -> zero CLV."""
        model_probs = np.array([0.50])
        closing_odds = np.array([2.0])

        clv = compute_match_clv(model_probs, closing_odds)

        assert clv[0] == pytest.approx(0.0)

    def test_multiple_bets(self) -> None:
        """CLV computed element-wise for multiple bets."""
        model_probs = np.array([0.60, 0.30, 0.50])
        closing_odds = np.array([2.0, 4.0, 2.0])
        # Expected: [0.60-0.50, 0.30-0.25, 0.50-0.50] = [0.10, 0.05, 0.00]

        clv = compute_match_clv(model_probs, closing_odds)

        assert len(clv) == 3
        assert clv[0] == pytest.approx(0.10)
        assert clv[1] == pytest.approx(0.05)
        assert clv[2] == pytest.approx(0.00)

    def test_nan_odds_produce_nan_clv(self) -> None:
        """NaN closing odds result in NaN CLV (not crash)."""
        model_probs = np.array([0.55, 0.60])
        closing_odds = np.array([2.0, np.nan])

        clv = compute_match_clv(model_probs, closing_odds)

        assert clv[0] == pytest.approx(0.05)
        assert np.isnan(clv[1])

    def test_zero_odds_produce_nan_clv(self) -> None:
        """Zero odds (invalid) result in NaN CLV."""
        model_probs = np.array([0.55])
        closing_odds = np.array([0.0])

        clv = compute_match_clv(model_probs, closing_odds)

        assert np.isnan(clv[0])

    def test_negative_odds_produce_nan_clv(self) -> None:
        """Negative odds (invalid) result in NaN CLV."""
        model_probs = np.array([0.55])
        closing_odds = np.array([-1.5])

        clv = compute_match_clv(model_probs, closing_odds)

        assert np.isnan(clv[0])

    def test_shape_mismatch_raises_value_error(self) -> None:
        """Different shapes raise ValueError."""
        model_probs = np.array([0.55, 0.60])
        closing_odds = np.array([2.0])

        with pytest.raises(ValueError, match="Shape mismatch"):
            compute_match_clv(model_probs, closing_odds)

    def test_empty_arrays(self) -> None:
        """Empty arrays return empty array."""
        clv = compute_match_clv(np.array([]), np.array([]))

        assert len(clv) == 0

    def test_accepts_plain_lists(self) -> None:
        """Plain Python lists are accepted (converted internally)."""
        clv = compute_match_clv([0.55], [2.0])  # type: ignore[arg-type]

        assert clv[0] == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Tests: compute_rolling_clv
# ---------------------------------------------------------------------------


class TestComputeRollingClv:
    """Tests for rolling mean CLV."""

    def test_rolling_window_produces_nan_prefix(self) -> None:
        """First (window-1) values are NaN."""
        clv_values = np.array([0.01, 0.02, 0.03, 0.04, 0.05])

        rolling = compute_rolling_clv(clv_values, window=3)

        assert np.isnan(rolling[0])
        assert np.isnan(rolling[1])
        assert np.isfinite(rolling[2])

    def test_rolling_mean_correct(self) -> None:
        """Rolling mean of window=3 over [1, 2, 3, 4, 5] = [NaN, NaN, 2, 3, 4]."""
        clv_values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        rolling = compute_rolling_clv(clv_values, window=3)

        assert rolling[2] == pytest.approx(2.0)
        assert rolling[3] == pytest.approx(3.0)
        assert rolling[4] == pytest.approx(4.0)

    def test_window_of_one_equals_identity(self) -> None:
        """Window=1 rolling mean equals the original values."""
        clv_values = np.array([0.05, -0.02, 0.03])

        rolling = compute_rolling_clv(clv_values, window=1)

        np.testing.assert_array_almost_equal(rolling, clv_values)

    def test_window_zero_raises(self) -> None:
        """Window < 1 raises ValueError."""
        with pytest.raises(ValueError, match="window must be >= 1"):
            compute_rolling_clv(np.array([1.0, 2.0]), window=0)

    def test_window_larger_than_array(self) -> None:
        """Window larger than data returns all NaN."""
        clv_values = np.array([0.01, 0.02])

        rolling = compute_rolling_clv(clv_values, window=10)

        assert all(np.isnan(rolling))

    def test_empty_array(self) -> None:
        """Empty input returns empty output."""
        rolling = compute_rolling_clv(np.array([]), window=5)

        assert len(rolling) == 0


# ---------------------------------------------------------------------------
# Tests: clv_summary
# ---------------------------------------------------------------------------


class TestClvSummary:
    """Tests for CLV summary statistics."""

    def test_positive_edge_summary(self) -> None:
        """All-positive CLV produces positive mean and 100% pct_positive."""
        clv_values = np.array([0.01, 0.02, 0.03, 0.04, 0.05])

        summary = clv_summary(clv_values)

        assert summary["mean"] == pytest.approx(0.03)
        assert summary["median"] == pytest.approx(0.03)
        assert summary["pct_positive"] == pytest.approx(100.0)
        assert summary["count"] == pytest.approx(5.0)
        assert summary["ci_lower"] < summary["mean"]
        assert summary["ci_upper"] > summary["mean"]

    def test_mixed_clv_summary(self) -> None:
        """Mixed positive/negative CLV values."""
        clv_values = np.array([0.10, -0.05, 0.03, -0.02])

        summary = clv_summary(clv_values)

        assert summary["mean"] == pytest.approx(0.015)
        assert summary["pct_positive"] == pytest.approx(50.0)
        assert summary["count"] == pytest.approx(4.0)

    def test_all_negative_clv(self) -> None:
        """All negative CLV -> 0% positive."""
        clv_values = np.array([-0.01, -0.02, -0.03])

        summary = clv_summary(clv_values)

        assert summary["mean"] < 0
        assert summary["pct_positive"] == pytest.approx(0.0)

    def test_empty_array_returns_nan_summary(self) -> None:
        """Empty input returns all NaN except count=0."""
        summary = clv_summary(np.array([]))

        assert np.isnan(summary["mean"])
        assert np.isnan(summary["median"])
        assert np.isnan(summary["std"])
        assert np.isnan(summary["pct_positive"])
        assert summary["count"] == pytest.approx(0.0)

    def test_all_nan_returns_nan_summary(self) -> None:
        """All-NaN input treated like empty."""
        summary = clv_summary(np.array([np.nan, np.nan]))

        assert np.isnan(summary["mean"])
        assert summary["count"] == pytest.approx(0.0)

    def test_nan_values_excluded_from_stats(self) -> None:
        """NaN values are stripped before computing statistics."""
        clv_values = np.array([0.10, np.nan, 0.20])

        summary = clv_summary(clv_values)

        assert summary["mean"] == pytest.approx(0.15)
        assert summary["count"] == pytest.approx(2.0)

    def test_single_value(self) -> None:
        """Single value has std=0 and tight CI."""
        summary = clv_summary(np.array([0.05]))

        assert summary["mean"] == pytest.approx(0.05)
        assert summary["std"] == pytest.approx(0.0)
        assert summary["se"] == pytest.approx(0.0)
        assert summary["ci_lower"] == pytest.approx(0.05)
        assert summary["ci_upper"] == pytest.approx(0.05)
        assert summary["count"] == pytest.approx(1.0)

    def test_confidence_interval_width(self) -> None:
        """CI width = 2 * 1.96 * SE."""
        clv_values = np.array([0.01, 0.02, 0.03, 0.04, 0.05])

        summary = clv_summary(clv_values)

        ci_width = summary["ci_upper"] - summary["ci_lower"]
        expected_width = 2 * 1.96 * summary["se"]
        assert ci_width == pytest.approx(expected_width)

    def test_all_required_keys_present(self) -> None:
        """Summary dict has all documented keys."""
        summary = clv_summary(np.array([0.01, 0.02]))

        required_keys = {
            "mean",
            "median",
            "std",
            "pct_positive",
            "se",
            "ci_lower",
            "ci_upper",
            "count",
        }
        assert required_keys == set(summary.keys())


# ---------------------------------------------------------------------------
# Tests: merge_closing_odds
# ---------------------------------------------------------------------------


class TestMergeClosingOdds:
    """Tests for prediction-odds merging."""

    @pytest.fixture
    def predictions(self) -> pd.DataFrame:
        """Minimal predictions DataFrame."""
        return pd.DataFrame(
            {
                "league": ["ENG-Premier League", "ENG-Premier League"],
                "season": ["2324", "2324"],
                "home_team": ["Arsenal", "Liverpool"],
                "away_team": ["Chelsea", "Everton"],
                "model_home_prob": [0.55, 0.65],
                "model_draw_prob": [0.25, 0.20],
                "model_away_prob": [0.20, 0.15],
            }
        )

    @pytest.fixture
    def odds(self) -> pd.DataFrame:
        """Minimal odds DataFrame matching predictions."""
        return pd.DataFrame(
            {
                "league": ["ENG-Premier League", "ENG-Premier League"],
                "season": ["2324", "2324"],
                "home_team": ["Arsenal", "Liverpool"],
                "away_team": ["Chelsea", "Everton"],
                "pinnacle_home": [1.90, 1.55],
                "pinnacle_draw": [3.50, 4.20],
                "pinnacle_away": [4.00, 6.00],
            }
        )

    def test_merge_preserves_all_predictions(
        self,
        predictions: pd.DataFrame,
        odds: pd.DataFrame,
    ) -> None:
        """Left join preserves all prediction rows."""
        merged = merge_closing_odds(predictions, odds)

        assert len(merged) == 2

    def test_merge_includes_odds_columns(
        self,
        predictions: pd.DataFrame,
        odds: pd.DataFrame,
    ) -> None:
        """Merged result contains odds columns."""
        merged = merge_closing_odds(predictions, odds)

        assert "pinnacle_home" in merged.columns
        assert "pinnacle_draw" in merged.columns
        assert "pinnacle_away" in merged.columns

    def test_merge_includes_prediction_columns(
        self,
        predictions: pd.DataFrame,
        odds: pd.DataFrame,
    ) -> None:
        """Merged result preserves prediction columns."""
        merged = merge_closing_odds(predictions, odds)

        assert "model_home_prob" in merged.columns

    def test_unmatched_predictions_get_nan_odds(
        self,
        predictions: pd.DataFrame,
    ) -> None:
        """Predictions without matching odds get NaN in odds columns."""
        partial_odds = pd.DataFrame(
            {
                "league": ["ENG-Premier League"],
                "season": ["2324"],
                "home_team": ["Arsenal"],
                "away_team": ["Chelsea"],
                "pinnacle_home": [1.90],
                "pinnacle_draw": [3.50],
                "pinnacle_away": [4.00],
            }
        )

        merged = merge_closing_odds(predictions, partial_odds)

        assert len(merged) == 2
        # Liverpool-Everton has no odds -> NaN.
        liverpool_row = merged[merged["home_team"] == "Liverpool"].iloc[0]
        assert pd.isna(liverpool_row["pinnacle_home"])

    def test_custom_join_columns(self) -> None:
        """Custom on= parameter changes join logic."""
        preds = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "home": ["Arsenal"],
                "away": ["Chelsea"],
                "prob": [0.55],
            }
        )
        odds = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "home": ["Arsenal"],
                "away": ["Chelsea"],
                "pinnacle_home": [1.90],
            }
        )

        merged = merge_closing_odds(
            preds,
            odds,
            on=["date", "home", "away"],
        )

        assert len(merged) == 1
        assert merged.iloc[0]["pinnacle_home"] == pytest.approx(1.90)

    def test_missing_join_column_raises(
        self,
        predictions: pd.DataFrame,
    ) -> None:
        """Missing join column raises ValueError."""
        bad_odds = pd.DataFrame({"col1": [1]})

        with pytest.raises(ValueError, match="missing join columns"):
            merge_closing_odds(predictions, bad_odds)

    def test_predictions_missing_join_column_raises(self) -> None:
        """Missing join column in predictions also raises ValueError."""
        bad_preds = pd.DataFrame({"col1": [1]})
        odds = pd.DataFrame(
            {
                "league": ["ENG-Premier League"],
                "season": ["2324"],
                "home_team": ["Arsenal"],
                "away_team": ["Chelsea"],
                "pinnacle_home": [1.90],
            }
        )

        with pytest.raises(ValueError, match="missing join columns"):
            merge_closing_odds(bad_preds, odds)

    def test_empty_predictions(self) -> None:
        """Empty predictions DataFrame produces empty result."""
        preds = pd.DataFrame(
            columns=["league", "season", "home_team", "away_team", "prob"],
        )
        odds = pd.DataFrame(
            {
                "league": ["ENG-Premier League"],
                "season": ["2324"],
                "home_team": ["Arsenal"],
                "away_team": ["Chelsea"],
                "pinnacle_home": [1.90],
            }
        )

        merged = merge_closing_odds(preds, odds)

        assert len(merged) == 0

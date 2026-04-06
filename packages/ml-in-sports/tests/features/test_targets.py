"""Tests for the extended target variables module."""

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.features.targets import (
    add_all_targets,
    compute_away_goals_over_0_5,
    compute_btts,
    compute_double_chance,
    compute_home_goals_over_1_5,
    compute_ht_over_0_5,
    compute_ht_result_1x2,
    compute_margin,
    compute_over_under,
    compute_result_1x2,
    compute_total_goals,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def match_df() -> pd.DataFrame:
    """DataFrame with a mix of match scorelines."""
    return pd.DataFrame({
        "home_goals": [3, 0, 1, 2, 0],
        "away_goals": [1, 2, 1, 0, 0],
    })


@pytest.fixture
def match_df_with_nan() -> pd.DataFrame:
    """DataFrame with missing goal data."""
    return pd.DataFrame({
        "home_goals": [2, np.nan, 1],
        "away_goals": [1, 1, np.nan],
    })


@pytest.fixture
def match_df_with_halftime() -> pd.DataFrame:
    """DataFrame including half-time score columns."""
    return pd.DataFrame({
        "home_goals": [3, 0, 1],
        "away_goals": [1, 2, 1],
        "ht_home_goals": [1, 0, 0],
        "ht_away_goals": [0, 1, 0],
    })


# ---------------------------------------------------------------------------
# compute_result_1x2
# ---------------------------------------------------------------------------

class TestComputeResult1X2:
    """Tests for compute_result_1x2."""

    def test_home_win(self) -> None:
        """Home win returns 'H'."""
        result = compute_result_1x2(pd.Series([3]), pd.Series([1]))
        assert result.iloc[0] == "H"

    def test_away_win(self) -> None:
        """Away win returns 'A'."""
        result = compute_result_1x2(pd.Series([0]), pd.Series([2]))
        assert result.iloc[0] == "A"

    def test_draw(self) -> None:
        """Draw returns 'D'."""
        result = compute_result_1x2(pd.Series([1]), pd.Series([1]))
        assert result.iloc[0] == "D"

    def test_nan_returns_nan(self) -> None:
        """Missing goals produce NaN."""
        result = compute_result_1x2(pd.Series([np.nan]), pd.Series([1]))
        assert pd.isna(result.iloc[0])


# ---------------------------------------------------------------------------
# compute_over_under
# ---------------------------------------------------------------------------

class TestComputeOverUnder:
    """Tests for compute_over_under."""

    def test_over_2_5_true(self) -> None:
        """3 total goals is over 2.5."""
        result = compute_over_under(pd.Series([2]), pd.Series([1]), 2.5)
        assert result.iloc[0] == True  # noqa: E712

    def test_over_2_5_false(self) -> None:
        """2 total goals is not over 2.5."""
        result = compute_over_under(pd.Series([1]), pd.Series([1]), 2.5)
        assert result.iloc[0] == False  # noqa: E712

    def test_over_1_5_true(self) -> None:
        """2 total goals is over 1.5."""
        result = compute_over_under(pd.Series([1]), pd.Series([1]), 1.5)
        assert result.iloc[0] == True  # noqa: E712

    def test_over_1_5_false(self) -> None:
        """1 total goal is not over 1.5."""
        result = compute_over_under(pd.Series([1]), pd.Series([0]), 1.5)
        assert result.iloc[0] == False  # noqa: E712

    def test_over_3_5_true(self) -> None:
        """4 total goals is over 3.5."""
        result = compute_over_under(pd.Series([3]), pd.Series([1]), 3.5)
        assert result.iloc[0] == True  # noqa: E712

    def test_over_3_5_false(self) -> None:
        """3 total goals is not over 3.5."""
        result = compute_over_under(pd.Series([2]), pd.Series([1]), 3.5)
        assert result.iloc[0] == False  # noqa: E712

    def test_nan_returns_nan(self) -> None:
        """Missing goals produce NaN."""
        result = compute_over_under(pd.Series([np.nan]), pd.Series([1]), 2.5)
        assert pd.isna(result.iloc[0])


# ---------------------------------------------------------------------------
# compute_btts
# ---------------------------------------------------------------------------

class TestComputeBtts:
    """Tests for compute_btts."""

    def test_both_scored(self) -> None:
        """Both teams scored returns True."""
        result = compute_btts(pd.Series([2]), pd.Series([1]))
        assert result.iloc[0] == True  # noqa: E712

    def test_one_clean_sheet(self) -> None:
        """One team did not score returns False."""
        result = compute_btts(pd.Series([1]), pd.Series([0]))
        assert result.iloc[0] == False  # noqa: E712

    def test_nan_returns_nan(self) -> None:
        """Missing goals produce NaN."""
        result = compute_btts(pd.Series([np.nan]), pd.Series([1]))
        assert pd.isna(result.iloc[0])


# ---------------------------------------------------------------------------
# compute_home_goals_over_1_5
# ---------------------------------------------------------------------------

class TestComputeHomeGoalsOver15:
    """Tests for compute_home_goals_over_1_5."""

    def test_true_when_home_scores_two(self) -> None:
        """Two home goals is over 1.5."""
        result = compute_home_goals_over_1_5(pd.Series([2]))
        assert result.iloc[0] == True  # noqa: E712

    def test_false_when_home_scores_one(self) -> None:
        """One home goal is not over 1.5."""
        result = compute_home_goals_over_1_5(pd.Series([1]))
        assert result.iloc[0] == False  # noqa: E712

    def test_nan_returns_nan(self) -> None:
        """Missing goals produce NaN."""
        result = compute_home_goals_over_1_5(pd.Series([np.nan]))
        assert pd.isna(result.iloc[0])


# ---------------------------------------------------------------------------
# compute_away_goals_over_0_5
# ---------------------------------------------------------------------------

class TestComputeAwayGoalsOver05:
    """Tests for compute_away_goals_over_0_5."""

    def test_true_when_away_scores(self) -> None:
        """One away goal is over 0.5."""
        result = compute_away_goals_over_0_5(pd.Series([1]))
        assert result.iloc[0] == True  # noqa: E712

    def test_false_when_away_clean_sheet(self) -> None:
        """Zero away goals is not over 0.5."""
        result = compute_away_goals_over_0_5(pd.Series([0]))
        assert result.iloc[0] == False  # noqa: E712

    def test_nan_returns_nan(self) -> None:
        """Missing goals produce NaN."""
        result = compute_away_goals_over_0_5(pd.Series([np.nan]))
        assert pd.isna(result.iloc[0])


# ---------------------------------------------------------------------------
# compute_double_chance
# ---------------------------------------------------------------------------

class TestComputeDoubleChance:
    """Tests for compute_double_chance."""

    def test_home_win_produces_true_for_h_or_d(self) -> None:
        """Home win: home_or_draw=True, home_or_away=True, draw_or_away=False."""
        home_or_draw, home_or_away, draw_or_away = compute_double_chance(
            pd.Series(["H"]),
        )
        assert home_or_draw.iloc[0] == True  # noqa: E712
        assert home_or_away.iloc[0] == True  # noqa: E712
        assert draw_or_away.iloc[0] == False  # noqa: E712

    def test_draw_produces_correct_values(self) -> None:
        """Draw: home_or_draw=True, home_or_away=False, draw_or_away=True."""
        home_or_draw, home_or_away, draw_or_away = compute_double_chance(
            pd.Series(["D"]),
        )
        assert home_or_draw.iloc[0] == True  # noqa: E712
        assert home_or_away.iloc[0] == False  # noqa: E712
        assert draw_or_away.iloc[0] == True  # noqa: E712

    def test_away_win_produces_correct_values(self) -> None:
        """Away win: home_or_draw=False, home_or_away=True, draw_or_away=True."""
        home_or_draw, home_or_away, draw_or_away = compute_double_chance(
            pd.Series(["A"]),
        )
        assert home_or_draw.iloc[0] == False  # noqa: E712
        assert home_or_away.iloc[0] == True  # noqa: E712
        assert draw_or_away.iloc[0] == True  # noqa: E712

    def test_nan_returns_nan(self) -> None:
        """NaN result produces NaN for all double chance columns."""
        home_or_draw, home_or_away, draw_or_away = compute_double_chance(
            pd.Series([np.nan]),
        )
        assert pd.isna(home_or_draw.iloc[0])
        assert pd.isna(home_or_away.iloc[0])
        assert pd.isna(draw_or_away.iloc[0])


# ---------------------------------------------------------------------------
# compute_margin / compute_total_goals
# ---------------------------------------------------------------------------

class TestComputeMargin:
    """Tests for compute_margin."""

    def test_positive_margin_home_win(self) -> None:
        """Home win has positive margin."""
        result = compute_margin(pd.Series([3]), pd.Series([1]))
        assert result.iloc[0] == 2

    def test_negative_margin_away_win(self) -> None:
        """Away win has negative margin."""
        result = compute_margin(pd.Series([0]), pd.Series([2]))
        assert result.iloc[0] == -2

    def test_zero_margin_draw(self) -> None:
        """Draw has zero margin."""
        result = compute_margin(pd.Series([1]), pd.Series([1]))
        assert result.iloc[0] == 0

    def test_nan_returns_nan(self) -> None:
        """Missing goals produce NaN."""
        result = compute_margin(pd.Series([np.nan]), pd.Series([1]))
        assert pd.isna(result.iloc[0])


class TestComputeTotalGoals:
    """Tests for compute_total_goals."""

    def test_total_goals(self) -> None:
        """Total is sum of home and away goals."""
        result = compute_total_goals(pd.Series([2]), pd.Series([1]))
        assert result.iloc[0] == 3

    def test_nan_returns_nan(self) -> None:
        """Missing goals produce NaN."""
        result = compute_total_goals(pd.Series([np.nan]), pd.Series([1]))
        assert pd.isna(result.iloc[0])


# ---------------------------------------------------------------------------
# Half-time targets
# ---------------------------------------------------------------------------

class TestHalftimeTargets:
    """Tests for half-time target functions."""

    def test_ht_result_1x2_home(self) -> None:
        """HT home lead returns 'H'."""
        result = compute_ht_result_1x2(pd.Series([1]), pd.Series([0]))
        assert result.iloc[0] == "H"

    def test_ht_result_1x2_draw(self) -> None:
        """HT level returns 'D'."""
        result = compute_ht_result_1x2(pd.Series([0]), pd.Series([0]))
        assert result.iloc[0] == "D"

    def test_ht_over_0_5_true(self) -> None:
        """1 HT goal is over 0.5."""
        result = compute_ht_over_0_5(pd.Series([1]), pd.Series([0]))
        assert result.iloc[0] == True  # noqa: E712

    def test_ht_over_0_5_false(self) -> None:
        """0 HT goals is not over 0.5."""
        result = compute_ht_over_0_5(pd.Series([0]), pd.Series([0]))
        assert result.iloc[0] == False  # noqa: E712


# ---------------------------------------------------------------------------
# add_all_targets (integration)
# ---------------------------------------------------------------------------

class TestAddAllTargets:
    """Tests for add_all_targets orchestrator."""

    def test_adds_core_target_columns(self, match_df: pd.DataFrame) -> None:
        """All core target columns are present."""
        result = add_all_targets(match_df)
        expected_columns = [
            "result_1x2", "over_2_5", "btts",
            "over_1_5", "over_3_5",
            "home_goals_over_1_5", "away_goals_over_0_5",
            "home_or_draw", "home_or_away", "draw_or_away",
            "margin", "total_goals",
        ]
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"

    def test_does_not_modify_input(self, match_df: pd.DataFrame) -> None:
        """Input DataFrame is not mutated."""
        original_columns = list(match_df.columns)
        add_all_targets(match_df)
        assert list(match_df.columns) == original_columns

    def test_preserves_original_columns(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Original columns are still present."""
        result = add_all_targets(match_df)
        assert "home_goals" in result.columns
        assert "away_goals" in result.columns

    def test_row_count_unchanged(self, match_df: pd.DataFrame) -> None:
        """Row count stays the same."""
        result = add_all_targets(match_df)
        assert len(result) == len(match_df)

    def test_handles_missing_goals_gracefully(
        self, match_df_with_nan: pd.DataFrame,
    ) -> None:
        """NaN goals produce NaN targets without errors."""
        result = add_all_targets(match_df_with_nan)
        assert pd.isna(result["result_1x2"].iloc[1])
        assert pd.isna(result["over_2_5"].iloc[1])
        assert pd.isna(result["btts"].iloc[1])

    def test_adds_halftime_targets_when_available(
        self, match_df_with_halftime: pd.DataFrame,
    ) -> None:
        """Half-time targets are added when HT columns exist."""
        result = add_all_targets(match_df_with_halftime)
        assert "ht_result_1x2" in result.columns
        assert "ht_over_0_5" in result.columns

    def test_skips_halftime_targets_when_missing(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Half-time targets are not added when HT columns are missing."""
        result = add_all_targets(match_df)
        assert "ht_result_1x2" not in result.columns
        assert "ht_over_0_5" not in result.columns

    def test_specific_values_home_win_3_1(self) -> None:
        """Verify exact target values for a 3-1 home win."""
        df = pd.DataFrame({"home_goals": [3], "away_goals": [1]})
        result = add_all_targets(df)
        assert result["result_1x2"].iloc[0] == "H"
        assert result["over_2_5"].iloc[0] == True  # noqa: E712
        assert result["over_1_5"].iloc[0] == True  # noqa: E712
        assert result["over_3_5"].iloc[0] == True  # noqa: E712
        assert result["btts"].iloc[0] == True  # noqa: E712
        assert result["home_goals_over_1_5"].iloc[0] == True  # noqa: E712
        assert result["away_goals_over_0_5"].iloc[0] == True  # noqa: E712
        assert result["home_or_draw"].iloc[0] == True  # noqa: E712
        assert result["home_or_away"].iloc[0] == True  # noqa: E712
        assert result["draw_or_away"].iloc[0] == False  # noqa: E712
        assert result["margin"].iloc[0] == 2
        assert result["total_goals"].iloc[0] == 4

    def test_specific_values_0_0_draw(self) -> None:
        """Verify exact target values for a 0-0 draw."""
        df = pd.DataFrame({"home_goals": [0], "away_goals": [0]})
        result = add_all_targets(df)
        assert result["result_1x2"].iloc[0] == "D"
        assert result["over_2_5"].iloc[0] == False  # noqa: E712
        assert result["over_1_5"].iloc[0] == False  # noqa: E712
        assert result["over_3_5"].iloc[0] == False  # noqa: E712
        assert result["btts"].iloc[0] == False  # noqa: E712
        assert result["home_goals_over_1_5"].iloc[0] == False  # noqa: E712
        assert result["away_goals_over_0_5"].iloc[0] == False  # noqa: E712
        assert result["home_or_draw"].iloc[0] == True  # noqa: E712
        assert result["home_or_away"].iloc[0] == False  # noqa: E712
        assert result["draw_or_away"].iloc[0] == True  # noqa: E712
        assert result["margin"].iloc[0] == 0
        assert result["total_goals"].iloc[0] == 0

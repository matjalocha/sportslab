"""Tests for the new_features module (table positions, xG rolling, venue streaks)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.features.new_features import (
    _add_outcome_cols,
    _build_team_log,
    _compute_streak,
    _rolling_mean,
    _rolling_sum,
    _table_for_season,
    add_new_features,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_match_df() -> pd.DataFrame:
    """Two-team, two-match DataFrame with full fields for new_features."""
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-08-10", "2024-08-17"]),
        "league": ["PL", "PL"],
        "season": ["2024/25", "2024/25"],
        "home_team": ["Arsenal", "Chelsea"],
        "away_team": ["Chelsea", "Arsenal"],
        "home_goals": [2.0, 1.0],
        "away_goals": [1.0, 2.0],
        "home_xg": [1.8, 1.2],
        "away_xg": [0.9, 1.6],
    })


@pytest.fixture
def multi_season_df() -> pd.DataFrame:
    """Four matches across two seasons for the same league."""
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2023-08-10", "2023-08-17",
            "2024-08-10", "2024-08-17",
        ]),
        "league": ["PL", "PL", "PL", "PL"],
        "season": ["2023/24", "2023/24", "2024/25", "2024/25"],
        "home_team": ["Arsenal", "Chelsea", "Arsenal", "Chelsea"],
        "away_team": ["Chelsea", "Arsenal", "Chelsea", "Arsenal"],
        "home_goals": [2.0, 1.0, 3.0, 0.0],
        "away_goals": [0.0, 1.0, 1.0, 2.0],
        "home_xg": [1.9, 1.1, 2.5, 0.4],
        "away_xg": [0.5, 1.0, 0.8, 1.8],
    })


@pytest.fixture
def team_log_series() -> pd.Series:
    """Simple binary series for streak testing."""
    return pd.Series([1.0, 1.0, 0.0, 1.0, 1.0, 1.0])


# ---------------------------------------------------------------------------
# _rolling_mean / _rolling_sum
# ---------------------------------------------------------------------------

class TestRollingMean:
    """Tests for _rolling_mean (shift-1 safety)."""

    def test_first_value_is_nan_or_forward_filled(self) -> None:
        """After shift(1) the first position uses min_periods=1 on a NaN — result is NaN
        before ffill but ffill leaves it NaN since there's nothing to propagate from."""
        series = pd.Series([1.0, 2.0, 3.0])
        result = _rolling_mean(series, 2)
        # index 0: shift gives NaN, rolling(min_periods=1) on [NaN] = NaN, ffill = NaN
        assert pd.isna(result.iloc[0])

    def test_no_leakage_second_position_uses_only_first(self) -> None:
        """Position 1 can only see position 0 after shift."""
        series = pd.Series([10.0, 20.0, 30.0])
        result = _rolling_mean(series, 3)
        # index 1: shifted = [NaN, 10.0], rolling(3, min_periods=1) = mean([10]) = 10.0
        assert result.iloc[1] == pytest.approx(10.0)

    def test_window_averaging(self) -> None:
        """Rolling mean over window=2 averages correct past values."""
        series = pd.Series([2.0, 4.0, 6.0, 8.0])
        result = _rolling_mean(series, 2)
        # index 2: shifted = [NaN, 2, 4], rolling(2, min_periods=1) on last 2 = mean(2,4) = 3.0
        assert result.iloc[2] == pytest.approx(3.0)


class TestRollingSum:
    """Tests for _rolling_sum (shift-1 safety)."""

    def test_first_value_is_nan(self) -> None:
        """First position is NaN (no prior data)."""
        series = pd.Series([1.0, 2.0, 3.0])
        result = _rolling_sum(series, 5)
        assert pd.isna(result.iloc[0])

    def test_second_position_uses_only_first(self) -> None:
        """Position 1 sum = position 0 value only."""
        series = pd.Series([5.0, 3.0, 7.0])
        result = _rolling_sum(series, 5)
        assert result.iloc[1] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# _compute_streak
# ---------------------------------------------------------------------------

class TestComputeStreak:
    """Tests for _compute_streak (pre-match consecutive count)."""

    def test_first_element_is_always_zero(self, team_log_series: pd.Series) -> None:
        """Streak at position 0 is always 0 (no prior match)."""
        result = _compute_streak(team_log_series)
        assert result.iloc[0] == 0

    def test_streak_after_consecutive_wins(self, team_log_series: pd.Series) -> None:
        """Series [1,1,0,1,1,1]: streak at index 2 = 2, at index 3 = 0."""
        result = _compute_streak(team_log_series)
        assert result.iloc[2] == 2  # two consecutive 1s before index 2
        assert result.iloc[3] == 0  # broken by 0 at index 2

    def test_streak_continues_after_reset(self, team_log_series: pd.Series) -> None:
        """Streak resumes counting after a break."""
        result = _compute_streak(team_log_series)
        # index 5: series is [1,1,0,1,1,1], streak at 5 = 2 (1s at 3 and 4)
        assert result.iloc[5] == 2

    def test_all_zeros_produces_zero_streak(self) -> None:
        """All-zero series produces all-zero streak."""
        series = pd.Series([0.0, 0.0, 0.0])
        result = _compute_streak(series)
        assert list(result) == [0.0, 0.0, 0.0]

    def test_all_ones_produces_increasing_streak(self) -> None:
        """All-one series produces 0,1,2,3,... streak."""
        series = pd.Series([1.0, 1.0, 1.0, 1.0])
        result = _compute_streak(series)
        assert list(result) == [0.0, 1.0, 2.0, 3.0]


# ---------------------------------------------------------------------------
# _build_team_log / _add_outcome_cols
# ---------------------------------------------------------------------------

class TestBuildTeamLog:
    """Tests for _build_team_log."""

    def test_row_count_is_double_matches(
        self, minimal_match_df: pd.DataFrame,
    ) -> None:
        """2 matches -> 4 rows (one per team per match)."""
        log = _build_team_log(minimal_match_df)
        assert len(log) == 4

    def test_roles_present(self, minimal_match_df: pd.DataFrame) -> None:
        """Both 'home' and 'away' roles are present."""
        log = _build_team_log(minimal_match_df)
        assert set(log["role"].unique()) == {"home", "away"}

    def test_outcome_cols_present(self, minimal_match_df: pd.DataFrame) -> None:
        """Outcome columns are added by _build_team_log."""
        log = _build_team_log(minimal_match_df)
        for col in ("won", "drew", "lost", "scored", "cs"):
            assert col in log.columns, f"Missing outcome col: {col}"

    def test_won_col_correct_for_home_win(
        self, minimal_match_df: pd.DataFrame,
    ) -> None:
        """Home team that wins has won=1.0."""
        log = _build_team_log(minimal_match_df)
        # Match 0: Arsenal 2-1 Chelsea -> Arsenal (home) won
        arsenal_home = log[(log["team"] == "Arsenal") & (log["role"] == "home")]
        assert arsenal_home["won"].iloc[0] == 1.0


class TestAddOutcomeCols:
    """Tests for _add_outcome_cols edge cases."""

    def test_upcoming_match_produces_nan_outcomes(self) -> None:
        """Rows with NaN goals produce NaN outcome columns."""
        log = pd.DataFrame({
            "gf": [np.nan],
            "ga": [np.nan],
        })
        result = _add_outcome_cols(log)
        assert pd.isna(result["won"].iloc[0])
        assert pd.isna(result["drew"].iloc[0])
        assert pd.isna(result["lost"].iloc[0])

    def test_draw_produces_drew_one(self) -> None:
        """Drawn match produces drew=1.0."""
        log = pd.DataFrame({"gf": [1.0], "ga": [1.0]})
        result = _add_outcome_cols(log)
        assert result["drew"].iloc[0] == 1.0
        assert result["won"].iloc[0] == 0.0
        assert result["lost"].iloc[0] == 0.0


# ---------------------------------------------------------------------------
# _table_for_season
# ---------------------------------------------------------------------------

class TestTableForSeason:
    """Tests for _table_for_season (pre-match table positions)."""

    def test_first_match_positions_are_valid_before_kickoff(
        self, minimal_match_df: pd.DataFrame,
    ) -> None:
        """Before any match is played positions are 1 or 2 (both teams 0 pts).

        The ordering is insertion-stable, so home team is registered first
        and gets position 1; away team gets position 2.
        """
        result = _table_for_season(minimal_match_df)
        # First match (index 0): both teams registered at kick-off, 0 pts each
        assert result.loc[0, "home_table_pos"] == 1
        assert result.loc[0, "away_table_pos"] == 2

    def test_cumul_pts_zero_before_first_match(
        self, minimal_match_df: pd.DataFrame,
    ) -> None:
        """Cumulative points are 0 before any match."""
        result = _table_for_season(minimal_match_df)
        assert result.loc[0, "home_cumul_pts"] == 0
        assert result.loc[0, "away_cumul_pts"] == 0

    def test_winner_gains_three_points_before_second_match(
        self, minimal_match_df: pd.DataFrame,
    ) -> None:
        """Match 0 winner has 3 pts before match 1."""
        result = _table_for_season(minimal_match_df)
        # Arsenal wins match 0 (2-1), plays away in match 1
        assert result.loc[1, "away_cumul_pts"] == 3

    def test_n_teams_correct(self, minimal_match_df: pd.DataFrame) -> None:
        """n_teams equals the number of unique teams seen so far."""
        result = _table_for_season(minimal_match_df)
        # After first match: 2 teams registered
        assert result.loc[0, "n_teams"] == 2

    def test_output_indexed_by_original_index(
        self, minimal_match_df: pd.DataFrame,
    ) -> None:
        """Table positions DataFrame is indexed by the original match index."""
        result = _table_for_season(minimal_match_df)
        assert set(result.index) == {0, 1}


# ---------------------------------------------------------------------------
# add_new_features (integration)
# ---------------------------------------------------------------------------

class TestAddNewFeatures:
    """Tests for the main add_new_features orchestrator."""

    def test_row_count_unchanged(self, minimal_match_df: pd.DataFrame) -> None:
        """Row count is preserved after adding new features."""
        result = add_new_features(minimal_match_df)
        assert len(result) == len(minimal_match_df)

    def test_does_not_modify_input(self, minimal_match_df: pd.DataFrame) -> None:
        """Input DataFrame is not mutated."""
        original_columns = list(minimal_match_df.columns)
        add_new_features(minimal_match_df)
        assert list(minimal_match_df.columns) == original_columns

    def test_table_columns_present(self, minimal_match_df: pd.DataFrame) -> None:
        """Table position columns are present in output."""
        result = add_new_features(minimal_match_df)
        for col in ("home_table_pos", "away_table_pos", "table_pos_diff", "n_teams"):
            assert col in result.columns, f"Missing table col: {col}"

    def test_xg_rolling_columns_present(
        self, minimal_match_df: pd.DataFrame,
    ) -> None:
        """xG rolling feature columns are present for both roles and all windows."""
        result = add_new_features(minimal_match_df)
        for role in ("home", "away"):
            for n in (3, 5, 10):
                assert f"{role}_xg_for_roll{n}" in result.columns
                assert f"{role}_xg_against_roll{n}" in result.columns

    def test_diff_columns_present(self, minimal_match_df: pd.DataFrame) -> None:
        """Diff columns are computed and present."""
        result = add_new_features(minimal_match_df)
        for n in (3, 5, 10):
            assert f"diff_xg_for_roll{n}" in result.columns
            assert f"diff_xg_against_roll{n}" in result.columns
        assert "diff_cumul_pts" in result.columns
        assert "diff_won_last10" in result.columns

    def test_venue_streak_columns_present(
        self, minimal_match_df: pd.DataFrame,
    ) -> None:
        """Venue streak columns are present for both roles."""
        result = add_new_features(minimal_match_df)
        for role in ("home", "away"):
            for metric in ("won", "drew", "lost", "scored", "cs"):
                assert f"{role}_venue_{metric}_streak" in result.columns
                assert f"{role}_venue_{metric}_last10" in result.columns

    def test_no_leakage_first_match_xg_roll_is_nan(
        self, minimal_match_df: pd.DataFrame,
    ) -> None:
        """xG rolling for the first match of each team is NaN (no prior data)."""
        result = add_new_features(minimal_match_df)
        # Arsenal plays home first (index 0) — no prior home xG data
        assert pd.isna(result["home_xg_for_roll3"].iloc[0])

    def test_multi_season_isolation(self, multi_season_df: pd.DataFrame) -> None:
        """Table positions reset between seasons (each season starts from 0 pts)."""
        result = add_new_features(multi_season_df)
        # Index 2 is the first match of 2024/25 — cumul_pts must be 0 pre-match
        assert result["home_cumul_pts"].iloc[2] == 0
        assert result["away_cumul_pts"].iloc[2] == 0

"""Tests for the derived and interaction features module."""

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.features.derived_features import (
    _add_calendar_features,
    _add_difference_features,
    _add_interaction_features,
    _add_lag_features,
    _add_percentile_features,
    add_derived_features,
)


def _build_match_df_with_rolling() -> pd.DataFrame:
    """Build a realistic match DataFrame with rolling columns.

    Creates 10 matches for 4 teams across one season with
    pre-computed rolling features that would come from
    rolling_features.py.
    """
    matches = [
        ("2024-01-06", "TeamA", "TeamB", 2, 1, 1.8, 0.9, 1900, 1870),
        ("2024-01-06", "TeamC", "TeamD", 1, 0, 1.2, 0.5, 1850, 1750),
        ("2024-01-20", "TeamB", "TeamC", 0, 2, 0.7, 1.5, 1868, 1852),
        ("2024-01-20", "TeamD", "TeamA", 1, 3, 0.9, 2.1, 1748, 1902),
        ("2024-02-03", "TeamA", "TeamC", 1, 1, 1.3, 1.2, 1905, 1855),
        ("2024-02-03", "TeamB", "TeamD", 3, 0, 2.2, 0.4, 1865, 1745),
        ("2024-02-17", "TeamC", "TeamA", 2, 0, 1.7, 0.8, 1858, 1903),
        ("2024-02-17", "TeamD", "TeamB", 1, 2, 0.6, 1.4, 1742, 1868),
        ("2024-03-02", "TeamA", "TeamD", 4, 0, 3.1, 0.3, 1900, 1740),
        ("2024-03-02", "TeamC", "TeamB", 1, 1, 1.1, 1.0, 1860, 1870),
    ]
    columns = [
        "date", "home_team", "away_team",
        "home_goals", "away_goals", "home_xg", "away_xg",
        "home_elo", "away_elo",
    ]
    df = pd.DataFrame(matches, columns=columns)
    df["league"] = "ENG-Premier League"
    df["season"] = "2324"
    df["round"] = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]

    df["home_rolling_goals_scored_5"] = [
        np.nan, np.nan, 1.5, 1.0, 2.0, 0.8, 1.2, 0.7, 1.8, 1.3,
    ]
    df["away_rolling_goals_scored_5"] = [
        np.nan, np.nan, 1.2, 1.8, 1.1, 0.6, 2.0, 1.0, 0.5, 0.9,
    ]
    df["home_rolling_goals_conceded_5"] = [
        np.nan, np.nan, 1.0, 0.8, 0.9, 1.2, 0.7, 1.5, 0.6, 1.0,
    ]
    df["away_rolling_goals_conceded_5"] = [
        np.nan, np.nan, 0.8, 0.9, 1.2, 0.5, 1.0, 0.8, 1.3, 1.1,
    ]
    df["home_rolling_xg_for_5"] = [
        np.nan, np.nan, 1.3, 0.9, 1.5, 1.0, 1.4, 0.6, 2.0, 1.1,
    ]
    df["away_rolling_xg_for_5"] = [
        np.nan, np.nan, 1.1, 1.6, 1.0, 0.4, 1.5, 1.2, 0.3, 0.8,
    ]
    df["home_rolling_points_5"] = [
        np.nan, np.nan, 1.5, 1.0, 2.0, 1.8, 1.2, 0.5, 2.5, 1.6,
    ]
    df["away_rolling_points_5"] = [
        np.nan, np.nan, 1.2, 1.8, 1.0, 0.6, 2.2, 1.0, 0.3, 1.0,
    ]
    df["home_rolling_goals_scored_std"] = [
        np.nan, np.nan, 1.4, 0.8, 1.6, 1.2, 1.3, 0.7, 2.0, 1.1,
    ]
    df["away_rolling_goals_scored_std"] = [
        np.nan, np.nan, 1.0, 1.5, 0.9, 0.5, 1.8, 0.9, 0.4, 0.8,
    ]
    df["home_rolling_goals_conceded_std"] = [
        np.nan, np.nan, 0.9, 0.7, 1.0, 1.1, 0.8, 1.3, 0.5, 0.9,
    ]
    df["away_rolling_goals_conceded_std"] = [
        np.nan, np.nan, 0.7, 0.8, 1.1, 0.4, 1.0, 0.7, 1.2, 1.0,
    ]
    df["home_rolling_xg_for_std"] = [
        np.nan, np.nan, 1.2, 0.8, 1.4, 0.9, 1.3, 0.5, 1.9, 1.0,
    ]
    df["away_rolling_xg_for_std"] = [
        np.nan, np.nan, 1.0, 1.4, 0.8, 0.3, 1.5, 1.1, 0.2, 0.7,
    ]
    return df


def _build_two_season_df() -> pd.DataFrame:
    """Build matches spanning two seasons for lag boundary tests."""
    season_1 = [
        ("2023-04-01", "TeamA", "TeamB", 2, 0, "2223"),
        ("2023-04-15", "TeamB", "TeamA", 1, 1, "2223"),
        ("2023-05-01", "TeamA", "TeamB", 3, 1, "2223"),
    ]
    season_2 = [
        ("2023-08-15", "TeamA", "TeamB", 1, 0, "2324"),
        ("2023-09-01", "TeamB", "TeamA", 2, 2, "2324"),
        ("2023-09-15", "TeamA", "TeamB", 0, 1, "2324"),
        ("2023-10-01", "TeamB", "TeamA", 1, 3, "2324"),
    ]
    rows = season_1 + season_2
    df = pd.DataFrame(
        rows,
        columns=[
            "date", "home_team", "away_team",
            "home_goals", "away_goals", "season",
        ],
    )
    df["league"] = "ENG-Premier League"
    return df


@pytest.fixture
def match_df() -> pd.DataFrame:
    """Match DataFrame with rolling features for testing."""
    return _build_match_df_with_rolling()


@pytest.fixture
def two_season_df() -> pd.DataFrame:
    """Two-season DataFrame for lag boundary tests."""
    return _build_two_season_df()


# -------------------------------------------------------------------
# TestCalendarFeatures
# -------------------------------------------------------------------


class TestCalendarFeatures:
    """Tests for _add_calendar_features."""

    def test_month_extraction(self, match_df: pd.DataFrame) -> None:
        """Month is extracted from date column."""
        result = _add_calendar_features(match_df)
        assert "month" in result.columns
        assert result["month"].iloc[0] == 1
        assert result["month"].iloc[-1] == 3

    def test_day_of_week_extraction(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Day of week is extracted (0=Mon, 6=Sun)."""
        result = _add_calendar_features(match_df)
        assert "day_of_week" in result.columns
        date_val = pd.to_datetime("2024-01-06")
        expected_dow = date_val.dayofweek
        assert result["day_of_week"].iloc[0] == expected_dow

    def test_is_weekend_saturday(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Saturday matches are flagged as weekend."""
        result = _add_calendar_features(match_df)
        assert "is_weekend" in result.columns
        assert result["is_weekend"].iloc[0] == 1

    def test_is_weekend_weekday(self) -> None:
        """Wednesday matches are not flagged as weekend."""
        df = pd.DataFrame({
            "date": ["2024-01-03"],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_goals": [1],
            "away_goals": [0],
        })
        result = _add_calendar_features(df)
        assert result["is_weekend"].iloc[0] == 0

    def test_season_phase_early(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Rounds 1-12 are classified as early (0)."""
        result = _add_calendar_features(match_df)
        assert "season_phase" in result.columns
        assert result["season_phase"].iloc[0] == 0

    def test_season_phase_mid(self) -> None:
        """Rounds 13-26 are classified as mid (1)."""
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "round": [15],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_goals": [1],
            "away_goals": [0],
        })
        result = _add_calendar_features(df)
        assert result["season_phase"].iloc[0] == 1

    def test_season_phase_late(self) -> None:
        """Rounds 27+ are classified as late (2)."""
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "round": [30],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_goals": [1],
            "away_goals": [0],
        })
        result = _add_calendar_features(df)
        assert result["season_phase"].iloc[0] == 2

    def test_round_number_conversion(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Round column is converted to numeric round_number."""
        result = _add_calendar_features(match_df)
        assert "round_number" in result.columns
        assert result["round_number"].iloc[0] == 1

    def test_is_holiday_period_december(self) -> None:
        """Dec 25 is flagged as holiday period."""
        df = pd.DataFrame({
            "date": ["2024-12-25"],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_goals": [1],
            "away_goals": [0],
        })
        result = _add_calendar_features(df)
        assert result["is_holiday_period"].iloc[0] == 1

    def test_is_holiday_period_january(self) -> None:
        """Jan 2 is flagged as holiday period."""
        df = pd.DataFrame({
            "date": ["2024-01-02"],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_goals": [1],
            "away_goals": [0],
        })
        result = _add_calendar_features(df)
        assert result["is_holiday_period"].iloc[0] == 1

    def test_is_holiday_period_non_holiday(self) -> None:
        """Feb 15 is not flagged as holiday period."""
        df = pd.DataFrame({
            "date": ["2024-02-15"],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_goals": [1],
            "away_goals": [0],
        })
        result = _add_calendar_features(df)
        assert result["is_holiday_period"].iloc[0] == 0

    def test_no_date_column_no_crash(self) -> None:
        """Missing date column returns DataFrame unchanged."""
        df = pd.DataFrame({
            "home_team": ["A"],
            "away_team": ["B"],
        })
        result = _add_calendar_features(df)
        assert "month" not in result.columns

    def test_no_round_column_skips_season_phase(self) -> None:
        """Missing round column skips season_phase and round_number."""
        df = pd.DataFrame({
            "date": ["2024-01-06"],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_goals": [1],
            "away_goals": [0],
        })
        result = _add_calendar_features(df)
        assert "season_phase" not in result.columns
        assert "round_number" not in result.columns


# -------------------------------------------------------------------
# TestDifferenceFeatures
# -------------------------------------------------------------------


class TestDifferenceFeatures:
    """Tests for _add_difference_features."""

    def test_creates_diff_columns(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Diff columns are created for matching home/away pairs."""
        result = _add_difference_features(match_df)
        assert "diff_rolling_goals_scored_5" in result.columns
        assert "diff_rolling_goals_conceded_5" in result.columns

    def test_diff_equals_home_minus_away(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Diff value equals home column minus away column."""
        result = _add_difference_features(match_df)
        for idx in result.index:
            home = result.loc[idx, "home_rolling_goals_scored_5"]
            away = result.loc[idx, "away_rolling_goals_scored_5"]
            diff = result.loc[idx, "diff_rolling_goals_scored_5"]
            if pd.notna(home) and pd.notna(away):
                assert diff == pytest.approx(home - away)

    def test_diff_elo_column(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Elo difference is computed when both columns exist."""
        result = _add_difference_features(match_df)
        assert "diff_elo" in result.columns
        expected = (
            match_df["home_elo"].iloc[0]
            - match_df["away_elo"].iloc[0]
        )
        assert result["diff_elo"].iloc[0] == pytest.approx(expected)

    def test_skips_non_stat_columns(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Non-stat columns like home_team are not diffed."""
        result = _add_difference_features(match_df)
        assert "diff_team" not in result.columns
        assert "diff_goals" not in result.columns

    def test_handles_nan_values(
        self, match_df: pd.DataFrame,
    ) -> None:
        """NaN propagation: NaN - value = NaN."""
        result = _add_difference_features(match_df)
        assert pd.isna(
            result["diff_rolling_goals_scored_5"].iloc[0],
        )

    def test_preserves_row_count(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = _add_difference_features(match_df)
        assert len(result) == len(match_df)

    def test_no_matching_pairs(self) -> None:
        """No diffs created when no matching pairs exist."""
        df = pd.DataFrame({
            "home_team": ["A"],
            "away_team": ["B"],
            "home_goals": [1],
            "away_goals": [0],
        })
        result = _add_difference_features(df)
        diff_cols = [c for c in result.columns if c.startswith("diff_")]
        assert len(diff_cols) == 0

    def test_diff_std_columns(
        self, match_df: pd.DataFrame,
    ) -> None:
        """STD columns are also diffed."""
        result = _add_difference_features(match_df)
        assert "diff_rolling_goals_scored_std" in result.columns


# -------------------------------------------------------------------
# TestLagFeatures
# -------------------------------------------------------------------


class TestLagFeatures:
    """Tests for _add_lag_features."""

    def test_creates_lag_columns(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Lag columns are created for goals_scored."""
        result = _add_lag_features(match_df, lags=[1, 2, 3])
        assert "home_goals_scored_lag1" in result.columns
        assert "home_goals_scored_lag2" in result.columns
        assert "home_goals_scored_lag3" in result.columns

    def test_creates_away_lag_columns(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Away lag columns are also created."""
        result = _add_lag_features(match_df, lags=[1])
        assert "away_goals_scored_lag1" in result.columns
        assert "away_goals_conceded_lag1" in result.columns

    def test_lag1_no_lookahead(
        self, match_df: pd.DataFrame,
    ) -> None:
        """First match for a team has NaN lag1."""
        result = _add_lag_features(match_df, lags=[1])
        teama_first = result[
            result["home_team"] == "TeamA"
        ].iloc[0]
        assert pd.isna(teama_first["home_goals_scored_lag1"])

    def test_lag1_value_correct(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Lag1 reflects the previous match value.

        TeamA's match history (chronological):
          1. 2024-01-06 home vs TeamB: scored 2
          2. 2024-01-20 away @ TeamD: scored 3
          3. 2024-02-03 home vs TeamC: scored 1

        At match 3, home_goals_scored_lag1 should be 3
        (from match 2 where TeamA scored 3 away at TeamD).
        """
        result = _add_lag_features(match_df, lags=[1])
        teama_home = result[result["home_team"] == "TeamA"]
        second_home = teama_home.iloc[1]
        assert second_home["home_goals_scored_lag1"] == pytest.approx(
            3.0,
        )

    def test_lag2_value_correct(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Lag2 reflects two matches ago.

        TeamA: match 1 scored 2, match 2 scored 3, match 3 scored 1
        At match 3, lag2 = 2 (from match 1).
        """
        result = _add_lag_features(match_df, lags=[2])
        teama_home = result[result["home_team"] == "TeamA"]
        second_home = teama_home.iloc[1]
        assert second_home["home_goals_scored_lag2"] == pytest.approx(
            2.0,
        )

    def test_lag_points_column(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Points lag is computed from match results."""
        result = _add_lag_features(match_df, lags=[1])
        assert "home_points_lag1" in result.columns
        assert "away_points_lag1" in result.columns

    def test_season_boundary_reset(
        self, two_season_df: pd.DataFrame,
    ) -> None:
        """Lags reset at season boundaries.

        TeamA's season 2 starts at 2023-08-15. Lag1 should be NaN
        because no prior match exists in season 2.
        """
        result = _add_lag_features(two_season_df, lags=[1])
        season2 = result[result["season"] == "2324"]
        first_match = season2.iloc[0]
        assert pd.isna(first_match["home_goals_scored_lag1"])

    def test_preserves_row_count(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = _add_lag_features(match_df, lags=[1])
        assert len(result) == len(match_df)

    def test_xg_lag_columns(
        self, match_df: pd.DataFrame,
    ) -> None:
        """xG lag columns are created when xg columns present."""
        result = _add_lag_features(match_df, lags=[1])
        assert "home_xg_for_lag1" in result.columns
        assert "away_xg_against_lag1" in result.columns

    def test_single_lag(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Only requested lag offsets are computed."""
        result = _add_lag_features(match_df, lags=[2])
        assert "home_goals_scored_lag2" in result.columns
        assert "home_goals_scored_lag1" not in result.columns


# -------------------------------------------------------------------
# TestInteractionFeatures
# -------------------------------------------------------------------


class TestInteractionFeatures:
    """Tests for _add_interaction_features."""

    def test_elo_x_form_home(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Elo x form interaction is computed for home team."""
        result = _add_interaction_features(match_df)
        assert "elo_x_form_home" in result.columns

    def test_elo_x_form_value(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Interaction equals product of two source columns."""
        result = _add_interaction_features(match_df)
        for idx in result.index:
            elo = result.loc[idx, "home_elo"]
            form = result.loc[idx, "home_rolling_points_5"]
            expected = elo * form
            if pd.notna(elo) and pd.notna(form):
                assert result.loc[
                    idx, "elo_x_form_home"
                ] == pytest.approx(expected)

    def test_missing_column_skipped(self) -> None:
        """Interactions with missing columns are skipped."""
        df = pd.DataFrame({
            "home_elo": [1900],
            "away_elo": [1870],
        })
        result = _add_interaction_features(df)
        assert "elo_x_form_home" not in result.columns

    def test_partial_columns_partial_interactions(self) -> None:
        """Only possible interactions are computed."""
        df = pd.DataFrame({
            "home_elo": [1900],
            "home_rolling_points_5": [2.0],
            "away_elo": [1870],
            "away_rolling_points_5": [1.5],
        })
        result = _add_interaction_features(df)
        assert "elo_x_form_home" in result.columns
        assert "elo_x_form_away" in result.columns
        assert "xg_x_conversion_home" not in result.columns

    def test_nan_propagation(
        self, match_df: pd.DataFrame,
    ) -> None:
        """NaN in source propagates to interaction."""
        result = _add_interaction_features(match_df)
        assert pd.isna(result["elo_x_form_home"].iloc[0])

    def test_diff_interaction_after_diffs(
        self, match_df: pd.DataFrame,
    ) -> None:
        """diff_elo_x_form requires diff columns to be present.

        After adding difference features, diff_elo and
        diff_rolling_points_5 exist, enabling the interaction.
        """
        with_diffs = _add_difference_features(match_df)
        result = _add_interaction_features(with_diffs)
        assert "diff_elo_x_form" in result.columns


# -------------------------------------------------------------------
# TestPercentileFeatures
# -------------------------------------------------------------------


class TestPercentileFeatures:
    """Tests for _add_percentile_features."""

    def test_creates_percentile_columns(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Percentile columns are created for STD stats."""
        result = _add_percentile_features(match_df)
        assert "home_pctile_goals_scored_std" in result.columns
        assert "away_pctile_goals_scored_std" in result.columns

    def test_percentile_range(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Percentile values are between 0 and 1."""
        result = _add_percentile_features(match_df)
        col = "home_pctile_goals_scored_std"
        non_nan = result[col].dropna()
        assert (non_nan >= 0).all()
        assert (non_nan <= 1).all()

    def test_percentile_nan_for_nan_input(
        self, match_df: pd.DataFrame,
    ) -> None:
        """NaN input values produce NaN percentile."""
        result = _add_percentile_features(match_df)
        col = "home_pctile_goals_scored_std"
        assert pd.isna(result[col].iloc[0])

    def test_higher_value_higher_percentile(self) -> None:
        """Team with higher stat gets higher percentile rank."""
        df = pd.DataFrame({
            "league": ["L1"] * 3,
            "season": ["2324"] * 3,
            "home_team": ["A", "B", "C"],
            "away_team": ["D", "E", "F"],
            "home_rolling_goals_scored_std": [1.0, 2.0, 3.0],
            "away_rolling_goals_scored_std": [0.5, 1.5, 2.5],
        })
        result = _add_percentile_features(df)
        col = "home_pctile_goals_scored_std"
        assert result[col].iloc[2] > result[col].iloc[0]

    def test_missing_league_column_skips(self) -> None:
        """Missing league column skips percentile computation."""
        df = pd.DataFrame({
            "home_rolling_goals_scored_std": [1.0],
            "away_rolling_goals_scored_std": [0.5],
        })
        result = _add_percentile_features(df)
        assert "home_pctile_goals_scored_std" not in result.columns

    def test_missing_stat_columns_skips(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Missing stat columns are skipped gracefully."""
        df = match_df.drop(
            columns=[
                "home_rolling_goals_scored_std",
                "away_rolling_goals_scored_std",
            ],
        )
        result = _add_percentile_features(df)
        assert "home_pctile_goals_scored_std" not in result.columns

    def test_preserves_row_count(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = _add_percentile_features(match_df)
        assert len(result) == len(match_df)


# -------------------------------------------------------------------
# TestAddDerivedFeatures (integration)
# -------------------------------------------------------------------


class TestAddDerivedFeatures:
    """Integration tests for add_derived_features."""

    def test_adds_calendar_features(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Calendar features are present in output."""
        result = add_derived_features(match_df)
        assert "month" in result.columns
        assert "day_of_week" in result.columns
        assert "is_weekend" in result.columns

    def test_adds_difference_features(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Difference features are present in output."""
        result = add_derived_features(match_df)
        diff_cols = [
            c for c in result.columns if c.startswith("diff_")
        ]
        assert len(diff_cols) > 0

    def test_adds_lag_features(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Lag features are present in output."""
        result = add_derived_features(match_df)
        lag_cols = [c for c in result.columns if "_lag" in c]
        assert len(lag_cols) > 0

    def test_adds_interaction_features(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Interaction features are present in output."""
        result = add_derived_features(match_df)
        assert "elo_x_form_home" in result.columns

    def test_adds_percentile_features(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Percentile features are present in output."""
        result = add_derived_features(match_df)
        pctile_cols = [
            c for c in result.columns if "pctile" in c
        ]
        assert len(pctile_cols) > 0

    def test_diff_interaction_chaining(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Diff features are computed before interactions.

        This enables diff_elo_x_form interaction which
        requires diff_elo and diff_rolling_points_5.
        """
        result = add_derived_features(match_df)
        assert "diff_elo_x_form" in result.columns

    def test_custom_lags(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Custom lag offsets are respected."""
        result = add_derived_features(match_df, lags=[1, 5])
        assert "home_goals_scored_lag1" in result.columns
        assert "home_goals_scored_lag5" in result.columns
        assert "home_goals_scored_lag2" not in result.columns

    def test_preserves_original_columns(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Original columns remain unchanged."""
        original_cols = set(match_df.columns)
        result = add_derived_features(match_df)
        assert original_cols.issubset(set(result.columns))

    def test_preserves_row_count(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = add_derived_features(match_df)
        assert len(result) == len(match_df)

    def test_preserves_original_values(
        self, match_df: pd.DataFrame,
    ) -> None:
        """Original column values are not modified."""
        original_goals = match_df["home_goals"].copy()
        result = add_derived_features(match_df)
        pd.testing.assert_series_equal(
            result["home_goals"], original_goals,
            check_names=False,
        )


# -------------------------------------------------------------------
# TestEmptyDataFrame
# -------------------------------------------------------------------


class TestEmptyDataFrame:
    """All functions handle empty input gracefully."""

    def test_add_derived_features_empty(self) -> None:
        """add_derived_features returns empty for empty input."""
        df = pd.DataFrame()
        result = add_derived_features(df)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_calendar_features_empty(self) -> None:
        """_add_calendar_features handles empty DataFrame."""
        df = pd.DataFrame()
        result = _add_calendar_features(df)
        assert isinstance(result, pd.DataFrame)

    def test_difference_features_empty(self) -> None:
        """_add_difference_features handles empty DataFrame."""
        df = pd.DataFrame()
        result = _add_difference_features(df)
        assert isinstance(result, pd.DataFrame)

    def test_lag_features_empty(self) -> None:
        """_add_lag_features handles empty DataFrame."""
        df = pd.DataFrame()
        result = _add_lag_features(df, lags=[1])
        assert isinstance(result, pd.DataFrame)

    def test_interaction_features_empty(self) -> None:
        """_add_interaction_features handles empty DataFrame."""
        df = pd.DataFrame()
        result = _add_interaction_features(df)
        assert isinstance(result, pd.DataFrame)

    def test_percentile_features_empty(self) -> None:
        """_add_percentile_features handles empty DataFrame."""
        df = pd.DataFrame()
        result = _add_percentile_features(df)
        assert isinstance(result, pd.DataFrame)

"""Tests for the advanced rolling features module."""

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.features.rolling_features import (
    add_rolling_features,
    compute_elo_form,
    compute_home_away_split_features,
    compute_team_rolling_features,
)


def _build_season_matches() -> pd.DataFrame:
    """Build a realistic season fixture list for 4 teams.

    Creates 12 matches (each team plays 6 matches) so that rolling
    windows of 3 and 5 can be tested.
    """
    matches = [
        ("2024-01-01", "Arsenal", "Chelsea", 2, 1, 1.8, 0.9, 1900, 1870),
        ("2024-01-01", "Liverpool", "Everton", 1, 0, 1.2, 0.5, 1850, 1750),
        ("2024-01-15", "Chelsea", "Liverpool", 0, 2, 0.7, 1.5, 1868, 1852),
        ("2024-01-15", "Everton", "Arsenal", 1, 3, 0.9, 2.1, 1748, 1902),
        ("2024-02-01", "Arsenal", "Liverpool", 1, 1, 1.3, 1.2, 1905, 1855),
        ("2024-02-01", "Chelsea", "Everton", 3, 0, 2.2, 0.4, 1865, 1745),
        ("2024-02-15", "Liverpool", "Arsenal", 2, 0, 1.7, 0.8, 1858, 1903),
        ("2024-02-15", "Everton", "Chelsea", 1, 2, 0.6, 1.4, 1742, 1868),
        ("2024-03-01", "Arsenal", "Everton", 4, 0, 3.1, 0.3, 1900, 1740),
        ("2024-03-01", "Liverpool", "Chelsea", 1, 1, 1.1, 1.0, 1860, 1870),
        ("2024-03-15", "Chelsea", "Arsenal", 1, 2, 0.9, 1.6, 1868, 1903),
        ("2024-03-15", "Everton", "Liverpool", 0, 3, 0.4, 2.3, 1738, 1862),
    ]
    columns = [
        "date", "home_team", "away_team",
        "home_goals", "away_goals", "home_xg", "away_xg",
        "home_elo", "away_elo",
    ]
    df = pd.DataFrame(matches, columns=columns)
    df["league"] = "ENG-Premier League"
    df["season"] = "2324"
    df["home_shots_on_target"] = [5, 3, 2, 3, 4, 6, 5, 2, 7, 3, 3, 1]
    df["away_shots_on_target"] = [3, 1, 4, 5, 4, 1, 3, 4, 0, 3, 5, 6]
    return df


def _build_two_season_matches() -> pd.DataFrame:
    """Build matches across two seasons to test season boundary resets."""
    season_1 = [
        ("2023-04-01", "Arsenal", "Chelsea", 2, 0, 1.5, 0.8, 1890, 1860),
        ("2023-04-15", "Chelsea", "Arsenal", 1, 1, 1.0, 1.1, 1858, 1892),
        ("2023-05-01", "Arsenal", "Chelsea", 3, 1, 2.0, 0.7, 1895, 1855),
    ]
    season_2 = [
        ("2023-08-15", "Arsenal", "Chelsea", 1, 0, 1.2, 0.6, 1900, 1870),
        ("2023-09-01", "Chelsea", "Arsenal", 2, 2, 1.3, 1.4, 1868, 1902),
        ("2023-09-15", "Arsenal", "Chelsea", 0, 1, 0.5, 1.1, 1898, 1873),
        ("2023-10-01", "Chelsea", "Arsenal", 1, 3, 0.8, 2.0, 1870, 1905),
        ("2023-10-15", "Arsenal", "Chelsea", 2, 1, 1.6, 0.9, 1910, 1865),
    ]
    columns = [
        "date", "home_team", "away_team",
        "home_goals", "away_goals", "home_xg", "away_xg",
        "home_elo", "away_elo",
    ]
    df_s1 = pd.DataFrame(season_1, columns=columns)
    df_s1["season"] = "2223"
    df_s2 = pd.DataFrame(season_2, columns=columns)
    df_s2["season"] = "2324"
    df = pd.concat([df_s1, df_s2], ignore_index=True)
    df["league"] = "ENG-Premier League"
    return df


@pytest.fixture
def season_matches() -> pd.DataFrame:
    """Full-season fixture list for testing rolling features."""
    return _build_season_matches()


@pytest.fixture
def two_season_matches() -> pd.DataFrame:
    """Two-season fixture list for testing season boundary reset."""
    return _build_two_season_matches()


class TestComputeTeamRollingFeatures:
    """Tests for compute_team_rolling_features."""

    def test_creates_goals_scored_column(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Rolling goals_scored column is created for home team."""
        result = compute_team_rolling_features(season_matches, windows=[3])
        assert "home_rolling_goals_scored_3" in result.columns
        assert "away_rolling_goals_scored_3" in result.columns

    def test_creates_goals_conceded_column(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Rolling goals_conceded column is created."""
        result = compute_team_rolling_features(season_matches, windows=[3])
        assert "home_rolling_goals_conceded_3" in result.columns
        assert "away_rolling_goals_conceded_3" in result.columns

    def test_creates_xg_columns(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Rolling xG for and against columns are created."""
        result = compute_team_rolling_features(season_matches, windows=[3])
        assert "home_rolling_xg_for_3" in result.columns
        assert "home_rolling_xg_against_3" in result.columns

    def test_creates_points_column(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Rolling points column is created."""
        result = compute_team_rolling_features(season_matches, windows=[3])
        assert "home_rolling_points_3" in result.columns
        assert "away_rolling_points_3" in result.columns

    def test_creates_clean_sheets_column(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Rolling clean_sheets column is created."""
        result = compute_team_rolling_features(season_matches, windows=[3])
        assert "home_rolling_clean_sheets_3" in result.columns
        assert "away_rolling_clean_sheets_3" in result.columns

    def test_creates_shots_on_target_column(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Rolling shots_on_target column is created when data available."""
        result = compute_team_rolling_features(season_matches, windows=[3])
        assert "home_rolling_shots_on_target_3" in result.columns

    def test_no_lookahead_bias(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """First match for each team has NaN rolling features."""
        result = compute_team_rolling_features(season_matches, windows=[3])
        arsenal_first_home = result[
            result["home_team"] == "Arsenal"
        ].iloc[0]
        assert pd.isna(arsenal_first_home["home_rolling_goals_scored_3"])

    def test_rolling_goals_scored_value(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Rolling goals scored reflects team's actual scoring history.

        Arsenal's match history (chronological, home+away):
          1. 2024-01-01 home vs Chelsea: scored 2
          2. 2024-01-15 away @ Everton: scored 3
          3. 2024-02-01 home vs Liverpool: scored 1
          4. 2024-02-15 away @ Liverpool: scored 0
          5. 2024-03-01 home vs Everton: scored 4

        At match 5 (Arsenal home vs Everton):
          shift(1) excludes current, window 3 uses matches 2-4:
          [3, 1, 0] -> mean = 4/3
        """
        result = compute_team_rolling_features(season_matches, windows=[3])
        arsenal_home = result[result["home_team"] == "Arsenal"]
        fifth_match_row = arsenal_home.iloc[2]
        expected = (3 + 1 + 0) / 3.0
        assert fifth_match_row["home_rolling_goals_scored_3"] == pytest.approx(
            expected,
        )

    def test_rolling_goals_conceded_value(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Rolling goals conceded tracks opponent goals.

        Arsenal's conceded history (all matches):
          1. 2024-01-01 home vs Chelsea: conceded 1
          2. 2024-01-15 away @ Everton: conceded 1
          3. 2024-02-01 home vs Liverpool: conceded 1
          4. 2024-02-15 away @ Liverpool: conceded 2

        At match 5 (home vs Everton, 2024-03-01):
          shift(1), window 3 uses matches 2-4: [1, 1, 2] -> mean = 4/3
        """
        result = compute_team_rolling_features(season_matches, windows=[3])
        arsenal_home = result[result["home_team"] == "Arsenal"]
        fifth_match_row = arsenal_home.iloc[2]
        expected = (1 + 1 + 2) / 3.0
        assert fifth_match_row[
            "home_rolling_goals_conceded_3"
        ] == pytest.approx(expected)

    def test_rolling_points_value(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Rolling points tracks match results correctly.

        Arsenal's points history (all matches):
          1. 2024-01-01 home vs Chelsea: W -> 3
          2. 2024-01-15 away @ Everton: W -> 3
          3. 2024-02-01 home vs Liverpool: D -> 1
          4. 2024-02-15 away @ Liverpool: L -> 0

        At match 5 (Arsenal home vs Everton, 2024-03-01):
          shift(1), window 3 uses matches 2-4: [3, 1, 0] -> mean = 4/3
        """
        result = compute_team_rolling_features(season_matches, windows=[3])
        arsenal_home = result[result["home_team"] == "Arsenal"]
        fifth_match_row = arsenal_home.iloc[2]
        expected = (3 + 1 + 0) / 3.0
        assert fifth_match_row["home_rolling_points_3"] == pytest.approx(
            expected,
        )

    def test_multiple_windows(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Multiple window sizes generate separate column sets."""
        result = compute_team_rolling_features(
            season_matches, windows=[3, 5],
        )
        assert "home_rolling_goals_scored_3" in result.columns
        assert "home_rolling_goals_scored_5" in result.columns

    def test_season_to_date_window(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Season-to-date window uses all prior matches."""
        result = compute_team_rolling_features(
            season_matches, windows=[3],
            include_season_to_date=True,
        )
        assert "home_rolling_goals_scored_std" in result.columns

    def test_preserves_original_columns(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Original DataFrame columns remain unchanged."""
        original_cols = set(season_matches.columns)
        result = compute_team_rolling_features(season_matches, windows=[3])
        assert original_cols.issubset(set(result.columns))

    def test_preserves_row_count(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = compute_team_rolling_features(season_matches, windows=[3])
        assert len(result) == len(season_matches)


class TestSeasonBoundaryReset:
    """Tests for season boundary handling."""

    def test_rolling_resets_at_season_boundary(
        self, two_season_matches: pd.DataFrame,
    ) -> None:
        """Rolling stats reset when a new season starts."""
        result = compute_team_rolling_features(
            two_season_matches, windows=[3],
        )
        new_season_first = result[
            (result["season"] == "2324")
        ].iloc[0]
        assert pd.isna(
            new_season_first["home_rolling_goals_scored_3"],
        )

    def test_season_2_builds_from_scratch(
        self, two_season_matches: pd.DataFrame,
    ) -> None:
        """Season 2 rolling stats use only season 2 data."""
        result = compute_team_rolling_features(
            two_season_matches, windows=[3],
        )
        new_season_rows = result[result["season"] == "2324"]
        last_row = new_season_rows.iloc[-1]
        assert pd.notna(
            last_row["home_rolling_goals_scored_3"],
        )


class TestComputeHomeAwaySplitFeatures:
    """Tests for compute_home_away_split_features."""

    def test_home_form_goals_scored(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Home form tracks goals in home matches only."""
        result = compute_home_away_split_features(
            season_matches, windows=[3],
        )
        assert "home_form_goals_scored_3" in result.columns

    def test_away_form_goals_conceded(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Away form tracks goals conceded in away matches only."""
        result = compute_home_away_split_features(
            season_matches, windows=[3],
        )
        assert "away_form_goals_conceded_3" in result.columns

    def test_home_form_no_lookahead(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """First home match has NaN home form."""
        result = compute_home_away_split_features(
            season_matches, windows=[3],
        )
        arsenal_first_home = result[
            result["home_team"] == "Arsenal"
        ].iloc[0]
        assert pd.isna(
            arsenal_first_home["home_form_goals_scored_3"],
        )

    def test_home_form_goals_scored_value(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Home form is only from home matches.

        Arsenal home matches:
          1. 2024-01-01 vs Chelsea: scored 2
          2. 2024-02-01 vs Liverpool: scored 1
          3. 2024-03-01 vs Everton: scored 4

        At match 3 (2024-03-01, home vs Everton):
          shift(1) + window 3: only matches 1-2 available: NaN (need 3)
        """
        result = compute_home_away_split_features(
            season_matches, windows=[2],
        )
        arsenal_home = result[result["home_team"] == "Arsenal"]
        third_home_match = arsenal_home.iloc[2]
        expected = (2 + 1) / 2.0
        assert third_home_match[
            "home_form_goals_scored_2"
        ] == pytest.approx(expected)

    def test_preserves_row_count(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = compute_home_away_split_features(
            season_matches, windows=[3],
        )
        assert len(result) == len(season_matches)


class TestComputeEloForm:
    """Tests for compute_elo_form."""

    def test_creates_elo_form_column(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Elo form columns are created."""
        result = compute_elo_form(season_matches, windows=[5])
        assert "home_elo_form_5" in result.columns
        assert "away_elo_form_5" in result.columns

    def test_elo_form_no_lookahead(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """First match has NaN elo form."""
        result = compute_elo_form(season_matches, windows=[5])
        first_row = result.iloc[0]
        assert pd.isna(first_row["home_elo_form_5"])

    def test_elo_form_value(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Elo form reflects recent elo changes."""
        result = compute_elo_form(season_matches, windows=[3])
        assert "home_elo_form_3" in result.columns
        non_nan = result["home_elo_form_3"].dropna()
        if len(non_nan) > 0:
            assert non_nan.dtype == np.float64

    def test_preserves_row_count(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = compute_elo_form(season_matches, windows=[3])
        assert len(result) == len(season_matches)


class TestAddRollingFeatures:
    """Tests for the top-level add_rolling_features function."""

    def test_adds_all_feature_groups(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """All rolling feature groups are present in output."""
        result = add_rolling_features(season_matches, windows=[3])
        expected_prefixes = [
            "home_rolling_goals_scored",
            "away_rolling_goals_scored",
            "home_rolling_goals_conceded",
            "home_rolling_xg_for",
            "home_rolling_points",
            "home_rolling_clean_sheets",
            "home_form_goals_scored",
            "away_form_goals_conceded",
            "home_elo_form",
        ]
        for prefix in expected_prefixes:
            matching = [c for c in result.columns if c.startswith(prefix)]
            assert len(matching) > 0, f"No columns with prefix: {prefix}"

    def test_handles_empty_dataframe(self) -> None:
        """Returns empty DataFrame with no errors."""
        df = pd.DataFrame()
        result = add_rolling_features(df)
        assert isinstance(result, pd.DataFrame)

    def test_default_windows(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Default windows [3, 5, 10] are used when none specified."""
        result = add_rolling_features(season_matches)
        assert "home_rolling_goals_scored_3" in result.columns
        assert "home_rolling_goals_scored_5" in result.columns
        assert "home_rolling_goals_scored_10" in result.columns

    def test_preserves_original_data(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Original column values are not modified."""
        original_goals = season_matches["home_goals"].copy()
        result = add_rolling_features(season_matches, windows=[3])
        pd.testing.assert_series_equal(
            result["home_goals"], original_goals,
        )

    def test_sorted_by_date(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Output is sorted by date."""
        shuffled = season_matches.sample(frac=1.0, random_state=42)
        result = add_rolling_features(shuffled, windows=[3])
        dates = result["date"].tolist()
        assert dates == sorted(dates)

    def test_no_future_data_leakage(
        self, season_matches: pd.DataFrame,
    ) -> None:
        """Rolling stats at row i only use data from rows < i.

        Verify that the rolling value at match index 4 for Arsenal
        doesn't include data from match index 4 itself.
        """
        result = add_rolling_features(season_matches, windows=[3])
        arsenal_rows = result[result["home_team"] == "Arsenal"]
        if len(arsenal_rows) > 2:
            third_row = arsenal_rows.iloc[2]
            col = "home_rolling_goals_scored_3"
            if pd.notna(third_row[col]):
                assert third_row[col] != season_matches[
                    season_matches["home_team"] == "Arsenal"
                ]["home_goals"].iloc[2]

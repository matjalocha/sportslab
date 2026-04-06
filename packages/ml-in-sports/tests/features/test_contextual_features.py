"""Tests for the contextual features module.

Covers venue-specific season-to-date, fatigue, and head-to-head
feature computation with lookahead prevention validation.
"""

import pandas as pd
import pytest
from ml_in_sports.features.contextual_features import (
    _add_fatigue_features,
    _add_h2h_features,
    _add_venue_std_features,
    add_contextual_features,
)

# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

def _build_match_data() -> pd.DataFrame:
    """Build a realistic match dataset for 4 teams across a season.

    Creates 12 matches where each team plays 6 times.
    Matches are spread across 6 matchdays.
    """
    matches = [
        ("2024-01-06", "2324", "Arsenal", "Chelsea", 2, 1),
        ("2024-01-06", "2324", "Liverpool", "Everton", 1, 0),
        ("2024-01-20", "2324", "Chelsea", "Liverpool", 0, 2),
        ("2024-01-20", "2324", "Everton", "Arsenal", 1, 3),
        ("2024-02-03", "2324", "Arsenal", "Liverpool", 1, 1),
        ("2024-02-03", "2324", "Chelsea", "Everton", 3, 0),
        ("2024-02-17", "2324", "Liverpool", "Arsenal", 2, 0),
        ("2024-02-17", "2324", "Everton", "Chelsea", 1, 2),
        ("2024-03-02", "2324", "Arsenal", "Everton", 4, 0),
        ("2024-03-02", "2324", "Liverpool", "Chelsea", 1, 1),
        ("2024-03-16", "2324", "Chelsea", "Arsenal", 1, 2),
        ("2024-03-16", "2324", "Everton", "Liverpool", 0, 3),
    ]
    columns = [
        "date", "season", "home_team", "away_team",
        "home_goals", "away_goals",
    ]
    df = pd.DataFrame(matches, columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    df["league"] = "ENG-Premier League"
    df["game"] = (
        df["date"].dt.strftime("%Y-%m-%d")
        + " "
        + df["home_team"]
        + "-"
        + df["away_team"]
    )
    return df


def _build_h2h_data() -> pd.DataFrame:
    """Build a dataset focused on Arsenal vs Chelsea meetings.

    Creates 8 meetings between Arsenal and Chelsea over 2 seasons,
    plus some filler matches to test isolation.
    """
    h2h_matches = [
        ("2023-01-07", "2223", "Arsenal", "Chelsea", 2, 0),
        ("2023-02-11", "2223", "Chelsea", "Arsenal", 1, 1),
        ("2023-03-18", "2223", "Arsenal", "Chelsea", 3, 1),
        ("2023-04-22", "2223", "Chelsea", "Arsenal", 0, 2),
        ("2024-01-06", "2324", "Arsenal", "Chelsea", 1, 0),
        ("2024-02-10", "2324", "Chelsea", "Arsenal", 2, 2),
        ("2024-03-16", "2324", "Arsenal", "Chelsea", 3, 1),
        ("2024-04-20", "2324", "Chelsea", "Arsenal", 0, 1),
    ]
    filler = [
        ("2023-01-14", "2223", "Arsenal", "Liverpool", 1, 0),
        ("2023-02-18", "2223", "Liverpool", "Arsenal", 2, 1),
        ("2024-01-13", "2324", "Arsenal", "Liverpool", 2, 2),
        ("2024-02-17", "2324", "Liverpool", "Arsenal", 0, 1),
    ]
    columns = [
        "date", "season", "home_team", "away_team",
        "home_goals", "away_goals",
    ]
    df = pd.DataFrame(h2h_matches + filler, columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    df["league"] = "ENG-Premier League"
    df["game"] = (
        df["date"].dt.strftime("%Y-%m-%d")
        + " "
        + df["home_team"]
        + "-"
        + df["away_team"]
    )
    return df.sort_values("date").reset_index(drop=True)


def _build_fatigue_data() -> pd.DataFrame:
    """Build a dataset with tight scheduling for fatigue tests.

    Arsenal plays 3 matches in 7 days, then has a 14-day break.
    """
    matches = [
        ("2024-01-01", "2324", "Arsenal", "Chelsea", 1, 0),
        ("2024-01-04", "2324", "Arsenal", "Liverpool", 2, 1),
        ("2024-01-07", "2324", "Everton", "Arsenal", 0, 1),
        ("2024-01-21", "2324", "Arsenal", "Everton", 3, 0),
        ("2024-01-01", "2324", "Liverpool", "Everton", 2, 2),
        ("2024-01-14", "2324", "Chelsea", "Everton", 1, 0),
        ("2024-01-21", "2324", "Chelsea", "Liverpool", 0, 2),
    ]
    columns = [
        "date", "season", "home_team", "away_team",
        "home_goals", "away_goals",
    ]
    df = pd.DataFrame(matches, columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    df["league"] = "ENG-Premier League"
    df["game"] = (
        df["date"].dt.strftime("%Y-%m-%d")
        + " "
        + df["home_team"]
        + "-"
        + df["away_team"]
    )
    return df.sort_values("date").reset_index(drop=True)


@pytest.fixture
def match_data() -> pd.DataFrame:
    """Standard match dataset for testing."""
    return _build_match_data()


@pytest.fixture
def h2h_data() -> pd.DataFrame:
    """Head-to-head focused dataset."""
    return _build_h2h_data()


@pytest.fixture
def fatigue_data() -> pd.DataFrame:
    """Fatigue-focused dataset with tight scheduling."""
    return _build_fatigue_data()


# -------------------------------------------------------------------
# Venue STD features
# -------------------------------------------------------------------

class TestVenueStdFeatures:
    """Tests for venue-specific season-to-date features."""

    def test_creates_home_venue_goals_scored_std(
        self, match_data: pd.DataFrame,
    ) -> None:
        """home_venue_goals_scored_std column is created."""
        result = _add_venue_std_features(match_data)
        assert "home_venue_goals_scored_std" in result.columns

    def test_creates_away_venue_goals_scored_std(
        self, match_data: pd.DataFrame,
    ) -> None:
        """away_venue_goals_scored_std column is created."""
        result = _add_venue_std_features(match_data)
        assert "away_venue_goals_scored_std" in result.columns

    def test_creates_home_venue_win_rate_std(
        self, match_data: pd.DataFrame,
    ) -> None:
        """home_venue_win_rate_std column is created."""
        result = _add_venue_std_features(match_data)
        assert "home_venue_win_rate_std" in result.columns

    def test_creates_away_venue_clean_sheets_std(
        self, match_data: pd.DataFrame,
    ) -> None:
        """away_venue_clean_sheets_std column is created."""
        result = _add_venue_std_features(match_data)
        assert "away_venue_clean_sheets_std" in result.columns

    def test_creates_home_venue_points_per_game_std(
        self, match_data: pd.DataFrame,
    ) -> None:
        """home_venue_points_per_game_std column is created."""
        result = _add_venue_std_features(match_data)
        assert "home_venue_points_per_game_std" in result.columns

    def test_no_lookahead_first_home_match(
        self, match_data: pd.DataFrame,
    ) -> None:
        """First home match for a team has NaN venue STD features."""
        result = _add_venue_std_features(match_data)
        arsenal_first_home = result[
            result["home_team"] == "Arsenal"
        ].iloc[0]
        assert pd.isna(
            arsenal_first_home["home_venue_goals_scored_std"],
        )

    def test_no_lookahead_first_away_match(
        self, match_data: pd.DataFrame,
    ) -> None:
        """First away match for a team has NaN venue STD features."""
        result = _add_venue_std_features(match_data)
        arsenal_first_away = result[
            result["away_team"] == "Arsenal"
        ].iloc[0]
        assert pd.isna(
            arsenal_first_away["away_venue_goals_scored_std"],
        )

    def test_home_venue_goals_scored_value(
        self, match_data: pd.DataFrame,
    ) -> None:
        """Home venue goals scored STD is correct for known history.

        Arsenal home matches (chronological):
          1. 2024-01-06 vs Chelsea: scored 2
          2. 2024-02-03 vs Liverpool: scored 1
          3. 2024-03-02 vs Everton: scored 4

        At match 3 (2024-03-02, home vs Everton):
          shift(1) -> expanding mean of [2, 1] = 1.5
        """
        result = _add_venue_std_features(match_data)
        arsenal_home = result[
            result["home_team"] == "Arsenal"
        ].sort_values("date")
        third_home = arsenal_home.iloc[2]
        expected = (2 + 1) / 2.0
        assert third_home[
            "home_venue_goals_scored_std"
        ] == pytest.approx(expected)

    def test_home_venue_win_rate_value(
        self, match_data: pd.DataFrame,
    ) -> None:
        """Home venue win rate STD is correct for known history.

        Arsenal home matches:
          1. 2024-01-06 vs Chelsea: W (2-1)
          2. 2024-02-03 vs Liverpool: D (1-1)
          3. 2024-03-02 vs Everton: W (4-0)

        At match 3: shift(1) -> expanding mean of [1, 0] = 0.5
        """
        result = _add_venue_std_features(match_data)
        arsenal_home = result[
            result["home_team"] == "Arsenal"
        ].sort_values("date")
        third_home = arsenal_home.iloc[2]
        expected = (1.0 + 0.0) / 2.0
        assert third_home[
            "home_venue_win_rate_std"
        ] == pytest.approx(expected)

    def test_preserves_row_count(
        self, match_data: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = _add_venue_std_features(match_data)
        assert len(result) == len(match_data)

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty DataFrame."""
        result = _add_venue_std_features(pd.DataFrame())
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# -------------------------------------------------------------------
# Fatigue features
# -------------------------------------------------------------------

class TestFatigueFeatures:
    """Tests for fatigue and scheduling features."""

    def test_creates_home_days_since_last(
        self, fatigue_data: pd.DataFrame,
    ) -> None:
        """home_days_since_last column is created."""
        result = _add_fatigue_features(fatigue_data)
        assert "home_days_since_last" in result.columns

    def test_creates_away_days_since_last(
        self, fatigue_data: pd.DataFrame,
    ) -> None:
        """away_days_since_last column is created."""
        result = _add_fatigue_features(fatigue_data)
        assert "away_days_since_last" in result.columns

    def test_creates_matches_last_14d(
        self, fatigue_data: pd.DataFrame,
    ) -> None:
        """home_matches_last_14d column is created."""
        result = _add_fatigue_features(fatigue_data)
        assert "home_matches_last_14d" in result.columns
        assert "away_matches_last_14d" in result.columns

    def test_creates_matches_last_7d(
        self, fatigue_data: pd.DataFrame,
    ) -> None:
        """home_matches_last_7d column is created."""
        result = _add_fatigue_features(fatigue_data)
        assert "home_matches_last_7d" in result.columns
        assert "away_matches_last_7d" in result.columns

    def test_first_match_has_nan_days_since(
        self, fatigue_data: pd.DataFrame,
    ) -> None:
        """First match for a team has NaN days since last."""
        result = _add_fatigue_features(fatigue_data)
        result_sorted = result.sort_values("date")
        arsenal_matches = result_sorted[
            (result_sorted["home_team"] == "Arsenal")
            | (result_sorted["away_team"] == "Arsenal")
        ]
        first_match = arsenal_matches.iloc[0]
        if first_match["home_team"] == "Arsenal":
            assert pd.isna(first_match["home_days_since_last"])
        else:
            assert pd.isna(first_match["away_days_since_last"])

    def test_days_since_last_value(
        self, fatigue_data: pd.DataFrame,
    ) -> None:
        """Days since last match is calculated correctly.

        Arsenal plays:
          Jan 01 (home vs Chelsea)
          Jan 04 (home vs Liverpool) -> 3 days
          Jan 07 (away at Everton) -> 3 days
          Jan 21 (home vs Everton) -> 14 days
        """
        result = _add_fatigue_features(fatigue_data)
        result_sorted = result.sort_values("date")
        arsenal_jan04 = result_sorted[
            (result_sorted["home_team"] == "Arsenal")
            & (result_sorted["date"] == pd.Timestamp("2024-01-04"))
        ]
        assert arsenal_jan04["home_days_since_last"].iloc[0] == 3.0

    def test_days_since_last_away(
        self, fatigue_data: pd.DataFrame,
    ) -> None:
        """Days since last match works for away team too.

        Arsenal: Jan 04 (home) -> Jan 07 (away at Everton) = 3 days
        """
        result = _add_fatigue_features(fatigue_data)
        result_sorted = result.sort_values("date")
        arsenal_jan07 = result_sorted[
            (result_sorted["away_team"] == "Arsenal")
            & (result_sorted["date"] == pd.Timestamp("2024-01-07"))
        ]
        assert arsenal_jan07["away_days_since_last"].iloc[0] == 3.0

    def test_matches_last_7d_value(
        self, fatigue_data: pd.DataFrame,
    ) -> None:
        """Matches in last 7 days is correct.

        Arsenal on Jan 07 (away at Everton):
          Prior matches within 7 days: Jan 01, Jan 04 -> 2 matches
        """
        result = _add_fatigue_features(fatigue_data)
        result_sorted = result.sort_values("date")
        arsenal_jan07 = result_sorted[
            (result_sorted["away_team"] == "Arsenal")
            & (result_sorted["date"] == pd.Timestamp("2024-01-07"))
        ]
        assert arsenal_jan07["away_matches_last_7d"].iloc[0] == 2

    def test_matches_last_14d_value(
        self, fatigue_data: pd.DataFrame,
    ) -> None:
        """Matches in last 14 days is correct.

        Arsenal on Jan 21 (home vs Everton):
          Prior matches within 14 days: Jan 07 -> 1 match
          (Jan 01 and Jan 04 are 20 and 17 days ago)
        """
        result = _add_fatigue_features(fatigue_data)
        result_sorted = result.sort_values("date")
        arsenal_jan21 = result_sorted[
            (result_sorted["home_team"] == "Arsenal")
            & (result_sorted["date"] == pd.Timestamp("2024-01-21"))
        ]
        assert arsenal_jan21["home_matches_last_14d"].iloc[0] == 1

    def test_preserves_row_count(
        self, fatigue_data: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = _add_fatigue_features(fatigue_data)
        assert len(result) == len(fatigue_data)

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty DataFrame."""
        result = _add_fatigue_features(pd.DataFrame())
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# -------------------------------------------------------------------
# Head-to-head features
# -------------------------------------------------------------------

class TestH2HFeatures:
    """Tests for head-to-head historical features."""

    def test_creates_h2h_home_wins_5(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """h2h_home_wins_5 column is created."""
        result = _add_h2h_features(h2h_data)
        assert "h2h_home_wins_5" in result.columns

    def test_creates_h2h_goals_avg_5(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """h2h_goals_avg_5 column is created."""
        result = _add_h2h_features(h2h_data)
        assert "h2h_goals_avg_5" in result.columns

    def test_creates_h2h_btts_rate_5(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """h2h_btts_rate_5 column is created."""
        result = _add_h2h_features(h2h_data)
        assert "h2h_btts_rate_5" in result.columns

    def test_creates_h2h_last_10_columns(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """Last-10 H2H columns are created."""
        result = _add_h2h_features(h2h_data)
        assert "h2h_home_wins_10" in result.columns
        assert "h2h_goals_avg_10" in result.columns
        assert "h2h_btts_rate_10" in result.columns

    def test_creates_h2h_home_goals_avg_5(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """h2h_home_goals_avg_5 column is created."""
        result = _add_h2h_features(h2h_data)
        assert "h2h_home_goals_avg_5" in result.columns

    def test_no_lookahead_first_meeting(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """First meeting between two teams has NaN H2H features."""
        result = _add_h2h_features(h2h_data)
        result_sorted = result.sort_values("date")
        ars_che = result_sorted[
            ((result_sorted["home_team"] == "Arsenal")
             & (result_sorted["away_team"] == "Chelsea"))
            | ((result_sorted["home_team"] == "Chelsea")
               & (result_sorted["away_team"] == "Arsenal"))
        ]
        first_meeting = ars_che.iloc[0]
        assert pd.isna(first_meeting["h2h_home_wins_5"])

    def test_h2h_home_wins_value(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """H2H home wins count is correct for known matchups.

        Arsenal vs Chelsea meetings (ordered):
          1. 2023-01-07 Ars(H) 2-0 Che -> home_win=1
          2. 2023-02-11 Che(H) 1-1 Ars -> home_win=0
          3. 2023-03-18 Ars(H) 3-1 Che -> home_win=1
          4. 2023-04-22 Che(H) 0-2 Ars -> home_win=0
          5. 2024-01-06 Ars(H) 1-0 Che -> home_win=1

        At match 6 (2024-02-10, Che(H) vs Ars):
          shift(1) uses meetings 1-5
          home_wins in last 5 = sum of home_win for meeting
          where current home=Chelsea: meetings 2(0) and 4(0)
          where current home=Arsenal: meetings 1(1), 3(1), 5(1)
          H2H home wins counts wins by the current home team.
          Current home = Chelsea.
          In last 5 meetings: Chelsea was home in #2 (drew) and
          #4 (lost). Arsenal was home in #1 (won), #3 (won), #5 (won).
          h2h_home_wins_5 = how many of last 5 the CURRENT home team
          won = 0 (Chelsea won 0 of those as home)
          ...Actually this is ambiguous. Let me re-read the spec.
          "h2h_home_wins_last_5 -- how many of last 5 meetings
           did home team win"
          This means: among the last 5 meetings between these
          two teams, how many did the HOME TEAM of the CURRENT
          match win (regardless of venue in past meetings).

        At match 6 (2024-02-10, Chelsea(H) vs Arsenal):
          Past 5 meetings: #1-#5
          Chelsea results in those: L, D, L, L, L -> 0 wins
        """
        result = _add_h2h_features(h2h_data)
        result_sorted = result.sort_values("date")
        che_home_feb = result_sorted[
            (result_sorted["home_team"] == "Chelsea")
            & (result_sorted["away_team"] == "Arsenal")
            & (result_sorted["date"] == pd.Timestamp("2024-02-10"))
        ]
        assert che_home_feb["h2h_home_wins_5"].iloc[0] == 0

    def test_h2h_goals_avg_value(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """H2H goals average is correct.

        At match 6 (2024-02-10, Chelsea vs Arsenal):
          Past 5 meetings:
            #1: 2+0=2, #2: 1+1=2, #3: 3+1=4, #4: 0+2=2, #5: 1+0=1
          avg = (2+2+4+2+1)/5 = 2.2
        """
        result = _add_h2h_features(h2h_data)
        result_sorted = result.sort_values("date")
        che_home_feb = result_sorted[
            (result_sorted["home_team"] == "Chelsea")
            & (result_sorted["away_team"] == "Arsenal")
            & (result_sorted["date"] == pd.Timestamp("2024-02-10"))
        ]
        expected = (2 + 2 + 4 + 2 + 1) / 5.0
        assert che_home_feb[
            "h2h_goals_avg_5"
        ].iloc[0] == pytest.approx(expected)

    def test_h2h_btts_rate_value(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """H2H BTTS rate is correct.

        At match 6 (2024-02-10):
          Past 5 meetings BTTS:
            #1: 2-0 No, #2: 1-1 Yes, #3: 3-1 Yes,
            #4: 0-2 No, #5: 1-0 No
          btts_rate = 2/5 = 0.4
        """
        result = _add_h2h_features(h2h_data)
        result_sorted = result.sort_values("date")
        che_home_feb = result_sorted[
            (result_sorted["home_team"] == "Chelsea")
            & (result_sorted["away_team"] == "Arsenal")
            & (result_sorted["date"] == pd.Timestamp("2024-02-10"))
        ]
        expected = 2.0 / 5.0
        assert che_home_feb[
            "h2h_btts_rate_5"
        ].iloc[0] == pytest.approx(expected)

    def test_h2h_only_uses_same_pair(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """H2H features only consider meetings between the same pair.

        Arsenal vs Liverpool matches should not affect
        Arsenal vs Chelsea H2H features.
        """
        result = _add_h2h_features(h2h_data)
        result_sorted = result.sort_values("date")
        ars_liv = result_sorted[
            (result_sorted["home_team"] == "Arsenal")
            & (result_sorted["away_team"] == "Liverpool")
        ]
        first_ars_liv = ars_liv.iloc[0]
        assert pd.isna(first_ars_liv["h2h_home_wins_5"])

    def test_preserves_row_count(
        self, h2h_data: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = _add_h2h_features(h2h_data)
        assert len(result) == len(h2h_data)

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty DataFrame."""
        result = _add_h2h_features(pd.DataFrame())
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# -------------------------------------------------------------------
# Orchestrator: add_contextual_features
# -------------------------------------------------------------------

class TestAddContextualFeatures:
    """Tests for the top-level orchestrator."""

    def test_returns_dataframe(
        self, match_data: pd.DataFrame,
    ) -> None:
        """Returns a pandas DataFrame."""
        result = add_contextual_features(match_data)
        assert isinstance(result, pd.DataFrame)

    def test_adds_venue_std_columns(
        self, match_data: pd.DataFrame,
    ) -> None:
        """Venue STD columns are present in output."""
        result = add_contextual_features(match_data)
        venue_cols = [
            c for c in result.columns if "venue_" in c
        ]
        assert len(venue_cols) > 0

    def test_adds_fatigue_columns(
        self, match_data: pd.DataFrame,
    ) -> None:
        """Fatigue columns are present in output."""
        result = add_contextual_features(match_data)
        assert "home_days_since_last" in result.columns
        assert "home_matches_last_14d" in result.columns

    def test_adds_h2h_columns(
        self, match_data: pd.DataFrame,
    ) -> None:
        """H2H columns are present in output."""
        result = add_contextual_features(match_data)
        h2h_cols = [
            c for c in result.columns if c.startswith("h2h_")
        ]
        assert len(h2h_cols) > 0

    def test_preserves_original_columns(
        self, match_data: pd.DataFrame,
    ) -> None:
        """Original DataFrame columns are preserved."""
        original_cols = set(match_data.columns)
        result = add_contextual_features(match_data)
        assert original_cols.issubset(set(result.columns))

    def test_preserves_row_count(
        self, match_data: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = add_contextual_features(match_data)
        assert len(result) == len(match_data)

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty DataFrame."""
        result = add_contextual_features(pd.DataFrame())
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_preserves_original_data(
        self, match_data: pd.DataFrame,
    ) -> None:
        """Original column values are not modified."""
        original_goals = match_data["home_goals"].copy()
        result = add_contextual_features(match_data)
        pd.testing.assert_series_equal(
            result["home_goals"],
            original_goals,
            check_names=False,
        )

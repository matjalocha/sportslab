"""Tests for the formation and tactical matchup features module.

Covers formation parsing, formation stability, performance vs N-back
systems, matchup features, and the orchestrator function.
"""

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.features.formation_features import (
    _compute_formation_stability,
    _compute_goals_scored_vs_nback,
    _compute_matchup_features,
    _compute_win_rate_current_formation,
    _compute_win_rate_vs_nback,
    add_formation_features,
    parse_formation,
)

# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

def _build_tm_games() -> pd.DataFrame:
    """Build a realistic tm_games DataFrame with formation data.

    Creates 12 matches across a single season with various formations.
    """
    games = [
        (1, "2324", "2024-01-06", 10, 20, "Arsenal FC", "Chelsea FC",
         2, 1, "4-2-3-1", "4-3-3 Attacking"),
        (2, "2324", "2024-01-06", 30, 40, "Liverpool FC", "Everton FC",
         1, 0, "4-3-3 Attacking", "3-5-2 flat"),
        (3, "2324", "2024-01-20", 20, 30, "Chelsea FC", "Liverpool FC",
         0, 2, "4-2-3-1", "4-3-3 Attacking"),
        (4, "2324", "2024-01-20", 40, 10, "Everton FC", "Arsenal FC",
         1, 3, "3-5-2 flat", "4-2-3-1"),
        (5, "2324", "2024-02-03", 10, 30, "Arsenal FC", "Liverpool FC",
         1, 1, "4-2-3-1", "4-3-3 Attacking"),
        (6, "2324", "2024-02-03", 20, 40, "Chelsea FC", "Everton FC",
         3, 0, "4-4-2 double 6", "3-5-2 flat"),
        (7, "2324", "2024-02-17", 30, 10, "Liverpool FC", "Arsenal FC",
         2, 0, "4-3-3 Attacking", "4-2-3-1"),
        (8, "2324", "2024-02-17", 40, 20, "Everton FC", "Chelsea FC",
         1, 2, "5-3-2", "4-4-2 double 6"),
        (9, "2324", "2024-03-02", 10, 40, "Arsenal FC", "Everton FC",
         4, 0, "4-2-3-1", "5-3-2"),
        (10, "2324", "2024-03-02", 30, 20, "Liverpool FC", "Chelsea FC",
         1, 1, "4-3-3 Attacking", "4-2-3-1"),
        (11, "2324", "2024-03-16", 20, 10, "Chelsea FC", "Arsenal FC",
         1, 2, "4-2-3-1", "4-2-3-1"),
        (12, "2324", "2024-03-16", 40, 30, "Everton FC", "Liverpool FC",
         0, 3, "3-5-2 flat", "4-3-3 Attacking"),
    ]
    columns = [
        "game_id", "season", "date", "home_club_id", "away_club_id",
        "home_club_name", "away_club_name",
        "home_club_goals", "away_club_goals",
        "home_club_formation", "away_club_formation",
    ]
    return pd.DataFrame(games, columns=columns)


def _build_match_data() -> pd.DataFrame:
    """Build a matches DataFrame matching the matches table schema."""
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


@pytest.fixture
def tm_games() -> pd.DataFrame:
    """Transfermarkt games with formation data."""
    return _build_tm_games()


@pytest.fixture
def match_data() -> pd.DataFrame:
    """Standard match dataset for testing."""
    return _build_match_data()


# -------------------------------------------------------------------
# Formation parsing
# -------------------------------------------------------------------

class TestParseFormation:
    """Tests for parse_formation helper."""

    def test_parse_4231(self) -> None:
        """Parse '4-2-3-1' into defenders=4, midfielders=5, forwards=1."""
        result = parse_formation("4-2-3-1")
        assert result["num_defenders"] == 4
        assert result["num_midfielders"] == 5
        assert result["num_forwards"] == 1
        assert result["formation_group"] == "4-back"

    def test_parse_352_flat(self) -> None:
        """Parse '3-5-2 flat' into defenders=3, midfielders=5, forwards=2."""
        result = parse_formation("3-5-2 flat")
        assert result["num_defenders"] == 3
        assert result["num_midfielders"] == 5
        assert result["num_forwards"] == 2
        assert result["formation_group"] == "3-back"

    def test_parse_433_attacking(self) -> None:
        """Parse '4-3-3 Attacking' -> defenders=4, mid=3, fwd=3."""
        result = parse_formation("4-3-3 Attacking")
        assert result["num_defenders"] == 4
        assert result["num_midfielders"] == 3
        assert result["num_forwards"] == 3
        assert result["formation_group"] == "4-back"

    def test_parse_541(self) -> None:
        """Parse '5-4-1' into defenders=5, midfielders=4, forwards=1."""
        result = parse_formation("5-4-1")
        assert result["num_defenders"] == 5
        assert result["num_midfielders"] == 4
        assert result["num_forwards"] == 1
        assert result["formation_group"] == "5-back"

    def test_parse_442_double_6(self) -> None:
        """Parse '4-4-2 double 6' -> defenders=4, mid=4, fwd=2."""
        result = parse_formation("4-4-2 double 6")
        assert result["num_defenders"] == 4
        assert result["num_midfielders"] == 4
        assert result["num_forwards"] == 2
        assert result["formation_group"] == "4-back"

    def test_parse_3421(self) -> None:
        """Parse '3-4-2-1' -> defenders=3, mid=6, fwd=1."""
        result = parse_formation("3-4-2-1")
        assert result["num_defenders"] == 3
        assert result["num_midfielders"] == 6
        assert result["num_forwards"] == 1
        assert result["formation_group"] == "3-back"

    def test_parse_4141(self) -> None:
        """Parse '4-1-4-1' -> defenders=4, mid=5, fwd=1."""
        result = parse_formation("4-1-4-1")
        assert result["num_defenders"] == 4
        assert result["num_midfielders"] == 5
        assert result["num_forwards"] == 1
        assert result["formation_group"] == "4-back"

    def test_parse_4312(self) -> None:
        """Parse '4-3-1-2' -> defenders=4, mid=4, fwd=2."""
        result = parse_formation("4-3-1-2")
        assert result["num_defenders"] == 4
        assert result["num_midfielders"] == 4
        assert result["num_forwards"] == 2
        assert result["formation_group"] == "4-back"

    def test_parse_343(self) -> None:
        """Parse '3-4-3' -> defenders=3, mid=4, fwd=3."""
        result = parse_formation("3-4-3")
        assert result["num_defenders"] == 3
        assert result["num_midfielders"] == 4
        assert result["num_forwards"] == 3
        assert result["formation_group"] == "3-back"

    def test_parse_532(self) -> None:
        """Parse '5-3-2' -> defenders=5, mid=3, fwd=2."""
        result = parse_formation("5-3-2")
        assert result["num_defenders"] == 5
        assert result["num_midfielders"] == 3
        assert result["num_forwards"] == 2
        assert result["formation_group"] == "5-back"

    def test_parse_none_returns_nans(self) -> None:
        """None formation returns NaN values."""
        result = parse_formation(None)
        assert np.isnan(float(result["num_defenders"]))  # type: ignore[arg-type]
        assert np.isnan(float(result["num_midfielders"]))  # type: ignore[arg-type]
        assert np.isnan(float(result["num_forwards"]))  # type: ignore[arg-type]
        assert result["formation_group"] is None

    def test_parse_empty_string_returns_nans(self) -> None:
        """Empty string formation returns NaN values."""
        result = parse_formation("")
        assert np.isnan(float(result["num_defenders"]))  # type: ignore[arg-type]
        assert result["formation_group"] is None

    def test_parse_nan_returns_nans(self) -> None:
        """NaN formation returns NaN values."""
        result = parse_formation(float("nan"))
        assert np.isnan(float(result["num_defenders"]))  # type: ignore[arg-type]
        assert result["formation_group"] is None


# -------------------------------------------------------------------
# Formation stability (rolling)
# -------------------------------------------------------------------

class TestFormationStability:
    """Tests for formation stability computation."""

    def test_stability_column_created(self, tm_games: pd.DataFrame) -> None:
        """Stability columns are created for requested windows."""
        result = _compute_formation_stability(tm_games, windows=[5])
        assert "formation_stability_5" in result.columns

    def test_stability_first_match_is_nan(
        self, tm_games: pd.DataFrame,
    ) -> None:
        """First match for a team has NaN stability (shift prevents lookahead)."""
        result = _compute_formation_stability(tm_games, windows=[5])
        arsenal_rows = result[result["team"] == "Arsenal FC"]
        first = arsenal_rows.sort_values("date").iloc[0]
        assert pd.isna(first["formation_stability_5"])

    def test_stability_value_all_same_formation(self) -> None:
        """Team using the same formation consistently has stability 1.0.

        Arsenal FC uses '4-2-3-1' in every match except match 11 where
        they switch. Create a scenario with 6 matches all same formation.
        """
        games = pd.DataFrame({
            "game_id": range(1, 7),
            "season": ["2324"] * 6,
            "date": pd.date_range("2024-01-01", periods=6, freq="14D"),
            "home_club_id": [10, 20, 10, 20, 10, 20],
            "away_club_id": [20, 10, 20, 10, 20, 10],
            "home_club_name": ["A", "B", "A", "B", "A", "B"],
            "away_club_name": ["B", "A", "B", "A", "B", "A"],
            "home_club_goals": [1, 0, 2, 1, 3, 0],
            "away_club_goals": [0, 1, 0, 2, 1, 2],
            "home_club_formation": ["4-2-3-1"] * 6,
            "away_club_formation": ["4-2-3-1"] * 6,
        })
        result = _compute_formation_stability(games, windows=[5])
        team_a = result[result["team"] == "A"].sort_values("date")
        last_row = team_a.iloc[-1]
        assert last_row["formation_stability_5"] == pytest.approx(1.0)

    def test_stability_value_mixed_formations(self) -> None:
        """Team switching formations has stability < 1.0.

        Team A plays 6 matches, alternating formations:
        4-2-3-1, 3-5-2, 4-2-3-1, 3-5-2, 4-2-3-1, 3-5-2
        """
        formations = ["4-2-3-1", "3-5-2 flat"] * 3
        games = pd.DataFrame({
            "game_id": range(1, 7),
            "season": ["2324"] * 6,
            "date": pd.date_range("2024-01-01", periods=6, freq="14D"),
            "home_club_id": [10] * 6,
            "away_club_id": [20] * 6,
            "home_club_name": ["A"] * 6,
            "away_club_name": ["B"] * 6,
            "home_club_goals": [1] * 6,
            "away_club_goals": [0] * 6,
            "home_club_formation": formations,
            "away_club_formation": ["4-4-2"] * 6,
        })
        result = _compute_formation_stability(games, windows=[5])
        team_a = result[result["team"] == "A"].sort_values("date")
        last_row = team_a.iloc[-1]
        # At last match (idx=5), shift(1) uses matches 0-4.
        # Current formation at match 5 is "3-5-2 flat".
        # In matches 0-4: formations are 4-2-3-1, 3-5-2 flat,
        # 4-2-3-1, 3-5-2 flat, 4-2-3-1.
        # Matching "3-5-2 flat": matches 1, 3 => 2/5 = 0.4
        assert last_row["formation_stability_5"] == pytest.approx(0.4)

    def test_stability_multiple_windows(
        self, tm_games: pd.DataFrame,
    ) -> None:
        """Both window 5 and 10 stability columns are created."""
        result = _compute_formation_stability(tm_games, windows=[5, 10])
        assert "formation_stability_5" in result.columns
        assert "formation_stability_10" in result.columns


# -------------------------------------------------------------------
# Win rate with current formation (STD)
# -------------------------------------------------------------------

class TestWinRateCurrentFormation:
    """Tests for season-to-date win rate when using current formation."""

    def test_column_created(self, tm_games: pd.DataFrame) -> None:
        """win_rate_current_formation_std column is created."""
        result = _compute_win_rate_current_formation(tm_games)
        assert "win_rate_current_formation_std" in result.columns

    def test_first_match_is_nan(self, tm_games: pd.DataFrame) -> None:
        """First match for a team has NaN win rate."""
        result = _compute_win_rate_current_formation(tm_games)
        arsenal_rows = result[result["team"] == "Arsenal FC"]
        first = arsenal_rows.sort_values("date").iloc[0]
        assert pd.isna(first["win_rate_current_formation_std"])

    def test_win_rate_value(self) -> None:
        """Win rate is correct for a known history.

        Team A plays 5 matches with '4-2-3-1':
        Match 1: W (goals 2-0)
        Match 2: L (goals 0-1)
        Match 3: W (goals 3-1)
        Match 4: L (goals 0-2)
        Match 5: W (goals 1-0) <-- query here

        At match 5: shift(1) uses matches 1-4 with same formation.
        All used '4-2-3-1'. Wins: 2 out of 4 -> 0.5
        """
        games = pd.DataFrame({
            "game_id": range(1, 6),
            "season": ["2324"] * 5,
            "date": pd.date_range("2024-01-01", periods=5, freq="14D"),
            "home_club_id": [10] * 5,
            "away_club_id": [20] * 5,
            "home_club_name": ["A"] * 5,
            "away_club_name": ["B"] * 5,
            "home_club_goals": [2, 0, 3, 0, 1],
            "away_club_goals": [0, 1, 1, 2, 0],
            "home_club_formation": ["4-2-3-1"] * 5,
            "away_club_formation": ["4-4-2"] * 5,
        })
        result = _compute_win_rate_current_formation(games)
        team_a = result[result["team"] == "A"].sort_values("date")
        last_row = team_a.iloc[-1]
        assert last_row["win_rate_current_formation_std"] == pytest.approx(
            0.5,
        )


# -------------------------------------------------------------------
# Performance vs N-back systems (STD)
# -------------------------------------------------------------------

class TestWinRateVsNback:
    """Tests for win rate vs 3/4/5-back systems."""

    def test_columns_created(self, tm_games: pd.DataFrame) -> None:
        """Win rate vs N-back columns are created."""
        result = _compute_win_rate_vs_nback(tm_games)
        assert "win_rate_vs_3back_std" in result.columns
        assert "win_rate_vs_4back_std" in result.columns
        assert "win_rate_vs_5back_std" in result.columns

    def test_first_match_is_nan(self, tm_games: pd.DataFrame) -> None:
        """First match vs a formation group has NaN."""
        result = _compute_win_rate_vs_nback(tm_games)
        arsenal_rows = result[result["team"] == "Arsenal FC"]
        first = arsenal_rows.sort_values("date").iloc[0]
        assert pd.isna(first["win_rate_vs_4back_std"])

    def test_win_rate_vs_3back_value(self) -> None:
        """Win rate vs 3-back is correct.

        Team A plays against 3-back teams:
        Match 1: vs 3-5-2 flat -> W (2-0)
        Match 2: vs 4-2-3-1 -> W (1-0) (not 3-back, skip)
        Match 3: vs 3-4-3 -> L (0-1)
        Match 4: vs 3-5-2 flat -> query here

        At match 4: shift(1) uses prior 3-back matches (1, 3).
        Wins vs 3-back: 1 out of 2 -> 0.5
        """
        games = pd.DataFrame({
            "game_id": range(1, 5),
            "season": ["2324"] * 4,
            "date": pd.date_range("2024-01-01", periods=4, freq="14D"),
            "home_club_id": [10] * 4,
            "away_club_id": [20] * 4,
            "home_club_name": ["A"] * 4,
            "away_club_name": ["B"] * 4,
            "home_club_goals": [2, 1, 0, 1],
            "away_club_goals": [0, 0, 1, 0],
            "home_club_formation": ["4-2-3-1"] * 4,
            "away_club_formation": [
                "3-5-2 flat", "4-2-3-1", "3-4-3", "3-5-2 flat",
            ],
        })
        result = _compute_win_rate_vs_nback(games)
        team_a = result[result["team"] == "A"].sort_values("date")
        last_row = team_a.iloc[-1]
        assert last_row["win_rate_vs_3back_std"] == pytest.approx(0.5)


class TestGoalsScoredVsNback:
    """Tests for goals scored vs N-back systems."""

    def test_columns_created(self, tm_games: pd.DataFrame) -> None:
        """Goals scored vs N-back columns are created."""
        result = _compute_goals_scored_vs_nback(tm_games)
        assert "goals_scored_vs_3back_std" in result.columns
        assert "goals_scored_vs_4back_std" in result.columns
        assert "goals_scored_vs_5back_std" in result.columns

    def test_goals_scored_vs_3back_value(self) -> None:
        """Goals scored vs 3-back is correct.

        Team A plays:
        Match 1: vs 3-5-2 flat -> scored 2
        Match 2: vs 4-2-3-1 -> scored 1 (skip, not 3-back)
        Match 3: vs 3-4-3 -> scored 0
        Match 4: vs 3-5-2 flat -> query here

        At match 4: expanding mean of goals vs 3-back = (2+0)/2 = 1.0
        """
        games = pd.DataFrame({
            "game_id": range(1, 5),
            "season": ["2324"] * 4,
            "date": pd.date_range("2024-01-01", periods=4, freq="14D"),
            "home_club_id": [10] * 4,
            "away_club_id": [20] * 4,
            "home_club_name": ["A"] * 4,
            "away_club_name": ["B"] * 4,
            "home_club_goals": [2, 1, 0, 1],
            "away_club_goals": [0, 0, 1, 0],
            "home_club_formation": ["4-2-3-1"] * 4,
            "away_club_formation": [
                "3-5-2 flat", "4-2-3-1", "3-4-3", "3-5-2 flat",
            ],
        })
        result = _compute_goals_scored_vs_nback(games)
        team_a = result[result["team"] == "A"].sort_values("date")
        last_row = team_a.iloc[-1]
        assert last_row["goals_scored_vs_3back_std"] == pytest.approx(1.0)


# -------------------------------------------------------------------
# Matchup features
# -------------------------------------------------------------------

class TestMatchupFeatures:
    """Tests for per-match matchup features."""

    def test_defender_mismatch_created(self) -> None:
        """defender_mismatch column is created."""
        df = pd.DataFrame({
            "home_num_defenders": [4, 3],
            "away_num_defenders": [3, 4],
            "home_num_midfielders": [5, 4],
            "away_num_midfielders": [4, 5],
            "home_num_forwards": [1, 3],
            "away_num_forwards": [3, 1],
        })
        result = _compute_matchup_features(df)
        assert "defender_mismatch" in result.columns
        assert "midfield_dominance" in result.columns

    def test_defender_mismatch_value(self) -> None:
        """defender_mismatch = home_num_forwards - away_num_defenders.

        Home plays 4-2-3-1 (fwd=1) vs Away 3-5-2 (def=3).
        Mismatch = 1 - 3 = -2
        """
        df = pd.DataFrame({
            "home_num_defenders": [4],
            "away_num_defenders": [3],
            "home_num_midfielders": [5],
            "away_num_midfielders": [5],
            "home_num_forwards": [1],
            "away_num_forwards": [2],
        })
        result = _compute_matchup_features(df)
        assert result["defender_mismatch"].iloc[0] == -2

    def test_midfield_dominance_value(self) -> None:
        """midfield_dominance = home_mid - away_mid.

        Home 4-2-3-1 (mid=5) vs Away 4-3-3 (mid=3).
        Dominance = 5 - 3 = 2
        """
        df = pd.DataFrame({
            "home_num_defenders": [4],
            "away_num_defenders": [4],
            "home_num_midfielders": [5],
            "away_num_midfielders": [3],
            "home_num_forwards": [1],
            "away_num_forwards": [3],
        })
        result = _compute_matchup_features(df)
        assert result["midfield_dominance"].iloc[0] == 2

    def test_matchup_with_nan_formation(self) -> None:
        """Matchup features are NaN when formations are missing."""
        df = pd.DataFrame({
            "home_num_defenders": [np.nan],
            "away_num_defenders": [4],
            "home_num_midfielders": [np.nan],
            "away_num_midfielders": [3],
            "home_num_forwards": [np.nan],
            "away_num_forwards": [3],
        })
        result = _compute_matchup_features(df)
        assert pd.isna(result["defender_mismatch"].iloc[0])
        assert pd.isna(result["midfield_dominance"].iloc[0])


# -------------------------------------------------------------------
# Empty / edge cases
# -------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and empty input."""

    def test_empty_dataframe(self) -> None:
        """Empty matches DataFrame returns empty DataFrame."""
        df = pd.DataFrame()
        tm = pd.DataFrame()
        result = add_formation_features(df, tm_games_df=tm)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_missing_formations_produce_nan(self) -> None:
        """Rows with missing formation strings get NaN parsed values."""
        matches = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-06"]),
            "season": ["2324"],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "home_goals": [2],
            "away_goals": [1],
            "league": ["ENG-Premier League"],
            "game": ["2024-01-06 Arsenal-Chelsea"],
        })
        tm = pd.DataFrame({
            "game_id": [1],
            "season": ["2324"],
            "date": ["2024-01-06"],
            "home_club_id": [10],
            "away_club_id": [20],
            "home_club_name": ["Arsenal FC"],
            "away_club_name": ["Chelsea FC"],
            "home_club_goals": [2],
            "away_club_goals": [1],
            "home_club_formation": [None],
            "away_club_formation": [None],
        })
        result = add_formation_features(matches, tm_games_df=tm)
        assert pd.isna(result["home_num_defenders"].iloc[0])
        assert pd.isna(result["away_num_defenders"].iloc[0])

    def test_preserves_row_count(
        self, match_data: pd.DataFrame, tm_games: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = add_formation_features(match_data, tm_games_df=tm_games)
        assert len(result) == len(match_data)

    def test_preserves_original_columns(
        self, match_data: pd.DataFrame, tm_games: pd.DataFrame,
    ) -> None:
        """Original DataFrame columns are preserved."""
        original_cols = set(match_data.columns)
        result = add_formation_features(match_data, tm_games_df=tm_games)
        assert original_cols.issubset(set(result.columns))


# -------------------------------------------------------------------
# Orchestrator: add_formation_features
# -------------------------------------------------------------------

class TestAddFormationFeatures:
    """Tests for the top-level orchestrator."""

    def test_returns_dataframe(
        self, match_data: pd.DataFrame, tm_games: pd.DataFrame,
    ) -> None:
        """Returns a pandas DataFrame."""
        result = add_formation_features(match_data, tm_games_df=tm_games)
        assert isinstance(result, pd.DataFrame)

    def test_adds_formation_parsing_columns(
        self, match_data: pd.DataFrame, tm_games: pd.DataFrame,
    ) -> None:
        """Formation parsing columns are present."""
        result = add_formation_features(match_data, tm_games_df=tm_games)
        for prefix in ["home", "away"]:
            assert f"{prefix}_num_defenders" in result.columns
            assert f"{prefix}_num_midfielders" in result.columns
            assert f"{prefix}_num_forwards" in result.columns
            assert f"{prefix}_formation_group" in result.columns

    def test_adds_stability_columns(
        self, match_data: pd.DataFrame, tm_games: pd.DataFrame,
    ) -> None:
        """Formation stability columns are present."""
        result = add_formation_features(match_data, tm_games_df=tm_games)
        assert "home_formation_stability_5" in result.columns
        assert "home_formation_stability_10" in result.columns

    def test_adds_win_rate_formation_column(
        self, match_data: pd.DataFrame, tm_games: pd.DataFrame,
    ) -> None:
        """Win rate with current formation column is present."""
        result = add_formation_features(match_data, tm_games_df=tm_games)
        assert "home_win_rate_current_formation_std" in result.columns

    def test_adds_vs_nback_columns(
        self, match_data: pd.DataFrame, tm_games: pd.DataFrame,
    ) -> None:
        """Performance vs N-back columns are present."""
        result = add_formation_features(match_data, tm_games_df=tm_games)
        for back in ["3back", "4back", "5back"]:
            assert f"home_win_rate_vs_{back}_std" in result.columns
            assert f"home_goals_scored_vs_{back}_std" in result.columns

    def test_adds_matchup_columns(
        self, match_data: pd.DataFrame, tm_games: pd.DataFrame,
    ) -> None:
        """Matchup feature columns are present."""
        result = add_formation_features(match_data, tm_games_df=tm_games)
        assert "defender_mismatch" in result.columns
        assert "midfield_dominance" in result.columns

    def test_no_lookahead_in_stability(
        self, match_data: pd.DataFrame, tm_games: pd.DataFrame,
    ) -> None:
        """First match stability is NaN (shift prevents lookahead)."""
        result = add_formation_features(match_data, tm_games_df=tm_games)
        first_row = result.sort_values("date").iloc[0]
        assert pd.isna(first_row["home_formation_stability_5"])

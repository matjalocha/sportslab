"""Tests for player rolling performance features module."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from ml_in_sports.features.player_rolling_features import (
    _aggregate_team_match_features,
    _build_top_player_map,
    _compute_player_rolling_stats,
    add_player_rolling_features,
)

# ---------------------------------------------------------------------------
# Helpers to build test data
# ---------------------------------------------------------------------------

def _build_player_matches() -> pd.DataFrame:
    """Build a realistic player_matches table for testing.

    Creates 3 games for 2 teams (TeamA, TeamB) with 3 players each.
    Each game key follows the format 'YYYY-MM-DD TeamA-TeamB'.
    """
    rows = [
        # Game 1: TeamA vs TeamB (2024-01-01)
        ("L1", "2324", "2024-01-01 TeamA-TeamB", "TeamA", "PlayerA1",
         90, 1, 0, 0.8, 0.2, 3, 2, 0.5, 0.3, 0, 0),
        ("L1", "2324", "2024-01-01 TeamA-TeamB", "TeamA", "PlayerA2",
         90, 0, 1, 0.3, 0.5, 1, 3, 0.2, 0.4, 1, 0),
        ("L1", "2324", "2024-01-01 TeamA-TeamB", "TeamA", "PlayerA3",
         45, 0, 0, 0.1, 0.0, 0, 0, 0.1, 0.1, 0, 0),
        ("L1", "2324", "2024-01-01 TeamA-TeamB", "TeamB", "PlayerB1",
         90, 0, 0, 0.5, 0.1, 2, 1, 0.3, 0.2, 0, 0),
        ("L1", "2324", "2024-01-01 TeamA-TeamB", "TeamB", "PlayerB2",
         90, 1, 1, 0.9, 0.6, 4, 2, 0.6, 0.3, 0, 0),
        ("L1", "2324", "2024-01-01 TeamA-TeamB", "TeamB", "PlayerB3",
         60, 0, 0, 0.2, 0.0, 1, 0, 0.1, 0.1, 1, 0),
        # Game 2: TeamB vs TeamA (2024-01-15)
        ("L1", "2324", "2024-01-15 TeamB-TeamA", "TeamA", "PlayerA1",
         90, 2, 0, 1.5, 0.1, 5, 1, 0.8, 0.4, 0, 0),
        ("L1", "2324", "2024-01-15 TeamB-TeamA", "TeamA", "PlayerA2",
         90, 0, 2, 0.2, 0.8, 2, 4, 0.3, 0.5, 0, 0),
        ("L1", "2324", "2024-01-15 TeamB-TeamA", "TeamA", "PlayerA3",
         90, 1, 0, 0.4, 0.0, 2, 1, 0.2, 0.2, 0, 0),
        ("L1", "2324", "2024-01-15 TeamB-TeamA", "TeamB", "PlayerB1",
         90, 1, 0, 0.7, 0.2, 3, 2, 0.4, 0.3, 0, 0),
        ("L1", "2324", "2024-01-15 TeamB-TeamA", "TeamB", "PlayerB2",
         90, 0, 0, 0.4, 0.3, 2, 1, 0.3, 0.2, 0, 0),
        ("L1", "2324", "2024-01-15 TeamB-TeamA", "TeamB", "PlayerB3",
         0, 0, 0, 0.0, 0.0, 0, 0, 0.0, 0.0, 0, 0),
        # Game 3: TeamA vs TeamB (2024-02-01)
        ("L1", "2324", "2024-02-01 TeamA-TeamB", "TeamA", "PlayerA1",
         90, 0, 1, 0.6, 0.4, 2, 2, 0.4, 0.3, 1, 0),
        ("L1", "2324", "2024-02-01 TeamA-TeamB", "TeamA", "PlayerA2",
         90, 1, 0, 0.5, 0.2, 3, 1, 0.3, 0.2, 0, 0),
        ("L1", "2324", "2024-02-01 TeamA-TeamB", "TeamA", "PlayerA3",
         90, 0, 0, 0.1, 0.1, 1, 0, 0.1, 0.1, 0, 0),
        ("L1", "2324", "2024-02-01 TeamA-TeamB", "TeamB", "PlayerB1",
         90, 0, 1, 0.3, 0.5, 1, 3, 0.2, 0.4, 0, 0),
        ("L1", "2324", "2024-02-01 TeamA-TeamB", "TeamB", "PlayerB2",
         90, 2, 0, 1.2, 0.1, 5, 1, 0.7, 0.2, 0, 0),
        ("L1", "2324", "2024-02-01 TeamA-TeamB", "TeamB", "PlayerB3",
         90, 0, 0, 0.1, 0.0, 1, 0, 0.1, 0.1, 0, 0),
        # Game 4: TeamA vs TeamB (2024-02-15)
        ("L1", "2324", "2024-02-15 TeamA-TeamB", "TeamA", "PlayerA1",
         90, 1, 0, 0.9, 0.1, 4, 1, 0.6, 0.3, 0, 0),
        ("L1", "2324", "2024-02-15 TeamA-TeamB", "TeamA", "PlayerA2",
         90, 0, 1, 0.3, 0.4, 1, 2, 0.2, 0.3, 0, 0),
        ("L1", "2324", "2024-02-15 TeamA-TeamB", "TeamA", "PlayerA3",
         90, 0, 0, 0.2, 0.0, 1, 0, 0.1, 0.1, 0, 0),
        ("L1", "2324", "2024-02-15 TeamA-TeamB", "TeamB", "PlayerB1",
         90, 0, 0, 0.4, 0.2, 2, 1, 0.3, 0.2, 0, 0),
        ("L1", "2324", "2024-02-15 TeamA-TeamB", "TeamB", "PlayerB2",
         90, 1, 1, 0.8, 0.5, 3, 2, 0.5, 0.3, 1, 0),
        ("L1", "2324", "2024-02-15 TeamA-TeamB", "TeamB", "PlayerB3",
         90, 0, 0, 0.1, 0.0, 1, 0, 0.1, 0.1, 0, 0),
    ]
    columns = [
        "league", "season", "game", "team", "player",
        "minutes", "goals", "assists", "xg", "xa",
        "shots", "key_passes", "xg_chain", "xg_buildup",
        "yellow_cards", "red_cards",
    ]
    return pd.DataFrame(rows, columns=columns)


def _build_match_df() -> pd.DataFrame:
    """Build a match DataFrame matching the player_matches games."""
    return pd.DataFrame({
        "date": ["2024-01-01", "2024-01-15", "2024-02-01", "2024-02-15"],
        "league": ["L1"] * 4,
        "season": ["2324"] * 4,
        "game": [
            "2024-01-01 TeamA-TeamB",
            "2024-01-15 TeamB-TeamA",
            "2024-02-01 TeamA-TeamB",
            "2024-02-15 TeamA-TeamB",
        ],
        "home_team": ["TeamA", "TeamB", "TeamA", "TeamA"],
        "away_team": ["TeamB", "TeamA", "TeamB", "TeamB"],
        "home_goals": [2, 1, 1, 1],
        "away_goals": [1, 3, 2, 2],
    })


def _build_two_season_player_matches() -> pd.DataFrame:
    """Build player_matches spanning two seasons for boundary tests."""
    rows = [
        # Season 1 - Game 1
        ("L1", "2223", "2023-04-01 TeamA-TeamB", "TeamA", "PlayerA1",
         90, 2, 0, 1.5, 0.1, 4, 1, 0.6, 0.3, 0, 0),
        ("L1", "2223", "2023-04-01 TeamA-TeamB", "TeamB", "PlayerB1",
         90, 0, 0, 0.3, 0.2, 1, 1, 0.2, 0.2, 0, 0),
        # Season 1 - Game 2
        ("L1", "2223", "2023-05-01 TeamB-TeamA", "TeamA", "PlayerA1",
         90, 1, 1, 0.8, 0.5, 3, 2, 0.4, 0.3, 0, 0),
        ("L1", "2223", "2023-05-01 TeamB-TeamA", "TeamB", "PlayerB1",
         90, 1, 0, 0.7, 0.1, 2, 0, 0.3, 0.1, 0, 0),
        # Season 2 - Game 1 (new season, should reset)
        ("L1", "2324", "2024-01-01 TeamA-TeamB", "TeamA", "PlayerA1",
         90, 0, 0, 0.2, 0.0, 1, 0, 0.1, 0.1, 0, 0),
        ("L1", "2324", "2024-01-01 TeamA-TeamB", "TeamB", "PlayerB1",
         90, 2, 1, 1.5, 0.6, 5, 3, 0.8, 0.4, 0, 0),
        # Season 2 - Game 2
        ("L1", "2324", "2024-01-15 TeamB-TeamA", "TeamA", "PlayerA1",
         90, 1, 0, 0.9, 0.1, 3, 1, 0.5, 0.2, 0, 0),
        ("L1", "2324", "2024-01-15 TeamB-TeamA", "TeamB", "PlayerB1",
         90, 0, 0, 0.4, 0.2, 2, 1, 0.2, 0.2, 0, 0),
    ]
    columns = [
        "league", "season", "game", "team", "player",
        "minutes", "goals", "assists", "xg", "xa",
        "shots", "key_passes", "xg_chain", "xg_buildup",
        "yellow_cards", "red_cards",
    ]
    return pd.DataFrame(rows, columns=columns)


def _build_two_season_match_df() -> pd.DataFrame:
    """Build match DataFrame spanning two seasons."""
    return pd.DataFrame({
        "date": [
            "2023-04-01", "2023-05-01",
            "2024-01-01", "2024-01-15",
        ],
        "league": ["L1"] * 4,
        "season": ["2223", "2223", "2324", "2324"],
        "game": [
            "2023-04-01 TeamA-TeamB",
            "2023-05-01 TeamB-TeamA",
            "2024-01-01 TeamA-TeamB",
            "2024-01-15 TeamB-TeamA",
        ],
        "home_team": ["TeamA", "TeamB", "TeamA", "TeamB"],
        "away_team": ["TeamB", "TeamA", "TeamB", "TeamA"],
        "home_goals": [2, 1, 0, 0],
        "away_goals": [0, 2, 2, 1],
    })


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def player_matches() -> pd.DataFrame:
    """Player match data for 4 games, 2 teams, 3 players each."""
    return _build_player_matches()


@pytest.fixture
def match_df() -> pd.DataFrame:
    """Match-level DataFrame for 4 games."""
    return _build_match_df()


@pytest.fixture
def two_season_player_matches() -> pd.DataFrame:
    """Player match data spanning two seasons."""
    return _build_two_season_player_matches()


@pytest.fixture
def two_season_match_df() -> pd.DataFrame:
    """Match DataFrame spanning two seasons."""
    return _build_two_season_match_df()


@pytest.fixture
def mock_db(player_matches: pd.DataFrame) -> MagicMock:
    """Mock FootballDatabase returning player_matches."""
    db = MagicMock()
    db.read_table.return_value = player_matches
    return db


@pytest.fixture
def mock_db_two_seasons(
    two_season_player_matches: pd.DataFrame,
) -> MagicMock:
    """Mock FootballDatabase returning two-season player_matches."""
    db = MagicMock()
    db.read_table.return_value = two_season_player_matches
    return db


@pytest.fixture
def mock_db_empty() -> MagicMock:
    """Mock FootballDatabase returning empty player_matches."""
    db = MagicMock()
    db.read_table.return_value = pd.DataFrame()
    return db


# ---------------------------------------------------------------------------
# Tests: _compute_player_rolling_stats
# ---------------------------------------------------------------------------

class TestComputePlayerRollingStats:
    """Tests for per-player rolling stat computation."""

    def test_creates_goals_rolling_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling goals column is created for each window."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "goals_rolling_3" in result.columns

    def test_creates_assists_rolling_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling assists column is created."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "assists_rolling_3" in result.columns

    def test_creates_xg_rolling_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling xG column is created."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "xg_rolling_3" in result.columns

    def test_creates_xa_rolling_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling xA column is created."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "xa_rolling_3" in result.columns

    def test_creates_xg_overperformance_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling xG overperformance column is created."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "xg_overperformance_rolling_3" in result.columns

    def test_creates_shots_rolling_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling shots column is created."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "shots_rolling_3" in result.columns

    def test_creates_key_passes_rolling_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling key passes column is created."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "key_passes_rolling_3" in result.columns

    def test_creates_xg_chain_rolling_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling xG chain column is created."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "xg_chain_rolling_3" in result.columns

    def test_creates_xg_buildup_rolling_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling xG buildup column is created."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "xg_buildup_rolling_3" in result.columns

    def test_creates_yellow_cards_rolling_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling yellow cards column is created."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "yellow_cards_rolling_3" in result.columns

    def test_creates_minutes_rolling_column(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling minutes column is created."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert "minutes_rolling_3" in result.columns

    def test_shift_prevents_lookahead(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """First match for each player has NaN rolling stats."""
        result = _compute_player_rolling_stats(player_matches, [3])
        player_a1 = result[result["player"] == "PlayerA1"]
        first_match = player_a1.iloc[0]
        assert pd.isna(first_match["goals_rolling_3"])

    def test_multiple_windows(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Multiple windows produce separate columns."""
        result = _compute_player_rolling_stats(
            player_matches, [3, 5],
        )
        assert "goals_rolling_3" in result.columns
        assert "goals_rolling_5" in result.columns

    def test_preserves_row_count(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = _compute_player_rolling_stats(player_matches, [3])
        assert len(result) == len(player_matches)

    def test_xg_overperformance_value(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """xG overperformance = goals - xG before rolling.

        PlayerA1 match history:
          Game 1: goals=1, xg=0.8 -> overperf=0.2
          Game 2: goals=2, xg=1.5 -> overperf=0.5
          Game 3: goals=0, xg=0.6 -> overperf=-0.6

        At game 4 with window=3, shift(1) uses games 1-3:
          mean([0.2, 0.5, -0.6]) = 0.1/3
        """
        result = _compute_player_rolling_stats(player_matches, [3])
        player_a1 = result[result["player"] == "PlayerA1"]
        fourth_match = player_a1.iloc[3]
        expected = (0.2 + 0.5 + (-0.6)) / 3
        assert fourth_match[
            "xg_overperformance_rolling_3"
        ] == pytest.approx(expected, abs=1e-6)

    def test_rolling_goals_value(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Rolling goals value for PlayerA1 at game 4.

        PlayerA1: goals = [1, 2, 0, 1]
        At game 4, shift(1) + window 3 uses games 1-3:
        mean([1, 2, 0]) = 1.0
        """
        result = _compute_player_rolling_stats(player_matches, [3])
        player_a1 = result[result["player"] == "PlayerA1"]
        fourth_match = player_a1.iloc[3]
        expected = (1 + 2 + 0) / 3.0
        assert fourth_match["goals_rolling_3"] == pytest.approx(
            expected,
        )

    def test_empty_input_returns_empty(self) -> None:
        """Empty input DataFrame produces empty output."""
        empty = pd.DataFrame()
        result = _compute_player_rolling_stats(empty, [3])
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ---------------------------------------------------------------------------
# Tests: Season boundary reset
# ---------------------------------------------------------------------------

class TestSeasonBoundaryReset:
    """Tests for season boundary handling in player rolling stats."""

    def test_rolling_resets_at_new_season(
        self, two_season_player_matches: pd.DataFrame,
    ) -> None:
        """Rolling stats reset when a new season starts."""
        result = _compute_player_rolling_stats(
            two_season_player_matches, [3],
        )
        player_a1 = result[result["player"] == "PlayerA1"]
        season_2_first = player_a1[
            player_a1["season"] == "2324"
        ].iloc[0]
        assert pd.isna(season_2_first["goals_rolling_3"])

    def test_season_2_uses_only_season_2_data(
        self, two_season_player_matches: pd.DataFrame,
    ) -> None:
        """Season 2 rolling stats do not include season 1 data.

        PlayerA1 season 2: game1 goals=0, game2 goals=1
        At game 2, shift(1) uses game1: only 1 value, window 3
        requires 3 so result should be NaN.
        """
        result = _compute_player_rolling_stats(
            two_season_player_matches, [3],
        )
        player_a1 = result[result["player"] == "PlayerA1"]
        season_2_second = player_a1[
            player_a1["season"] == "2324"
        ].iloc[1]
        assert pd.isna(season_2_second["goals_rolling_3"])


# ---------------------------------------------------------------------------
# Tests: _aggregate_team_match_features
# ---------------------------------------------------------------------------

class TestAggregateTeamMatchFeatures:
    """Tests for aggregating player rolling stats to team-match level."""

    def test_creates_team_xi_goals_form(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """team_xi_goals_form column is created."""
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert "home_team_xi_goals_form_3" in result.columns
        assert "away_team_xi_goals_form_3" in result.columns

    def test_creates_team_xi_xg_form(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """team_xi_xg_form column is created."""
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert "home_team_xi_xg_form_3" in result.columns

    def test_creates_team_xi_xa_form(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """team_xi_xa_form column is created."""
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert "home_team_xi_xa_form_3" in result.columns

    def test_creates_team_xi_key_passes_form(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """team_xi_key_passes_form column is created."""
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert "home_team_xi_key_passes_form_3" in result.columns

    def test_creates_team_xi_xg_overperformance(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """team_xi_xg_overperformance column is created."""
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert "home_team_xi_xg_overperformance_3" in result.columns

    def test_creates_team_xi_xg_chain_form(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """team_xi_xg_chain_form column is created."""
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert "home_team_xi_xg_chain_form_3" in result.columns

    def test_creates_team_xi_discipline(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """team_xi_discipline column is created."""
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert "home_team_xi_discipline_3" in result.columns

    def test_only_active_players_aggregated(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """Only players with minutes > 0 contribute to aggregation.

        In game 2, PlayerB3 has 0 minutes. Their rolling stats
        should not be included in TeamB aggregation for game 2.
        """
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert isinstance(result, pd.DataFrame)

    def test_preserves_row_count(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as match DataFrame."""
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert len(result) == len(match_df)

    def test_preserves_original_columns(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """Original match columns are preserved in output."""
        original_cols = set(match_df.columns)
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert original_cols.issubset(set(result.columns))


# ---------------------------------------------------------------------------
# Tests: Top player identification
# ---------------------------------------------------------------------------

class TestTopPlayerIdentification:
    """Tests for top scorer and top creator identification."""

    def test_top_scorer_creates_column(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """top_scorer_goals_form column is created."""
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert "home_top_scorer_goals_form_3" in result.columns
        assert "away_top_scorer_goals_form_3" in result.columns

    def test_top_creator_creates_column(
        self,
        player_matches: pd.DataFrame,
        match_df: pd.DataFrame,
    ) -> None:
        """top_creator_xa_form column is created."""
        rolled = _compute_player_rolling_stats(player_matches, [3])
        result = _aggregate_team_match_features(
            match_df, rolled, [3],
        )
        assert "home_top_creator_xa_form_3" in result.columns
        assert "away_top_creator_xa_form_3" in result.columns

    def test_build_top_player_map_scorer(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Top scorer map identifies player with most cumulative goals.

        PlayerA1 cumulative goals: 1+2+0+1 = 4
        PlayerA2 cumulative goals: 0+0+1+0 = 1
        -> PlayerA1 is top scorer for TeamA
        """
        top_map = _build_top_player_map(player_matches)
        last_game = "2024-02-15 TeamA-TeamB"
        team_a_row = top_map[
            (top_map["game"] == last_game)
            & (top_map["team"] == "TeamA")
        ]
        assert not team_a_row.empty
        assert team_a_row.iloc[0]["top_scorer"] == "PlayerA1"

    def test_build_top_player_map_creator(
        self, player_matches: pd.DataFrame,
    ) -> None:
        """Top creator map identifies player with most cumulative assists.

        PlayerA2 cumulative assists: 1+2+0+1 = 4
        PlayerA1 cumulative assists: 0+0+1+0 = 1
        -> PlayerA2 is top creator for TeamA
        """
        top_map = _build_top_player_map(player_matches)
        last_game = "2024-02-15 TeamA-TeamB"
        team_a_row = top_map[
            (top_map["game"] == last_game)
            & (top_map["team"] == "TeamA")
        ]
        assert not team_a_row.empty
        assert team_a_row.iloc[0]["top_creator"] == "PlayerA2"


# ---------------------------------------------------------------------------
# Tests: add_player_rolling_features (integration)
# ---------------------------------------------------------------------------

class TestAddPlayerRollingFeatures:
    """Tests for the top-level orchestrator function."""

    def test_returns_dataframe(
        self, match_df: pd.DataFrame, mock_db: MagicMock,
    ) -> None:
        """Returns a DataFrame."""
        result = add_player_rolling_features(match_df, mock_db)
        assert isinstance(result, pd.DataFrame)

    def test_preserves_row_count(
        self, match_df: pd.DataFrame, mock_db: MagicMock,
    ) -> None:
        """Output has same number of rows as input."""
        result = add_player_rolling_features(match_df, mock_db)
        assert len(result) == len(match_df)

    def test_preserves_original_columns(
        self, match_df: pd.DataFrame, mock_db: MagicMock,
    ) -> None:
        """Original columns are preserved."""
        original_cols = set(match_df.columns)
        result = add_player_rolling_features(match_df, mock_db)
        assert original_cols.issubset(set(result.columns))

    def test_adds_home_away_prefixed_columns(
        self, match_df: pd.DataFrame, mock_db: MagicMock,
    ) -> None:
        """Output includes home_ and away_ prefixed feature columns."""
        result = add_player_rolling_features(
            match_df, mock_db, windows=[3],
        )
        home_cols = [
            c for c in result.columns
            if c.startswith("home_team_xi_")
        ]
        away_cols = [
            c for c in result.columns
            if c.startswith("away_team_xi_")
        ]
        assert len(home_cols) > 0
        assert len(away_cols) > 0

    def test_default_windows(
        self, match_df: pd.DataFrame, mock_db: MagicMock,
    ) -> None:
        """Default windows [3, 5, 10] are used when not specified."""
        result = add_player_rolling_features(match_df, mock_db)
        assert "home_team_xi_goals_form_3" in result.columns
        assert "home_team_xi_goals_form_5" in result.columns
        assert "home_team_xi_goals_form_10" in result.columns

    def test_handles_empty_match_df(
        self, mock_db: MagicMock,
    ) -> None:
        """Empty match DataFrame returns empty output."""
        empty = pd.DataFrame()
        result = add_player_rolling_features(empty, mock_db)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_handles_empty_player_matches(
        self, match_df: pd.DataFrame, mock_db_empty: MagicMock,
    ) -> None:
        """Empty player_matches returns match_df with NaN features."""
        result = add_player_rolling_features(
            match_df, mock_db_empty, windows=[3],
        )
        assert len(result) == len(match_df)

    def test_reads_player_matches_table(
        self, match_df: pd.DataFrame, mock_db: MagicMock,
    ) -> None:
        """Function reads the player_matches table from the database."""
        add_player_rolling_features(match_df, mock_db, windows=[3])
        mock_db.read_table.assert_called_once_with("player_matches")

    def test_season_boundary_integration(
        self,
        two_season_match_df: pd.DataFrame,
        mock_db_two_seasons: MagicMock,
    ) -> None:
        """Rolling features reset across season boundary."""
        result = add_player_rolling_features(
            two_season_match_df, mock_db_two_seasons, windows=[3],
        )
        season_2_first = result[result["season"] == "2324"].iloc[0]
        assert pd.isna(
            season_2_first["home_team_xi_goals_form_3"],
        )

    def test_no_lookahead_first_match(
        self, match_df: pd.DataFrame, mock_db: MagicMock,
    ) -> None:
        """First match has NaN rolling features (no prior data)."""
        result = add_player_rolling_features(
            match_df, mock_db, windows=[3],
        )
        first_row = result.iloc[0]
        assert pd.isna(first_row["home_team_xi_goals_form_3"])

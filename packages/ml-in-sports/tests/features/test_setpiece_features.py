"""Tests for the set-piece effectiveness features module."""

from pathlib import Path

import pandas as pd
import pytest
from ml_in_sports.features.setpiece_features import (
    _aggregate_shot_group,
    _build_corner_stats,
    _build_team_shot_stats,
    _compute_raw_features,
    _compute_rolling_setpiece,
    _join_to_matches,
    _safe_divide,
    add_setpiece_features,
)
from ml_in_sports.utils.database import FootballDatabase

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sp_sample_shots() -> pd.DataFrame:
    """Sample shots DataFrame with varied situations and results."""
    return pd.DataFrame({
        "league": ["EPL"] * 10,
        "season": ["2324"] * 10,
        "game": ["game1"] * 5 + ["game1"] * 5,
        "team": ["Arsenal"] * 5 + ["Chelsea"] * 5,
        "player": [f"player_{i}" for i in range(10)],
        "shot_id": list(range(10)),
        "xg": [0.12, 0.08, 0.35, 0.05, 0.72,
               0.15, 0.45, 0.03, 0.22, 0.10],
        "situation": [
            "From Corner", "From Corner", "Open Play",
            "Direct Freekick", "Open Play",
            "From Corner", "Open Play", "Set Piece",
            "Open Play", "Direct Freekick",
        ],
        "result": [
            "Goal", "Saved Shot", "Goal",
            "Missed Shot", "Goal",
            "Goal", "Goal", "Blocked Shot",
            "Saved Shot", "Goal",
        ],
        "date": ["2024-01-15"] * 10,
    })


@pytest.fixture
def sp_sample_matches() -> pd.DataFrame:
    """Sample matches DataFrame with corner data."""
    return pd.DataFrame({
        "league": ["EPL", "EPL"],
        "season": ["2324", "2324"],
        "game": ["game1", "game2"],
        "date": ["2024-01-15", "2024-01-22"],
        "home_team": ["Arsenal", "Chelsea"],
        "away_team": ["Chelsea", "Arsenal"],
        "home_goals": [3, 1],
        "away_goals": [2, 0],
        "home_won_corners": [7, 4],
        "away_won_corners": [5, 6],
    })


@pytest.fixture
def multi_game_shots() -> pd.DataFrame:
    """Shots across multiple games for rolling computation."""
    games = []
    for idx, game_id in enumerate(["g1", "g2", "g3", "g4", "g5"]):
        for team in ["TeamA", "TeamB"]:
            goals = 2 if team == "TeamA" else 1
            for shot_idx in range(3):
                is_goal = shot_idx < goals
                games.append({
                    "league": "EPL",
                    "season": "2324",
                    "game": game_id,
                    "team": team,
                    "player": f"p_{team}_{shot_idx}",
                    "shot_id": idx * 10 + shot_idx + (0 if team == "TeamA" else 5),
                    "xg": 0.3 if is_goal else 0.1,
                    "situation": "From Corner" if shot_idx == 0 else "Open Play",
                    "result": "Goal" if is_goal else "Saved Shot",
                    "date": f"2024-01-{15 + idx:02d}",
                })
    return pd.DataFrame(games)


@pytest.fixture
def multi_game_matches() -> pd.DataFrame:
    """Matches across multiple games for rolling computation."""
    records = []
    for idx, game_id in enumerate(["g1", "g2", "g3", "g4", "g5"]):
        records.append({
            "league": "EPL",
            "season": "2324",
            "game": game_id,
            "date": f"2024-01-{15 + idx:02d}",
            "home_team": "TeamA",
            "away_team": "TeamB",
            "home_goals": 2,
            "away_goals": 1,
            "home_won_corners": 6,
            "away_won_corners": 4,
        })
    return pd.DataFrame(records)


@pytest.fixture
def sp_football_db(tmp_path: Path) -> FootballDatabase:
    """Create a temporary FootballDatabase instance."""
    db_path = tmp_path / "test.db"
    db = FootballDatabase(db_path=db_path)
    db.create_tables()
    return db


# ---------------------------------------------------------------------------
# _safe_divide
# ---------------------------------------------------------------------------

class TestSafeDivide:
    """Tests for safe division helper."""

    def test_normal_division(self) -> None:
        """Normal division produces correct result."""
        num = pd.Series([10, 20])
        den = pd.Series([2, 5])
        result = _safe_divide(num, den)
        assert result.iloc[0] == pytest.approx(5.0)
        assert result.iloc[1] == pytest.approx(4.0)

    def test_division_by_zero_returns_nan(self) -> None:
        """Division by zero returns NaN."""
        num = pd.Series([10, 0])
        den = pd.Series([0, 0])
        result = _safe_divide(num, den)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])


# ---------------------------------------------------------------------------
# _aggregate_shot_group
# ---------------------------------------------------------------------------

class TestAggregateShotGroup:
    """Tests for per-team per-game shot aggregation."""

    def test_counts_goals_from_corners(
        self, sp_sample_shots: pd.DataFrame,
    ) -> None:
        """Corner goals are counted correctly."""
        arsenal = sp_sample_shots[sp_sample_shots["team"] == "Arsenal"]
        result = _aggregate_shot_group(arsenal)
        assert result["goals_from_corners"] == 1

    def test_counts_shots_from_corners(
        self, sp_sample_shots: pd.DataFrame,
    ) -> None:
        """Corner shots are counted correctly."""
        arsenal = sp_sample_shots[sp_sample_shots["team"] == "Arsenal"]
        result = _aggregate_shot_group(arsenal)
        assert result["shots_from_corners"] == 2

    def test_xg_from_corners_summed(
        self, sp_sample_shots: pd.DataFrame,
    ) -> None:
        """Corner xG is summed correctly."""
        arsenal = sp_sample_shots[sp_sample_shots["team"] == "Arsenal"]
        result = _aggregate_shot_group(arsenal)
        assert result["xg_from_corners"] == pytest.approx(0.12 + 0.08)

    def test_goals_open_play(
        self, sp_sample_shots: pd.DataFrame,
    ) -> None:
        """Open play goals are counted correctly."""
        arsenal = sp_sample_shots[sp_sample_shots["team"] == "Arsenal"]
        result = _aggregate_shot_group(arsenal)
        assert result["goals_open_play"] == 2

    def test_total_goals(
        self, sp_sample_shots: pd.DataFrame,
    ) -> None:
        """Total goals are counted correctly."""
        arsenal = sp_sample_shots[sp_sample_shots["team"] == "Arsenal"]
        result = _aggregate_shot_group(arsenal)
        assert result["total_goals"] == 3

    def test_fk_stats(
        self, sp_sample_shots: pd.DataFrame,
    ) -> None:
        """Free kick stats are computed correctly."""
        chelsea = sp_sample_shots[sp_sample_shots["team"] == "Chelsea"]
        result = _aggregate_shot_group(chelsea)
        assert result["goals_from_fk"] == 1
        assert result["shots_from_fk"] == 1

    def test_setpiece_includes_all_types(
        self, sp_sample_shots: pd.DataFrame,
    ) -> None:
        """Set piece stats include corners, FKs, and generic set pieces."""
        chelsea = sp_sample_shots[sp_sample_shots["team"] == "Chelsea"]
        result = _aggregate_shot_group(chelsea)
        assert result["shots_from_setpieces"] == 3


# ---------------------------------------------------------------------------
# _build_team_shot_stats
# ---------------------------------------------------------------------------

class TestBuildTeamShotStats:
    """Tests for building team shot stats."""

    def test_returns_one_row_per_team_per_game(
        self, sp_sample_shots: pd.DataFrame,
    ) -> None:
        """Produces one row per team per game."""
        result = _build_team_shot_stats(sp_sample_shots)
        assert len(result) == 2

    def test_empty_shots_returns_empty(self) -> None:
        """Empty input returns empty DataFrame."""
        result = _build_team_shot_stats(pd.DataFrame())
        assert result.empty


# ---------------------------------------------------------------------------
# _build_corner_stats
# ---------------------------------------------------------------------------

class TestBuildCornerStats:
    """Tests for corner stats extraction from matches."""

    def test_produces_two_rows_per_match(
        self, sp_sample_matches: pd.DataFrame,
    ) -> None:
        """Each match produces two rows (home and away)."""
        result = _build_corner_stats(sp_sample_matches)
        assert len(result) == 4

    def test_home_corners_correct(
        self, sp_sample_matches: pd.DataFrame,
    ) -> None:
        """Home team corners_won is correct."""
        result = _build_corner_stats(sp_sample_matches)
        arsenal_game1 = result[
            (result["team"] == "Arsenal") & (result["game"] == "game1")
        ]
        assert arsenal_game1["corners_won"].iloc[0] == 7
        assert arsenal_game1["opponent_corners"].iloc[0] == 5

    def test_away_corners_correct(
        self, sp_sample_matches: pd.DataFrame,
    ) -> None:
        """Away team corners_won is correct."""
        result = _build_corner_stats(sp_sample_matches)
        chelsea_game1 = result[
            (result["team"] == "Chelsea") & (result["game"] == "game1")
        ]
        assert chelsea_game1["corners_won"].iloc[0] == 5
        assert chelsea_game1["opponent_corners"].iloc[0] == 7

    def test_empty_matches_returns_empty(self) -> None:
        """Empty input returns empty DataFrame."""
        result = _build_corner_stats(pd.DataFrame())
        assert result.empty

    def test_missing_corner_columns_returns_empty(self) -> None:
        """Missing corner columns returns empty DataFrame."""
        matches = pd.DataFrame({
            "league": ["EPL"],
            "season": ["2324"],
            "game": ["g1"],
            "home_team": ["A"],
            "away_team": ["B"],
        })
        result = _build_corner_stats(matches)
        assert result.empty


# ---------------------------------------------------------------------------
# _compute_raw_features
# ---------------------------------------------------------------------------

class TestComputeRawFeatures:
    """Tests for raw set-piece feature computation."""

    def test_corner_attack_effectiveness(self) -> None:
        """Corner attack effectiveness is goals/corners."""
        stats = pd.DataFrame({
            "goals_from_corners": [2],
            "corners_won": [10],
            "xg_from_corners": [0.8],
            "goals_conceded_from_corners": [1],
            "opponent_corners": [8],
            "goals_from_fk": [1],
            "shots_from_fk": [3],
            "goals_from_setpieces": [3],
            "total_goals": [5],
            "goals_open_play": [2],
            "shots_open_play": [12],
            "goals_conceded_from_setpieces": [1],
            "shots_from_corners": [4],
            "xg_from_fk": [0.3],
            "xg_open_play": [1.5],
        })
        result = _compute_raw_features(stats)
        assert result["corner_attack_effectiveness"].iloc[0] == (
            pytest.approx(0.2)
        )

    def test_corner_xg_efficiency(self) -> None:
        """Corner xG efficiency is xG_from_corners / corners_won."""
        stats = pd.DataFrame({
            "goals_from_corners": [1],
            "corners_won": [10],
            "xg_from_corners": [1.5],
            "goals_conceded_from_corners": [0],
            "opponent_corners": [5],
            "goals_from_fk": [0],
            "shots_from_fk": [2],
            "goals_from_setpieces": [1],
            "total_goals": [3],
            "goals_open_play": [2],
            "shots_open_play": [10],
            "goals_conceded_from_setpieces": [0],
            "shots_from_corners": [3],
            "xg_from_fk": [0.2],
            "xg_open_play": [1.8],
        })
        result = _compute_raw_features(stats)
        assert result["corner_xg_efficiency"].iloc[0] == (
            pytest.approx(0.15)
        )

    def test_setpiece_dependency(self) -> None:
        """Set piece dependency is SP goals / total goals."""
        stats = pd.DataFrame({
            "goals_from_corners": [1],
            "corners_won": [5],
            "xg_from_corners": [0.5],
            "goals_conceded_from_corners": [0],
            "opponent_corners": [4],
            "goals_from_fk": [1],
            "shots_from_fk": [2],
            "goals_from_setpieces": [2],
            "total_goals": [4],
            "goals_open_play": [2],
            "shots_open_play": [8],
            "goals_conceded_from_setpieces": [1],
            "shots_from_corners": [2],
            "xg_from_fk": [0.15],
            "xg_open_play": [1.2],
        })
        result = _compute_raw_features(stats)
        assert result["setpiece_dependency"].iloc[0] == (
            pytest.approx(0.5)
        )

    def test_open_play_efficiency(self) -> None:
        """Open play efficiency is open goals / open shots."""
        stats = pd.DataFrame({
            "goals_from_corners": [0],
            "corners_won": [3],
            "xg_from_corners": [0.2],
            "goals_conceded_from_corners": [0],
            "opponent_corners": [3],
            "goals_from_fk": [0],
            "shots_from_fk": [1],
            "goals_from_setpieces": [0],
            "total_goals": [2],
            "goals_open_play": [2],
            "shots_open_play": [10],
            "goals_conceded_from_setpieces": [0],
            "shots_from_corners": [1],
            "xg_from_fk": [0.1],
            "xg_open_play": [1.0],
        })
        result = _compute_raw_features(stats)
        assert result["open_play_efficiency"].iloc[0] == (
            pytest.approx(0.2)
        )

    def test_zero_denominator_produces_nan(self) -> None:
        """Zero-denominator features produce NaN."""
        stats = pd.DataFrame({
            "goals_from_corners": [0],
            "corners_won": [0],
            "xg_from_corners": [0.0],
            "goals_conceded_from_corners": [0],
            "opponent_corners": [0],
            "goals_from_fk": [0],
            "shots_from_fk": [0],
            "goals_from_setpieces": [0],
            "total_goals": [0],
            "goals_open_play": [0],
            "shots_open_play": [0],
            "goals_conceded_from_setpieces": [0],
            "shots_from_corners": [0],
            "xg_from_fk": [0.0],
            "xg_open_play": [0.0],
        })
        result = _compute_raw_features(stats)
        assert pd.isna(result["corner_attack_effectiveness"].iloc[0])
        assert pd.isna(result["fk_effectiveness"].iloc[0])
        assert pd.isna(result["setpiece_dependency"].iloc[0])


# ---------------------------------------------------------------------------
# _compute_rolling_setpiece
# ---------------------------------------------------------------------------

class TestComputeRollingSetpiece:
    """Tests for rolling set-piece feature computation."""

    def test_rolling_produces_columns(self) -> None:
        """Rolling computation produces expected column names."""
        stats = pd.DataFrame({
            "league": ["EPL"] * 5,
            "season": ["2324"] * 5,
            "game": [f"g{i}" for i in range(5)],
            "team": ["TeamA"] * 5,
            "date": [f"2024-01-{15+i:02d}" for i in range(5)],
            "corner_attack_effectiveness": [0.1, 0.2, 0.15, 0.1, 0.25],
            "corner_defense": [0.05, 0.0, 0.1, 0.05, 0.0],
            "corner_xg_efficiency": [0.08, 0.1, 0.09, 0.07, 0.12],
            "fk_effectiveness": [0.0, 0.5, 0.0, 0.0, 1.0],
            "setpiece_dependency": [0.5, 0.3, 0.4, 0.2, 0.6],
            "open_play_efficiency": [0.15, 0.2, 0.1, 0.25, 0.15],
            "sp_defensive_vulnerability": [0, 1, 0, 0, 1],
            "xg_per_corner_shot": [0.08, 0.1, 0.09, 0.07, 0.12],
            "xg_per_fk_shot": [0.05, 0.15, 0.0, 0.0, 0.2],
            "xg_per_open_play_shot": [0.12, 0.15, 0.1, 0.18, 0.11],
        })
        result = _compute_rolling_setpiece(stats, windows=[3])
        rolling_cols = [c for c in result.columns if c.startswith("sp_")]
        assert len(rolling_cols) > 0
        assert any("roll_3" in c for c in rolling_cols)
        assert any("_std" in c for c in rolling_cols)

    def test_shift_prevents_lookahead(self) -> None:
        """First game has NaN rolling values (shift prevents lookahead)."""
        stats = pd.DataFrame({
            "league": ["EPL"] * 3,
            "season": ["2324"] * 3,
            "game": ["g1", "g2", "g3"],
            "team": ["TeamA"] * 3,
            "date": ["2024-01-15", "2024-01-22", "2024-01-29"],
            "corner_attack_effectiveness": [0.1, 0.2, 0.3],
            "corner_defense": [0.0, 0.0, 0.0],
            "corner_xg_efficiency": [0.0, 0.0, 0.0],
            "fk_effectiveness": [0.0, 0.0, 0.0],
            "setpiece_dependency": [0.0, 0.0, 0.0],
            "open_play_efficiency": [0.0, 0.0, 0.0],
            "sp_defensive_vulnerability": [0, 0, 0],
            "xg_per_corner_shot": [0.0, 0.0, 0.0],
            "xg_per_fk_shot": [0.0, 0.0, 0.0],
            "xg_per_open_play_shot": [0.0, 0.0, 0.0],
        })
        result = _compute_rolling_setpiece(stats, windows=[3])
        g1_row = result[result["game"] == "g1"]
        assert pd.isna(
            g1_row["sp_corner_attack_effectiveness_roll_3"].iloc[0]
        )

    def test_empty_returns_empty(self) -> None:
        """Empty input returns empty DataFrame."""
        result = _compute_rolling_setpiece(pd.DataFrame(), windows=[3])
        assert result.empty


# ---------------------------------------------------------------------------
# _join_to_matches
# ---------------------------------------------------------------------------

class TestJoinToMatches:
    """Tests for joining set-piece features to match DataFrame."""

    def test_creates_home_and_away_columns(self) -> None:
        """Join creates prefixed columns for both sides."""
        match_df = pd.DataFrame({
            "game": ["g1"],
            "home_team": ["TeamA"],
            "away_team": ["TeamB"],
        })
        rolled = pd.DataFrame({
            "game": ["g1", "g1"],
            "team": ["TeamA", "TeamB"],
            "sp_corner_attack_effectiveness_roll_3": [0.15, 0.10],
        })
        result = _join_to_matches(match_df, rolled)
        assert "home_sp_corner_attack_effectiveness_roll_3" in result.columns
        assert "away_sp_corner_attack_effectiveness_roll_3" in result.columns

    def test_values_assigned_correctly(self) -> None:
        """Correct values are assigned to home and away sides."""
        match_df = pd.DataFrame({
            "game": ["g1"],
            "home_team": ["TeamA"],
            "away_team": ["TeamB"],
        })
        rolled = pd.DataFrame({
            "game": ["g1", "g1"],
            "team": ["TeamA", "TeamB"],
            "sp_setpiece_dependency_std": [0.35, 0.50],
        })
        result = _join_to_matches(match_df, rolled)
        assert result["home_sp_setpiece_dependency_std"].iloc[0] == (
            pytest.approx(0.35)
        )
        assert result["away_sp_setpiece_dependency_std"].iloc[0] == (
            pytest.approx(0.50)
        )

    def test_empty_rolled_returns_copy(self) -> None:
        """Empty rolled data returns match df unchanged."""
        match_df = pd.DataFrame({
            "game": ["g1"],
            "home_team": ["A"],
            "away_team": ["B"],
        })
        result = _join_to_matches(match_df, pd.DataFrame())
        assert len(result.columns) == len(match_df.columns)


# ---------------------------------------------------------------------------
# add_setpiece_features (integration)
# ---------------------------------------------------------------------------

class TestAddSetpieceFeatures:
    """Tests for the add_setpiece_features orchestrator."""

    def test_returns_dataframe(
        self,
        sp_football_db: FootballDatabase,
        multi_game_shots: pd.DataFrame,
        multi_game_matches: pd.DataFrame,
    ) -> None:
        """Returns a DataFrame."""
        sp_football_db.upsert_dataframe("shots", multi_game_shots)
        sp_football_db.upsert_dataframe("matches", multi_game_matches)

        match_df = multi_game_matches[[
            "game", "home_team", "away_team",
        ]].copy()

        result = add_setpiece_features(match_df, sp_football_db)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(match_df)

    def test_adds_sp_columns(
        self,
        sp_football_db: FootballDatabase,
        multi_game_shots: pd.DataFrame,
        multi_game_matches: pd.DataFrame,
    ) -> None:
        """Set-piece columns are added to the result."""
        sp_football_db.upsert_dataframe("shots", multi_game_shots)
        sp_football_db.upsert_dataframe("matches", multi_game_matches)

        match_df = multi_game_matches[[
            "game", "home_team", "away_team",
        ]].copy()

        result = add_setpiece_features(match_df, sp_football_db)
        sp_cols = [c for c in result.columns if "sp_" in c]
        assert len(sp_cols) > 0

    def test_empty_df_returns_empty(
        self, sp_football_db: FootballDatabase,
    ) -> None:
        """Empty input returns empty DataFrame."""
        result = add_setpiece_features(pd.DataFrame(), sp_football_db)
        assert result.empty

    def test_no_shots_returns_unchanged(
        self, sp_football_db: FootballDatabase,
    ) -> None:
        """No shots data returns input unchanged."""
        match_df = pd.DataFrame({
            "game": ["g1"],
            "home_team": ["A"],
            "away_team": ["B"],
        })
        result = add_setpiece_features(match_df, sp_football_db)
        assert len(result.columns) == len(match_df.columns)

    def test_custom_windows(
        self,
        sp_football_db: FootballDatabase,
        multi_game_shots: pd.DataFrame,
        multi_game_matches: pd.DataFrame,
    ) -> None:
        """Custom window sizes produce correct column names."""
        sp_football_db.upsert_dataframe("shots", multi_game_shots)
        sp_football_db.upsert_dataframe("matches", multi_game_matches)

        match_df = multi_game_matches[[
            "game", "home_team", "away_team",
        ]].copy()

        result = add_setpiece_features(
            match_df, sp_football_db, windows=[5],
        )
        sp_cols = [c for c in result.columns if "roll_5" in c]
        assert len(sp_cols) > 0

"""Tests for the feature engineering module."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.features.build_features import (
    add_rolling_features,
    add_target_variables,
    build_master_dataframe,
)
from ml_in_sports.utils.database import FootballDatabase


@pytest.fixture
def db(tmp_path: Path) -> FootballDatabase:
    """Create a temporary test database with sample data."""
    database = FootballDatabase(db_path=tmp_path / "test.db")
    database.create_tables()
    return database


@pytest.fixture
def sample_matches() -> pd.DataFrame:
    """Minimal matches DataFrame for testing."""
    return pd.DataFrame({
        "league": ["ENG-Premier League"] * 4,
        "season": ["2324"] * 4,
        "game": [
            "2024-01-01 Arsenal-Chelsea",
            "2024-01-01 Liverpool-Everton",
            "2024-01-15 Chelsea-Liverpool",
            "2024-01-15 Everton-Arsenal",
        ],
        "date": ["2024-01-01", "2024-01-01", "2024-01-15", "2024-01-15"],
        "home_team": ["Arsenal", "Liverpool", "Chelsea", "Everton"],
        "away_team": ["Chelsea", "Everton", "Liverpool", "Arsenal"],
        "home_goals": [2, 1, 0, 1],
        "away_goals": [1, 0, 2, 3],
        "home_xg": [1.8, 1.2, 0.7, 0.9],
        "away_xg": [0.9, 0.5, 1.5, 2.1],
        "home_elo": [1900.0, 1850.0, 1870.0, 1750.0],
        "away_elo": [1870.0, 1750.0, 1850.0, 1900.0],
    })


@pytest.fixture
def sample_odds() -> pd.DataFrame:
    """Minimal match_odds DataFrame for testing."""
    return pd.DataFrame({
        "league": ["ENG-Premier League"] * 2,
        "season": ["2324"] * 2,
        "game": [
            "2024-01-01 Arsenal-Chelsea",
            "2024-01-01 Liverpool-Everton",
        ],
        "b365_home": [1.8, 2.1],
        "b365_draw": [3.5, 3.2],
        "b365_away": [4.5, 3.8],
        "avg_home": [1.85, 2.05],
        "avg_draw": [3.4, 3.3],
        "avg_away": [4.2, 3.7],
    })


@pytest.fixture
def sample_elo() -> pd.DataFrame:
    """Minimal elo_ratings DataFrame for testing."""
    return pd.DataFrame({
        "team": ["Arsenal", "Chelsea", "Liverpool", "Everton"],
        "date": ["2023-08-01"] * 4,
        "elo": [1900.0, 1870.0, 1850.0, 1750.0],
    })


@pytest.fixture
def sample_league_table() -> pd.DataFrame:
    """Minimal league_tables DataFrame for testing."""
    return pd.DataFrame({
        "league": ["ENG-Premier League"] * 4,
        "season": ["2324"] * 4,
        "team": ["Arsenal", "Liverpool", "Chelsea", "Everton"],
        "matches_played": [20, 20, 20, 20],
        "wins": [15, 12, 10, 5],
        "draws": [3, 5, 4, 6],
        "losses": [2, 3, 6, 9],
        "goals_for": [45, 38, 30, 22],
        "goals_against": [15, 20, 25, 35],
        "goal_difference": [30, 18, 5, -13],
        "points": [48, 41, 34, 21],
    })


@pytest.fixture
def populated_db(
    db: FootballDatabase,
    sample_matches: pd.DataFrame,
    sample_odds: pd.DataFrame,
    sample_elo: pd.DataFrame,
    sample_league_table: pd.DataFrame,
) -> FootballDatabase:
    """Database pre-populated with sample data."""
    db.upsert_dataframe("matches", sample_matches)
    db.upsert_dataframe("match_odds", sample_odds)
    db.upsert_dataframe("elo_ratings", sample_elo)
    db.upsert_dataframe("league_tables", sample_league_table)
    return db


def _build_rolling_df() -> pd.DataFrame:
    """Build a DataFrame with enough rows for rolling window tests."""
    dates = pd.date_range("2024-01-01", periods=10, freq="7D")
    rows = []
    for i, date in enumerate(dates):
        rows.append({
            "league": "ENG-Premier League",
            "season": "2324",
            "game": f"{date.strftime('%Y-%m-%d')} Arsenal-Chelsea",
            "date": date.strftime("%Y-%m-%d"),
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_goals": (i % 3) + 1,
            "away_goals": i % 2,
            "home_xg": 1.5 + (i * 0.1),
            "away_xg": 0.8 + (i * 0.05),
            "home_elo": 1900.0,
            "away_elo": 1870.0,
        })
    return pd.DataFrame(rows)


class TestBuildMasterDataframe:
    """Tests for build_master_dataframe."""

    def test_returns_dataframe_with_matches(
        self, populated_db: FootballDatabase,
    ) -> None:
        """Returns a non-empty DataFrame when matches exist."""
        result = build_master_dataframe(
            "ENG-Premier League", "2324", populated_db,
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_contains_match_columns(
        self, populated_db: FootballDatabase,
    ) -> None:
        """Result includes core match columns."""
        result = build_master_dataframe(
            "ENG-Premier League", "2324", populated_db,
        )
        for col in ["home_team", "away_team", "home_goals", "away_goals"]:
            assert col in result.columns

    def test_contains_odds_columns_after_join(
        self, populated_db: FootballDatabase,
    ) -> None:
        """Result includes odds columns from match_odds table."""
        result = build_master_dataframe(
            "ENG-Premier League", "2324", populated_db,
        )
        assert "b365_home" in result.columns

    def test_contains_elo_delta(
        self, populated_db: FootballDatabase,
    ) -> None:
        """Result includes elo_delta computed column."""
        result = build_master_dataframe(
            "ENG-Premier League", "2324", populated_db,
        )
        assert "elo_delta" in result.columns
        first = result.iloc[0]
        expected = first["home_elo"] - first["away_elo"]
        assert first["elo_delta"] == pytest.approx(expected)

    def test_contains_league_table_columns(
        self, populated_db: FootballDatabase,
    ) -> None:
        """Result includes league position info."""
        result = build_master_dataframe(
            "ENG-Premier League", "2324", populated_db,
        )
        assert "home_league_points" in result.columns
        assert "away_league_points" in result.columns

    def test_returns_empty_when_no_matches(
        self, db: FootballDatabase,
    ) -> None:
        """Returns empty DataFrame when no matches in DB."""
        result = build_master_dataframe(
            "ENG-Premier League", "2324", db,
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_one_row_per_match(
        self, populated_db: FootballDatabase,
    ) -> None:
        """Each match appears exactly once (no duplicate rows)."""
        result = build_master_dataframe(
            "ENG-Premier League", "2324", populated_db,
        )
        assert result["game"].nunique() == len(result)

    def test_sorted_by_date(
        self, populated_db: FootballDatabase,
    ) -> None:
        """Result is sorted by date."""
        result = build_master_dataframe(
            "ENG-Premier League", "2324", populated_db,
        )
        dates = result["date"].tolist()
        assert dates == sorted(dates)


class TestAddTargetVariables:
    """Tests for add_target_variables."""

    def test_result_1x2_home_win(self) -> None:
        """Home win returns 'H'."""
        df = pd.DataFrame({
            "home_goals": [3], "away_goals": [1],
        })
        result = add_target_variables(df)
        assert result["result_1x2"].iloc[0] == "H"

    def test_result_1x2_away_win(self) -> None:
        """Away win returns 'A'."""
        df = pd.DataFrame({
            "home_goals": [0], "away_goals": [2],
        })
        result = add_target_variables(df)
        assert result["result_1x2"].iloc[0] == "A"

    def test_result_1x2_draw(self) -> None:
        """Draw returns 'D'."""
        df = pd.DataFrame({
            "home_goals": [1], "away_goals": [1],
        })
        result = add_target_variables(df)
        assert result["result_1x2"].iloc[0] == "D"

    def test_over_2_5_true(self) -> None:
        """Total goals > 2.5 returns True."""
        df = pd.DataFrame({
            "home_goals": [2], "away_goals": [1],
        })
        result = add_target_variables(df)
        assert result["over_2_5"].iloc[0] == True  # noqa: E712

    def test_over_2_5_false(self) -> None:
        """Total goals <= 2.5 returns False."""
        df = pd.DataFrame({
            "home_goals": [1], "away_goals": [1],
        })
        result = add_target_variables(df)
        assert result["over_2_5"].iloc[0] == False  # noqa: E712

    def test_btts_true(self) -> None:
        """Both teams scored returns True."""
        df = pd.DataFrame({
            "home_goals": [2], "away_goals": [1],
        })
        result = add_target_variables(df)
        assert result["btts"].iloc[0] == True  # noqa: E712

    def test_btts_false(self) -> None:
        """One team clean sheet returns False."""
        df = pd.DataFrame({
            "home_goals": [1], "away_goals": [0],
        })
        result = add_target_variables(df)
        assert result["btts"].iloc[0] == False  # noqa: E712

    def test_handles_missing_goals(self) -> None:
        """NaN goals produce NaN targets."""
        df = pd.DataFrame({
            "home_goals": [np.nan], "away_goals": [1],
        })
        result = add_target_variables(df)
        assert pd.isna(result["result_1x2"].iloc[0])

    def test_all_targets_added(self) -> None:
        """All three target columns are present."""
        df = pd.DataFrame({
            "home_goals": [2], "away_goals": [1],
        })
        result = add_target_variables(df)
        assert "result_1x2" in result.columns
        assert "over_2_5" in result.columns
        assert "btts" in result.columns


class TestAddRollingFeatures:
    """Tests for add_rolling_features."""

    def test_adds_rolling_columns(self) -> None:
        """Rolling feature columns are created."""
        df = _build_rolling_df()
        result = add_rolling_features(df, windows=[5])
        assert "home_goals_rolled_5" in result.columns
        assert "away_goals_rolled_5" in result.columns

    def test_rolling_xg_columns(self) -> None:
        """Rolling xG columns are created."""
        df = _build_rolling_df()
        result = add_rolling_features(df, windows=[5])
        assert "home_xg_rolled_5" in result.columns
        assert "away_xg_rolled_5" in result.columns

    def test_first_rows_have_nan(self) -> None:
        """First rows within window have NaN (no lookahead)."""
        df = _build_rolling_df()
        result = add_rolling_features(df, windows=[5])
        assert pd.isna(result["home_goals_rolled_5"].iloc[0])

    def test_no_lookahead_bias(self) -> None:
        """Rolling window uses only past data (shift=1)."""
        df = _build_rolling_df()
        result = add_rolling_features(df, windows=[3])
        row_4 = result.iloc[3]
        expected = df["home_goals"].iloc[0:3].mean()
        assert row_4["home_goals_rolled_3"] == pytest.approx(expected)

    def test_multiple_windows(self) -> None:
        """Multiple window sizes create separate columns."""
        df = _build_rolling_df()
        result = add_rolling_features(df, windows=[3, 5])
        assert "home_goals_rolled_3" in result.columns
        assert "home_goals_rolled_5" in result.columns

    def test_preserves_original_columns(self) -> None:
        """Original columns are not modified."""
        df = _build_rolling_df()
        original_cols = set(df.columns)
        result = add_rolling_features(df, windows=[5])
        assert original_cols.issubset(set(result.columns))

    def test_form_points_column(self) -> None:
        """Rolling form points column is created."""
        df = _build_rolling_df()
        result = add_rolling_features(df, windows=[5])
        assert "home_form_points_5" in result.columns
        assert "away_form_points_5" in result.columns

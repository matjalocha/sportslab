"""Shared fixtures for features tests.

Provides match, shots, player_matches, and database fixtures used by
test_form_features.py. Ported from the research codebase during SPO-39.
"""

from pathlib import Path

import pandas as pd
import pytest
from ml_in_sports.utils.database import FootballDatabase


@pytest.fixture
def simple_matches() -> pd.DataFrame:
    """Six matches across one season for two teams."""
    return pd.DataFrame({
        "league": ["EPL"] * 6,
        "season": ["2324"] * 6,
        "game": [f"g{i}" for i in range(1, 7)],
        "date": [
            "2024-01-01", "2024-01-15", "2024-02-01",
            "2024-02-15", "2024-03-01", "2024-03-15",
        ],
        "home_team": [
            "Arsenal", "Chelsea", "Arsenal",
            "Chelsea", "Arsenal", "Chelsea",
        ],
        "away_team": [
            "Chelsea", "Arsenal", "Chelsea",
            "Arsenal", "Chelsea", "Arsenal",
        ],
        "home_goals": [2, 0, 1, 1, 3, 0],
        "away_goals": [1, 2, 1, 0, 0, 1],
    })


@pytest.fixture
def two_season_matches() -> pd.DataFrame:
    """Matches across two seasons to test boundary reset."""
    season_1 = pd.DataFrame({
        "league": ["EPL"] * 3,
        "season": ["2223"] * 3,
        "game": ["s1g1", "s1g2", "s1g3"],
        "date": ["2023-04-01", "2023-04-15", "2023-05-01"],
        "home_team": ["Arsenal", "Chelsea", "Arsenal"],
        "away_team": ["Chelsea", "Arsenal", "Chelsea"],
        "home_goals": [2, 0, 3],
        "away_goals": [0, 1, 1],
    })
    season_2 = pd.DataFrame({
        "league": ["EPL"] * 3,
        "season": ["2324"] * 3,
        "game": ["s2g1", "s2g2", "s2g3"],
        "date": ["2023-08-15", "2023-09-01", "2023-09-15"],
        "home_team": ["Arsenal", "Chelsea", "Arsenal"],
        "away_team": ["Chelsea", "Arsenal", "Chelsea"],
        "home_goals": [1, 2, 0],
        "away_goals": [0, 2, 1],
    })
    return pd.concat([season_1, season_2], ignore_index=True)


@pytest.fixture
def sample_shots() -> pd.DataFrame:
    """Shots with minute info for timing-based features."""
    records = []
    for idx, (game, team, minute, result) in enumerate([
        ("g1", "Arsenal", 5, "Goal"),
        ("g1", "Arsenal", 80, "Goal"),
        ("g1", "Chelsea", 88, "Goal"),
        ("g2", "Chelsea", 10, "Goal"),
        ("g2", "Arsenal", 78, "Goal"),
        ("g2", "Arsenal", 90, "Goal"),
        ("g3", "Arsenal", 3, "Goal"),
        ("g3", "Chelsea", 85, "Goal"),
        ("g4", "Chelsea", 12, "Goal"),
        ("g4", "Arsenal", 77, "Goal"),
    ]):
        records.append({
            "league": "EPL",
            "season": "2324",
            "game": game,
            "team": team,
            "player": f"player_{idx}",
            "shot_id": idx,
            "xg": 0.3,
            "result": result,
            "situation": "Open Play",
            "minute": minute,
            "date": f"2024-01-{1 + int(game[1:]):02d}",
        })
    return pd.DataFrame(records)


@pytest.fixture
def sample_player_matches() -> pd.DataFrame:
    """Player match data for discipline and xG chain features."""
    records = []
    for game in ["g1", "g2", "g3", "g4", "g5"]:
        for team in ["Arsenal", "Chelsea"]:
            for player_idx in range(3):
                records.append({
                    "league": "EPL",
                    "season": "2324",
                    "game": game,
                    "team": team,
                    "player": f"{team}_p{player_idx}",
                    "minutes": 90,
                    "goals": 1 if player_idx == 0 else 0,
                    "assists": 0,
                    "xg": 0.5 if player_idx == 0 else 0.1,
                    "xa": 0.2,
                    "shots": 3 if player_idx == 0 else 1,
                    "key_passes": 2,
                    "yellow_cards": 1 if player_idx == 1 else 0,
                    "red_cards": 0,
                    "xg_chain": 0.8,
                    "xg_buildup": 0.5,
                    "fouls_committed": 2,
                })
    return pd.DataFrame(records)


@pytest.fixture
def matches_with_corners() -> pd.DataFrame:
    """Matches with corner data for corners rolling features."""
    return pd.DataFrame({
        "league": ["EPL"] * 5,
        "season": ["2324"] * 5,
        "game": [f"g{i}" for i in range(1, 6)],
        "date": [f"2024-01-{i:02d}" for i in range(1, 6)],
        "home_team": ["Arsenal"] * 5,
        "away_team": ["Chelsea"] * 5,
        "home_goals": [2, 1, 0, 3, 1],
        "away_goals": [1, 0, 1, 0, 2],
        "home_won_corners": [7, 5, 8, 6, 4],
        "away_won_corners": [3, 6, 4, 5, 7],
    })


@pytest.fixture
def football_db(tmp_path: Path) -> FootballDatabase:
    """Create a temporary FootballDatabase instance."""
    db_path = tmp_path / "test.db"
    db = FootballDatabase(db_path=db_path)
    db.create_tables()
    return db

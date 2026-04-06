"""Shared fixtures for tests.

Ported from the research codebase `ml_in_sports/tests/conftest.py` during
SPO-35 (extractors migration). These fixtures supply minimal fake DataFrames
with the same MultiIndex shape that production extractors return, so tests
can exercise pivot/merge logic without network access.
"""

import pandas as pd
import pytest


@pytest.fixture
def understat_schedule() -> pd.DataFrame:
    """Fake Understat schedule DataFrame."""
    index = pd.MultiIndex.from_tuples(
        [
            ("ENG-Premier League", "2324", "2024-01-01 Arsenal-Chelsea"),
            ("ENG-Premier League", "2324", "2024-01-01 Liverpool-Everton"),
        ],
        names=["league", "season", "game"],
    )
    return pd.DataFrame(
        {
            "home_team": ["Arsenal", "Liverpool"],
            "away_team": ["Chelsea", "Everton"],
            "home_goals": [2, 1],
            "away_goals": [1, 0],
            "home_xg": [1.8, 1.2],
            "away_xg": [0.9, 0.5],
        },
        index=index,
    )


@pytest.fixture
def understat_team_match() -> pd.DataFrame:
    """Fake Understat team match stats DataFrame."""
    index = pd.MultiIndex.from_tuples(
        [
            ("ENG-Premier League", "2324", "2024-01-01 Arsenal-Chelsea"),
            ("ENG-Premier League", "2324", "2024-01-01 Liverpool-Everton"),
        ],
        names=["league", "season", "game"],
    )
    return pd.DataFrame(
        {
            "home_ppda": [10.5, 12.0],
            "away_ppda": [8.3, 9.1],
            "home_deep_completions": [5, 3],
            "away_deep_completions": [2, 4],
        },
        index=index,
    )


@pytest.fixture
def espn_matchsheet() -> pd.DataFrame:
    """Fake ESPN matchsheet DataFrame (2 rows per match)."""
    index = pd.MultiIndex.from_tuples(
        [
            ("ENG-Premier League", "2324", "2024-01-01 Arsenal-Chelsea", "Arsenal"),
            ("ENG-Premier League", "2324", "2024-01-01 Arsenal-Chelsea", "Chelsea"),
        ],
        names=["league", "season", "game", "team"],
    )
    return pd.DataFrame(
        {
            "is_home": [True, False],
            "possession_pct": [62.0, 38.0],
            "total_shots": [15, 8],
            "effective_tackles": [12, 14],
        },
        index=index,
    )

"""Tests for Sofascore integration (merge with features DataFrame)."""

from __future__ import annotations

import pandas as pd
from ml_in_sports.processing.scrapers.sofascore import MatchStats
from ml_in_sports.processing.scrapers.sofascore_integration import (
    merge_sofascore_stats,
)
from ml_in_sports.utils.team_names import normalize_team_name

# ---------------------------------------------------------------------------
# Team name normalisation (canonical from utils.team_names)
# ---------------------------------------------------------------------------


class TestNormalizeTeamName:
    """Tests for canonical team name normalisation via utils.team_names."""

    def test_known_alias_man_city(self) -> None:
        assert normalize_team_name("Man City") == "Manchester City"

    def test_known_alias_wolves(self) -> None:
        assert normalize_team_name("Wolves") == "Wolverhampton Wanderers"

    def test_known_alias_wolverhampton_wanderers(self) -> None:
        result = normalize_team_name("Wolverhampton Wanderers")
        assert result == "Wolverhampton Wanderers"

    def test_known_alias_spurs(self) -> None:
        assert normalize_team_name("Spurs") == "Tottenham Hotspur"

    def test_unknown_name_returned_unchanged(self) -> None:
        assert normalize_team_name("Some Obscure FC") == "Some Obscure FC"

    def test_known_alias_bayern(self) -> None:
        assert normalize_team_name("Bayern München") == "Bayern Munich"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stats(
    match_id: int,
    home: str,
    away: str,
    date: str,
    possession_home: float = 55.0,
    xg_home: float = 1.5,
) -> MatchStats:
    """Create a MatchStats with minimal non-None fields."""
    return MatchStats(
        match_id=match_id,
        home_team=home,
        away_team=away,
        date=date,
        home_possession=possession_home,
        away_possession=100.0 - possession_home,
        home_total_shots=10,
        away_total_shots=8,
        home_shots_on_target=4,
        away_shots_on_target=3,
        home_tackles=15,
        away_tackles=12,
        home_accurate_passes=400,
        away_accurate_passes=350,
        home_accurate_passes_pct=85.0,
        away_accurate_passes_pct=80.0,
        home_accurate_crosses=4,
        away_accurate_crosses=2,
        home_interceptions=10,
        away_interceptions=8,
        home_clearances=12,
        away_clearances=18,
        home_accurate_long_balls=6,
        away_accurate_long_balls=9,
        home_ground_duels_won=22,
        away_ground_duels_won=18,
        home_aerial_duels_won=8,
        away_aerial_duels_won=11,
        home_successful_dribbles=5,
        away_successful_dribbles=3,
        home_saves=3,
        away_saves=4,
        home_expected_goals=xg_home,
        away_expected_goals=0.8,
    )


# ---------------------------------------------------------------------------
# merge_sofascore_stats
# ---------------------------------------------------------------------------


class TestMergeSofascoreStats:
    """Tests for merging Sofascore stats into a features DataFrame."""

    def test_exact_match(self) -> None:
        features = pd.DataFrame({
            "home_team": ["Arsenal", "Liverpool"],
            "away_team": ["Chelsea", "Everton"],
            "date": ["2024-01-15", "2024-01-16"],
            "some_feature": [1.0, 2.0],
        })
        stats = [
            _make_stats(100, "Arsenal", "Chelsea", "2024-01-15", 62.0, 1.85),
            _make_stats(101, "Liverpool", "Everton", "2024-01-16", 58.0, 2.1),
        ]

        result = merge_sofascore_stats(features, stats)

        assert "sofa_home_possession" in result.columns
        assert "sofa_home_expected_goals" in result.columns
        assert result["sofa_home_possession"].iloc[0] == 62.0
        assert result["sofa_home_expected_goals"].iloc[1] == 2.1
        # Original columns preserved
        assert result["some_feature"].iloc[0] == 1.0

    def test_date_tolerance_matches(self) -> None:
        features = pd.DataFrame({
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "date": ["2024-01-15"],
        })
        # Stats have date off by 1 day
        stats = [_make_stats(100, "Arsenal", "Chelsea", "2024-01-16")]

        result = merge_sofascore_stats(features, stats, date_tolerance_days=1)

        assert result["sofa_home_possession"].iloc[0] == 55.0

    def test_no_match_produces_nan(self) -> None:
        features = pd.DataFrame({
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "date": ["2024-01-15"],
        })
        stats = [_make_stats(999, "Brighton", "Villa", "2024-01-15")]

        result = merge_sofascore_stats(features, stats)

        assert pd.isna(result["sofa_home_possession"].iloc[0])

    def test_normalised_team_names(self) -> None:
        """Features say 'Man City', Sofascore says 'Manchester City'."""
        features = pd.DataFrame({
            "home_team": ["Man City"],
            "away_team": ["Wolves"],
            "date": ["2024-01-15"],
        })
        stats = [_make_stats(200, "Manchester City", "Wolverhampton Wanderers", "2024-01-15")]

        result = merge_sofascore_stats(features, stats)

        assert result["sofa_home_possession"].iloc[0] == 55.0

    def test_empty_stats_returns_original(self) -> None:
        features = pd.DataFrame({
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "date": ["2024-01-15"],
        })

        result = merge_sofascore_stats(features, [])

        assert list(result.columns) == list(features.columns)

    def test_partial_match(self) -> None:
        """Only some rows match -- unmatched rows get NaN."""
        features = pd.DataFrame({
            "home_team": ["Arsenal", "Liverpool"],
            "away_team": ["Chelsea", "Everton"],
            "date": ["2024-01-15", "2024-01-16"],
        })
        stats = [_make_stats(100, "Arsenal", "Chelsea", "2024-01-15")]

        result = merge_sofascore_stats(features, stats)

        assert result["sofa_home_possession"].iloc[0] == 55.0
        assert pd.isna(result["sofa_home_possession"].iloc[1])

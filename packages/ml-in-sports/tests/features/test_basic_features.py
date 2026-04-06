"""Tests for basic non-xG feature generation."""

import pandas as pd
from ml_in_sports.features.basic_features import build_basic_features


def _sample_matches() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "league": ["ENG-Championship"] * 5,
            "season": ["2425"] * 5,
            "date": pd.to_datetime(
                ["2024-08-01", "2024-08-02", "2024-08-08", "2024-08-09", "2024-08-15"]
            ),
            "home_team": ["Team A", "Team C", "Team A", "Team D", "Team A"],
            "away_team": ["Team B", "Team A", "Team D", "Team A", "Team E"],
            "home_goals": [2, 1, 0, 3, 4],
            "away_goals": [0, 1, 3, 2, 1],
            "home_shots_on_target": [5, 3, 1, 7, 8],
            "away_shots_on_target": [2, 4, 6, 5, 1],
            "home_corners": [6, 4, 2, 9, 5],
            "away_corners": [3, 5, 8, 4, 2],
            "avg_home": [2.0, 2.5, 1.8, 2.1, 1.6],
            "avg_draw": [3.2, 3.1, 3.5, 3.0, 3.4],
            "avg_away": [3.8, 2.9, 4.2, 3.7, 5.0],
        }
    )


def test_build_basic_features_without_xg_columns() -> None:
    """The pipeline works without xG inputs."""
    features = build_basic_features(_sample_matches(), windows=[3])

    assert "home_goals_for_roll_3" in features.columns
    assert "away_goals_against_roll_3" in features.columns
    assert "home_shots_on_target_for_roll_3" in features.columns
    assert "fair_prob_home" in features.columns


def test_shift_prevents_lookahead() -> None:
    """Current-match goals are not used in same-row rolling features."""
    features = build_basic_features(_sample_matches(), windows=[1])

    team_a_second_match = features.iloc[1]
    assert team_a_second_match["away_goals_for_roll_1"] == 2.0
    assert team_a_second_match["away_goals_against_roll_1"] == 0.0


def test_multiple_rolling_windows() -> None:
    """Different window sizes produce different rolling values."""
    features = build_basic_features(_sample_matches(), windows=[1, 2])

    team_a_fifth_match = features.iloc[4]
    assert team_a_fifth_match["home_goals_for_roll_1"] == 2.0
    assert team_a_fifth_match["home_goals_for_roll_2"] == 1.0


def test_table_position_feature_when_available() -> None:
    """Table-position delta is added only when inputs exist."""
    matches = _sample_matches()
    matches["home_table_position"] = [1, 8, 2, 4, 3]
    matches["away_table_position"] = [12, 5, 7, 2, 18]

    features = build_basic_features(matches, windows=[3])

    assert "table_position_diff" in features.columns
    assert features.loc[0, "table_position_diff"] == 11

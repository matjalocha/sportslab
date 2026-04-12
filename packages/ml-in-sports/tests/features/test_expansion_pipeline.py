"""Tests for the expansion league feature pipeline.

Covers happy path (end-to-end on synthetic football-data.co.uk output),
column growth assertions, presence of key feature families, graceful
handling when optional inputs are missing, and the required-column
validator.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.features.basic_features import build_basic_features
from ml_in_sports.features.expansion_pipeline import (
    _prepare_frame,
    _run_stage,
    build_expansion_features,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def expansion_matches() -> pd.DataFrame:
    """Build 24 fixtures across four teams in one season.

    Schema mirrors what `league_ingestion._standardize_frame` produces
    for football-data.co.uk CSVs, i.e. the input to
    `build_basic_features` downstream.
    """
    rng = np.random.default_rng(seed=7)
    teams = ["Red", "Blue", "Green", "Yellow"]
    fixtures = list(itertools.permutations(teams, 2))
    start_date = pd.Timestamp("2024-08-10")

    records: list[dict[str, object]] = []
    for idx, (home, away) in enumerate(fixtures * 2):
        match_date = start_date + pd.Timedelta(days=idx * 4)
        records.append({
            "league": "TST-Expansion",
            "season": "2425",
            "date": match_date,
            "game": f"{match_date:%Y-%m-%d} {home}-{away}",
            "home_team": home,
            "away_team": away,
            "home_goals": int(rng.integers(0, 4)),
            "away_goals": int(rng.integers(0, 4)),
            "home_shots": int(rng.integers(5, 20)),
            "away_shots": int(rng.integers(5, 20)),
            "home_shots_on_target": int(rng.integers(1, 10)),
            "away_shots_on_target": int(rng.integers(1, 10)),
            "home_corners": int(rng.integers(2, 12)),
            "away_corners": int(rng.integers(2, 12)),
            "home_fouls": int(rng.integers(5, 20)),
            "away_fouls": int(rng.integers(5, 20)),
            "home_yellow_cards": int(rng.integers(0, 5)),
            "away_yellow_cards": int(rng.integers(0, 5)),
            "home_red_cards": 0,
            "away_red_cards": 0,
            "avg_home": round(float(rng.uniform(1.6, 3.6)), 2),
            "avg_draw": round(float(rng.uniform(3.0, 4.0)), 2),
            "avg_away": round(float(rng.uniform(2.0, 5.0)), 2),
            "avg_over_25": round(float(rng.uniform(1.7, 2.3)), 2),
            "avg_under_25": round(float(rng.uniform(1.7, 2.3)), 2),
            "b365_home": round(float(rng.uniform(1.6, 3.6)), 2),
            "b365_draw": round(float(rng.uniform(3.0, 4.0)), 2),
            "b365_away": round(float(rng.uniform(2.0, 5.0)), 2),
            "result_1x2": "H",
        })
    return pd.DataFrame(records)


@pytest.fixture
def two_season_matches() -> pd.DataFrame:
    """Matches spanning two seasons to exercise team-season resets."""
    teams = ["Red", "Blue"]
    rows: list[dict[str, object]] = []
    base = pd.Timestamp("2023-08-10")
    for season_idx, season in enumerate(["2324", "2425"]):
        season_start = base + pd.DateOffset(years=season_idx)
        for i, (home, away) in enumerate(
            [(teams[0], teams[1]), (teams[1], teams[0])] * 3,
        ):
            match_date = season_start + pd.Timedelta(days=i * 7)
            rows.append({
                "league": "TST-Expansion",
                "season": season,
                "date": match_date,
                "game": f"{match_date:%Y-%m-%d} {home}-{away}",
                "home_team": home,
                "away_team": away,
                "home_goals": (i + season_idx) % 4,
                "away_goals": (i + 1) % 3,
                "avg_home": 2.0,
                "avg_draw": 3.3,
                "avg_away": 3.5,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_build_expansion_features_runs_end_to_end(
    expansion_matches: pd.DataFrame,
) -> None:
    """Pipeline completes without errors on realistic synthetic data."""
    basic = build_basic_features(expansion_matches)

    result = build_expansion_features(basic)

    assert len(result) == len(expansion_matches)
    assert len(result.columns) > len(basic.columns)


def test_build_expansion_features_adds_expected_columns(
    expansion_matches: pd.DataFrame,
) -> None:
    """Key feature families are materialized by the expansion pipeline."""
    basic = build_basic_features(expansion_matches)

    result = build_expansion_features(basic)

    # Targets
    assert "over_2_5" in result.columns
    assert "btts" in result.columns
    assert "total_goals" in result.columns
    # Streaks (form_features streak helper)
    assert "home_win_streak" in result.columns
    assert "away_unbeaten_streak" in result.columns
    # Table features from new_features
    assert "home_table_pos" in result.columns
    assert "away_cumul_pts" in result.columns
    assert "table_pos_diff" in result.columns
    # Contextual (venue STD, fatigue)
    assert "home_venue_goals_scored_std" in result.columns
    assert "away_days_since_last" in result.columns
    # Betting (fair probs / consensus)
    assert "fair_prob_home" in result.columns
    # Derived (calendar + lag)
    assert "month" in result.columns
    assert "home_goals_scored_lag1" in result.columns


def test_build_expansion_features_doubles_column_count(
    expansion_matches: pd.DataFrame,
) -> None:
    """Expansion pipeline roughly doubles the feature set over basic."""
    basic = build_basic_features(expansion_matches)

    result = build_expansion_features(basic)

    # Basic outputs ~130 columns; expansion adds 150+ more.
    added = len(result.columns) - len(basic.columns)
    assert added >= 100, (
        f"expansion pipeline only added {added} columns; expected >= 100"
    )


def test_build_expansion_features_preserves_top5_columns(
    expansion_matches: pd.DataFrame,
) -> None:
    """Existing basic-feature columns are not dropped."""
    basic = build_basic_features(expansion_matches)

    result = build_expansion_features(basic)

    for col in basic.columns:
        assert col in result.columns, f"basic column {col!r} was dropped"


def test_build_expansion_features_resets_across_seasons(
    two_season_matches: pd.DataFrame,
) -> None:
    """Pipeline handles multi-season data without boundary leakage.

    Smoke-check that the frame runs through all stages on a tiny
    two-season dataset; value-level checks on streak/table semantics
    live in the individual feature-module tests.
    """
    basic = build_basic_features(two_season_matches)

    result = build_expansion_features(basic)

    assert len(result) == len(two_season_matches)
    # Cumulative points are season-scoped, so the first match of each
    # season must have cumul_pts == 0 for both sides.
    first_of_season = result.sort_values(["season", "date"]).groupby(
        "season", as_index=False,
    ).first()
    assert (first_of_season["home_cumul_pts"] == 0).all()
    assert (first_of_season["away_cumul_pts"] == 0).all()


# ---------------------------------------------------------------------------
# Robustness to missing optional columns
# ---------------------------------------------------------------------------


def test_build_expansion_features_without_odds_columns(
    expansion_matches: pd.DataFrame,
) -> None:
    """Pipeline still runs when bookmaker odds are absent."""
    basic = build_basic_features(expansion_matches)
    odds_cols = [
        "avg_home", "avg_draw", "avg_away",
        "avg_over_25", "avg_under_25",
        "b365_home", "b365_draw", "b365_away",
    ]
    stripped = basic.drop(columns=[c for c in odds_cols if c in basic.columns])

    result = build_expansion_features(stripped)

    assert len(result) == len(expansion_matches)
    # Targets still computed from goals.
    assert "over_2_5" in result.columns
    # Table features still computed from goals.
    assert "home_cumul_pts" in result.columns


def test_build_expansion_features_without_xg_is_idempotent_on_xg_cols(
    expansion_matches: pd.DataFrame,
) -> None:
    """Stubbed xG columns come back all-NaN but the pipeline succeeds."""
    basic = build_basic_features(expansion_matches)

    result = build_expansion_features(basic)

    # `new_features` emits xG rolling columns; they should all be NaN
    # because we stubbed xG inputs as NaN.
    xg_cols = [c for c in result.columns if "xg_for_roll" in c]
    assert xg_cols, "expected xG rolling columns to be present from new_features"
    for col in xg_cols:
        assert result[col].isna().all(), (
            f"{col} should be all-NaN without real xG inputs"
        )


def test_build_expansion_features_missing_required_columns_raises() -> None:
    """Required-column validator rejects incomplete inputs."""
    incomplete = pd.DataFrame({
        "league": ["X"],
        "season": ["2425"],
        "home_team": ["A"],
        "away_team": ["B"],
        "date": [pd.Timestamp("2024-08-10")],
        # missing home_goals and away_goals
    })

    with pytest.raises(ValueError, match="home_goals"):
        build_expansion_features(incomplete)


# ---------------------------------------------------------------------------
# Helper-level tests
# ---------------------------------------------------------------------------


def test_prepare_frame_adds_xg_stubs_and_sorts(
    expansion_matches: pd.DataFrame,
) -> None:
    """`_prepare_frame` sorts, resets index, and stubs xG."""
    shuffled = expansion_matches.sample(frac=1.0, random_state=1)

    prepared = _prepare_frame(shuffled)

    assert "home_xg" in prepared.columns
    assert "away_xg" in prepared.columns
    assert prepared["home_xg"].isna().all()
    assert prepared["away_xg"].isna().all()
    assert list(prepared.index) == list(range(len(prepared)))
    dates = prepared["date"].tolist()
    assert dates == sorted(dates)


def test_run_stage_catches_exceptions_and_returns_input(
    expansion_matches: pd.DataFrame,
) -> None:
    """A raising stage does not abort the pipeline."""
    def raising_stage(df: pd.DataFrame) -> pd.DataFrame:
        raise RuntimeError("boom")

    result = _run_stage(expansion_matches, "failing", raising_stage)

    # Input returned unchanged (same object, not a copy).
    assert result is expansion_matches


def test_run_stage_propagates_successful_output(
    expansion_matches: pd.DataFrame,
) -> None:
    """A successful stage's DataFrame is forwarded."""
    def adding_stage(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["test_marker"] = 1
        return out

    result = _run_stage(expansion_matches, "marker", adding_stage)

    assert "test_marker" in result.columns
    assert (result["test_marker"] == 1).all()

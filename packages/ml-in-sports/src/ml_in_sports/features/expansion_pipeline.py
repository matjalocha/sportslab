"""Full feature pipeline for expansion (non-xG) leagues.

This module runs the same feature stack as the Top-5 pipeline for leagues
where we have football-data.co.uk match stats (goals, shots, corners,
cards, odds) but no xG or player-level tactical data.

Included stages (all operating purely on an in-memory DataFrame):

- `targets.add_all_targets` — 1X2 / O/U / BTTS / double chance / margin
- `form_features._add_streak_features` — win / unbeaten / losing / draw /
  scoring / clean-sheet streaks (bypasses the DB-bound form orchestrator)
- `new_features.add_new_features` — league table positions, cumulative
  points, W/D/L last N, venue streaks. xG inputs are stubbed as NaN so
  the xG rolling columns become NaN; table features remain valid.
- `contextual_features.add_contextual_features` — venue season-to-date,
  fatigue, head-to-head
- `betting_features.add_betting_features` — implied probabilities,
  overround, fair probabilities, cross-book consensus
- `derived_features.add_derived_features` — calendar, home-minus-away
  diffs, lag features, interactions, percentile ranks

Every stage is wrapped in try/except so a single broken module cannot
take down the whole ingestion. Skipped stages are logged at WARNING.

Intentionally excluded (require inputs we do not have for expansion
leagues): `rolling_features`, `tactical_features`, `setpiece_features`,
`formation_features`, `player_features`, `player_rolling_features`,
`match_player_quality`, `form_features` DB-bound sub-stages (timing
goals, discipline, xG chain, corners from shots/player_matches).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.features.betting_features import add_betting_features
from ml_in_sports.features.contextual_features import add_contextual_features
from ml_in_sports.features.derived_features import add_derived_features
from ml_in_sports.features.form_features import _add_streak_features
from ml_in_sports.features.new_features import add_new_features
from ml_in_sports.features.targets import add_all_targets

logger = structlog.get_logger(__name__)

_REQUIRED_COLUMNS: tuple[str, ...] = (
    "league",
    "season",
    "home_team",
    "away_team",
    "date",
    "home_goals",
    "away_goals",
)


def build_expansion_features(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full non-xG feature pipeline on expansion-league matches.

    The input is expected to be the output of `build_basic_features`,
    i.e. a DataFrame with match-level schema plus the shifted rolling
    stats produced by `basic_features.py`. Each stage appends columns;
    no stage removes or mutates existing ones.

    Stages that raise are caught and logged; the pipeline continues
    with whatever has been produced so far. This keeps partial-feature
    ingestion resilient when an individual module encounters unusual
    data (e.g. a season with only one team).

    Args:
        df: Match-level DataFrame with at least `league`, `season`,
            `home_team`, `away_team`, `date`, `home_goals`, `away_goals`.

    Returns:
        New DataFrame with expansion feature columns added. Original
        columns are preserved. The frame is sorted by
        `(league, season, date)` and has a contiguous 0..n-1 index.

    Raises:
        ValueError: If any of the required base columns is missing.
    """
    _validate_required_columns(df)

    logger.info("expansion_pipeline_start", rows=len(df), cols=len(df.columns))

    result = _prepare_frame(df)
    starting_cols = len(result.columns)

    result = _run_stage(result, "targets", add_all_targets)
    result = _run_stage(result, "streaks", _add_streak_features)
    result = _run_stage(result, "new_features", _add_new_features_no_xg)
    result = _run_stage(result, "contextual", add_contextual_features)
    result = _run_stage(result, "betting", add_betting_features)
    result = _run_stage(result, "derived", add_derived_features)

    added = len(result.columns) - starting_cols
    logger.info(
        "expansion_pipeline_complete",
        rows=len(result),
        cols=len(result.columns),
        columns_added=added,
    )
    return result


def _validate_required_columns(df: pd.DataFrame) -> None:
    """Check that the minimum schema is present before running stages.

    Args:
        df: Input match-level DataFrame.

    Raises:
        ValueError: If any required column is missing.
    """
    missing = [col for col in _REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"expansion_pipeline requires columns {missing!r} to be present"
        )


def _prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Copy, coerce date, sort, reset index, and stub xG columns.

    `new_features.add_new_features` references `home_xg`/`away_xg`
    unconditionally. Stubbing them as NaN lets the stage run; the
    table features (the piece we care about) are unaffected, and the
    xG rolling columns will be all-NaN on output.

    Args:
        df: Input match-level DataFrame.

    Returns:
        Prepared copy with datetime date, stable sort, contiguous
        integer index, and xG stub columns if absent.
    """
    result = df.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result = result.sort_values(
        ["league", "season", "date"], kind="stable"
    ).reset_index(drop=True)

    if "home_xg" not in result.columns:
        result["home_xg"] = np.nan
    if "away_xg" not in result.columns:
        result["away_xg"] = np.nan

    return result


def _add_new_features_no_xg(df: pd.DataFrame) -> pd.DataFrame:
    """Call `add_new_features` with NaN xG stubs already present.

    Thin adapter that enforces the xG stub invariant before delegating
    to `new_features.add_new_features`. Any xG-derived rolling columns
    it produces are all-NaN for expansion leagues.

    Args:
        df: Prepared match DataFrame with (possibly NaN) xG columns.

    Returns:
        DataFrame with table position and W/D/L last-N columns added.
    """
    # `_prepare_frame` already guarantees xG columns exist, but this
    # helper may be called on intermediate frames in the future, so
    # re-assert the invariant cheaply.
    if "home_xg" not in df.columns:
        df = df.assign(home_xg=np.nan)
    if "away_xg" not in df.columns:
        df = df.assign(away_xg=np.nan)
    return add_new_features(df)


StageFn = Callable[[pd.DataFrame], pd.DataFrame]


def _run_stage(
    df: pd.DataFrame,
    stage_name: str,
    stage_fn: StageFn,
) -> pd.DataFrame:
    """Run a single pipeline stage, logging success or skip on failure.

    If `stage_fn` raises, the input DataFrame is returned unchanged and
    a WARNING is emitted with the exception message. This keeps a
    single bad module from tanking ingestion of an entire league.

    Args:
        df: Current pipeline DataFrame.
        stage_name: Short identifier used in structured logs.
        stage_fn: Callable taking a DataFrame and returning a new one.

    Returns:
        Updated DataFrame on success, or the input DataFrame on failure.
    """
    before = len(df.columns)
    try:
        result = stage_fn(df)
    except Exception as exc:
        logger.warning(
            "expansion_stage_failed",
            stage=stage_name,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return df

    added = len(result.columns) - before
    logger.info(
        "expansion_stage_complete",
        stage=stage_name,
        columns_added=added,
        total_columns=len(result.columns),
    )
    return result

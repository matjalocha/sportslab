"""Ingest new league data from football-data.co.uk into features parquet."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.features.basic_features import build_basic_features
from ml_in_sports.features.expansion_pipeline import build_expansion_features
from ml_in_sports.processing.leagues import get_league
from ml_in_sports.processing.odds.pinnacle import (
    download_season_csv,
    load_football_data_csv,
)
from ml_in_sports.utils.team_names import normalize_team_name

logger = structlog.get_logger(__name__)


def ingest_league(
    league: str,
    seasons: list[str],
    odds_dir: Path = Path("data/odds"),
    output_parquet: Path = Path("data/features/all_features.parquet"),
) -> int:
    """Download, parse, compute basic features, and append to parquet.

    Args:
        league: SportsLab canonical league name.
        seasons: Season codes to ingest, e.g. ``["2223", "2324"]``.
        odds_dir: Root directory for downloaded football-data CSVs.
        output_parquet: Target features parquet path.

    Returns:
        Number of parsed matches added from the requested seasons.

    Raises:
        ValueError: If ``league`` is unknown or ``seasons`` is empty.
    """
    league_info = get_league(league)
    if league_info is None:
        raise ValueError(f"Unknown league: {league!r}")
    if not seasons:
        raise ValueError("At least one season is required")

    frames: list[pd.DataFrame] = []
    for season in seasons:
        csv_path = download_season_csv(
            league_info.football_data_code,
            season,
            odds_dir,
        )
        parsed = load_football_data_csv(csv_path)
        parsed = _standardize_frame(parsed, league=league, season=season)
        frames.append(parsed)

    if not frames:
        return 0

    raw_features = pd.concat(frames, ignore_index=True)
    raw_features = raw_features.sort_values(["league", "season", "date", "game"])
    new_features = build_basic_features(raw_features)
    try:
        new_features = build_expansion_features(new_features)
    except Exception as exc:
        logger.warning(
            "expansion_pipeline_partial",
            league=league,
            error=str(exc),
            error_type=type(exc).__name__,
        )
    matches_added = len(new_features)

    combined = _append_to_parquet(new_features, output_parquet)
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output_parquet, index=False)

    logger.info(
        "league_ingested",
        league=league,
        seasons=seasons,
        rows=matches_added,
        output=str(output_parquet),
    )
    return matches_added


def _standardize_frame(df: pd.DataFrame, league: str, season: str) -> pd.DataFrame:
    """Add SportsLab columns expected by backtests and prediction jobs."""
    result = df.copy()
    result["league"] = league
    result["season"] = season
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result["home_team"] = result["home_team"].map(normalize_team_name)
    result["away_team"] = result["away_team"].map(normalize_team_name)
    result["game"] = (
        result["date"].dt.strftime("%Y-%m-%d")
        + " "
        + result["home_team"].astype(str)
        + "-"
        + result["away_team"].astype(str)
    )
    result["result_1x2"] = _result_1x2(result)

    result["avg_home"] = _coalesce_columns(result, ["max_home", "pinnacle_home"])
    result["avg_draw"] = _coalesce_columns(result, ["max_draw", "pinnacle_draw"])
    result["avg_away"] = _coalesce_columns(result, ["max_away", "pinnacle_away"])
    result["b365_home"] = result["avg_home"]
    result["b365_draw"] = result["avg_draw"]
    result["b365_away"] = result["avg_away"]
    return result


def _result_1x2(df: pd.DataFrame) -> pd.Series:
    """Return H/D/A result labels from full-time goals."""
    home_goals = pd.to_numeric(df["home_goals"], errors="coerce")
    away_goals = pd.to_numeric(df["away_goals"], errors="coerce")
    result = np.select(
        [home_goals > away_goals, home_goals == away_goals, home_goals < away_goals],
        ["H", "D", "A"],
        default="",
    )
    result_series = pd.Series(result, index=df.index, dtype="string")
    return result_series.mask(home_goals.isna() | away_goals.isna(), pd.NA)


def _coalesce_columns(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Coalesce the first non-null value across available columns."""
    values = pd.Series(np.nan, index=df.index, dtype=float)
    for col in columns:
        if col in df.columns:
            values = values.fillna(pd.to_numeric(df[col], errors="coerce"))
    return values


def _append_to_parquet(new_features: pd.DataFrame, output_parquet: Path) -> pd.DataFrame:
    """Append features to existing parquet and deduplicate stable match keys."""
    if not output_parquet.exists():
        return new_features.reset_index(drop=True)

    existing = pd.read_parquet(output_parquet)
    combined = pd.concat([existing, new_features], ignore_index=True, sort=False)
    dedupe_cols = ["league", "season", "game"]
    present_dedupe_cols = [col for col in dedupe_cols if col in combined.columns]
    if len(present_dedupe_cols) == len(dedupe_cols):
        combined = combined.drop_duplicates(subset=dedupe_cols, keep="last")
    return combined.reset_index(drop=True)

"""Load, match, and merge Sofascore JSON cache into a features DataFrame.

This module is the bridge between the raw JSON cache files produced by
the background Sofascore scraper and the ``sofa_*`` feature columns in
the features parquet.  It handles:

1. **Loading**: glob all ``data/sofascore/{league}/{season}/{game_id}.json``
   files and parse the raw format (``game_id``, ``timestamp``, ``stats``).
2. **Normalization**: convert team names to canonical form via
   ``normalize_team_name`` and convert timestamps to dates.
3. **Matching**: left-join Sofascore rows to parquet rows on
   (normalized home_team, normalized away_team, date +/- 1 day).
4. **Rolling features**: delegate to ``sofascore_features.compute_sofascore_rolling_features``.
5. **Saving**: overwrite the parquet with new ``sofa_*`` columns appended.

The module is consumed by both ``scripts/merge_sofascore.py`` and the
``sl merge-sofascore`` CLI command.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import structlog

from ml_in_sports.processing.sofascore_features import (
    compute_sofascore_rolling_features,
)
from ml_in_sports.utils.team_names import normalize_team_name

logger = structlog.get_logger(__name__)

# Mapping from raw Sofascore JSON stat keys to the ``sofa_*`` column name
# suffix.  Keys may appear with ``home_`` or ``away_`` prefix in the JSON.
_RAW_KEY_TO_COLUMN: dict[str, str] = {
    "expectedGoals": "expected_goals",
    "ballPossession": "possession",
    "totalShotsOnGoal": "total_shots",
    "shotsOnGoal": "shots_on_target",
    "shotsOffGoal": "shots_off_target",
    "goalkeeperSaves": "saves",
    "cornerKicks": "corner_kicks",
    "fouls": "fouls",
    "freeKicks": "free_kicks",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
    "offsides": "offsides",
    "throwIns": "throw_ins",
    "goalKicks": "goal_kicks",
    "totalTackle": "tackles",
    "wonTacklePercent": "tackle_pct",
    "accuratePasses": "accurate_passes",
    "passes": "total_passes",
    "accurateCross": "accurate_crosses",
    "accurateLongBalls": "accurate_long_balls",
    "interceptionWon": "interceptions",
    "totalClearance": "clearances",
    "groundDuelsPercentage": "ground_duels_pct",
    "aerialDuelsPercentage": "aerial_duels_pct",
    "dribblesPercentage": "dribbles_pct",
    "bigChanceCreated": "big_chance_created",
    "finalThirdEntries": "final_third_entries",
    "goalsPrevented": "goals_prevented",
    "duelWonPercent": "duel_won_pct",
    # Direct passthrough for any keys not in the map: handled below.
}


def load_sofascore_cache(
    sofascore_dir: Path,
) -> pd.DataFrame:
    """Scan and parse all Sofascore JSON cache files.

    Handles the raw scraper format::

        {"game_id": int, "home_team": str, "away_team": str,
         "timestamp": int, "stats": {...}}

    Also handles the ``MatchStats``-serialized format (from
    ``scrape_league_season``) which has flat keys like
    ``home_possession``, ``away_expected_goals``.

    Args:
        sofascore_dir: Root directory (e.g. ``data/sofascore``).

    Returns:
        DataFrame with columns: ``game_id``, ``home_team``, ``away_team``,
        ``date``, plus ``sofa_home_*`` / ``sofa_away_*`` for every stat.
        Empty DataFrame if no files found.
    """
    json_paths = sorted(sofascore_dir.glob("*/*/*.json"))
    if not json_paths:
        logger.warning(
            "sofascore_cache_empty",
            dir=str(sofascore_dir),
        )
        return pd.DataFrame()

    records: list[dict[str, Any]] = []
    parse_errors = 0

    for path in json_paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            record = _parse_cache_file(data, path)
            if record is not None:
                records.append(record)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            parse_errors += 1
            logger.warning(
                "sofascore_cache_parse_error",
                path=str(path),
                error=str(exc),
            )

    logger.info(
        "sofascore_cache_loaded",
        files=len(json_paths),
        parsed=len(records),
        errors=parse_errors,
    )

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def _parse_cache_file(
    data: dict[str, Any],
    path: Path,
) -> dict[str, Any] | None:
    """Parse a single JSON cache file into a flat dict.

    Handles two formats:
    1. Raw scraper: ``{game_id, home_team, away_team, timestamp, stats: {...}}``
    2. MatchStats: ``{match_id, home_team, away_team, date, home_*, away_*}``

    Args:
        data: Parsed JSON dict.
        path: File path (for logging).

    Returns:
        Flat dict with ``game_id``, ``home_team``, ``away_team``, ``date``,
        and ``sofa_home_*`` / ``sofa_away_*`` columns, or None on failure.
    """
    if "stats" in data and "timestamp" in data:
        return _parse_raw_format(data)
    if "match_id" in data and "date" in data:
        return _parse_matchstats_format(data)

    logger.warning(
        "sofascore_cache_unknown_format",
        path=str(path),
        keys=list(data.keys())[:10],
    )
    return None


def _parse_raw_format(data: dict[str, Any]) -> dict[str, Any]:
    """Parse the raw scraper JSON format.

    Args:
        data: Dict with ``game_id``, ``home_team``, ``away_team``,
            ``timestamp``, ``stats``.

    Returns:
        Flat dict with ``sofa_*`` prefixed stat columns.
    """
    timestamp = int(data["timestamp"])
    date = datetime.fromtimestamp(timestamp, tz=UTC).strftime("%Y-%m-%d")

    record: dict[str, Any] = {
        "game_id": data["game_id"],
        "home_team": str(data["home_team"]),
        "away_team": str(data["away_team"]),
        "date": date,
    }

    stats = data.get("stats", {})
    for raw_key, value in stats.items():
        # Keys are like "home_ballPossession", "away_expectedGoals"
        side, _, stat_key = raw_key.partition("_")
        if side not in ("home", "away") or not stat_key:
            continue

        # Map to canonical column name
        mapped = _RAW_KEY_TO_COLUMN.get(stat_key, stat_key)
        col_name = f"sofa_{side}_{mapped}"
        record[col_name] = _parse_numeric(value)

    return record


def _parse_matchstats_format(data: dict[str, Any]) -> dict[str, Any]:
    """Parse the MatchStats-serialized JSON format.

    Args:
        data: Dict with ``match_id``, ``home_team``, ``away_team``,
            ``date``, and flat ``home_*`` / ``away_*`` stat fields.

    Returns:
        Flat dict with ``sofa_*`` prefixed stat columns.
    """
    skip_keys = {"match_id", "home_team", "away_team", "date"}

    record: dict[str, Any] = {
        "game_id": data["match_id"],
        "home_team": str(data["home_team"]),
        "away_team": str(data["away_team"]),
        "date": str(data["date"]),
    }

    for key, value in data.items():
        if key in skip_keys:
            continue
        record[f"sofa_{key}"] = _parse_numeric(value)

    return record


def _parse_numeric(value: Any) -> float | None:
    """Parse a value to float, returning None for unparseable values.

    Handles strings like ``"62%"``, ``"1.45"``, plain numbers, and None.

    Args:
        value: Raw value from JSON.

    Returns:
        Float or None.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().rstrip("%")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def match_sofascore_to_features(
    features_df: pd.DataFrame,
    sofascore_df: pd.DataFrame,
    date_tolerance_days: int = 1,
) -> pd.DataFrame:
    """Left-join Sofascore stats to features parquet on team names + date.

    Matching logic:
    1. Normalize team names in both DataFrames.
    2. For each features row, find the Sofascore row with the same
       (normalized home_team, normalized away_team) and date within
       +/- ``date_tolerance_days``.
    3. Unmatched features rows get NaN for all ``sofa_*`` columns.

    Args:
        features_df: Features parquet DataFrame.
        sofascore_df: Sofascore cache DataFrame from ``load_sofascore_cache``.
        date_tolerance_days: Days of tolerance for date matching.

    Returns:
        Features DataFrame with ``sofa_*`` columns added.
    """
    if sofascore_df.empty:
        logger.warning("sofascore_match_empty_input")
        return features_df

    features = features_df.copy()
    features["date"] = pd.to_datetime(features["date"])

    sofa = sofascore_df.copy()
    sofa["date"] = pd.to_datetime(sofa["date"])

    # Normalize team names
    features["_norm_home"] = features["home_team"].map(normalize_team_name)
    features["_norm_away"] = features["away_team"].map(normalize_team_name)
    sofa["_norm_home"] = sofa["home_team"].map(normalize_team_name)
    sofa["_norm_away"] = sofa["away_team"].map(normalize_team_name)

    # Identify sofa stat columns (everything except metadata)
    sofa_stat_cols = [c for c in sofa.columns if c.startswith("sofa_")]

    # Drop existing sofa columns from features to avoid duplicates
    existing_sofa = [c for c in features.columns if c.startswith("sofa_")]
    if existing_sofa:
        logger.info(
            "sofascore_dropping_existing_columns",
            count=len(existing_sofa),
        )
        features = features.drop(columns=existing_sofa)

    # Build lookup: (norm_home, norm_away) -> list of (date, row_data)
    lookup: dict[tuple[str, str], list[tuple[pd.Timestamp, dict[str, Any]]]] = {}
    for _, row in sofa.iterrows():
        key = (row["_norm_home"], row["_norm_away"])
        entry = (row["date"], {col: row[col] for col in sofa_stat_cols})
        lookup.setdefault(key, []).append(entry)

    # Match features rows to sofascore rows
    matched_count = 0
    sofa_values: list[dict[str, Any]] = []
    empty_row = dict.fromkeys(sofa_stat_cols, None)
    tolerance = timedelta(days=date_tolerance_days)

    for _, feat_row in features.iterrows():
        key = (feat_row["_norm_home"], feat_row["_norm_away"])
        candidates = lookup.get(key, [])

        best_match: dict[str, Any] | None = None
        best_delta = timedelta(days=999)

        for sofa_date, sofa_data in candidates:
            delta = abs(feat_row["date"] - sofa_date)
            if delta <= tolerance and delta < best_delta:
                best_match = sofa_data
                best_delta = delta

        if best_match is not None:
            sofa_values.append(best_match)
            matched_count += 1
        else:
            sofa_values.append(empty_row)

    # Build result
    sofa_result = pd.DataFrame(sofa_values, index=features.index)
    result = pd.concat([features, sofa_result], axis=1)

    # Clean up temp columns
    result = result.drop(columns=["_norm_home", "_norm_away"], errors="ignore")

    logger.info(
        "sofascore_match_complete",
        total_features=len(features),
        sofascore_files=len(sofa),
        matched=matched_count,
        unmatched=len(features) - matched_count,
        sofa_columns=len(sofa_stat_cols),
    )

    return result


def run_sofascore_merge(
    parquet_path: Path,
    sofascore_dir: Path,
    windows: list[int] | None = None,
    dry_run: bool = False,
) -> pd.DataFrame:
    """Full pipeline: load cache, match, compute rolling, save.

    Args:
        parquet_path: Path to features parquet file.
        sofascore_dir: Root directory for Sofascore JSON cache.
        windows: Rolling window sizes. Defaults to ``[3, 5, 10]``.
        dry_run: If True, skip saving the parquet.

    Returns:
        Updated DataFrame with ``sofa_*`` columns and rolling features.
    """
    if windows is None:
        windows = [3, 5, 10]

    # Step 1: Load parquet
    logger.info("loading_parquet", path=str(parquet_path))
    features = pd.read_parquet(parquet_path)
    features["date"] = pd.to_datetime(features["date"])
    logger.info(
        "parquet_loaded",
        rows=len(features),
        cols=len(features.columns),
    )

    # Step 2: Load Sofascore cache
    logger.info(
        "loading_sofascore_cache",
        dir=str(sofascore_dir),
    )
    sofascore_df = load_sofascore_cache(sofascore_dir)
    if sofascore_df.empty:
        logger.error("sofascore_cache_empty_abort")
        return features

    # Step 3: Match and merge
    logger.info("matching_sofascore_to_features")
    merged = match_sofascore_to_features(features, sofascore_df)

    # Step 4: Compute rolling features
    logger.info(
        "computing_rolling_features",
        windows=windows,
    )
    result = compute_sofascore_rolling_features(merged, windows=windows)

    # Step 5: Report fill rates per league
    _report_fill_rates(result)

    # Step 6: Save
    if not dry_run:
        result.to_parquet(parquet_path, index=False)
        logger.info(
            "parquet_saved",
            path=str(parquet_path),
            rows=len(result),
            cols=len(result.columns),
        )
    else:
        logger.info(
            "dry_run_complete",
            rows=len(result),
            cols=len(result.columns),
            new_cols=len(result.columns) - len(features.columns),
        )

    return result


def _report_fill_rates(df: pd.DataFrame) -> None:
    """Log Sofascore fill rate per league.

    Args:
        df: DataFrame with ``sofa_*`` columns.
    """
    sofa_cols = [c for c in df.columns if c.startswith("sofa_")]
    if not sofa_cols:
        return

    # Use the first sofa column as a proxy for "has sofascore data"
    proxy_col = sofa_cols[0]

    for league in sorted(df["league"].unique()):
        league_df = df[df["league"] == league]
        total = len(league_df)
        filled = league_df[proxy_col].notna().sum()
        pct = round(filled / total * 100, 1) if total > 0 else 0.0
        logger.info(
            "sofascore_fill_rate",
            league=league,
            filled=int(filled),
            total=total,
            pct=pct,
        )

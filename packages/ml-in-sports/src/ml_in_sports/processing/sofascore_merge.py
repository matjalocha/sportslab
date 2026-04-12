"""Match and merge Sofascore stats into a features DataFrame.

This module is the bridge between the raw JSON cache files produced by
the background Sofascore scraper and the ``sofa_*`` feature columns in
the features parquet.  It handles:

1. **Loading**: delegate to ``sofascore_parsers.load_sofascore_cache``.
2. **Matching**: left-join Sofascore rows to parquet rows on
   (normalized home_team, normalized away_team, date +/- 1 day).
3. **Rolling features**: delegate to ``sofascore_features``.
4. **Saving**: overwrite the parquet with new ``sofa_*`` columns appended.

The module is consumed by both ``scripts/merge_sofascore.py`` and the
``sl merge-sofascore`` CLI command.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import structlog

from ml_in_sports.processing.sofascore_features import (
    compute_sofascore_rolling_features,
)
from ml_in_sports.processing.sofascore_parsers import (
    _parse_numeric,
    _parse_raw_format,
    load_sofascore_cache,
)
from ml_in_sports.utils.team_names import normalize_team_name

logger = structlog.get_logger(__name__)

# Re-export for backward compatibility — existing imports from this module
# that reference these names will continue to work.
__all__ = [
    "_parse_numeric",
    "_parse_raw_format",
    "load_sofascore_cache",
    "match_sofascore_to_features",
    "run_sofascore_merge",
]


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

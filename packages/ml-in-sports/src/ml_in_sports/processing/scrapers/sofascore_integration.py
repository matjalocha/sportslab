"""Merge Sofascore match statistics into the features pipeline.

Provides a function to join Sofascore tactical stats with an existing
features DataFrame by fuzzy-matching on team names and date.

Team name normalisation handles common differences between data sources
(e.g. "Wolverhampton Wanderers" vs "Wolverhampton", "Man City" vs
"Manchester City").
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import structlog

from ml_in_sports.processing.scrapers.sofascore import MatchStats

logger = structlog.get_logger(__name__)


# Common team name aliases across data sources.
# Keys are lowercased variants; values are the canonical form.
_TEAM_NAME_ALIASES: dict[str, str] = {
    "man city": "manchester city",
    "man utd": "manchester united",
    "man united": "manchester united",
    "wolves": "wolverhampton",
    "wolverhampton wanderers": "wolverhampton",
    "spurs": "tottenham",
    "tottenham hotspur": "tottenham",
    "nottingham forest": "nott'm forest",
    "nottm forest": "nott'm forest",
    "west ham united": "west ham",
    "brighton and hove albion": "brighton",
    "brighton hove albion": "brighton",
    "leicester city": "leicester",
    "newcastle united": "newcastle",
    "newcastle utd": "newcastle",
    "sheffield united": "sheffield utd",
    "crystal palace": "crystal palace",
    "atletico madrid": "atl. madrid",
    "atletico de madrid": "atl. madrid",
    "real sociedad": "sociedad",
    "paris saint-germain": "paris sg",
    "paris saint germain": "paris sg",
    "bayern munich": "bayern munchen",
    "bayern muenchen": "bayern munchen",
    "borussia dortmund": "dortmund",
    "borussia m.gladbach": "m'gladbach",
    "borussia monchengladbach": "m'gladbach",
    "inter milan": "inter",
    "internazionale": "inter",
    "ac milan": "milan",
}


def normalise_team_name(name: str) -> str:
    """Normalise a team name for cross-source matching.

    Lowercases, strips whitespace, then applies known aliases.

    Args:
        name: Raw team name from any source.

    Returns:
        Normalised lowercase team name.
    """
    lower = name.strip().lower()
    return _TEAM_NAME_ALIASES.get(lower, lower)


def _parse_date(date_str: str) -> datetime | None:
    """Parse a date string in common formats.

    Args:
        date_str: Date string (ISO, DD/MM/YYYY, etc.).

    Returns:
        Datetime or None if parsing fails.
    """
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _build_stats_lookup(
    stats_list: list[MatchStats],
) -> dict[tuple[str, str, str], MatchStats]:
    """Build a lookup dict from normalised (home, away, date) to MatchStats.

    Args:
        stats_list: List of MatchStats to index.

    Returns:
        Dict keyed by (normalised_home, normalised_away, date_str).
    """
    lookup: dict[tuple[str, str, str], MatchStats] = {}
    for stats in stats_list:
        key = (
            normalise_team_name(stats.home_team),
            normalise_team_name(stats.away_team),
            stats.date,
        )
        lookup[key] = stats
    return lookup


def _find_match(
    home: str,
    away: str,
    date_str: str,
    lookup: dict[tuple[str, str, str], MatchStats],
    date_tolerance_days: int = 1,
) -> MatchStats | None:
    """Find a matching MatchStats entry with date tolerance.

    First tries exact date match, then +/- tolerance days.

    Args:
        home: Normalised home team name.
        away: Normalised away team name.
        date_str: Date string from the features DataFrame.
        lookup: Pre-built lookup dict.
        date_tolerance_days: Number of days to search around the target date.

    Returns:
        Matching MatchStats or None.
    """
    # Exact match first
    exact_key = (home, away, date_str)
    if exact_key in lookup:
        return lookup[exact_key]

    # Try date tolerance
    target_date = _parse_date(date_str)
    if target_date is None:
        return None

    for delta in range(1, date_tolerance_days + 1):
        for direction in (-1, 1):
            candidate_date = target_date + timedelta(days=direction * delta)
            candidate_str = candidate_date.strftime("%Y-%m-%d")
            candidate_key = (home, away, candidate_str)
            if candidate_key in lookup:
                return lookup[candidate_key]

    return None


def _sofa_column_names() -> list[str]:
    """Return the list of sofa_ column names derived from MatchStats fields.

    Returns:
        Sorted list of column names with ``sofa_`` prefix.
    """
    from dataclasses import fields as dc_fields

    skip = {"match_id", "home_team", "away_team", "date"}
    return [f"sofa_{f.name}" for f in dc_fields(MatchStats) if f.name not in skip]


def _stats_to_flat_dict(stats: MatchStats) -> dict[str, Any]:
    """Convert MatchStats to a flat dict with ``sofa_`` prefix for merge.

    Args:
        stats: MatchStats instance.

    Returns:
        Dict with keys like ``sofa_home_possession``, ``sofa_away_tackles``.
    """
    result: dict[str, Any] = {}
    skip = {"match_id", "home_team", "away_team", "date"}
    for field_name in [f.name for f in stats.__dataclass_fields__.values()]:
        if field_name in skip:
            continue
        result[f"sofa_{field_name}"] = getattr(stats, field_name)
    return result


def _empty_sofa_dict() -> dict[str, Any]:
    """Return a dict with all sofa_ columns set to None (for unmatched rows).

    Returns:
        Dict with all sofa_ column names mapped to None.
    """
    return dict.fromkeys(_sofa_column_names(), None)


def merge_sofascore_stats(
    features_df: pd.DataFrame,
    stats: list[MatchStats],
    home_col: str = "home_team",
    away_col: str = "away_team",
    date_col: str = "date",
    date_tolerance_days: int = 1,
) -> pd.DataFrame:
    """Merge Sofascore match stats into a features DataFrame.

    Matches by normalised team names and date with tolerance. Adds
    columns with ``sofa_`` prefix for all tactical stats and xG.

    Unmatched rows get NaN for all Sofascore columns (left join behaviour).

    Args:
        features_df: Existing features DataFrame.
        stats: List of MatchStats from Sofascore.
        home_col: Column name for home team in features_df.
        away_col: Column name for away team in features_df.
        date_col: Column name for match date in features_df.
        date_tolerance_days: Days of tolerance for date matching.

    Returns:
        DataFrame with additional ``sofa_*`` columns.
    """
    if not stats:
        logger.warning("sofascore_merge_empty_stats")
        return features_df

    lookup = _build_stats_lookup(stats)
    sofa_rows: list[dict[str, Any]] = []
    matched = 0
    unmatched = 0

    for _, row in features_df.iterrows():
        home_norm = normalise_team_name(str(row[home_col]))
        away_norm = normalise_team_name(str(row[away_col]))
        date_val = str(row[date_col])

        match = _find_match(
            home_norm,
            away_norm,
            date_val,
            lookup,
            date_tolerance_days=date_tolerance_days,
        )

        if match is not None:
            sofa_rows.append(_stats_to_flat_dict(match))
            matched += 1
        else:
            sofa_rows.append(_empty_sofa_dict())
            unmatched += 1

    sofa_df = pd.DataFrame(sofa_rows, index=features_df.index)
    result = pd.concat([features_df, sofa_df], axis=1)

    logger.info(
        "sofascore_merge_complete",
        total_rows=len(features_df),
        matched=matched,
        unmatched=unmatched,
        new_columns=len(sofa_df.columns),
    )
    return result

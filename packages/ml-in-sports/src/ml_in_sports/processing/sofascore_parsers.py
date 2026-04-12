"""Parse Sofascore JSON cache files into flat dictionaries.

Handles two cache formats:
1. Raw scraper format: ``{game_id, home_team, away_team, timestamp, stats}``
2. MatchStats-serialized format: ``{match_id, home_team, away_team, date, ...}``

Used by ``sofascore_merge.load_sofascore_cache`` to normalize cache
files before matching and merging into the features parquet.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import structlog

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

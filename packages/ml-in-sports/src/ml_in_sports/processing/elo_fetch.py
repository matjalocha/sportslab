"""Fetch and cache ClubElo rating snapshots.

Downloads ELO snapshots at configurable intervals, caches them as CSV
files, and normalizes the raw ClubElo format to a standard schema.
Rate limit: 1 request per 2 seconds (free service).
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import structlog

from ml_in_sports.processing.extractors import ClubEloExtractor
from ml_in_sports.utils.team_names import normalize_team_name

logger = structlog.get_logger(__name__)

_REQUEST_INTERVAL_SECONDS = 2.0
_DEFAULT_CACHE_DIR = Path("data/elo")

# Maps our league identifiers to ClubElo country codes.
# ClubElo only fills the `league` column for Top-5; for the rest
# we rely on `country` + `level` to identify the correct teams.
LEAGUE_TO_COUNTRY: dict[str, str] = {
    "ENG-Premier League": "ENG",
    "ENG-Championship": "ENG",
    "ESP-La Liga": "ESP",
    "ESP-Segunda": "ESP",
    "GER-Bundesliga": "GER",
    "GER-Bundesliga 2": "GER",
    "ITA-Serie A": "ITA",
    "ITA-Serie B": "ITA",
    "FRA-Ligue 1": "FRA",
    "FRA-Ligue 2": "FRA",
    "NED-Eredivisie": "NED",
    "POR-Primeira Liga": "POR",
    "BEL-Jupiler Pro League": "BEL",
    "TUR-Süper Lig": "TUR",
    "GRE-Super League": "GRE",
    "SCO-Premiership": "SCO",
}

# Maps our league identifiers to ClubElo tier level (1=top, 2=second).
# Used to disambiguate teams that appear in both tiers for the same
# country (e.g. ENG teams in Championship vs Premier League).
LEAGUE_TO_LEVEL: dict[str, int] = {
    "ENG-Premier League": 1,
    "ENG-Championship": 2,
    "ESP-La Liga": 1,
    "ESP-Segunda": 2,
    "GER-Bundesliga": 1,
    "GER-Bundesliga 2": 2,
    "ITA-Serie A": 1,
    "ITA-Serie B": 2,
    "FRA-Ligue 1": 1,
    "FRA-Ligue 2": 2,
    "NED-Eredivisie": 1,
    "POR-Primeira Liga": 1,
    "BEL-Jupiler Pro League": 1,
    "TUR-Süper Lig": 1,
    "GRE-Super League": 1,
    "SCO-Premiership": 1,
}


def fetch_elo_for_date_range(
    start_date: str,
    end_date: str,
    step_days: int = 7,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Fetch ELO ratings for a date range, one snapshot per step_days.

    Caches each snapshot as a CSV in cache_dir to avoid redundant
    network requests on re-runs.  Respects ClubElo rate limits with
    a 2-second sleep between requests.

    Args:
        start_date: First date to fetch (YYYY-MM-DD).
        end_date: Last date to fetch (YYYY-MM-DD), inclusive.
        step_days: Days between successive snapshots.
        cache_dir: Directory for cached CSV files.

    Returns:
        DataFrame with columns: team, date, elo, country, level.
        One row per team per snapshot date.
    """
    if cache_dir is None:
        cache_dir = _DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    dates = pd.date_range(start=start_date, end=end_date, freq=f"{step_days}D")
    extractor = ClubEloExtractor()

    frames: list[pd.DataFrame] = []
    fetched_count = 0

    for snapshot_date in dates:
        date_str = snapshot_date.strftime("%Y-%m-%d")
        csv_path = cache_dir / f"elo_{date_str}.csv"

        if csv_path.exists():
            cached = pd.read_csv(csv_path)
            frames.append(cached)
            continue

        logger.info("fetching_elo_snapshot", date=date_str)

        if fetched_count > 0:
            time.sleep(_REQUEST_INTERVAL_SECONDS)

        raw = extractor.extract_ratings(date_str)
        if raw is None or raw.empty:
            logger.warning("elo_snapshot_empty", date=date_str)
            fetched_count += 1
            continue

        snapshot = _normalize_elo_snapshot(raw, date_str)
        snapshot.to_csv(csv_path, index=False)
        frames.append(snapshot)
        fetched_count += 1

        logger.info(
            "elo_snapshot_saved",
            date=date_str,
            teams=len(snapshot),
            path=str(csv_path),
        )

    if not frames:
        logger.warning("no_elo_data_fetched")
        return pd.DataFrame(columns=["team", "date", "elo", "country", "level"])

    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    logger.info(
        "elo_fetch_complete",
        snapshots=len(frames),
        total_rows=len(combined),
        dates_fetched=fetched_count,
    )
    return combined


def _normalize_elo_snapshot(
    raw: pd.DataFrame,
    date_str: str,
) -> pd.DataFrame:
    """Convert a raw ClubElo snapshot to our standard schema.

    Applies normalize_team_name to the index (team name) and
    keeps only the columns we need.

    Args:
        raw: DataFrame from ClubEloExtractor (indexed by team name).
        date_str: The snapshot date as YYYY-MM-DD.

    Returns:
        DataFrame with columns: team, date, elo, country, level.
    """
    result = pd.DataFrame({
        "team": raw.index.map(normalize_team_name),
        "date": date_str,
        "elo": raw["elo"].values,
        "country": raw["country"].values,
        "level": raw["level"].values,
    })
    return result

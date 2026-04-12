"""Sofascore cache utilities: load and organize cached match statistics.

Provides filesystem-level helpers for reading cached MatchStats JSON
files without network access, and a ``scrape_league_season`` function
that orchestrates scraping with per-match JSON caching.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from ml_in_sports.processing.scrapers.sofascore_types import (
    MatchStats,
    match_stats_from_dict,
    match_stats_to_dict,
)

if TYPE_CHECKING:
    from ml_in_sports.processing.scrapers.sofascore_scraper import (
        SofascoreScraper,
    )

logger = structlog.get_logger(__name__)


def _league_season_cache_dir(cache_dir: Path, league: str, season: str) -> Path:
    """Build the cache directory path for a league/season.

    Sanitises league and season strings for filesystem safety.

    Args:
        cache_dir: Root cache directory.
        league: Canonical league name.
        season: Season code.

    Returns:
        Path like ``cache_dir/ENG-Championship/24_25/``.
    """
    safe_league = league.replace(" ", "_").replace("/", "_")
    safe_season = season.replace("/", "_")
    return cache_dir / safe_league / safe_season


def load_cached_stats(
    cache_dir: Path,
    league: str,
    season: str,
) -> list[MatchStats]:
    """Load all cached MatchStats for a league/season without network access.

    Useful for offline analysis or integration with the feature pipeline.

    Args:
        cache_dir: Root cache directory.
        league: Canonical league name.
        season: Season code.

    Returns:
        List of MatchStats loaded from cache. Empty if no cache exists.
    """
    season_dir = _league_season_cache_dir(cache_dir, league, season)
    if not season_dir.exists():
        return []

    results: list[MatchStats] = []
    for path in sorted(season_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            results.append(match_stats_from_dict(data))
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(
                "sofascore_cache_load_failed",
                path=str(path),
                error=str(exc),
            )
    return results


def scrape_league_season(
    scraper: SofascoreScraper,
    league: str,
    season: str,
    cache_dir: Path = Path("data/sofascore"),
) -> list[MatchStats]:
    """Scrape all matches for a league/season with per-match caching.

    Caches each match's stats as JSON in
    ``cache_dir/{league}/{season}/{match_id}.json``.
    Skips already-cached matches on re-runs, making re-runs
    cheap and idempotent.

    Args:
        scraper: An initialized SofascoreScraper instance.
        league: Canonical league name.
        season: Season code (e.g. ``"24/25"``).
        cache_dir: Root directory for JSON cache files.

    Returns:
        List of MatchStats for all successfully scraped matches.
    """
    season_dir = _league_season_cache_dir(cache_dir, league, season)
    season_dir.mkdir(parents=True, exist_ok=True)

    events = scraper.get_season_match_ids(league, season)
    all_stats: list[MatchStats] = []
    cached_count = 0
    fetched_count = 0
    failed_count = 0

    for event in events:
        cache_path = season_dir / f"{event.match_id}.json"

        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                all_stats.append(match_stats_from_dict(data))
                cached_count += 1
                continue
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning(
                    "sofascore_cache_corrupt",
                    match_id=event.match_id,
                    path=str(cache_path),
                    error=str(exc),
                )
                # Fall through to re-fetch

        stats = scraper.get_match_stats(
            match_id=event.match_id,
            home_team=event.home_team,
            away_team=event.away_team,
            start_timestamp=event.start_timestamp,
        )

        if stats is None:
            failed_count += 1
            continue

        cache_path.write_text(
            json.dumps(match_stats_to_dict(stats), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        all_stats.append(stats)
        fetched_count += 1

    logger.info(
        "sofascore_league_season_complete",
        league=league,
        season=season,
        total_events=len(events),
        cached=cached_count,
        fetched=fetched_count,
        failed=failed_count,
    )
    return all_stats

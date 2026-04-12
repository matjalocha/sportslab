"""Sofascore scraper facade -- re-exports from submodules.

All public symbols are available from this module for backward
compatibility.  New code should import from the specific submodule.
"""

from ml_in_sports.processing.scrapers.sofascore_cache import (
    _league_season_cache_dir,
    load_cached_stats,
)
from ml_in_sports.processing.scrapers.sofascore_scraper import (
    SofascoreScraper,
)
from ml_in_sports.processing.scrapers.sofascore_types import (
    _STAT_KEY_MAP,
    SOFASCORE_SEASON_IDS,
    SOFASCORE_TOURNAMENTS,
    MatchStats,
    SofascoreMatchEvent,
    build_match_stats,
    match_stats_from_dict,
    match_stats_to_dict,
    parse_stat_value,
)

__all__ = [
    "SOFASCORE_SEASON_IDS",
    "SOFASCORE_TOURNAMENTS",
    "_STAT_KEY_MAP",
    "MatchStats",
    "SofascoreMatchEvent",
    "SofascoreScraper",
    "_league_season_cache_dir",
    "build_match_stats",
    "load_cached_stats",
    "match_stats_from_dict",
    "match_stats_to_dict",
    "parse_stat_value",
]

"""Scrape match statistics and xG from Sofascore.

Uses SeleniumBase to render sofascore.com, then fetches API endpoints
from within the browser context (bypasses CORS/Cloudflare).

Rate limit: 1 request per 2 seconds (configurable).

Failure modes handled:
- 403 Cloudflare block: close browser, re-init session, retry once
- 404 match not found: skip, log warning, return None
- Timeout / network error: retry up to MAX_RETRIES times
- Browser crash: re-init session, retry

Failure modes NOT handled (yet):
- IP ban (would need proxy rotation)
- Captcha challenge (would need manual intervention or solver)
- Season ID lookup (hardcoded per league, must be updated each season)
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_MAX_RETRIES = 3

# Sofascore unique tournament IDs for our target leagues.
SOFASCORE_TOURNAMENTS: dict[str, int] = {
    "ENG-Premier League": 17,
    "ENG-Championship": 18,
    "ESP-La Liga": 8,
    "ESP-Segunda": 54,
    "GER-Bundesliga": 35,
    "GER-Bundesliga 2": 44,
    "ITA-Serie A": 23,
    "ITA-Serie B": 53,
    "FRA-Ligue 1": 34,
    "FRA-Ligue 2": 182,
    "NED-Eredivisie": 37,
    "POR-Primeira Liga": 238,
    "BEL-Jupiler Pro League": 38,
    "TUR-Super Lig": 52,
    "GRE-Super League": 185,
    "SCO-Premiership": 36,
}

# Sofascore season IDs keyed by our season code (e.g. "24/25").
# These change every year and must be updated manually or discovered
# via the /api/v1/unique-tournament/{id}/seasons endpoint.
SOFASCORE_SEASON_IDS: dict[str, dict[str, int]] = {
    "24/25": {
        "ENG-Premier League": 61627,
        "ENG-Championship": 62045,
        "ESP-La Liga": 61643,
        "ESP-Segunda": 62046,
        "GER-Bundesliga": 61635,
        "GER-Bundesliga 2": 62047,
        "ITA-Serie A": 61639,
        "ITA-Serie B": 62048,
        "FRA-Ligue 1": 61736,
        "FRA-Ligue 2": 62049,
        "NED-Eredivisie": 61641,
        "POR-Primeira Liga": 62050,
        "BEL-Jupiler Pro League": 62051,
        "TUR-Super Lig": 62052,
        "GRE-Super League": 62053,
        "SCO-Premiership": 62054,
    },
}

# JavaScript template: fetch match list from Sofascore API.
# Parameters: tournamentId (int), seasonId (int), page (int).
_JS_FETCH_MATCH_LIST = """
const resp = await fetch(
    '/api/v1/unique-tournament/' + arguments[0]
    + '/season/' + arguments[1]
    + '/events/last/' + arguments[2]
);
if (!resp.ok) return JSON.stringify({error: resp.status});
const data = await resp.json();
return JSON.stringify(
    (data.events || []).map(e => ({
        id: e.id,
        home: e.homeTeam.name,
        away: e.awayTeam.name,
        date: e.startTimestamp
    }))
);
"""

# JavaScript template: fetch match statistics and flatten nested structure.
# Parameters: matchId (int).
_JS_FETCH_MATCH_STATS = """
const matchId = arguments[0];
const resp = await fetch('/api/v1/event/' + matchId + '/statistics');
if (!resp.ok) return JSON.stringify({error: resp.status});
const data = await resp.json();
const stats = {};
for (const period of data.statistics || []) {
    if (period.period !== 'ALL') continue;
    for (const group of period.groups || []) {
        for (const item of group.statisticsItems || []) {
            stats[item.key + '_home'] = item.homeValue;
            stats[item.key + '_away'] = item.awayValue;
        }
    }
}
return JSON.stringify(stats);
"""


@dataclass(frozen=True)
class SofascoreMatchEvent:
    """Minimal match metadata from the Sofascore events endpoint."""

    match_id: int
    home_team: str
    away_team: str
    start_timestamp: int


@dataclass(frozen=True)
class MatchStats:
    """Statistics for one match from Sofascore.

    All stat fields are Optional because Sofascore does not guarantee
    every statistic is present for every match (e.g. lower leagues
    may lack xG or detailed passing data).
    """

    match_id: int
    home_team: str
    away_team: str
    date: str
    # Tactical stats
    home_possession: float | None
    away_possession: float | None
    home_total_shots: int | None
    away_total_shots: int | None
    home_shots_on_target: int | None
    away_shots_on_target: int | None
    home_tackles: int | None
    away_tackles: int | None
    home_accurate_passes: int | None
    away_accurate_passes: int | None
    home_accurate_passes_pct: float | None
    away_accurate_passes_pct: float | None
    home_accurate_crosses: int | None
    away_accurate_crosses: int | None
    home_interceptions: int | None
    away_interceptions: int | None
    home_clearances: int | None
    away_clearances: int | None
    home_accurate_long_balls: int | None
    away_accurate_long_balls: int | None
    home_ground_duels_won: int | None
    away_ground_duels_won: int | None
    home_aerial_duels_won: int | None
    away_aerial_duels_won: int | None
    home_successful_dribbles: int | None
    away_successful_dribbles: int | None
    home_saves: int | None
    away_saves: int | None
    # xG
    home_expected_goals: float | None
    away_expected_goals: float | None


# Mapping from Sofascore JSON keys to MatchStats field names (minus home/away prefix).
# The JSON keys use camelCase; we map to snake_case fields.
_STAT_KEY_MAP: dict[str, str] = {
    "ballPossession": "possession",
    "totalShotsOnGoal": "total_shots",  # Sofascore calls total "on goal"
    "shotsOnTarget": "shots_on_target",
    "tackles": "tackles",
    "accuratePasses": "accurate_passes",
    "accuratePassesPercentage": "accurate_passes_pct",
    "accurateCrosses": "accurate_crosses",
    "interceptions": "interceptions",
    "clearances": "clearances",
    "accurateLongBalls": "accurate_long_balls",
    "groundDuelsWon": "ground_duels_won",
    "aerialDuelsWon": "aerial_duels_won",
    "successfulDribbles": "successful_dribbles",
    "saves": "saves",
    "expectedGoals": "expected_goals",
}


def parse_stat_value(value: Any) -> int | float | None:
    """Parse a stat value from Sofascore JSON to int or float.

    Sofascore returns stats as strings like "62%", "15", "1.45",
    or sometimes as plain numbers. This function normalises them.

    Args:
        value: Raw value from Sofascore JSON.

    Returns:
        Parsed numeric value or None if unparseable.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        cleaned = value.strip().rstrip("%")
        if not cleaned:
            return None
        try:
            if "." in cleaned:
                return float(cleaned)
            return int(cleaned)
        except ValueError:
            return None
    return None


def build_match_stats(
    match_id: int,
    home_team: str,
    away_team: str,
    date: str,
    raw_stats: dict[str, Any],
) -> MatchStats:
    """Build a MatchStats from flattened Sofascore JSON stats.

    The raw_stats dict has keys like ``"ballPossession_home"``,
    ``"tackles_away"``, etc. This function maps them to MatchStats fields.

    Args:
        match_id: Sofascore event ID.
        home_team: Home team name.
        away_team: Away team name.
        date: ISO date string.
        raw_stats: Flattened statistics dict from the JS fetch script.

    Returns:
        Populated MatchStats dataclass.
    """
    parsed: dict[str, Any] = {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "date": date,
    }

    for sofa_key, field_base in _STAT_KEY_MAP.items():
        home_raw = raw_stats.get(f"{sofa_key}_home")
        away_raw = raw_stats.get(f"{sofa_key}_away")
        parsed[f"home_{field_base}"] = parse_stat_value(home_raw)
        parsed[f"away_{field_base}"] = parse_stat_value(away_raw)

    # Only pass fields that exist on MatchStats to avoid TypeError
    valid_field_names = {f.name for f in fields(MatchStats)}
    filtered = {k: v for k, v in parsed.items() if k in valid_field_names}
    return MatchStats(**filtered)


def match_stats_to_dict(stats: MatchStats) -> dict[str, Any]:
    """Convert MatchStats to a JSON-serialisable dict.

    Args:
        stats: MatchStats instance.

    Returns:
        Dictionary suitable for ``json.dumps``.
    """
    return asdict(stats)


def match_stats_from_dict(data: dict[str, Any]) -> MatchStats:
    """Reconstruct MatchStats from a dict (e.g. loaded from JSON cache).

    Args:
        data: Dictionary with MatchStats field names as keys.

    Returns:
        MatchStats instance.
    """
    valid_field_names = {f.name for f in fields(MatchStats)}
    filtered = {k: v for k, v in data.items() if k in valid_field_names}
    return MatchStats(**filtered)


class SofascoreScraper:
    """Scrape match statistics from Sofascore via SeleniumBase.

    Opens sofascore.com once to establish a browser session, then uses
    ``sb.execute_script(fetch(...))`` to call the internal API from
    within the page context.

    Args:
        headless: Run browser in headless mode.
        rate_limit: Minimum seconds between API requests.

    Usage::

        scraper = SofascoreScraper()
        try:
            matches = scraper.get_season_match_ids("ENG-Championship", "24/25")
            for match_id, home, away, ts in matches:
                stats = scraper.get_match_stats(match_id, home, away, ts)
        finally:
            scraper.close()
    """

    def __init__(self, headless: bool = True, rate_limit: float = 2.0) -> None:
        self._headless = headless
        self._rate_limit = rate_limit
        self._last_request_time: float = 0.0
        self._browser_ctx: Any = None
        self._browser: Any = None
        self._session_active: bool = False

    def _ensure_session(self) -> Any:
        """Start browser and navigate to sofascore.com if not already active.

        Returns:
            The entered SeleniumBase SB instance (the driver).
        """
        if self._session_active and self._browser is not None:
            return self._browser

        from seleniumbase import SB

        self._browser_ctx = SB(uc=True, headless=self._headless)
        self._browser = self._browser_ctx.__enter__()
        self._browser.open("https://www.sofascore.com/")
        self._browser.sleep(2)
        self._session_active = True
        logger.info("sofascore_session_started", headless=self._headless)
        return self._browser

    def _reset_session(self) -> Any:
        """Close and re-open the browser session.

        Used when we hit a 403 or other session-level error.

        Returns:
            Fresh SeleniumBase SB instance.
        """
        self._close_browser()
        return self._ensure_session()

    def _close_browser(self) -> None:
        """Close browser if active, swallowing errors."""
        if self._browser_ctx is not None:
            try:
                self._browser_ctx.__exit__(None, None, None)
            except Exception as exc:
                logger.debug("sofascore_browser_close_error", error=str(exc))
            self._browser_ctx = None
            self._browser = None
            self._session_active = False

    def _wait_for_rate_limit(self) -> None:
        """Sleep if needed to respect rate limit."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)

    def _execute_api_call(self, js_script: str, *args: Any) -> dict[str, Any] | list[Any] | None:
        """Execute a JavaScript fetch call within the browser context.

        Handles rate limiting, retries on 403, and JSON parsing.

        Args:
            js_script: JavaScript code that calls ``fetch()`` and returns
                a JSON string via ``return JSON.stringify(...)``.
            *args: Arguments passed to the script via ``arguments[]``.

        Returns:
            Parsed JSON (dict or list), or None on failure.
        """
        for attempt in range(_MAX_RETRIES):
            self._wait_for_rate_limit()
            try:
                sb = self._ensure_session()
                raw = sb.execute_script(js_script, *args)
                self._last_request_time = time.monotonic()
            except Exception as exc:
                logger.warning(
                    "sofascore_script_execution_failed",
                    attempt=attempt + 1,
                    error=str(exc),
                )
                sb = self._reset_session()
                continue

            if raw is None:
                logger.warning("sofascore_null_response", attempt=attempt + 1)
                continue

            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning(
                    "sofascore_json_parse_failed",
                    attempt=attempt + 1,
                    error=str(exc),
                    raw_preview=str(raw)[:200],
                )
                continue

            if isinstance(parsed, dict) and "error" in parsed:
                error_code = parsed["error"]
                if error_code == 404:
                    logger.info("sofascore_not_found", args=args)
                    return None
                if error_code == 403:
                    logger.warning(
                        "sofascore_403_blocked",
                        attempt=attempt + 1,
                    )
                    sb = self._reset_session()
                    continue
                logger.warning(
                    "sofascore_api_error",
                    error_code=error_code,
                    attempt=attempt + 1,
                )
                continue

            return parsed  # type: ignore[no-any-return]

        logger.error("sofascore_max_retries_exceeded", args=args)
        return None

    def get_season_match_ids(
        self,
        league: str,
        season: str,
    ) -> list[SofascoreMatchEvent]:
        """Get all finished match events for a league/season.

        Paginates through the ``events/last/{page}`` endpoint until
        an empty page is returned.

        Args:
            league: Canonical league name (e.g. ``"ENG-Championship"``).
            season: Season code (e.g. ``"24/25"``).

        Returns:
            List of SofascoreMatchEvent with match metadata.

        Raises:
            ValueError: If league or season is not in our lookup tables.
        """
        tournament_id = SOFASCORE_TOURNAMENTS.get(league)
        if tournament_id is None:
            raise ValueError(
                f"Unknown league {league!r}. "
                f"Available: {sorted(SOFASCORE_TOURNAMENTS.keys())}"
            )

        season_ids = SOFASCORE_SEASON_IDS.get(season)
        if season_ids is None:
            raise ValueError(
                f"Unknown season {season!r}. "
                f"Available: {sorted(SOFASCORE_SEASON_IDS.keys())}"
            )

        season_id = season_ids.get(league)
        if season_id is None:
            raise ValueError(
                f"No season ID for {league!r} in season {season!r}."
            )

        all_events: list[SofascoreMatchEvent] = []
        page = 0

        while True:
            logger.info(
                "sofascore_fetching_match_list",
                league=league,
                season=season,
                page=page,
            )
            result = self._execute_api_call(
                _JS_FETCH_MATCH_LIST,
                tournament_id,
                season_id,
                page,
            )

            if result is None or not isinstance(result, list) or len(result) == 0:
                break

            for event in result:
                all_events.append(
                    SofascoreMatchEvent(
                        match_id=int(event["id"]),
                        home_team=str(event["home"]),
                        away_team=str(event["away"]),
                        start_timestamp=int(event["date"]),
                    )
                )

            page += 1

        logger.info(
            "sofascore_match_list_complete",
            league=league,
            season=season,
            total_matches=len(all_events),
        )
        return all_events

    def get_match_stats(
        self,
        match_id: int,
        home_team: str,
        away_team: str,
        start_timestamp: int,
    ) -> MatchStats | None:
        """Get statistics for a single match.

        Args:
            match_id: Sofascore event ID.
            home_team: Home team name.
            away_team: Away team name.
            start_timestamp: Unix timestamp of match start.

        Returns:
            MatchStats if statistics are available, None otherwise.
        """
        from datetime import UTC, datetime

        result = self._execute_api_call(_JS_FETCH_MATCH_STATS, match_id)
        if result is None or not isinstance(result, dict):
            logger.warning(
                "sofascore_no_stats_for_match",
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
            )
            return None

        date_str = datetime.fromtimestamp(start_timestamp, tz=UTC).strftime("%Y-%m-%d")

        stats = build_match_stats(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            date=date_str,
            raw_stats=result,
        )
        logger.info(
            "sofascore_match_stats_fetched",
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
        )
        return stats

    def scrape_league_season(
        self,
        league: str,
        season: str,
        cache_dir: Path = Path("data/sofascore"),
    ) -> list[MatchStats]:
        """Scrape all matches for a league/season with caching.

        Caches each match's stats as JSON in
        ``cache_dir/{league}/{season}/{match_id}.json``.
        Skips already-cached matches on re-runs, making re-runs
        cheap and idempotent.

        Args:
            league: Canonical league name.
            season: Season code (e.g. ``"24/25"``).
            cache_dir: Root directory for JSON cache files.

        Returns:
            List of MatchStats for all successfully scraped matches.
        """
        season_dir = _league_season_cache_dir(cache_dir, league, season)
        season_dir.mkdir(parents=True, exist_ok=True)

        events = self.get_season_match_ids(league, season)
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

            stats = self.get_match_stats(
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

    def close(self) -> None:
        """Close the browser session."""
        self._close_browser()
        logger.info("sofascore_scraper_closed")


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

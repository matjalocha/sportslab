"""Scrape match statistics and xG from Sofascore via SeleniumBase.

Renders sofascore.com, then fetches API endpoints from within the
browser context (bypasses CORS/Cloudflare).  Handles 403 resets,
404 skips, and automatic retries on network errors.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import structlog

from ml_in_sports.processing.scrapers.sofascore_types import (
    _JS_FETCH_MATCH_LIST,
    _JS_FETCH_MATCH_STATS,
    SOFASCORE_SEASON_IDS,
    SOFASCORE_TOURNAMENTS,
    MatchStats,
    SofascoreMatchEvent,
    build_match_stats,
)

logger = structlog.get_logger(__name__)

_MAX_RETRIES = 3


class SofascoreScraper:
    """Scrape match statistics from Sofascore via SeleniumBase.

    Opens sofascore.com once, then uses ``sb.execute_script(fetch(...))``
    to call the internal API from within the page context.

    Args:
        headless: Run browser in headless mode.
        rate_limit: Minimum seconds between API requests.
    """

    def __init__(self, headless: bool = True, rate_limit: float = 2.0) -> None:
        self._headless = headless
        self._rate_limit = rate_limit
        self._last_request_time: float = 0.0
        self._browser_ctx: Any = None
        self._browser: Any = None
        self._session_active: bool = False

    def _ensure_session(self) -> Any:
        """Start browser and navigate to sofascore.com if not already active."""
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
        """Close and re-open the browser session (e.g. after 403)."""
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
        """Execute a JS fetch call with rate limiting, retries, and JSON parsing."""
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

        Delegates to ``sofascore_cache.scrape_league_season``.
        """
        from ml_in_sports.processing.scrapers.sofascore_cache import (
            scrape_league_season,
        )

        return scrape_league_season(
            scraper=self,
            league=league,
            season=season,
            cache_dir=cache_dir,
        )

    def close(self) -> None:
        """Close the browser session."""
        self._close_browser()
        logger.info("sofascore_scraper_closed")

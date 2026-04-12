"""Proof-of-concept scraper for footballdatabase.eu competition pages.

This module is intentionally conservative. It is designed around canonical
competition pages, a small per-run page budget, on-disk caching, and a default
delay above the site's published ``Crawl-Delay: 2`` value.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import structlog

if TYPE_CHECKING:
    from bs4 import Tag

logger = structlog.get_logger(__name__)

_BASE_URL = "https://www.footballdatabase.eu"
_MOMENT_TZ_RE = re.compile(r'moment\.tz\("([^"]+)","([^"]+)"\)')
_MATCH_ID_RE = re.compile(r"/match/podsumowanie/(\d+)-")
_SCORE_RE = re.compile(r"(?P<home>\d+)\s*-\s*(?P<away>\d+)")


@dataclass(frozen=True)
class FootballDatabaseFixture:
    """Fixture or result parsed from a footballdatabase.eu competition page."""

    match_id: str
    competition_url: str
    round_name: str | None
    kickoff: datetime | None
    timezone: str | None
    home_team: str
    away_team: str
    status: str
    home_goals: int | None
    away_goals: int | None
    match_url: str | None


class FootballDatabaseScraper:
    """Conservative footballdatabase.eu competition-page scraper.

    Args:
        rate_limit_seconds: Minimum seconds between network requests. Defaults
            to 2.5 to stay above the public robots.txt crawl delay.
        timeout_seconds: HTTP timeout.
        cache_dir: Optional cache directory. Cached pages do not consume the
            page budget or create network traffic.
        max_pages_per_run: Hard stop to avoid accidental broad crawls.
    """

    def __init__(
        self,
        rate_limit_seconds: float = 2.5,
        timeout_seconds: float = 15.0,
        cache_dir: Path | None = Path(".cache/footballdatabase"),
        max_pages_per_run: int = 20,
    ) -> None:
        self._rate_limit_seconds = rate_limit_seconds
        self._timeout_seconds = timeout_seconds
        self._cache_dir = cache_dir
        self._max_pages_per_run = max_pages_per_run
        self._last_request_time = 0.0
        self._pages_fetched = 0

    def scrape_competition_fixtures(
        self,
        competition_url: str,
    ) -> list[FootballDatabaseFixture]:
        """Fetch and parse fixtures/results from a competition page."""
        html = self._fetch_page(competition_url)
        if html is None:
            return []
        return parse_competition_fixtures(html, competition_url)

    def _fetch_page(self, url: str) -> str | None:
        """Fetch a single URL with cache, delay, budget, and error handling."""
        cache_path = self._cache_path(url)
        if cache_path is not None and cache_path.exists():
            return cache_path.read_text(encoding="utf-8")

        if self._pages_fetched >= self._max_pages_per_run:
            logger.warning(
                "footballdatabase_page_budget_exhausted",
                max_pages=self._max_pages_per_run,
            )
            return None

        import requests

        self._wait_for_rate_limit()
        try:
            response = requests.get(
                url,
                timeout=self._timeout_seconds,
                headers={
                    "User-Agent": "SportsLab research crawler; respectful rate-limited PoC",
                    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
                },
            )
            self._last_request_time = time.monotonic()
            self._pages_fetched += 1
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("footballdatabase_fetch_failed", url=url, error=str(exc))
            return None

        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(response.text, encoding="utf-8")
        return response.text

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._rate_limit_seconds:
            time.sleep(self._rate_limit_seconds - elapsed)

    def _cache_path(self, url: str) -> Path | None:
        if self._cache_dir is None:
            return None
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{digest}.html"


def parse_competition_fixtures(
    html: str,
    competition_url: str,
) -> list[FootballDatabaseFixture]:
    """Parse visible fixtures/results from a competition page HTML document."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    results = soup.select_one("div#results")
    if results is None:
        logger.warning("footballdatabase_results_section_missing")
        return []

    round_title = _extract_round_title(results)
    fixtures: list[FootballDatabaseFixture] = []

    for table in results.select("table.list"):
        current_date_text: str | None = None
        for row in table.select("tr"):
            raw_classes = row.get("class")
            classes = set(raw_classes if isinstance(raw_classes, list) else [])
            if "date" in classes:
                current_date_text = row.get_text(" ", strip=True)
                continue
            if "line" not in classes:
                continue

            fixture = _parse_fixture_row(row, competition_url, round_title, current_date_text)
            if fixture is not None:
                fixtures.append(fixture)

    logger.info(
        "footballdatabase_fixtures_parsed",
        competition_url=competition_url,
        fixtures=len(fixtures),
    )
    return fixtures


def _extract_round_title(results: Tag) -> str | None:
    title = results.select_one("span.dday")
    if title is None:
        return None
    return title.get_text(" ", strip=True) or None


def _parse_fixture_row(
    row: Tag,
    competition_url: str,
    round_title: str | None,
    current_date_text: str | None,
) -> FootballDatabaseFixture | None:
    home = row.select_one("td.club.left a")
    away = row.select_one("td.club.right a")
    if home is None or away is None:
        return None

    score_cell = row.select_one("td.score")
    match_url = _extract_match_url(score_cell)
    match_id = _extract_match_id(match_url)
    if match_id is None:
        match_id = _fallback_match_id(current_date_text, home, away)

    score_text = score_cell.get_text(" ", strip=True) if score_cell is not None else ""
    score_match = _SCORE_RE.search(score_text)
    home_goals = int(score_match.group("home")) if score_match else None
    away_goals = int(score_match.group("away")) if score_match else None
    status = "played" if score_match else "upcoming"

    kickoff, timezone = _extract_kickoff(row)

    return FootballDatabaseFixture(
        match_id=match_id,
        competition_url=competition_url,
        round_name=round_title,
        kickoff=kickoff,
        timezone=timezone,
        home_team=home.get_text(" ", strip=True),
        away_team=away.get_text(" ", strip=True),
        status=status,
        home_goals=home_goals,
        away_goals=away_goals,
        match_url=match_url,
    )


def _extract_match_url(score_cell: Tag | None) -> str | None:
    if score_cell is None:
        return None
    link = score_cell.select_one("a[href]")
    if link is None:
        return None
    href = link.get("href")
    if not isinstance(href, str):
        return None
    return urljoin(_BASE_URL, href)


def _extract_match_id(match_url: str | None) -> str | None:
    if match_url is None:
        return None
    match = _MATCH_ID_RE.search(match_url)
    if match is None:
        return None
    return match.group(1)


def _fallback_match_id(
    current_date_text: str | None,
    home: Tag,
    away: Tag,
) -> str:
    parts = [
        current_date_text or "unknown-date",
        home.get_text(" ", strip=True),
        away.get_text(" ", strip=True),
    ]
    return "|".join(parts)


def _extract_kickoff(row: Tag) -> tuple[datetime | None, str | None]:
    script = row.select_one("td.hour script")
    script_text = script.get_text(" ", strip=True) if script is not None else ""
    match = _MOMENT_TZ_RE.search(script_text)
    if match is None:
        return None, None

    dt_str, timezone = match.groups()
    try:
        kickoff = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None, timezone
    return kickoff, timezone

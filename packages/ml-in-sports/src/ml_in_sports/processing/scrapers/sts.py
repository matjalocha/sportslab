"""Scrape upcoming match odds from STS.pl.

STS.pl is a Polish bookmaker. This scraper fetches current odds for
football matches from their website.

Rate limited: 1 request per rate_limit_seconds (default 3.0).
Uses requests + BeautifulSoup for HTML parsing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from bs4 import Tag

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class OddsSnapshot:
    """Current odds from a bookmaker for one market of one match.

    Attributes:
        bookmaker: Bookmaker name (e.g. "STS").
        match_id: Constructed match identifier (e.g. "2024-04-06 Arsenal-Chelsea").
        home_team: Home team name.
        away_team: Away team name.
        league: League name (e.g. "ENG-Premier League").
        kickoff: Match kickoff datetime (UTC).
        market: Bet market (e.g. "1x2_home", "1x2_draw", "1x2_away").
        odds: Decimal odds (e.g. 2.15).
        scraped_at: When the odds were scraped (UTC).
    """

    bookmaker: str
    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff: datetime
    market: str
    odds: float
    scraped_at: datetime


# STS.pl football section URL
_STS_BASE_URL = "https://www.sts.pl/pl/oferta/pilka-nozna/"

# Map STS league names to our canonical names
_STS_LEAGUE_MAP: dict[str, str] = {
    "Anglia - Premier League": "ENG-Premier League",
    "Hiszpania - LaLiga": "ESP-La Liga",
    "Niemcy - Bundesliga": "GER-Bundesliga",
    "Wlochy - Serie A": "ITA-Serie A",
    "Francja - Ligue 1": "FRA-Ligue 1",
    "Anglia - Championship": "ENG-Championship",
    "Polska - Ekstraklasa": "POL-Ekstraklasa",
    "Holandia - Eredivisie": "NED-Eredivisie",
}


class StsScraper:
    """Scrape odds from STS.pl website.

    Implements rate limiting between requests. Handles errors gracefully --
    returns empty list if website is unreachable or HTML structure changed.

    Args:
        rate_limit_seconds: Minimum time between HTTP requests.
        timeout_seconds: HTTP request timeout.

    Usage::

        scraper = StsScraper()
        odds = scraper.scrape_upcoming(leagues=["ENG-Premier League"])
    """

    def __init__(
        self,
        rate_limit_seconds: float = 3.0,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._rate_limit = rate_limit_seconds
        self._timeout = timeout_seconds
        self._last_request_time: float = 0.0

    def _wait_for_rate_limit(self) -> None:
        """Sleep if needed to respect rate limit."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)

    def _fetch_page(self, url: str) -> str | None:
        """Fetch a URL with rate limiting and error handling.

        Returns HTML string or None if request failed.
        """
        import requests

        self._wait_for_rate_limit()
        try:
            resp = requests.get(
                url,
                timeout=self._timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "pl-PL,pl;q=0.9",
                },
            )
            self._last_request_time = time.monotonic()
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("sts_fetch_failed", url=url, error=str(exc))
            return None
        else:
            return resp.text

    def scrape_upcoming(
        self,
        leagues: list[str] | None = None,
    ) -> list[OddsSnapshot]:
        """Scrape upcoming match odds from STS.pl.

        Args:
            leagues: Filter to these leagues (our canonical names).
                     None = all available.

        Returns:
            List of OddsSnapshot. Empty list if scraping fails.
        """
        html = self._fetch_page(_STS_BASE_URL)
        if html is None:
            return []
        return self._parse_odds_page(html, leagues)

    def _parse_odds_page(
        self,
        html: str,
        leagues: list[str] | None = None,
    ) -> list[OddsSnapshot]:
        """Parse STS.pl HTML for match odds.

        STS.pl uses a dynamic JS-rendered page, so static HTML parsing
        may not capture all matches. This is a best-effort parser.

        Args:
            html: Raw HTML string.
            leagues: Optional league filter.

        Returns:
            List of OddsSnapshot.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        snapshots: list[OddsSnapshot] = []
        now = datetime.now(tz=UTC)

        # STS.pl structure (as of 2026 -- may change):
        # Look for match containers with team names and odds.
        # Common patterns: div.match-row, div.event-row, etc.
        #
        # Since the exact HTML structure is unknown and may change,
        # we try multiple selector strategies:
        match_elements = (
            soup.select("div.match-row")
            or soup.select("div[data-event-id]")
            or soup.select("tr.event-row")
            or soup.select("div.event")
        )

        if not match_elements:
            logger.warning(
                "sts_no_matches_found",
                reason="HTML structure may have changed or page is JS-rendered",
            )
            return []

        for element in match_elements:
            try:
                snapshot_group = self._parse_match_element(element, now, leagues)
                snapshots.extend(snapshot_group)
            except Exception as exc:
                logger.debug("sts_parse_match_failed", error=str(exc))
                continue

        logger.info(
            "sts_scrape_complete",
            matches=len(snapshots) // 3 if snapshots else 0,
            odds=len(snapshots),
        )
        return snapshots

    def _parse_match_element(
        self,
        element: Tag,
        now: datetime,
        leagues: list[str] | None,
    ) -> list[OddsSnapshot]:
        """Parse a single match element into OddsSnapshot list.

        Attempts to extract: home_team, away_team, league, kickoff, 1X2 odds.
        Returns 3 OddsSnapshot (home/draw/away) for a valid match, or empty list.

        This is a placeholder -- real implementation needs adaptation to
        actual STS.pl HTML structure.
        """
        # TODO(SPO-68): Implement live STS.pl HTML parsing when structure is known
        return []

    @staticmethod
    def parse_from_html_fixture(
        html: str,
        leagues: list[str] | None = None,
    ) -> list[OddsSnapshot]:
        """Parse odds from a saved HTML fixture (for testing).

        This parses a simplified HTML format used in test fixtures::

            <div class="match-row" data-league="Anglia - Premier League">
              <span class="team-home">Arsenal</span>
              <span class="team-away">Chelsea</span>
              <span class="kickoff">2024-04-06 15:30</span>
              <span class="odds-home">2.15</span>
              <span class="odds-draw">3.40</span>
              <span class="odds-away">3.20</span>
            </div>

        Args:
            html: HTML string in the fixture format.
            leagues: Optional league filter.

        Returns:
            List of OddsSnapshot.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        snapshots: list[OddsSnapshot] = []
        now = datetime.now(tz=UTC)

        for row in soup.select("div.match-row"):
            league_raw = row.get("data-league", "")
            league = _STS_LEAGUE_MAP.get(str(league_raw), str(league_raw))

            if leagues and league not in leagues:
                continue

            home = row.select_one("span.team-home")
            away = row.select_one("span.team-away")
            kickoff_el = row.select_one("span.kickoff")
            odds_home_el = row.select_one("span.odds-home")
            odds_draw_el = row.select_one("span.odds-draw")
            odds_away_el = row.select_one("span.odds-away")

            if not all([home, away, kickoff_el, odds_home_el, odds_draw_el, odds_away_el]):
                continue

            # All elements guaranteed non-None by the check above
            assert home is not None
            assert away is not None
            assert kickoff_el is not None
            assert odds_home_el is not None
            assert odds_draw_el is not None
            assert odds_away_el is not None

            home_name = home.get_text(strip=True)
            away_name = away.get_text(strip=True)
            kickoff_str = kickoff_el.get_text(strip=True)

            try:
                kickoff = datetime.strptime(kickoff_str, "%Y-%m-%d %H:%M").replace(
                    tzinfo=UTC,
                )
            except ValueError:
                continue

            try:
                odds_values = {
                    "1x2_home": float(odds_home_el.get_text(strip=True)),
                    "1x2_draw": float(odds_draw_el.get_text(strip=True)),
                    "1x2_away": float(odds_away_el.get_text(strip=True)),
                }
            except ValueError:
                continue

            match_id = f"{kickoff.strftime('%Y-%m-%d')} {home_name}-{away_name}"

            for market, odds_val in odds_values.items():
                snapshots.append(
                    OddsSnapshot(
                        bookmaker="STS",
                        match_id=match_id,
                        home_team=home_name,
                        away_team=away_name,
                        league=league,
                        kickoff=kickoff,
                        market=market,
                        odds=odds_val,
                        scraped_at=now,
                    ),
                )

        return snapshots

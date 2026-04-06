"""CLI command: download Pinnacle closing odds from football-data.co.uk.

Downloads historical match CSVs containing Pinnacle closing odds for
the configured leagues and seasons. Files are saved to the directory
specified by ``pinnacle_odds_dir`` in settings (default: ``data/odds/``).

Usage::

    sl download-odds
    sl download-odds --leagues "ENG-Premier League" "ESP-La Liga"
    sl download-odds --seasons 2122 2223 2324
    sl download-odds --output-dir data/odds
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import structlog
import typer

logger = structlog.get_logger(__name__)

download_odds_app = typer.Typer(no_args_is_help=True)

# Default leagues: top 5 European leagues.
_DEFAULT_LEAGUES: list[str] = [
    "ENG-Premier League",
    "ESP-La Liga",
    "GER-Bundesliga",
    "ITA-Serie A",
    "FRA-Ligue 1",
]

# Default seasons to download.
_DEFAULT_SEASONS: list[str] = ["2122", "2223", "2324"]


@download_odds_app.command("run")
def run(
    leagues: Annotated[
        list[str] | None,
        typer.Option(
            "--leagues",
            help=(
                "SportsLab league names to download. "
                "Defaults to top 5 European leagues."
            ),
        ),
    ] = None,
    seasons: Annotated[
        list[str] | None,
        typer.Option(
            "--seasons",
            help="Season codes (e.g. 2122 2223). Defaults to 2122 2223 2324.",
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            help="Directory to save CSVs. Defaults to settings.pinnacle_odds_dir.",
        ),
    ] = None,
) -> None:
    """Download Pinnacle closing odds CSVs from football-data.co.uk."""
    from ml_in_sports.processing.odds.pinnacle import (
        _LEAGUE_TO_CODE,
        download_season_csv,
    )
    from ml_in_sports.settings import get_settings

    settings = get_settings()
    target_dir = output_dir or settings.pinnacle_odds_dir
    target_leagues = leagues or _DEFAULT_LEAGUES
    target_seasons = seasons or _DEFAULT_SEASONS

    logger.info(
        "download_odds_start",
        leagues=target_leagues,
        seasons=target_seasons,
        output_dir=str(target_dir),
    )

    downloaded = 0
    failed = 0

    for league_name in target_leagues:
        league_code = _LEAGUE_TO_CODE.get(league_name)
        if league_code is None:
            logger.warning(
                "unknown_league_skipped",
                league=league_name,
                known=sorted(_LEAGUE_TO_CODE.keys()),
            )
            failed += 1
            continue

        for season in target_seasons:
            try:
                dest = download_season_csv(league_code, season, target_dir)
                downloaded += 1
                typer.echo(f"  OK  {league_name} {season} -> {dest}")
            except (RuntimeError, ValueError) as exc:
                failed += 1
                logger.warning(
                    "download_failed",
                    league=league_name,
                    season=season,
                    error=str(exc),
                )
                typer.echo(f"  FAIL  {league_name} {season}: {exc}")

    logger.info(
        "download_odds_complete",
        downloaded=downloaded,
        failed=failed,
    )
    typer.echo(f"\nDone: {downloaded} downloaded, {failed} failed.")

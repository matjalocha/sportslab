"""CLI command: scrape Sofascore match statistics for a league/season."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import structlog
import typer

logger = structlog.get_logger(__name__)

scrape_sofascore_app = typer.Typer(no_args_is_help=True)


def _scrape_sofascore(
    league: str,
    season: str,
    cache_dir: Path,
    headless: bool,
    rate_limit: float,
) -> None:
    """Run the Sofascore scraper for a single league/season."""
    from ml_in_sports.processing.scrapers.sofascore import (
        SOFASCORE_TOURNAMENTS,
        SofascoreScraper,
    )

    if league not in SOFASCORE_TOURNAMENTS:
        typer.echo(
            f"Unknown league: {league}\n"
            f"Available: {', '.join(sorted(SOFASCORE_TOURNAMENTS.keys()))}",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Scraping Sofascore: {league} {season}")
    typer.echo(f"Cache dir: {cache_dir}")
    typer.echo(f"Rate limit: {rate_limit}s between requests")

    scraper = SofascoreScraper(headless=headless, rate_limit=rate_limit)
    try:
        stats = scraper.scrape_league_season(
            league=league,
            season=season,
            cache_dir=cache_dir,
        )
    finally:
        scraper.close()

    typer.echo(f"\nDone: {len(stats)} matches scraped for {league} {season}")


@scrape_sofascore_app.callback(invoke_without_command=True)
def scrape_sofascore(
    ctx: typer.Context,
    league: Annotated[
        str,
        typer.Option(
            "--league",
            help="Canonical league name (e.g. 'ENG-Championship').",
        ),
    ] = "",
    season: Annotated[
        str,
        typer.Option(
            "--season",
            help="Season code (e.g. '24/25').",
        ),
    ] = "24/25",
    cache_dir: Annotated[
        Path,
        typer.Option(
            "--cache-dir",
            help="Directory for JSON cache files.",
        ),
    ] = Path("data/sofascore"),
    headless: Annotated[
        bool,
        typer.Option(
            "--headless/--no-headless",
            help="Run browser in headless mode.",
        ),
    ] = True,
    rate_limit: Annotated[
        float,
        typer.Option(
            "--rate-limit",
            help="Seconds between API requests.",
        ),
    ] = 2.0,
) -> None:
    """Scrape match statistics from Sofascore for a league/season."""
    if ctx.invoked_subcommand is not None:
        return
    if not league:
        typer.echo("Error: --league is required.", err=True)
        raise typer.Exit(code=1)
    _scrape_sofascore(league, season, cache_dir, headless, rate_limit)


@scrape_sofascore_app.command("run")
def run(
    league: Annotated[
        str,
        typer.Option(
            "--league",
            help="Canonical league name (e.g. 'ENG-Championship').",
        ),
    ],
    season: Annotated[
        str,
        typer.Option(
            "--season",
            help="Season code (e.g. '24/25').",
        ),
    ] = "24/25",
    cache_dir: Annotated[
        Path,
        typer.Option(
            "--cache-dir",
            help="Directory for JSON cache files.",
        ),
    ] = Path("data/sofascore"),
    headless: Annotated[
        bool,
        typer.Option(
            "--headless/--no-headless",
            help="Run browser in headless mode.",
        ),
    ] = True,
    rate_limit: Annotated[
        float,
        typer.Option(
            "--rate-limit",
            help="Seconds between API requests.",
        ),
    ] = 2.0,
) -> None:
    """Scrape match statistics from Sofascore for a league/season."""
    _scrape_sofascore(league, season, cache_dir, headless, rate_limit)

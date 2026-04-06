"""CLI command: download football-data.co.uk CSVs for registered leagues."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import structlog
import typer

from ml_in_sports.processing.leagues import get_league

logger = structlog.get_logger(__name__)

download_leagues_app = typer.Typer(no_args_is_help=True)

_DEFAULT_SEASONS: list[str] = ["2223", "2324", "2425"]


def _download_leagues(
    leagues: list[str] | None,
    seasons: list[str] | None,
    output_dir: Path,
) -> None:
    """Download requested league/season CSVs."""
    from ml_in_sports.processing.leagues import get_all_leagues
    from ml_in_sports.processing.odds.pinnacle import download_season_csv

    target_leagues = leagues or [
        league.canonical_name for league in get_all_leagues()
    ]
    target_seasons = seasons or _DEFAULT_SEASONS

    logger.info(
        "download_leagues_start",
        leagues=target_leagues,
        seasons=target_seasons,
        output_dir=str(output_dir),
    )

    downloaded = 0
    failed = 0

    for league_name in target_leagues:
        league = get_league(league_name)
        if league is None:
            failed += 1
            typer.echo(f"  FAIL  {league_name}: unknown league")
            logger.warning("unknown_league_skipped", league=league_name)
            continue

        for season in target_seasons:
            try:
                dest = download_season_csv(
                    league.football_data_code,
                    season,
                    output_dir,
                )
            except (RuntimeError, ValueError) as exc:
                failed += 1
                typer.echo(f"  FAIL  {league_name} {season}: {exc}")
                logger.warning(
                    "league_download_failed",
                    league=league_name,
                    season=season,
                    error=str(exc),
                )
                continue

            downloaded += 1
            typer.echo(f"  OK  {league_name} {season} -> {dest}")

    logger.info("download_leagues_complete", downloaded=downloaded, failed=failed)
    typer.echo(f"\nDone: {downloaded} downloaded, {failed} failed.")


@download_leagues_app.callback(invoke_without_command=True)
def download_leagues(
    ctx: typer.Context,
    leagues: Annotated[
        list[str] | None,
        typer.Option(
            "--leagues",
            help="SportsLab league names to download. Defaults to all registered leagues.",
        ),
    ] = None,
    seasons: Annotated[
        list[str] | None,
        typer.Option(
            "--seasons",
            help="Season codes to download, e.g. 2223 2324 2425.",
        ),
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Directory to save CSVs.",
        ),
    ] = Path("data/odds"),
) -> None:
    """Download football-data.co.uk CSVs by registered league name."""
    if ctx.invoked_subcommand is not None:
        return
    _download_leagues(leagues, seasons, output_dir)


@download_leagues_app.command("run")
def run(
    leagues: Annotated[
        list[str] | None,
        typer.Option(
            "--leagues",
            help="SportsLab league names to download. Defaults to all registered leagues.",
        ),
    ] = None,
    seasons: Annotated[
        list[str] | None,
        typer.Option(
            "--seasons",
            help="Season codes to download, e.g. 2223 2324 2425.",
        ),
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Directory to save CSVs.",
        ),
    ] = Path("data/odds"),
) -> None:
    """Download football-data.co.uk CSVs by registered league name."""
    _download_leagues(leagues, seasons, output_dir)

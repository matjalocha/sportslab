"""CLI command: ingest football-data.co.uk league CSVs into features parquet."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import structlog
import typer

from ml_in_sports.processing.league_ingestion import ingest_league

logger = structlog.get_logger(__name__)

ingest_app = typer.Typer(no_args_is_help=True)


def _run_ingest(
    league: str,
    seasons: list[str],
    odds_dir: Path,
    output_parquet: Path,
) -> None:
    """Run ingestion and print a compact status line."""
    try:
        added = ingest_league(
            league=league,
            seasons=seasons,
            odds_dir=odds_dir,
            output_parquet=output_parquet,
        )
    except ValueError as exc:
        typer.echo(f"FAIL: {exc}")
        raise typer.Exit(code=2) from exc
    logger.info(
        "ingest_complete",
        league=league,
        seasons=seasons,
        matches_added=added,
        output=str(output_parquet),
    )
    typer.echo(f"Done: {added} matches added to {output_parquet}")


@ingest_app.callback(invoke_without_command=True)
def ingest(
    ctx: typer.Context,
    league: Annotated[
        str | None,
        typer.Option("--league", help="SportsLab canonical league name."),
    ] = None,
    seasons: Annotated[
        list[str] | None,
        typer.Option("--seasons", help="Season codes, e.g. 2223 2324 2425."),
    ] = None,
    odds_dir: Annotated[
        Path,
        typer.Option("--odds-dir", help="Directory with/download target for CSV odds."),
    ] = Path("data/odds"),
    output_parquet: Annotated[
        Path,
        typer.Option("--output-parquet", help="Target features parquet."),
    ] = Path("data/features/all_features.parquet"),
) -> None:
    """Ingest football-data.co.uk league data into features parquet."""
    if ctx.invoked_subcommand is not None:
        return
    if league is None or seasons is None:
        typer.echo("Missing --league or --seasons. Use --help for details.")
        raise typer.Exit(code=2)
    _run_ingest(league, seasons, odds_dir, output_parquet)


@ingest_app.command("run")
def run(
    league: Annotated[str, typer.Option("--league", help="SportsLab canonical league name.")],
    seasons: Annotated[
        list[str],
        typer.Option("--seasons", help="Season codes, e.g. 2223 2324 2425."),
    ],
    odds_dir: Annotated[
        Path,
        typer.Option("--odds-dir", help="Directory with/download target for CSV odds."),
    ] = Path("data/odds"),
    output_parquet: Annotated[
        Path,
        typer.Option("--output-parquet", help="Target features parquet."),
    ] = Path("data/features/all_features.parquet"),
) -> None:
    """Ingest football-data.co.uk league data into features parquet."""
    _run_ingest(league, seasons, odds_dir, output_parquet)

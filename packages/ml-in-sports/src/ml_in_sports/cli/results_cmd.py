"""CLI command: process daily bet results."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Annotated

import structlog
import typer

from ml_in_sports.prediction.results import ResultsTracker

logger = structlog.get_logger(__name__)

results_app = typer.Typer(no_args_is_help=True)


@results_app.command("run")
def run(
    result_date: Annotated[
        str,
        typer.Option("--date", help="Result date in YYYY-MM-DD format."),
    ],
    predictions_dir: Annotated[
        Path,
        typer.Option("--predictions-dir", help="Directory with prediction JSON files."),
    ] = Path("reports/predictions"),
    results_dir: Annotated[
        Path,
        typer.Option("--results-dir", help="Directory with manual and processed result JSON files."),
    ] = Path("results"),
    initial_bankroll: Annotated[
        float,
        typer.Option("--initial-bankroll", help="Starting bankroll for running totals."),
    ] = 5000.0,
) -> None:
    """Process daily bet results and print a compact summary."""
    day = dt.date.fromisoformat(result_date)
    tracker = ResultsTracker(
        predictions_dir=predictions_dir,
        results_dir=results_dir,
        initial_bankroll=initial_bankroll,
    )
    results = tracker.process_day(day)
    totals = tracker.running_totals()

    pnl = sum(result.pnl for result in results)
    wins = sum(1 for result in results if result.hit)
    losses = len(results) - wins
    typer.echo(
        f"{day.isoformat()} | Bets: {len(results)} | W-L: {wins}-{losses} | "
        f"P&L: EUR {pnl:+.2f}"
    )
    typer.echo(
        f"Running bankroll: EUR {totals['current_bankroll']:.2f} | "
        f"ROI: {totals['roi']:+.2%} | Hit rate: {totals['hit_rate']:.1%}"
    )
    logger.info("results_cli_complete", day=day.isoformat(), processed=len(results))

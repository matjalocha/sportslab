"""CLI command: generate weekly performance report."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Annotated

import structlog
import typer

from ml_in_sports.prediction.report.weekly_html import render_weekly_html
from ml_in_sports.prediction.report.weekly_terminal import print_weekly_terminal
from ml_in_sports.prediction.results import ResultsTracker
from ml_in_sports.prediction.weekly import WeeklyReporter

logger = structlog.get_logger(__name__)

weekly_app = typer.Typer(no_args_is_help=True)


@weekly_app.command("run")
def run(
    week: Annotated[
        str,
        typer.Option("--week", help="Week start date in YYYY-MM-DD format."),
    ],
    results_dir: Annotated[
        Path,
        typer.Option("--results-dir", help="Directory with processed result JSON files."),
    ] = Path("results"),
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Directory for weekly HTML reports."),
    ] = Path("reports/weekly"),
    initial_bankroll: Annotated[
        float,
        typer.Option("--initial-bankroll", help="Starting bankroll for running totals."),
    ] = 5000.0,
) -> None:
    """Generate weekly performance report."""
    week_start = dt.date.fromisoformat(week)
    tracker = ResultsTracker(results_dir=results_dir, initial_bankroll=initial_bankroll)
    data = WeeklyReporter(tracker).generate(week_start)
    print_weekly_terminal(data)
    output_path = render_weekly_html(
        data,
        output_dir / f"weekly_{week_start.isoformat()}.html",
    )
    typer.echo(f"HTML report: {output_path}")
    logger.info("weekly_cli_complete", week_start=week_start.isoformat(), bets=data.total_bets)

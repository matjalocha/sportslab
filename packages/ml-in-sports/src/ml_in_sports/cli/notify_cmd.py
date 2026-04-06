"""CLI commands for Telegram notifications."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Annotated

import structlog
import typer

from ml_in_sports.notification import TelegramNotifier
from ml_in_sports.prediction.daily import BetRecommendation, DailyPredictor
from ml_in_sports.prediction.report.results_telegram import render_results_telegram
from ml_in_sports.prediction.report.telegram import render_telegram_bet_slip
from ml_in_sports.prediction.results import ResultsTracker

logger = structlog.get_logger(__name__)

notify_app = typer.Typer(no_args_is_help=True)


@notify_app.command("bet-slip")
def bet_slip(
    notification_date: Annotated[
        str | None,
        typer.Option("--date", help="Prediction date in YYYY-MM-DD format."),
    ] = None,
    predictions_dir: Annotated[
        Path,
        typer.Option("--predictions-dir", help="Directory with prediction JSON files."),
    ] = Path("reports/predictions"),
) -> None:
    """Send a Telegram bet slip for a given date."""
    day = dt.date.fromisoformat(notification_date) if notification_date else dt.date.today()
    predictions = _load_predictions(predictions_dir, day)
    message = render_telegram_bet_slip(predictions, report_date=day)
    _send(message)
    logger.info("notify_bet_slip_complete", day=day.isoformat(), bets=len(predictions))


@notify_app.command("results")
def results(
    notification_date: Annotated[
        str | None,
        typer.Option("--date", help="Result date in YYYY-MM-DD format."),
    ] = None,
    results_dir: Annotated[
        Path,
        typer.Option("--results-dir", help="Directory with processed result JSON files."),
    ] = Path("results"),
) -> None:
    """Send a Telegram daily results summary for a given date."""
    day = dt.date.fromisoformat(notification_date) if notification_date else dt.date.today()
    tracker = ResultsTracker(results_dir=results_dir)
    processed_results = tracker.load_processed_results(start_date=day, end_date=day)
    message = render_results_telegram(processed_results)
    _send(message)
    logger.info("notify_results_complete", day=day.isoformat(), results=len(processed_results))


def _load_predictions(predictions_dir: Path, day: dt.date) -> list[BetRecommendation]:
    candidates = [
        predictions_dir / f"predictions_{day.isoformat()}.json",
        predictions_dir / f"bet_recommendations_{day.isoformat()}.json",
    ]
    for path in candidates:
        if path.exists():
            return DailyPredictor.load_predictions(path)
    return []


def _send(message: str) -> None:
    notifier = TelegramNotifier()
    sent = notifier.send_message(message)
    if sent:
        typer.echo("Telegram notification sent.")
    else:
        typer.echo("Telegram notification failed.")

"""CLI command: generate daily bet recommendations.

Usage::

    sl predict run --date 2026-04-06 --bankroll 5000 --min-edge 0.02
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Annotated

import structlog
import typer

from ml_in_sports.prediction import DailyPredictor
from ml_in_sports.prediction.report import print_terminal_bet_slip, render_html_bet_slip

logger = structlog.get_logger(__name__)

predict_app = typer.Typer(no_args_is_help=True)


@predict_app.command("run")
def run(
    prediction_date: Annotated[
        str | None,
        typer.Option("--date", help="Prediction date in YYYY-MM-DD format."),
    ] = None,
    bankroll: Annotated[
        float,
        typer.Option("--bankroll", help="Bankroll used for Kelly stake sizing."),
    ] = 5000.0,
    min_edge: Annotated[
        float,
        typer.Option("--min-edge", help="Minimum edge required for recommendations."),
    ] = 0.02,
    kelly_fraction: Annotated[
        float,
        typer.Option("--kelly-fraction", help="Fractional Kelly multiplier."),
    ] = 0.25,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Directory for JSON recommendation output."),
    ] = Path("reports/predictions"),
    model_dir: Annotated[
        Path,
        typer.Option("--model-dir", help="Future persisted model directory."),
    ] = Path("models/latest"),
    features_path: Annotated[
        Path,
        typer.Option("--features-path", help="Features parquet with upcoming matches."),
    ] = Path("data/features/all_features.parquet"),
) -> None:
    """Generate daily bet recommendations and save them as JSON."""
    parsed_date = dt.date.fromisoformat(prediction_date) if prediction_date else None
    logger.info(
        "predict_cli_start",
        date=prediction_date,
        bankroll=bankroll,
        min_edge=min_edge,
        features_path=str(features_path),
    )

    predictor = DailyPredictor(
        model_dir=model_dir,
        bankroll=bankroll,
        kelly_fraction=kelly_fraction,
        min_edge=min_edge,
        features_path=features_path,
    )
    recommendations = predictor.predict(date=parsed_date)
    json_output_path = predictor.save_predictions(recommendations, output_dir)
    report_date = parsed_date or (
        recommendations[0].kickoff_dt.date() if recommendations else dt.datetime.now().date()
    )
    html_output_path = render_html_bet_slip(
        recommendations,
        output_dir / f"bet_slip_{report_date.isoformat()}.html",
        report_date=report_date,
    )
    print_terminal_bet_slip(recommendations)

    typer.echo(f"Saved JSON to {json_output_path}")
    typer.echo(f"Saved HTML to {html_output_path}")

    logger.info("predict_cli_complete", recommendations=len(recommendations))

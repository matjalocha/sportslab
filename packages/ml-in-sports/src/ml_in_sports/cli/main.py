"""Main CLI app with subcommands."""

import typer

from ml_in_sports.cli.backtest_cmd import backtest_app
from ml_in_sports.cli.download_odds_cmd import download_odds_app
from ml_in_sports.cli.features_cmd import features_app
from ml_in_sports.cli.kelly_cmd import kelly_app
from ml_in_sports.cli.leakage_cmd import leakage_app
from ml_in_sports.cli.notify_cmd import notify_app
from ml_in_sports.cli.pipeline_cmd import pipeline_app
from ml_in_sports.cli.predict_cmd import predict_app
from ml_in_sports.cli.refresh_cmd import refresh_app
from ml_in_sports.cli.results_cmd import results_app
from ml_in_sports.cli.weekly_cmd import weekly_app
from ml_in_sports.logging import configure_logging

app = typer.Typer(
    name="sl",
    help="SportsLab CLI — data pipeline, features, and predictions.",
    no_args_is_help=True,
)


@app.callback()
def main(
    log_json: bool = typer.Option(
        False,
        "--json",
        help="JSON log output.",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Log level (DEBUG, INFO, WARNING, ERROR).",
    ),
) -> None:
    """Configure logging for all subcommands."""
    configure_logging(json=log_json, level=log_level)


app.add_typer(backtest_app, name="backtest", help="Run walk-forward backtest.")
app.add_typer(download_odds_app, name="download-odds", help="Download Pinnacle odds CSVs.")
app.add_typer(pipeline_app, name="pipeline", help="Run data pipeline.")
app.add_typer(features_app, name="features", help="Materialize features to Parquet.")
app.add_typer(kelly_app, name="kelly", help="Compute Kelly stakes.")
app.add_typer(leakage_app, name="leakage-check", help="Run automated leakage detection.")
app.add_typer(notify_app, name="notify", help="Send Telegram notifications.")
app.add_typer(predict_app, name="predict", help="Generate daily bet recommendations.")
app.add_typer(refresh_app, name="refresh", help="Refresh current season data.")
app.add_typer(results_app, name="results", help="Process daily bet results.")
app.add_typer(weekly_app, name="weekly", help="Generate weekly performance report.")

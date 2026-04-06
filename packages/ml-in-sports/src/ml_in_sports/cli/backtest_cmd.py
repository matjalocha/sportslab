"""CLI command: run walk-forward backtest and generate report.

Usage::

    sl backtest run experiments/hybrid_v1.yaml
    sl backtest run experiments/hybrid_v1.yaml --synthetic
    sl backtest run experiments/hybrid_v1.yaml --data-path data/features/all_features.parquet
    sl backtest run experiments/hybrid_v1.yaml --output-dir reports/
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import structlog
import typer

logger = structlog.get_logger(__name__)

backtest_app = typer.Typer(no_args_is_help=True)


@backtest_app.command("run")
def run(
    config: Annotated[
        Path,
        typer.Argument(help="Path to experiment YAML config."),
    ],
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Output directory for HTML report."),
    ] = Path("reports"),
    synthetic: Annotated[
        bool,
        typer.Option("--synthetic", help="Use synthetic data (no real models)."),
    ] = False,
    data_path: Annotated[
        Path | None,
        typer.Option("--data-path", help="Override path to features parquet."),
    ] = None,
    seed: Annotated[
        int,
        typer.Option("--seed", help="Random seed for reproducibility."),
    ] = 42,
) -> None:
    """Run walk-forward backtest and generate report."""
    from ml_in_sports.backtesting.config import ExperimentConfig
    from ml_in_sports.backtesting.report.generator import build_report_data
    from ml_in_sports.backtesting.report.html import render_html_report
    from ml_in_sports.backtesting.report.terminal import print_terminal_report
    from ml_in_sports.backtesting.runner import WalkForwardRunner

    logger.info(
        "backtest_cli_start",
        config=str(config),
        synthetic=synthetic,
        data_path=str(data_path) if data_path else None,
    )

    experiment_config = ExperimentConfig.from_yaml(config)
    runner = WalkForwardRunner(experiment_config)

    if synthetic:
        result = runner.run_synthetic(seed=seed)
    else:
        result = runner.run(data_path=data_path, seed=seed)

    report_data = build_report_data(result)

    if "terminal" in experiment_config.report.format:
        print_terminal_report(report_data)

    if "html" in experiment_config.report.format:
        timestamp = result.generated_at.strftime("%Y-%m-%d")
        slug = experiment_config.name.lower().replace(" ", "_")
        filename = f"backtest_{timestamp}_{slug}.html"
        output_path = Path(output_dir) / filename
        render_html_report(report_data, output_path)
        logger.info("html_report_path", path=str(output_path))

    logger.info("backtest_cli_complete")

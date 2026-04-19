"""CLI command: run walk-forward backtest and generate report.

Usage::

    sl backtest run experiments/hybrid_v1.yaml
    sl backtest run experiments/hybrid_v1.yaml --synthetic
    sl backtest run experiments/hybrid_v1.yaml --data-path data/features/all_features.parquet
    sl backtest run experiments/hybrid_v1.yaml --output-dir reports/
    sl backtest run experiments/hybrid_v1.yaml --mlflow
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
    enable_mlflow: Annotated[
        bool,
        typer.Option("--mlflow/--no-mlflow", help="Log run to MLflow tracking server."),
    ] = False,
) -> None:
    """Run walk-forward backtest and generate report."""
    from ml_in_sports.backtesting.config import ExperimentConfig
    from ml_in_sports.backtesting.report.generator import build_report_data
    from ml_in_sports.backtesting.report.html import render_html_report
    from ml_in_sports.backtesting.report.terminal import print_terminal_report
    from ml_in_sports.backtesting.runner import WalkForwardRunner
    from ml_in_sports.mlflow_integration import (
        MLflowRunContext,
        build_experiment_name,
        build_run_name,
        get_tracking_uri,
        is_mlflow_available,
    )

    logger.info(
        "backtest_cli_start",
        config=str(config),
        synthetic=synthetic,
        data_path=str(data_path) if data_path else None,
        mlflow=enable_mlflow,
    )

    if enable_mlflow and not is_mlflow_available():
        logger.warning(
            "mlflow_requested_but_not_installed",
            hint="Install mlflow: uv add mlflow",
        )

    experiment_config = ExperimentConfig.from_yaml(config)
    runner = WalkForwardRunner(experiment_config)

    if synthetic:
        result = runner.run_synthetic(seed=seed)
    else:
        result = runner.run(data_path=data_path, seed=seed)

    report_data = build_report_data(result)

    html_output_path: Path | None = None

    if "terminal" in experiment_config.report.format:
        print_terminal_report(report_data)

    if "html" in experiment_config.report.format:
        timestamp = result.generated_at.strftime("%Y-%m-%d")
        slug = experiment_config.name.lower().replace(" ", "_")
        filename = f"backtest_{timestamp}_{slug}.html"
        html_output_path = Path(output_dir) / filename
        render_html_report(report_data, html_output_path)
        logger.info("html_report_path", path=str(html_output_path))

    if enable_mlflow:
        _log_to_mlflow(
            experiment_config=experiment_config,
            result=result,
            html_output_path=html_output_path,
        )

    logger.info("backtest_cli_complete")


def _log_to_mlflow(
    experiment_config: object,
    result: object,
    html_output_path: Path | None,
) -> None:
    """Log backtest params, metrics, and artifacts to MLflow.

    Derives the experiment name from the first market and first model in the
    config, using version 1. All standard SportsLab metrics are extracted from
    the aggregate results of the first (best-CLV) model.

    Args:
        experiment_config: Validated ExperimentConfig instance.
        result: BacktestResult from the walk-forward runner.
        html_output_path: Path to the generated HTML report, if any.
    """
    from ml_in_sports.backtesting.config import ExperimentConfig
    from ml_in_sports.backtesting.runner import BacktestResult
    from ml_in_sports.mlflow_integration import (
        MLflowRunContext,
        build_experiment_name,
        build_run_name,
        get_tracking_uri,
    )

    assert isinstance(experiment_config, ExperimentConfig)
    assert isinstance(result, BacktestResult)

    # Derive experiment/run names from first market + first model
    markets = experiment_config.data.markets
    models = experiment_config.models
    first_market = markets[0] if markets else "unknown"
    first_model_name = models[0].name.lower().replace(" ", "_") if models else "unknown"
    first_model_type = models[0].type if models else "unknown"
    run_date = result.generated_at.strftime("%Y-%m-%d")

    experiment_name = build_experiment_name(
        market=first_market,
        model=first_model_type,
        version=1,
    )
    run_name = build_run_name(model=first_model_type, date=run_date)

    # Build params from config
    first_model_params = dict(models[0].params) if models and models[0].params else {}
    params: dict[str, object] = {
        "n_estimators": first_model_params.get("n_estimators", ""),
        "learning_rate": first_model_params.get("learning_rate", ""),
        "features_count": first_model_params.get("features_count", ""),
        "leagues": ",".join(experiment_config.data.leagues),
        "markets": ",".join(experiment_config.data.markets),
        "seed": first_model_params.get("seed", ""),
        "train_seasons": experiment_config.evaluation.walk_forward.train_seasons,
        "test_seasons": experiment_config.evaluation.walk_forward.test_seasons,
        "kelly_fraction": experiment_config.kelly.fraction,
        "calibration_methods": ",".join(experiment_config.calibration.methods),
    }

    # Extract aggregate metrics from best model (first by CLV)
    aggregate = result.aggregate_metrics
    best_model_key: str | None = None
    best_clv = float("-inf")
    for model_key, model_metrics in aggregate.items():
        clv = model_metrics.get("clv_mean", float("-inf"))
        if clv > best_clv:
            best_clv = clv
            best_model_key = model_key

    if best_model_key is None:
        logger.warning("mlflow_no_aggregate_metrics_to_log")
        return

    agg = aggregate[best_model_key]
    metrics: dict[str, float] = {
        "log_loss": agg.get("log_loss", 0.0),
        "ece": agg.get("ece", 0.0),
        "clv_mean": agg.get("clv_mean", 0.0),
        "roi_pct": agg.get("roi", 0.0) * 100.0,
        "sharpe": agg.get("sharpe", 0.0),
        "max_drawdown": agg.get("max_drawdown", 0.0),
        "n_bets": float(
            sum(len(fr.actuals) for fr in result.fold_results if fr.model_name == best_model_key)
        ),
        "hit_rate": agg.get("hit_rate", 0.0),
    }

    # Determine artifact paths
    artifact_candidates: list[Path] = []
    if html_output_path:
        artifact_candidates.append(html_output_path)

    with MLflowRunContext(
        experiment_name=experiment_name,
        run_name=run_name,
        tracking_uri=get_tracking_uri(),
    ) as mlflow_run:
        mlflow_run.log_params(params)
        mlflow_run.log_metrics(metrics)
        for artifact_path in artifact_candidates:
            mlflow_run.log_artifact(artifact_path)

    logger.info(
        "mlflow_logging_complete",
        experiment=experiment_name,
        run_name=run_name,
        best_model=best_model_key,
    )

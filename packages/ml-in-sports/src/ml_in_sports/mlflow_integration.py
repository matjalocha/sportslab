"""MLflow integration utilities for the SportsLab backtest runner."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_MLFLOW_AVAILABLE = False
try:
    import mlflow

    _MLFLOW_AVAILABLE = True
except ImportError:
    pass


def is_mlflow_available() -> bool:
    """Return True if the mlflow package is installed.

    Returns:
        True when mlflow can be imported, False otherwise.
    """
    return _MLFLOW_AVAILABLE


def get_tracking_uri() -> str:
    """Return the MLflow tracking URI from the environment or a default.

    Reads ``MLFLOW_TRACKING_URI`` environment variable. Falls back to
    ``http://localhost:5000`` when the variable is absent.

    Returns:
        MLflow tracking server URI string.
    """
    return os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")


def build_experiment_name(market: str, model: str, version: int) -> str:
    """Build experiment name following SportsLab convention.

    Convention: ``football-<market>-<model>-v<N>``

    Args:
        market: Betting market identifier, e.g. ``"1x2"``, ``"ou25"``.
        model: Model type identifier, e.g. ``"lgbm"``, ``"ensemble"``.
        version: Integer version number.

    Returns:
        Experiment name string, e.g. ``"football-1x2-lgbm-v1"``.
    """
    return f"football-{market}-{model}-v{version}"


def build_run_name(model: str, date: str) -> str:
    """Build run name following SportsLab convention.

    Convention: ``<model>-<YYYY-MM-DD>``

    Args:
        model: Model type identifier, e.g. ``"lgbm"``.
        date: ISO date string, e.g. ``"2026-04-19"``.

    Returns:
        Run name string, e.g. ``"lgbm-2026-04-19"``.
    """
    return f"{model}-{date}"


class MLflowRunContext:
    """Context manager for an MLflow run. No-op when MLflow is unavailable.

    When MLflow is not installed, all methods silently do nothing so the
    backtest runner can call them unconditionally without branching.

    Example::

        with MLflowRunContext(
            experiment_name="football-1x2-lgbm-v1",
            run_name="lgbm-2026-04-19",
            tracking_uri="http://localhost:5000",
        ) as run:
            run.log_params({"n_estimators": 100})
            run.log_metrics({"log_loss": 0.55})
            run.log_artifact(Path("reports/backtest.html"))

    Attributes:
        _experiment_name: MLflow experiment name.
        _run_name: MLflow run name.
        _tracking_uri: MLflow server URI.
        _active: True when mlflow is installed and tracking is enabled.
    """

    def __init__(
        self,
        *,
        experiment_name: str,
        run_name: str,
        tracking_uri: str,
    ) -> None:
        self._experiment_name = experiment_name
        self._run_name = run_name
        self._tracking_uri = tracking_uri
        self._active = _MLFLOW_AVAILABLE

    def __enter__(self) -> "MLflowRunContext":
        if not self._active:
            return self
        mlflow.set_tracking_uri(self._tracking_uri)
        mlflow.set_experiment(self._experiment_name)
        mlflow.start_run(run_name=self._run_name)
        logger.info(
            "mlflow_run_started",
            experiment=self._experiment_name,
            run_name=self._run_name,
            tracking_uri=self._tracking_uri,
        )
        return self

    def __exit__(self, *_: Any) -> None:
        if not self._active:
            return
        mlflow.end_run()

    def log_params(self, params: dict[str, Any]) -> None:
        """Log hyperparameters to the active MLflow run.

        Args:
            params: Mapping of parameter names to values.
        """
        if not self._active:
            return
        mlflow.log_params(params)

    def log_metrics(self, metrics: dict[str, float]) -> None:
        """Log evaluation metrics to the active MLflow run.

        Args:
            metrics: Mapping of metric names to float values.
        """
        if not self._active:
            return
        mlflow.log_metrics(metrics)

    def log_artifact(self, path: Path) -> None:
        """Log a file artifact to the active MLflow run.

        Skips silently when the path does not exist.

        Args:
            path: Path to the file to upload as an artifact.
        """
        if not self._active or not path.exists():
            return
        mlflow.log_artifact(str(path))
        logger.info("mlflow_artifact_logged", path=str(path))

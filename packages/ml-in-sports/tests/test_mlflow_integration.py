"""Tests for MLflow integration module."""
import pytest
from unittest.mock import patch, MagicMock
from ml_in_sports.mlflow_integration import (
    build_experiment_name,
    build_run_name,
    get_tracking_uri,
    MLflowRunContext,
)


def test_build_experiment_name_follows_convention() -> None:
    result = build_experiment_name(market="1x2", model="lgbm", version=1)
    assert result == "football-1x2-lgbm-v1"


def test_build_experiment_name_ou25() -> None:
    result = build_experiment_name(market="ou25", model="ensemble", version=3)
    assert result == "football-ou25-ensemble-v3"


def test_build_run_name() -> None:
    result = build_run_name(model="lgbm", date="2026-04-19")
    assert result == "lgbm-2026-04-19"


def test_get_tracking_uri_default() -> None:
    import os
    os.environ.pop("MLFLOW_TRACKING_URI", None)
    assert get_tracking_uri() == "http://localhost:5000"


def test_get_tracking_uri_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://pi:5000")
    assert get_tracking_uri() == "http://pi:5000"


def test_mlflow_run_context_noop_when_unavailable() -> None:
    """MLflowRunContext must be a no-op when mlflow is not installed."""
    with patch("ml_in_sports.mlflow_integration._MLFLOW_AVAILABLE", False):
        ctx = MLflowRunContext(
            experiment_name="football-1x2-lgbm-v1",
            run_name="lgbm-2026-04-19",
            tracking_uri="http://localhost:5000",
        )
        # Should not raise
        with ctx:
            ctx.log_params({"n_estimators": 100})
            ctx.log_metrics({"log_loss": 0.55})

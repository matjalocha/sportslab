"""Backtesting framework for SportsLab experiments.

Provides YAML-driven experiment configuration, evaluation metrics,
walk-forward runner, data loading, and report generation.
"""

from ml_in_sports.backtesting.config import ExperimentConfig
from ml_in_sports.backtesting.data import BacktestDataLoader
from ml_in_sports.backtesting.metrics import (
    compute_brier_score,
    compute_clv,
    compute_clv_mean,
    compute_ece,
    compute_hit_rate,
    compute_log_loss,
    compute_max_drawdown,
    compute_max_losing_streak,
    compute_roi,
    compute_sharpe,
    compute_yield,
)
from ml_in_sports.backtesting.models import BaseModel, DummyModel, ModelRegistry
from ml_in_sports.backtesting.runner import (
    BacktestResult,
    FoldResult,
    WalkForwardRunner,
)

__all__ = [
    "BacktestDataLoader",
    "BacktestResult",
    "BaseModel",
    "DummyModel",
    "ExperimentConfig",
    "FoldResult",
    "ModelRegistry",
    "WalkForwardRunner",
    "compute_brier_score",
    "compute_clv",
    "compute_clv_mean",
    "compute_ece",
    "compute_hit_rate",
    "compute_log_loss",
    "compute_max_drawdown",
    "compute_max_losing_streak",
    "compute_roi",
    "compute_sharpe",
    "compute_yield",
]

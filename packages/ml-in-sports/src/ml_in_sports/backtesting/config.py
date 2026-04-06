"""Experiment configuration for backtest runs.

Loaded from YAML files via ``ExperimentConfig.from_yaml(path)``.
Validates all fields with Pydantic so config errors surface early.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class ModelConfig(BaseModel):
    """Configuration for a single model in the experiment.

    Attributes:
        name: Human-readable model name (used in report legends).
        type: Model backend type.
        params: Model-specific hyperparameters.
        base_models: Names of base models (stacking only).
        meta_learner: Meta-learner type (stacking only).
    """

    name: str
    type: Literal["lightgbm", "xgboost", "tabpfn", "stacking", "logistic_regression"]
    params: dict[str, object] = Field(default_factory=dict)
    base_models: list[str] | None = None
    meta_learner: str | None = None

    @model_validator(mode="after")
    def _stacking_requires_base_models(self) -> ModelConfig:
        if self.type == "stacking":
            if not self.base_models:
                msg = "Stacking model requires 'base_models' list"
                raise ValueError(msg)
            if not self.meta_learner:
                msg = "Stacking model requires 'meta_learner'"
                raise ValueError(msg)
        return self


class CalibrationConfig(BaseModel):
    """Calibration method selection settings.

    Attributes:
        methods: Calibration methods to evaluate.
        selection: How to pick the best method.
    """

    methods: list[Literal["temperature", "platt", "isotonic"]] = Field(
        default=["temperature", "platt", "isotonic"],
    )
    selection: Literal["walk_forward"] = "walk_forward"


class KellyConfig(BaseModel):
    """Portfolio Kelly staking parameters.

    Attributes:
        fraction: Global Kelly multiplier (quarter-Kelly = 0.25).
        max_exposure_per_match: Max stake on a single match.
        max_exposure_per_round: Max total stake in a single round.
        shrinkage: Whether to apply shrinkage toward market.
    """

    fraction: float = 0.25
    max_exposure_per_match: float = 0.03
    max_exposure_per_round: float = 0.15
    shrinkage: bool = True

    @field_validator("fraction")
    @classmethod
    def _fraction_in_range(cls, v: float) -> float:
        if not 0 < v <= 1:
            msg = f"Kelly fraction must be in (0, 1], got {v}"
            raise ValueError(msg)
        return v


class WalkForwardConfig(BaseModel):
    """Walk-forward cross-validation settings.

    Attributes:
        train_seasons: Number of seasons to train on.
        test_seasons: Number of seasons to test on.
    """

    train_seasons: int = 3
    test_seasons: int = 1


class EvaluationConfig(BaseModel):
    """Evaluation settings for the backtest.

    Attributes:
        walk_forward: Walk-forward CV parameters.
        metrics: List of metric names to compute.
        pinnacle_source: Source for closing odds.
    """

    walk_forward: WalkForwardConfig = Field(default_factory=WalkForwardConfig)
    metrics: list[str] = Field(
        default=[
            "log_loss",
            "ece",
            "brier_score",
            "clv_mean",
            "roi",
            "sharpe",
            "max_drawdown",
            "max_losing_streak",
        ],
    )
    pinnacle_source: Literal["football-data", "odds-api"] = "football-data"


class ReportConfig(BaseModel):
    """Report output settings.

    Attributes:
        format: Output formats to generate.
        include: Report sections to include.
    """

    format: list[Literal["html", "terminal"]] = Field(default=["html", "terminal"])
    include: list[str] = Field(
        default=[
            "calibration_curves",
            "ece_per_league",
            "clv_timeseries",
            "roi_cumulative",
            "feature_importance_top20",
            "model_comparison_table",
            "kelly_stake_distribution",
        ],
    )


class DataConfig(BaseModel):
    """Data scope for the experiment.

    Attributes:
        leagues: Leagues to include in backtesting.
        seasons: Season codes (4-char format, e.g. "2324").
        markets: Betting markets to evaluate.
    """

    leagues: list[str] = Field(
        default=[
            "ENG-Premier League",
            "ESP-La Liga",
            "GER-Bundesliga",
            "ITA-Serie A",
            "FRA-Ligue 1",
        ],
    )
    seasons: list[str] = Field(default=["2122", "2223", "2324", "2425"])
    markets: list[Literal["1x2", "over_under_25", "btts"]] = Field(
        default=["1x2", "over_under_25", "btts"],
    )

    @field_validator("seasons")
    @classmethod
    def _validate_season_format(cls, v: list[str]) -> list[str]:
        for s in v:
            if len(s) != 4 or not s.isdigit():
                msg = f"Season code must be 4 digits (e.g. '2324'), got '{s}'"
                raise ValueError(msg)
        return v


class ExperimentConfig(BaseModel):
    """Top-level experiment configuration.

    Load from YAML::

        config = ExperimentConfig.from_yaml(Path("experiments/hybrid_v1.yaml"))

    Attributes:
        name: Experiment name (shown in report header).
        description: Free-text description.
        data: Data scope configuration.
        models: List of models to train and evaluate.
        calibration: Calibration settings.
        kelly: Kelly staking settings.
        evaluation: Evaluation and metrics settings.
        report: Report output settings.
    """

    name: str = "Unnamed Experiment"
    description: str = ""
    data: DataConfig = Field(default_factory=DataConfig)
    models: list[ModelConfig] = Field(default_factory=list)
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)
    kelly: KellyConfig = Field(default_factory=KellyConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> ExperimentConfig:
        """Load experiment config from a YAML file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            Validated ExperimentConfig instance.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            ValidationError: If the YAML content is invalid.
        """
        with open(path) as f:
            data = yaml.safe_load(f)
        if data is None:
            data = {}
        return cls(**data)

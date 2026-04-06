"""Walk-forward backtest runner.

Orchestrates the full backtest pipeline: fold splitting, model training,
calibration, prediction, metric computation, and result aggregation.

Supports two modes:
  - ``run_synthetic()``: Pipeline testing with fake data and DummyModels.
  - ``run()``: Real backtesting with parquet data and registry models
    (LightGBM, XGBoost, stacking, etc.).
"""

from __future__ import annotations

import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.backtesting.config import CalibrationConfig, ExperimentConfig
from ml_in_sports.backtesting.models import DummyModel
from ml_in_sports.backtesting.simulation import compute_fold_metrics
from ml_in_sports.models.calibration.selector import CalibrationSelector

logger = structlog.get_logger(__name__)

_MIN_CALIBRATION_SAMPLES = 50


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FoldResult:
    """Result of a single walk-forward fold for one model.

    Attributes:
        fold_idx: Zero-based fold index.
        train_seasons: Season codes used for training.
        test_seasons: Season codes used for testing.
        model_name: Model identifier.
        predictions: Predicted probabilities, shape (n_test, n_classes).
        actuals: True label indices, shape (n_test,).
        odds: Closing decimal odds, shape (n_test, n_classes) or None.
        metrics: Computed metric values keyed by metric name.
        leagues: League name per test sample, shape (n_test,).
        calibration_method: Name of calibration method applied, or None
            if calibration was skipped.
    """

    fold_idx: int
    train_seasons: list[str]
    test_seasons: list[str]
    model_name: str
    predictions: np.ndarray
    actuals: np.ndarray
    odds: np.ndarray | None
    metrics: dict[str, float]
    leagues: np.ndarray | None = None
    calibration_method: str | None = None


@dataclass
class BacktestResult:
    """Aggregated result of a full walk-forward backtest.

    Attributes:
        config: Experiment configuration used.
        fold_results: Per-fold, per-model results.
        aggregate_metrics: Aggregated metrics keyed by model name.
        generated_at: Timestamp of report generation.
        duration_seconds: Wall-clock time for the backtest run.
        git_hash: Short git commit hash, if available.
    """

    config: ExperimentConfig
    fold_results: list[FoldResult]
    aggregate_metrics: dict[str, dict[str, float]]
    generated_at: datetime
    duration_seconds: float
    git_hash: str | None


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------


def _generate_synthetic_data(
    config: ExperimentConfig,
    seed: int = 42,
) -> dict[str, dict[str, np.ndarray]]:
    """Generate synthetic match data for pipeline testing.

    Creates fake features, labels, odds, and league assignments grouped
    by season. Each season has 200 matches with 20 features.

    Args:
        config: Experiment config (uses leagues and seasons).
        seed: Random seed for reproducibility.

    Returns:
        Dict keyed by season code. Each value is a dict with keys:
        ``features``, ``labels``, ``odds``, ``leagues``.
    """
    rng = np.random.default_rng(seed)
    matches_per_season = 200
    n_features = 20
    n_classes = 3
    leagues = config.data.leagues

    data: dict[str, dict[str, np.ndarray]] = {}

    for season in config.data.seasons:
        features = rng.standard_normal((matches_per_season, n_features))
        labels = rng.integers(0, n_classes, size=matches_per_season)
        odds = rng.uniform(1.5, 5.0, (matches_per_season, n_classes))
        league_indices = rng.integers(0, len(leagues), size=matches_per_season)
        league_names = np.array([leagues[i] for i in league_indices])

        data[season] = {
            "features": features,
            "labels": labels,
            "odds": odds,
            "leagues": league_names,
        }

    return data


# ---------------------------------------------------------------------------
# Git hash helper
# ---------------------------------------------------------------------------


def _get_git_hash() -> str | None:
    """Return the short git hash, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None


# ---------------------------------------------------------------------------
# Walk-forward runner
# ---------------------------------------------------------------------------


class WalkForwardRunner:
    """Orchestrates walk-forward backtesting.

    Splits seasons into training and test folds, trains models on each
    fold, computes metrics, and aggregates results.

    The runner is stateless between runs -- calling ``run`` or
    ``run_synthetic`` multiple times produces independent results.
    """

    def __init__(self, config: ExperimentConfig) -> None:
        self._config = config

    def _calibrate_predictions(
        self,
        raw_predictions: np.ndarray,
        cal_labels: np.ndarray,
        cal_probs: np.ndarray,
        fold_idx: int,
        model_name: str,
    ) -> tuple[np.ndarray, str | None]:
        """Calibrate test predictions using the best method from CalibrationSelector.

        Splits the training data into a calibration set, selects the best
        calibration method via walk-forward CV on that set, and applies it
        to the raw test predictions.

        Args:
            raw_predictions: Raw model probabilities on test set,
                shape (n_test, n_classes).
            cal_labels: Ground truth labels for calibration set, shape (n_cal,).
            cal_probs: Model probabilities on calibration set,
                shape (n_cal, n_classes).
            fold_idx: Fold index for logging context.
            model_name: Model name for logging context.

        Returns:
            Tuple of (calibrated_predictions, calibration_method_name).
            If calibration is skipped or fails, returns (raw_predictions, None).
        """
        calibration_config: CalibrationConfig = self._config.calibration

        # Skip if no methods configured
        if not calibration_config.methods:
            logger.info(
                "calibration_skipped_no_methods",
                fold=fold_idx,
                model=model_name,
            )
            return raw_predictions, None

        # Skip if calibration set is too small
        if len(cal_labels) < _MIN_CALIBRATION_SAMPLES:
            logger.warning(
                "calibration_skipped_insufficient_samples",
                fold=fold_idx,
                model=model_name,
                n_cal_samples=len(cal_labels),
                min_required=_MIN_CALIBRATION_SAMPLES,
            )
            return raw_predictions, None

        try:
            selector = CalibrationSelector(methods=list(calibration_config.methods))
            method_name, calibrator = selector.select(cal_labels, cal_probs)
            calibrated = calibrator.transform(raw_predictions)

            logger.info(
                "calibration_applied",
                fold=fold_idx,
                model=model_name,
                method=method_name,
            )
            return calibrated, method_name

        except Exception:
            logger.warning(
                "calibration_failed_using_raw_probs",
                fold=fold_idx,
                model=model_name,
                exc_info=True,
            )
            return raw_predictions, None

    def run_synthetic(self, seed: int = 42) -> BacktestResult:
        """Run backtest on synthetic data (no database required).

        Generates fake match data, trains DummyModels, and computes
        all requested metrics. Ideal for pipeline testing.

        Args:
            seed: Random seed for reproducible synthetic data.

        Returns:
            BacktestResult with synthetic data metrics.
        """
        start_time = time.monotonic()
        logger.info(
            "backtest_synthetic_start",
            experiment=self._config.name,
            seasons=self._config.data.seasons,
        )

        data = _generate_synthetic_data(self._config, seed=seed)
        fold_results = self._run_walk_forward(data, seed=seed)
        aggregate = self._aggregate_results(fold_results)
        duration = time.monotonic() - start_time

        result = BacktestResult(
            config=self._config,
            fold_results=fold_results,
            aggregate_metrics=aggregate,
            generated_at=datetime.now(tz=UTC),
            duration_seconds=round(duration, 2),
            git_hash=_get_git_hash(),
        )

        logger.info(
            "backtest_synthetic_complete",
            duration_seconds=result.duration_seconds,
            n_folds=len(fold_results),
            models=list(aggregate.keys()),
        )

        return result

    def run(
        self,
        data_path: Path | None = None,
        seed: int = 42,
    ) -> BacktestResult:
        """Run backtest on real data from a features parquet file.

        Loads features from parquet, creates walk-forward folds by
        season, trains real models from the experiment config, and
        computes all requested metrics.

        If the parquet file does not exist, falls back to synthetic
        data with a warning.

        Args:
            data_path: Override path to features parquet. If None, uses
                the default ``data/features/all_features.parquet``.
            seed: Random seed for model training reproducibility.

        Returns:
            BacktestResult with real data metrics.
        """
        from ml_in_sports.backtesting.data import BacktestDataLoader
        from ml_in_sports.models.ensemble.registry import create_model

        start_time = time.monotonic()
        logger.info(
            "backtest_real_start",
            experiment=self._config.name,
            leagues=self._config.data.leagues,
            seasons=self._config.data.seasons,
        )

        # Resolve parquet path
        parquet_path = data_path or Path("data/features/all_features.parquet")
        if not parquet_path.exists():
            logger.warning(
                "parquet_not_found_falling_back_to_synthetic",
                path=str(parquet_path),
            )
            return self.run_synthetic(seed=seed)

        # Load and prepare data
        loader = BacktestDataLoader(parquet_path=parquet_path)
        df = loader.load(
            leagues=self._config.data.leagues,
            seasons=self._config.data.seasons,
        )

        if len(df) == 0:
            logger.warning("no_data_after_filtering")
            return self.run_synthetic(seed=seed)

        # Generate walk-forward folds
        seasons = sorted(df["season"].unique().tolist())
        train_size = self._config.evaluation.walk_forward.train_seasons
        test_size = self._config.evaluation.walk_forward.test_seasons
        requested_metrics = self._config.evaluation.metrics
        fold_results: list[FoldResult] = []

        n_folds = len(seasons) - train_size
        if n_folds <= 0:
            logger.warning(
                "insufficient_seasons_for_walk_forward",
                n_seasons=len(seasons),
                train_size=train_size,
            )
            duration = time.monotonic() - start_time
            return BacktestResult(
                config=self._config,
                fold_results=[],
                aggregate_metrics={},
                generated_at=datetime.now(tz=UTC),
                duration_seconds=round(duration, 2),
                git_hash=_get_git_hash(),
            )

        for fold_idx in range(n_folds):
            fold_train_seasons = seasons[fold_idx : fold_idx + train_size]
            fold_test_seasons = seasons[fold_idx + train_size : fold_idx + train_size + test_size]
            if not fold_test_seasons:
                continue

            x_train, y_train, x_test, y_test, test_odds = loader.get_fold_data(
                df, fold_train_seasons, fold_test_seasons
            )

            # Split train into train_proper + calibration set (last 20%)
            cal_split = int(len(y_train) * 0.8)
            x_train_proper = x_train.iloc[:cal_split]
            y_train_proper = y_train[:cal_split]
            x_cal = x_train.iloc[cal_split:]
            y_cal = y_train[cal_split:]

            # Extract test league names for per-league reporting
            test_mask = df["season"].isin(fold_test_seasons)
            test_leagues = np.asarray(df.loc[test_mask, "league"].values)

            # Create and train models from config
            model_configs = self._config.models
            if not model_configs:
                logger.warning("no_models_configured_using_dummy")
                model_configs = []

            for model_idx, model_cfg in enumerate(model_configs):
                model_seed = seed + fold_idx * 100 + model_idx
                logger.info(
                    "training_model",
                    fold=fold_idx,
                    model=model_cfg.name,
                    model_type=model_cfg.type,
                    train_seasons=fold_train_seasons,
                    test_seasons=fold_test_seasons,
                    train_rows=len(x_train_proper),
                )

                if model_cfg.type == "stacking":
                    raw_predictions = self._train_stacking_model(
                        model_cfg, x_train_proper, y_train_proper, x_test, seed=model_seed
                    )
                    # Get calibration probs using stacking model on cal set
                    cal_probs = self._train_stacking_model(
                        model_cfg, x_train_proper, y_train_proper, x_cal, seed=model_seed
                    )
                else:
                    # Standard single model
                    params = dict(model_cfg.params) if model_cfg.params else {}
                    if "seed" not in params and "random_state" not in params:
                        params["seed"] = model_seed
                    model = create_model(model_cfg.type, **params)
                    model.fit(x_train_proper, y_train_proper)
                    raw_predictions = model.predict_proba(x_test)
                    cal_probs = model.predict_proba(x_cal)

                # Calibrate predictions
                predictions, cal_method = self._calibrate_predictions(
                    raw_predictions, y_cal, cal_probs, fold_idx, model_cfg.name
                )

                # Compute fold metrics
                metrics = compute_fold_metrics(predictions, y_test, test_odds, requested_metrics)

                fold_results.append(
                    FoldResult(
                        fold_idx=fold_idx,
                        train_seasons=fold_train_seasons,
                        test_seasons=fold_test_seasons,
                        model_name=model_cfg.name,
                        predictions=predictions,
                        actuals=y_test,
                        odds=test_odds,
                        metrics=metrics,
                        leagues=test_leagues,
                        calibration_method=cal_method,
                    )
                )
                logger.info(
                    "fold_model_complete",
                    fold=fold_idx,
                    model=model_cfg.name,
                    calibration_method=cal_method,
                    test_rows=len(y_test),
                    metrics={k: round(v, 4) for k, v in metrics.items()},
                )

        aggregate = self._aggregate_results(fold_results)
        duration = time.monotonic() - start_time

        result = BacktestResult(
            config=self._config,
            fold_results=fold_results,
            aggregate_metrics=aggregate,
            generated_at=datetime.now(tz=UTC),
            duration_seconds=round(duration, 2),
            git_hash=_get_git_hash(),
        )

        logger.info(
            "backtest_real_complete",
            duration_seconds=result.duration_seconds,
            n_folds=len({fr.fold_idx for fr in fold_results}),
            models=list(aggregate.keys()),
        )

        return result

    def _train_stacking_model(
        self,
        model_cfg: object,
        x_train: pd.DataFrame,
        y_train: np.ndarray,
        x_test: pd.DataFrame,
        seed: int = 42,
    ) -> np.ndarray:
        """Train a stacking ensemble and return test predictions.

        Resolves base model names from the config, creates fresh
        instances, builds the stacking ensemble, and returns
        ``predict_proba`` output.

        Args:
            model_cfg: Model configuration with base_models and
                meta_learner attributes.
            x_train: Training features DataFrame.
            y_train: Training labels array.
            x_test: Test features DataFrame.
            seed: Random seed for base model construction.

        Returns:
            Predicted probabilities, shape (n_test, n_classes).
        """
        from ml_in_sports.models.ensemble.registry import create_model
        from ml_in_sports.models.ensemble.stacking import StackingEnsemble

        # Resolve base models from config names
        base_model_names: list[str] = getattr(model_cfg, "base_models", []) or []
        meta_learner_type: str = (
            getattr(model_cfg, "meta_learner", "logistic_regression") or "logistic_regression"
        )

        # Find base model configs by name
        name_to_cfg = {m.name: m for m in self._config.models}
        base_models = []
        for bm_name in base_model_names:
            if bm_name in name_to_cfg:
                bm_cfg = name_to_cfg[bm_name]
                params = dict(bm_cfg.params) if bm_cfg.params else {}
                if "seed" not in params and "random_state" not in params:
                    params["seed"] = seed
                base_models.append(create_model(bm_cfg.type, **params))
            else:
                logger.warning(
                    "base_model_not_found_in_config",
                    base_model_name=bm_name,
                )

        if not base_models:
            logger.warning("no_base_models_resolved_for_stacking")
            # Fallback: return uniform probabilities
            n_classes = len(np.unique(y_train))
            return np.full((len(x_test), n_classes), 1.0 / n_classes)

        ensemble = StackingEnsemble(
            base_models=base_models,
            meta_learner_type=meta_learner_type,
        )
        ensemble.fit(x_train, y_train)
        result: np.ndarray = ensemble.predict_proba(x_test)
        return result

    def _run_walk_forward(
        self,
        season_data: dict[str, dict[str, np.ndarray]],
        seed: int = 42,
    ) -> list[FoldResult]:
        """Execute walk-forward folds across seasons."""
        seasons = sorted(season_data.keys())
        train_size = self._config.evaluation.walk_forward.train_seasons
        test_size = self._config.evaluation.walk_forward.test_seasons
        requested_metrics = self._config.evaluation.metrics
        fold_results: list[FoldResult] = []

        n_folds = len(seasons) - train_size
        if n_folds <= 0:
            logger.warning(
                "insufficient_seasons_for_walk_forward",
                n_seasons=len(seasons),
                train_size=train_size,
            )
            return fold_results

        model_configs = self._config.models
        if not model_configs:
            model_configs = [type("_MC", (), {"name": "DummyModel", "type": "dummy", "params": {}})]  # type: ignore[list-item]

        for fold_idx in range(n_folds):
            train_seasons = seasons[fold_idx : fold_idx + train_size]
            test_seasons = seasons[fold_idx + train_size : fold_idx + train_size + test_size]
            if not test_seasons:
                continue

            train_f, train_l = _concat_seasons(season_data, train_seasons)
            test_f, test_l, test_odds, test_leagues = _concat_seasons_with_odds(
                season_data, test_seasons
            )

            # Split train into train_proper + calibration set (last 20%)
            cal_split = int(len(train_l) * 0.8)
            train_proper_f = train_f[:cal_split]
            train_proper_l = train_l[:cal_split]
            cal_f = train_f[cal_split:]
            cal_l = train_l[cal_split:]

            for model_idx, model_cfg in enumerate(model_configs):
                model = DummyModel(
                    model_name=model_cfg.name, seed=seed + fold_idx * 100 + model_idx
                )
                model.fit(train_proper_f, train_proper_l)
                raw_predictions = model.predict_proba(test_f)

                # Calibrate predictions
                cal_probs = model.predict_proba(cal_f)
                predictions, cal_method = self._calibrate_predictions(
                    raw_predictions, cal_l, cal_probs, fold_idx, model_cfg.name
                )

                metrics = compute_fold_metrics(predictions, test_l, test_odds, requested_metrics)

                fold_results.append(
                    FoldResult(
                        fold_idx=fold_idx,
                        train_seasons=train_seasons,
                        test_seasons=test_seasons,
                        model_name=model_cfg.name,
                        predictions=predictions,
                        actuals=test_l,
                        odds=test_odds,
                        metrics=metrics,
                        leagues=test_leagues,
                        calibration_method=cal_method,
                    )
                )
                logger.debug(
                    "fold_complete",
                    fold=fold_idx,
                    model=model_cfg.name,
                    train=train_seasons,
                    test=test_seasons,
                    calibration_method=cal_method,
                    metrics=metrics,
                )

        return fold_results

    @staticmethod
    def _aggregate_results(
        fold_results: list[FoldResult],
    ) -> dict[str, dict[str, float]]:
        """Aggregate fold metrics per model (mean across folds)."""
        model_metrics: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list),
        )
        for fold in fold_results:
            for metric_name, value in fold.metrics.items():
                if not np.isnan(value):
                    model_metrics[fold.model_name][metric_name].append(value)

        return {
            model_name: {metric: float(np.mean(values)) for metric, values in metrics.items()}
            for model_name, metrics in model_metrics.items()
        }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _concat_seasons(
    season_data: dict[str, dict[str, np.ndarray]],
    seasons: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    """Concatenate features and labels across seasons."""
    features_list = [season_data[s]["features"] for s in seasons]
    labels_list = [season_data[s]["labels"] for s in seasons]
    return np.concatenate(features_list), np.concatenate(labels_list)


def _concat_seasons_with_odds(
    season_data: dict[str, dict[str, np.ndarray]],
    seasons: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    """Concatenate features, labels, odds, and leagues for test seasons."""
    features_list = [season_data[s]["features"] for s in seasons]
    labels_list = [season_data[s]["labels"] for s in seasons]
    odds_list = [season_data[s]["odds"] for s in seasons if "odds" in season_data[s]]
    leagues_list = [season_data[s]["leagues"] for s in seasons if "leagues" in season_data[s]]

    features = np.concatenate(features_list)
    labels = np.concatenate(labels_list)
    odds = np.concatenate(odds_list) if odds_list else None
    leagues = np.concatenate(leagues_list) if leagues_list else None

    return features, labels, odds, leagues

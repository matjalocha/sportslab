"""Daily bet recommendation pipeline (orchestrator)."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.models.kelly.portfolio import PortfolioConstraints, PortfolioKelly
from ml_in_sports.prediction._helpers import (
    collect_candidates,
    mock_candidate,
    prepare_features,
    select_feature_columns,
    select_recent_training_matches,
    select_upcoming_matches,
)
from ml_in_sports.prediction.models import (
    BetRecommendation,
    ProbabilityModel,
    _BetCandidate,
)
from ml_in_sports.prediction.trainer import (
    calibrate_probabilities,
    predict_probabilities,
    train_lightgbm,
)

# Backward-compatible re-exports
__all__ = ["BetRecommendation", "DailyPredictor", "ProbabilityModel"]

logger = structlog.get_logger(__name__)


class DailyPredictor:
    """Generate daily bet recommendations from materialized features."""

    def __init__(
        self,
        model_type: str | Path = "lightgbm",
        bankroll: float = 5000.0,
        kelly_fraction: float = 0.25,
        min_edge: float = 0.02,
        parquet_path: Path | None = None,
        *,
        model_dir: Path = Path("models/latest"),
        features_path: Path = Path("data/features/all_features.parquet"),
        model: ProbabilityModel | None = None,
    ) -> None:
        if bankroll <= 0.0:
            raise ValueError("bankroll must be positive")
        if not 0.0 < kelly_fraction <= 1.0:
            raise ValueError("kelly_fraction must be in (0, 1]")
        if min_edge < 0.0:
            raise ValueError("min_edge must be non-negative")

        if isinstance(model_type, Path):
            model_dir = model_type
            resolved_model_type = "lightgbm"
        else:
            resolved_model_type = model_type

        self._model_type = resolved_model_type
        self._model_dir = model_dir
        self._bankroll = bankroll
        self._kelly_fraction = kelly_fraction
        self._min_edge = min_edge
        self._features_path = parquet_path or features_path
        self._model = model

    def predict(
        self,
        date: dt.date | None = None,
        *,
        target_date: dt.date | None = None,
    ) -> list[BetRecommendation]:
        """Generate recommendations for a prediction date.

        Args:
            date: Target fixture date. Defaults to today.
            target_date: Compatibility alias for ``date``.

        Returns:
            Recommendations sorted by descending edge.
        """
        prediction_date = target_date or date or dt.datetime.now().date()

        upcoming_df, train_df, feature_cols = self._load_and_prepare_data(prediction_date)
        if upcoming_df is None:
            return self._mock_predictions(prediction_date)
        if upcoming_df.empty:
            return []
        if train_df is None or train_df.empty or not feature_cols:
            return self._mock_predictions(prediction_date)

        probabilities = self._train_and_predict(train_df, upcoming_df, feature_cols)
        if probabilities is None:
            return self._mock_predictions(prediction_date)

        candidates = collect_candidates(
            upcoming_df, probabilities, prediction_date, self._min_edge,
        )
        return self._candidates_to_recommendations(candidates)

    def save_predictions(
        self,
        predictions: list[BetRecommendation],
        output_dir: Path,
    ) -> Path:
        """Save recommendations to a JSON file and return its path."""
        output_dir.mkdir(parents=True, exist_ok=True)
        report_date = (
            predictions[0].kickoff_dt.date().isoformat()
            if predictions
            else dt.datetime.now().date().isoformat()
        )
        output_path = output_dir / f"bet_recommendations_{report_date}.json"

        payload: list[dict[str, object]] = []
        for recommendation in predictions:
            item = asdict(recommendation)
            item["kickoff"] = recommendation.kickoff_dt.isoformat()
            payload.append(item)

        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        logger.info(
            "daily_predictions_saved",
            output_path=str(output_path),
            recommendations=len(predictions),
        )
        return output_path

    @staticmethod
    def load_predictions(path: Path) -> list[BetRecommendation]:
        """Load predictions from a JSON file."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        data = raw["predictions"] if isinstance(raw, dict) and "predictions" in raw else raw
        if not isinstance(data, list):
            raise ValueError(f"Unexpected predictions JSON structure in {path}")
        return [BetRecommendation(**item) for item in data]

    def _load_and_prepare_data(
        self,
        prediction_date: dt.date,
    ) -> tuple[pd.DataFrame | None, pd.DataFrame | None, list[str]]:
        """Load features and split into (upcoming_df, train_df, feature_cols)."""
        df = self._load_features()
        if df is None or df.empty:
            logger.warning(
                "daily_predictor_features_missing",
                features_path=str(self._features_path),
            )
            return None, None, []

        upcoming_df = select_upcoming_matches(df, prediction_date)
        if upcoming_df.empty:
            logger.warning("daily_predictor_no_upcoming_matches", date=str(prediction_date))
            return upcoming_df, None, []

        train_df = select_recent_training_matches(df, prediction_date)
        feature_cols = select_feature_columns(train_df)
        if train_df.empty or not feature_cols:
            logger.warning(
                "daily_predictor_training_data_unavailable",
                training_rows=len(train_df),
                feature_columns=len(feature_cols),
            )
        return upcoming_df, train_df, feature_cols

    def _train_and_predict(
        self,
        train_df: pd.DataFrame,
        upcoming_df: pd.DataFrame,
        feature_cols: list[str],
    ) -> np.ndarray | None:
        """Train a model and return calibrated probabilities, or ``None`` on failure."""
        x_train, y_train, x_upcoming = prepare_features(
            train_df=train_df,
            upcoming_df=upcoming_df,
            feature_cols=feature_cols,
        )
        model = self._model or train_lightgbm(
            x_train, y_train, self._model_type, self._model_dir,
        )
        if model is None:
            return None

        try:
            probabilities = predict_probabilities(model, x_upcoming)
            if self._model is None:
                probabilities = calibrate_probabilities(
                    model=model,
                    x_train=x_train,
                    y_train=y_train,
                    prediction_probs=probabilities,
                )
        except ValueError:
            logger.warning("daily_predictor_prediction_failed", exc_info=True)
            return None

        return probabilities

    def _load_features(self) -> pd.DataFrame | None:
        """Read the materialized features parquet."""
        if not self._features_path.exists():
            return None
        df = pd.read_parquet(self._features_path)
        logger.info(
            "daily_predictor_features_loaded",
            path=str(self._features_path),
            rows=len(df),
            columns=df.shape[1],
        )
        return df

    def _mock_predictions(self, prediction_date: dt.date) -> list[BetRecommendation]:
        """Generate placeholder recommendations when real data is unavailable."""
        kickoff_one = dt.datetime.combine(prediction_date, dt.time(hour=18, minute=30))
        kickoff_two = dt.datetime.combine(prediction_date, dt.time(hour=20, minute=45))
        mock_candidates = [
            mock_candidate("1", "North FC", "South United", "1x2_home", 0.60, 2.00, kickoff_one, prediction_date),
            mock_candidate("2", "East City", "West Athletic", "1x2_away", 0.54, 2.08, kickoff_two, prediction_date),
        ]
        filtered = [
            c for c in mock_candidates
            if c.opportunity.model_prob - c.bookmaker_prob >= self._min_edge
        ]
        return self._candidates_to_recommendations(filtered)

    def _candidates_to_recommendations(
        self,
        candidates: list[_BetCandidate],
    ) -> list[BetRecommendation]:
        """Apply Kelly sizing and build final recommendation list."""
        kelly = PortfolioKelly(
            PortfolioConstraints(kelly_fraction=self._kelly_fraction)
        )
        stake_results = kelly.compute_stakes(
            [c.opportunity for c in candidates],
            bankroll=self._bankroll,
        )

        recommendations: list[BetRecommendation] = []
        for candidate, stake in zip(candidates, stake_results, strict=True):
            bet = candidate.opportunity
            recommendations.append(
                BetRecommendation(
                    match_id=bet.match_id,
                    home_team=bet.home_team,
                    away_team=bet.away_team,
                    league=bet.league,
                    kickoff=candidate.kickoff,
                    market=bet.market,
                    model_prob=round(bet.model_prob, 6),
                    bookmaker_prob=round(candidate.bookmaker_prob, 6),
                    edge=round(stake.edge, 6),
                    min_odds=round(candidate.min_odds, 4),
                    kelly_fraction=round(stake.final_stake_frac, 6),
                    stake_eur=round(stake.final_stake_frac * self._bankroll, 2),
                    model_agreement=candidate.model_agreement,
                    best_bookmaker=candidate.best_bookmaker,
                    best_odds=round(bet.odds, 4),
                )
            )

        recommendations.sort(key=lambda r: r.edge, reverse=True)
        logger.info("daily_predictor_recommendations_ready", count=len(recommendations))
        return recommendations

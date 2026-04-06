"""Tests for daily bet recommendations."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.prediction.daily import BetRecommendation, DailyPredictor


class FixedProbModel:
    """Deterministic model used to isolate predictor plumbing in tests."""

    def __init__(self, probabilities: tuple[float, float, float]) -> None:
        self._probabilities = np.asarray(probabilities, dtype=np.float64)

    def fit(self, x: pd.DataFrame, y: np.ndarray) -> None:
        """No-op fit for protocol compatibility."""

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        """Return the same 1x2 probabilities for every row."""
        return np.tile(self._probabilities, (len(x), 1))


@pytest.fixture
def features_path(tmp_path: Path) -> Path:
    """Create a small features parquet with completed and upcoming matches."""
    rows: list[dict[str, Any]] = []
    outcomes = ["H", "D", "A"] * 4
    for idx, outcome in enumerate(outcomes):
        rows.append(
            {
                "id": f"train-{idx}",
                "league": "ENG-Premier League",
                "season": "2024-2025" if idx < 6 else "2025-2026",
                "date": f"2025-0{(idx % 6) + 1}-01",
                "home_team": f"Home {idx}",
                "away_team": f"Away {idx}",
                "result_1x2": outcome,
                "avg_home": 1.90,
                "avg_draw": 3.40,
                "avg_away": 4.20,
                "feature_rating_delta": float(idx),
                "feature_form_delta": float(idx % 3),
            }
        )

    rows.extend(
        [
            {
                "id": "match-high-edge",
                "league": "ENG-Premier League",
                "season": "2025-2026",
                "date": "2026-04-06",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "result_1x2": None,
                "avg_home": 2.00,
                "avg_draw": 4.00,
                "avg_away": 6.00,
                "feature_rating_delta": 10.0,
                "feature_form_delta": 2.0,
            },
            {
                "id": "match-low-edge",
                "league": "ENG-Premier League",
                "season": "2025-2026",
                "date": "2026-04-06",
                "home_team": "Liverpool",
                "away_team": "Everton",
                "result_1x2": None,
                "avg_home": 1.80,
                "avg_draw": 4.00,
                "avg_away": 6.00,
                "feature_rating_delta": 7.0,
                "feature_form_delta": 1.0,
            },
        ]
    )

    path = tmp_path / "features.parquet"
    pd.DataFrame(rows).to_parquet(path)
    return path


def test_bet_recommendation_is_frozen() -> None:
    """BetRecommendation should be an immutable value object."""
    recommendation = BetRecommendation(
        match_id="m1",
        home_team="Home",
        away_team="Away",
        league="League",
        kickoff=dt.datetime(2026, 4, 6, 20, 45),
        market="1x2_home",
        model_prob=0.60,
        bookmaker_prob=0.50,
        edge=0.10,
        min_odds=1.6667,
        kelly_fraction=0.03,
        stake_eur=150.0,
        model_agreement=1,
        best_bookmaker="Market Avg",
        best_odds=2.0,
    )

    assert recommendation.edge == 0.10
    with pytest.raises(FrozenInstanceError):
        recommendation.edge = 0.20  # type: ignore[misc]


def test_predict_with_fixed_model(features_path: Path) -> None:
    """predict() should use injected model probabilities and feature parquet rows."""
    predictor = DailyPredictor(
        features_path=features_path,
        model=FixedProbModel((0.60, 0.25, 0.15)),
        min_edge=0.02,
    )

    recommendations = predictor.predict(date=dt.date(2026, 4, 6))

    assert recommendations
    assert all(recommendation.market == "1x2_home" for recommendation in recommendations)
    assert recommendations[0].match_id == "match-high-edge"
    assert recommendations[0].model_prob == pytest.approx(0.60)


def test_filtering_by_min_edge(features_path: Path) -> None:
    """High min_edge should filter out recommendations below the threshold."""
    predictor = DailyPredictor(
        features_path=features_path,
        model=FixedProbModel((0.60, 0.25, 0.15)),
        min_edge=0.08,
    )

    recommendations = predictor.predict(date=dt.date(2026, 4, 6))

    assert [recommendation.match_id for recommendation in recommendations] == [
        "match-high-edge"
    ]


def test_kelly_fraction_computation(features_path: Path) -> None:
    """Kelly output should use the constrained PortfolioKelly stake fraction."""
    predictor = DailyPredictor(
        bankroll=5000.0,
        kelly_fraction=0.25,
        min_edge=0.08,
        features_path=features_path,
        model=FixedProbModel((0.60, 0.25, 0.15)),
    )

    recommendations = predictor.predict(date=dt.date(2026, 4, 6))

    assert recommendations[0].kelly_fraction == pytest.approx(0.03)
    assert recommendations[0].stake_eur == pytest.approx(150.0)


def test_save_load_json_roundtrip(features_path: Path, tmp_path: Path) -> None:
    """save_predictions() should serialize datetimes as ISO strings."""
    predictor = DailyPredictor(
        features_path=features_path,
        model=FixedProbModel((0.60, 0.25, 0.15)),
        min_edge=0.08,
    )
    recommendations = predictor.predict(date=dt.date(2026, 4, 6))

    output_path = predictor.save_predictions(recommendations, tmp_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload[0]["match_id"] == "match-high-edge"
    assert payload[0]["kickoff"] == "2026-04-06T00:00:00"
    assert payload[0]["best_odds"] == 2.0


def test_sorting_by_edge_desc(features_path: Path) -> None:
    """Recommendations should be sorted from highest to lowest edge."""
    predictor = DailyPredictor(
        features_path=features_path,
        model=FixedProbModel((0.60, 0.25, 0.15)),
        min_edge=0.02,
    )

    recommendations = predictor.predict(date=dt.date(2026, 4, 6))
    edges = [recommendation.edge for recommendation in recommendations]

    assert edges == sorted(edges, reverse=True)

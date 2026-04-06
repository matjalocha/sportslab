"""Tests for daily bet result tracking."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path

from ml_in_sports.prediction.daily import BetRecommendation
from ml_in_sports.prediction.results import BetResult, ResultsTracker


def _recommendation(
    match_id: str = "2024-04-06 Arsenal-Chelsea",
    market: str = "1x2_home",
    stake_eur: float = 100.0,
    best_odds: float = 2.0,
) -> BetRecommendation:
    return BetRecommendation(
        match_id=match_id,
        home_team="Arsenal",
        away_team="Chelsea",
        league="ENG-Premier League",
        kickoff=dt.datetime(2024, 4, 6, 15, 30),
        market=market,
        model_prob=0.60,
        bookmaker_prob=0.50,
        edge=0.10,
        min_odds=1.67,
        kelly_fraction=0.02,
        stake_eur=stake_eur,
        model_agreement=1,
        best_bookmaker="Pinnacle",
        best_odds=best_odds,
    )


def _write_predictions(path: Path, recommendations: list[BetRecommendation]) -> None:
    payload = []
    for recommendation in recommendations:
        item = asdict(recommendation)
        item["kickoff"] = recommendation.kickoff_dt.isoformat()
        payload.append(item)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_actual_results(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding="utf-8")


def test_bet_result_creation() -> None:
    """BetResult should keep the original recommendation and result fields."""
    recommendation = _recommendation()
    result = BetResult(
        recommendation=recommendation,
        actual_score="2-1",
        actual_result="home",
        hit=True,
        closing_odds=1.95,
        clv=0.087179,
        pnl=100.0,
        bankroll_after=5100.0,
    )

    assert result.recommendation.match_id == recommendation.match_id
    assert result.hit is True
    assert result.pnl == 100.0


def test_process_day_hit_positive_pnl_and_clv(tmp_path: Path) -> None:
    """A correct bet should produce positive P&L and CLV when closing odds exist."""
    day = dt.date(2024, 4, 6)
    predictions_dir = tmp_path / "predictions"
    results_dir = tmp_path / "results"
    _write_predictions(predictions_dir / f"predictions_{day.isoformat()}.json", [_recommendation()])
    _write_actual_results(
        results_dir / f"results_{day.isoformat()}.json",
        [{"match_id": "2024-04-06 Arsenal-Chelsea", "score": "2-1", "result": "home", "closing_odds": 1.95}],
    )

    results = ResultsTracker(predictions_dir, results_dir).process_day(day)

    assert results[0].hit is True
    assert results[0].pnl == 100.0
    assert results[0].clv == 0.087179


def test_process_day_miss_negative_pnl(tmp_path: Path) -> None:
    """An incorrect bet should lose the stake."""
    day = dt.date(2024, 4, 6)
    predictions_dir = tmp_path / "predictions"
    results_dir = tmp_path / "results"
    _write_predictions(predictions_dir / f"predictions_{day.isoformat()}.json", [_recommendation()])
    _write_actual_results(
        results_dir / f"results_{day.isoformat()}.json",
        [{"match_id": "2024-04-06 Arsenal-Chelsea", "score": "0-1", "result": "away"}],
    )

    results = ResultsTracker(predictions_dir, results_dir).process_day(day)

    assert results[0].hit is False
    assert results[0].pnl == -100.0


def test_running_totals_accumulate_over_three_days(tmp_path: Path) -> None:
    """Running totals should aggregate processed result files chronologically."""
    predictions_dir = tmp_path / "predictions"
    results_dir = tmp_path / "results"
    tracker = ResultsTracker(predictions_dir, results_dir, initial_bankroll=5000.0)

    for offset, actual in enumerate(["home", "away", "home"]):
        day = dt.date(2024, 4, 6 + offset)
        recommendation = _recommendation(match_id=f"match-{offset}")
        _write_predictions(predictions_dir / f"predictions_{day.isoformat()}.json", [recommendation])
        _write_actual_results(
            results_dir / f"results_{day.isoformat()}.json",
            [{"match_id": f"match-{offset}", "score": "2-1", "result": actual, "closing_odds": 2.0}],
        )
        tracker.process_day(day)

    totals = tracker.running_totals()

    assert totals["total_bets"] == 3.0
    assert totals["wins"] == 2.0
    assert totals["losses"] == 1.0
    assert totals["total_pnl"] == 100.0
    assert totals["current_bankroll"] == 5100.0


def test_empty_predictions_for_date_returns_empty(tmp_path: Path) -> None:
    """Missing predictions should produce an empty processed result list."""
    tracker = ResultsTracker(tmp_path / "predictions", tmp_path / "results")

    assert tracker.process_day(dt.date(2024, 4, 6)) == []


def test_missing_results_file_skips_processing(tmp_path: Path) -> None:
    """Predictions without a manual results file should be skipped."""
    day = dt.date(2024, 4, 6)
    predictions_dir = tmp_path / "predictions"
    _write_predictions(predictions_dir / f"predictions_{day.isoformat()}.json", [_recommendation()])
    tracker = ResultsTracker(predictions_dir, tmp_path / "results")

    assert tracker.process_day(day) == []

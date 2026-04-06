"""Tests for weekly performance aggregation and reports."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path

from ml_in_sports.prediction.daily import BetRecommendation
from ml_in_sports.prediction.report.weekly_html import render_weekly_html_string
from ml_in_sports.prediction.report.weekly_telegram import render_weekly_telegram
from ml_in_sports.prediction.report.weekly_terminal import render_weekly_terminal_string
from ml_in_sports.prediction.results import BetResult, ResultsTracker
from ml_in_sports.prediction.weekly import WeeklyReporter


def _result(
    day: dt.date,
    index: int,
    league: str = "ENG-Premier League",
    market: str = "1x2_home",
    hit: bool = True,
    pnl: float = 100.0,
) -> BetResult:
    recommendation = BetRecommendation(
        match_id=f"match-{index}",
        home_team=f"Home {index}",
        away_team=f"Away {index}",
        league=league,
        kickoff=dt.datetime.combine(day, dt.time(hour=20, minute=45)),
        market=market,
        model_prob=0.60,
        bookmaker_prob=0.50,
        edge=0.10,
        min_odds=1.67,
        kelly_fraction=0.02,
        stake_eur=100.0,
        model_agreement=1,
        best_bookmaker="Pinnacle",
        best_odds=2.0,
    )
    return BetResult(
        recommendation=recommendation,
        actual_score="2-1" if hit else "0-1",
        actual_result="home" if hit else "away",
        hit=hit,
        closing_odds=1.95,
        clv=0.087179,
        pnl=pnl,
        bankroll_after=5000.0 + pnl,
    )


def _write_processed(path: Path, results: list[BetResult]) -> None:
    payload = []
    for result in results:
        item = asdict(result)
        item["recommendation"]["kickoff"] = result.recommendation.kickoff_dt.isoformat()
        payload.append(item)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_weekly_reporter_aggregates_week(tmp_path: Path) -> None:
    """WeeklyReporter should aggregate only results inside the requested week."""
    results_dir = tmp_path / "results"
    _write_processed(
        results_dir / "processed_results_2026-04-06.json",
        [
            _result(dt.date(2026, 4, 6), 1, hit=True, pnl=100.0),
            _result(dt.date(2026, 4, 6), 2, market="1x2_away", hit=False, pnl=-50.0),
        ],
    )
    _write_processed(
        results_dir / "processed_results_2026-04-13.json",
        [_result(dt.date(2026, 4, 13), 3, hit=True, pnl=100.0)],
    )

    data = WeeklyReporter(ResultsTracker(results_dir=results_dir)).generate(
        dt.date(2026, 4, 6)
    )

    assert data.total_bets == 2
    assert data.wins == 1
    assert data.losses == 1
    assert data.pnl == 50.0
    assert data.bankroll_end == 5050.0
    assert data.daily_pnl["2026-04-06"] == 50.0
    assert data.per_league[0]["bets"] == 2
    assert len(data.per_market) == 2
    assert data.best_bets[0].pnl == 100.0
    assert data.worst_bets[0].pnl == -50.0


def test_weekly_html_terminal_and_telegram_render(tmp_path: Path) -> None:
    """Weekly renderers should produce non-empty output under Telegram limits."""
    results_dir = tmp_path / "results"
    _write_processed(
        results_dir / "processed_results_2026-04-06.json",
        [_result(dt.date(2026, 4, 6), 1, hit=True, pnl=100.0)],
    )
    data = WeeklyReporter(ResultsTracker(results_dir=results_dir)).generate(
        dt.date(2026, 4, 6)
    )

    html = render_weekly_html_string(data)
    terminal = render_weekly_terminal_string(data)
    telegram = render_weekly_telegram(data)

    assert "Weekly Performance Report" in html
    assert "Daily P&L" in html
    assert "Weekly Performance" in terminal
    assert "Weekly Performance" in telegram
    assert len(telegram) < 4096

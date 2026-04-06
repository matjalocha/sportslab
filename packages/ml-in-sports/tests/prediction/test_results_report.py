"""Tests for daily results report rendering."""

from __future__ import annotations

import datetime as dt

from ml_in_sports.prediction.daily import BetRecommendation
from ml_in_sports.prediction.report.results_html import render_results_html_string
from ml_in_sports.prediction.report.results_telegram import render_results_telegram
from ml_in_sports.prediction.report.results_terminal import render_results_terminal_string
from ml_in_sports.prediction.results import BetResult


def _result(hit: bool = True, pnl: float = 100.0) -> BetResult:
    recommendation = BetRecommendation(
        match_id="match-1",
        home_team="Arsenal",
        away_team="Chelsea",
        league="ENG-Premier League",
        kickoff=dt.datetime(2026, 4, 6, 20, 45),
        market="1x2_home",
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


def test_results_html_has_summary_and_table() -> None:
    """Results HTML should include summary cards and the result table."""
    html = render_results_html_string([_result()], report_date=dt.date(2026, 4, 6))

    assert html.startswith("<!DOCTYPE html>")
    assert "Daily Results Tracker" in html
    assert "Bet Results" in html
    assert "Arsenal vs Chelsea" in html
    assert "WIN" in html


def test_results_terminal_does_not_crash() -> None:
    """Terminal renderer should return non-empty output."""
    output = render_results_terminal_string([_result()])

    assert "Daily Results" in output
    assert "Arsenal vs Chelsea" in output


def test_results_telegram_under_limit() -> None:
    """Telegram output should fit in one Telegram message."""
    message = render_results_telegram([_result(), _result(hit=False, pnl=-100.0)])

    assert len(message) < 4096
    assert "TRAFIONE" in message
    assert "PUDLA" in message


def test_results_empty_state() -> None:
    """Empty results should show an empty-state message."""
    html = render_results_html_string([])
    terminal = render_results_terminal_string([])
    telegram = render_results_telegram([])

    assert "No bet results to display." in html
    assert "No bet results to display." in terminal
    assert "No bet results to display." in telegram

"""Tests for daily bet slip report renderers."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from ml_in_sports.prediction.daily import BetRecommendation
from ml_in_sports.prediction.report.html import (
    render_html_bet_slip,
    render_html_bet_slip_string,
)
from ml_in_sports.prediction.report.telegram import render_telegram_bet_slip
from ml_in_sports.prediction.report.terminal import render_terminal_bet_slip_string


def _recommendation(index: int = 1, edge: float = 0.08) -> BetRecommendation:
    model_prob = 0.58 + min(index, 5) * 0.005
    bookmaker_prob = max(0.01, model_prob - edge)
    best_odds = 1.0 / bookmaker_prob
    return BetRecommendation(
        match_id=f"match-{index}",
        home_team=f"Home {index}",
        away_team=f"Away {index}",
        league="ENG-Premier League",
        kickoff=dt.datetime(2026, 4, 6, 20, 45),
        market="1x2_home",
        model_prob=model_prob,
        bookmaker_prob=bookmaker_prob,
        edge=edge,
        min_odds=1.0 / model_prob,
        kelly_fraction=0.02,
        stake_eur=100.0 + index,
        model_agreement=min(3, max(1, index % 4)),
        best_bookmaker="Pinnacle",
        best_odds=best_odds,
    )


def test_html_contains_summary_table_and_glossary(tmp_path: Path) -> None:
    """HTML report should include summary, recommendations table, and glossary."""
    output_path = tmp_path / "bet_slip.html"

    render_html_bet_slip([_recommendation()], output_path, report_date=dt.date(2026, 4, 6))
    html = output_path.read_text(encoding="utf-8")

    assert "Daily Bet Slip" in html
    assert "N Bets" in html
    assert "Recommendations" in html
    assert "Glossary" in html
    assert "Home 1 vs Away 1" in html


def test_terminal_output_non_empty() -> None:
    """Terminal renderer should return visible Rich output."""
    output = render_terminal_bet_slip_string([_recommendation()])

    assert "Daily Bet Slip" in output
    assert "Home 1 vs Away 1" in output


def test_telegram_under_4096_chars() -> None:
    """Telegram renderer should respect the Telegram message length limit."""
    message = render_telegram_bet_slip([_recommendation(index) for index in range(1, 10)])

    assert len(message) < 4096
    assert "Daily Bet Slip" in message


def test_empty_bets_show_empty_state() -> None:
    """Empty HTML and Telegram reports should show the approved empty-state copy."""
    html = render_html_bet_slip_string([], report_date=dt.date(2026, 4, 6))
    telegram = render_telegram_bet_slip([], report_date=dt.date(2026, 4, 6))

    assert "Zero betów dzisiaj. Model nie znalazł wartości." in html
    assert "Zero betów dzisiaj. Model nie znalazł wartości." in telegram


def test_telegram_truncates_30_bets() -> None:
    """When there are more than 25 bets, Telegram should include top 15 only."""
    message = render_telegram_bet_slip([_recommendation(index) for index in range(1, 31)])

    assert len(message) < 4096
    assert "Truncated to top 15 of 30 bets" in message
    assert "Home 15 vs Away 15" in message
    assert "Home 16 vs Away 16" not in message

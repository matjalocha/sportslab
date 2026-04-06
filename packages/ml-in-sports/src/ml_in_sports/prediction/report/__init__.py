"""Bet slip and results report rendering."""

from ml_in_sports.prediction.report.html import render_bet_slip_html, render_html_bet_slip
from ml_in_sports.prediction.report.results_html import render_results_html
from ml_in_sports.prediction.report.results_telegram import render_results_telegram
from ml_in_sports.prediction.report.results_terminal import print_results_terminal
from ml_in_sports.prediction.report.telegram import (
    format_bet_slip_telegram,
    render_telegram_bet_slip,
)
from ml_in_sports.prediction.report.terminal import (
    print_bet_slip_terminal,
    print_terminal_bet_slip,
)
from ml_in_sports.prediction.report.weekly_html import render_weekly_html
from ml_in_sports.prediction.report.weekly_telegram import render_weekly_telegram
from ml_in_sports.prediction.report.weekly_terminal import print_weekly_terminal

__all__ = [
    "format_bet_slip_telegram",
    "print_bet_slip_terminal",
    "print_results_terminal",
    "print_terminal_bet_slip",
    "print_weekly_terminal",
    "render_bet_slip_html",
    "render_html_bet_slip",
    "render_results_html",
    "render_results_telegram",
    "render_telegram_bet_slip",
    "render_weekly_html",
    "render_weekly_telegram",
]

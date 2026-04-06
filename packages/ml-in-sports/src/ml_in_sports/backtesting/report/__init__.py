"""Backtest report generation: data building, HTML, and terminal output."""

from ml_in_sports.backtesting.report.generator import ReportData, build_report_data
from ml_in_sports.backtesting.report.html import render_html_report
from ml_in_sports.backtesting.report.terminal import print_terminal_report

__all__ = [
    "ReportData",
    "build_report_data",
    "print_terminal_report",
    "render_html_report",
]

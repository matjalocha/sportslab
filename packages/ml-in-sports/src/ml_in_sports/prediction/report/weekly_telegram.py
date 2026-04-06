"""Telegram renderer for weekly performance reports."""

from __future__ import annotations

from ml_in_sports.prediction.report._utils import truncate_telegram
from ml_in_sports.prediction.weekly import WeeklyData


def render_weekly_telegram(data: WeeklyData) -> str:
    """Render weekly performance as compact Telegram Markdown."""
    lines = [
        f"*Weekly Performance* | {data.week_start} to {data.week_end}",
        f"Bets: *{data.total_bets}* | W-L: *{data.wins}-{data.losses}*",
        f"P&L: *EUR {data.pnl:+.2f}* | ROI: *{data.roi_7d:+.2%}* | CLV: *{data.clv_7d:+.2%}*",
        f"Bankroll: EUR {data.bankroll_start:.2f} -> EUR {data.bankroll_end:.2f}",
        "",
        "*Daily P&L*",
    ]
    lines.extend(f"{day}: EUR {pnl:+.2f}" for day, pnl in data.daily_pnl.items())

    if data.best_bets:
        lines.append("")
        lines.append("*Best Bets*")
        for result in data.best_bets:
            rec = result.recommendation
            lines.append(f"+ {rec.home_team} vs {rec.away_team}: EUR {result.pnl:+.2f}")

    message = "\n".join(lines)
    return truncate_telegram(message)

"""Telegram renderer for daily bet results."""

from __future__ import annotations

from ml_in_sports.prediction.report._utils import truncate_telegram
from ml_in_sports.prediction.results import BetResult


def render_results_telegram(results: list[BetResult]) -> str:
    """Render daily bet results as compact Telegram Markdown."""
    wins = sum(1 for result in results if result.hit)
    losses = len(results) - wins
    pnl = sum(result.pnl for result in results)
    lines = [f"*Daily Results* | W-L {wins}-{losses} | P&L EUR {pnl:+.2f}", ""]

    if not results:
        lines.append("No bet results to display.")
        return "\n".join(lines)

    visible = results[:20]
    for result in visible:
        recommendation = result.recommendation
        prefix = "TRAFIONE" if result.hit else "PUDLA"
        sign = "+" if result.pnl >= 0.0 else ""
        lines.append(
            f"{prefix}: {recommendation.home_team} vs {recommendation.away_team} "
            f"@{recommendation.best_odds:.2f} EUR {sign}{result.pnl:.2f}"
        )

    if len(results) > len(visible):
        lines.append(f"... + {len(results) - len(visible)} more")

    message = "\n".join(lines)
    return truncate_telegram(message)

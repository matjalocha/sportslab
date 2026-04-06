"""Telegram Markdown renderer for daily bet slips."""

from __future__ import annotations

import datetime as dt

from ml_in_sports.prediction.daily import BetRecommendation
from ml_in_sports.prediction.report._utils import (
    MAX_TELEGRAM_CHARS,
    infer_report_date_from_recommendations,
    truncate_telegram,
)

_EMPTY_STATE = "Zero betów dzisiaj. Model nie znalazł wartości."


def render_telegram_bet_slip(
    predictions: list[BetRecommendation],
    report_date: dt.date | None = None,
) -> str:
    """Render plain-text Markdown suitable for Telegram.

    Args:
        predictions: Bet recommendations to render.
        report_date: Optional report date override.

    Returns:
        Markdown text no longer than Telegram's 4096 character message limit.
    """
    resolved_date = report_date or infer_report_date_from_recommendations(predictions)
    total_stake = sum(prediction.stake_eur for prediction in predictions)
    ev = sum(
        prediction.stake_eur * (prediction.model_prob * prediction.best_odds - 1.0)
        for prediction in predictions
    )

    lines = [
        f"*Daily Bet Slip* | {resolved_date.isoformat()}",
        f"Bets: *{len(predictions)}* | Stake: *EUR {total_stake:.2f}* | EV: *{ev:+.2f} EUR*",
        "",
    ]

    if not predictions:
        lines.append(_EMPTY_STATE)
        return "\n".join(lines)[:MAX_TELEGRAM_CHARS]

    visible_predictions = predictions[:15] if len(predictions) > 25 else predictions
    for idx, prediction in enumerate(visible_predictions, start=1):
        lines.extend(
            [
                f"{idx}. *{prediction.home_team} vs {prediction.away_team}* | {prediction.league}",
                (
                    f"{prediction.market} | edge {prediction.edge:+.1%} | "
                    f"stake EUR {prediction.stake_eur:.2f}"
                ),
                (
                    f"{prediction.best_bookmaker} @ {prediction.best_odds:.2f} | "
                    f"agreement {prediction.model_agreement}/3"
                ),
                "",
            ]
        )

    if len(predictions) > 25:
        lines.append(f"_Truncated to top 15 of {len(predictions)} bets._")

    message = "\n".join(lines).strip()
    return truncate_telegram(message)


def format_bet_slip_telegram(bets: list[BetRecommendation]) -> str:
    """Compatibility wrapper for Telegram bet slip formatting."""
    return render_telegram_bet_slip(bets)

"""Shared utilities for prediction report renderers."""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

MAX_TELEGRAM_CHARS = 4096


@runtime_checkable
class _HasKickoffDt(Protocol):
    """Protocol for items with a kickoff_dt attribute."""

    @property
    def kickoff_dt(self) -> dt.datetime: ...


@runtime_checkable
class _HasRecommendation(Protocol):
    """Protocol for items wrapping a recommendation with kickoff_dt."""

    @property
    def recommendation(self) -> _HasKickoffDt: ...


def infer_report_date_from_recommendations(
    items: Sequence[_HasKickoffDt],
) -> dt.date:
    """Infer report date from the first item's kickoff_dt.

    Args:
        items: List of objects with a ``kickoff_dt`` attribute
            (e.g. ``BetRecommendation``).

    Returns:
        The date of the first item's kickoff, or today if the list is empty.
    """
    if items:
        return items[0].kickoff_dt.date()
    return dt.datetime.now().date()


def infer_report_date_from_results(
    items: Sequence[_HasRecommendation],
) -> dt.date:
    """Infer report date from the first result's recommendation kickoff_dt.

    Args:
        items: List of objects with a ``recommendation.kickoff_dt`` path
            (e.g. ``BetResult``).

    Returns:
        The date of the first item's recommendation kickoff, or today if empty.
    """
    if items:
        return items[0].recommendation.kickoff_dt.date()
    return dt.datetime.now().date()


def truncate_telegram(text: str, max_chars: int = MAX_TELEGRAM_CHARS) -> str:
    """Truncate text to fit Telegram's message limit.

    If the text exceeds *max_chars*, it is cut and an ellipsis marker appended.

    Args:
        text: Message text.
        max_chars: Maximum allowed characters.

    Returns:
        The original text if short enough, otherwise a truncated version.
    """
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + "\n_...truncated_"

"""Pydantic models for track-record endpoints.

Schema mirrors the frontend ``sportslab-web`` types (single source of
truth). Every camelCase-on-the-wire field declares an explicit
``alias`` so Python code stays snake_case internally while serializing
to the exact shape the Next.js app expects.

``populate_by_name=True`` keeps the constructors permissive: both the
snake_case and camelCase names work on input. Important for fixtures
and for round-tripping payloads echoed back from the frontend.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _AliasedModel(BaseModel):
    """Shared base with camelCase-on-wire / snake_case-in-Python config."""

    model_config = ConfigDict(populate_by_name=True)


StreakType = Literal["win", "loss"]


class TrackRecordStats(_AliasedModel):
    """Aggregate track-record KPIs over a rolling or fixed window."""

    bets: int = Field(description="Number of settled bets in the window.", ge=0)
    win_rate: float = Field(
        alias="winRate",
        description="Fraction of wins over settled bets (0..1).",
        ge=0.0,
        le=1.0,
    )
    roi_percent: float = Field(
        alias="roiPercent",
        description="Return on investment in percent (profit / turnover * 100).",
    )
    clv_percent: float = Field(
        alias="clvPercent",
        description="Closing-line value in percent, averaged across bets.",
    )
    profit_eur: float = Field(
        alias="profitEur",
        description="Cumulative profit in EUR (negative = loss).",
    )
    avg_edge_percent: float = Field(
        alias="avgEdgePercent",
        description="Average pre-bet edge in percent.",
    )
    max_drawdown_percent: float = Field(
        alias="maxDrawdownPercent",
        description="Worst peak-to-trough drawdown in percent (non-positive).",
        le=0.0,
    )
    current_streak_type: StreakType = Field(
        alias="currentStreakType",
        description="Whether the current run is a win or loss streak.",
    )
    current_streak_count: int = Field(
        alias="currentStreakCount",
        description="Length of the current streak in bets.",
        ge=0,
    )
    since_date: date_type = Field(
        alias="sinceDate",
        description="Earliest settlement date included in the aggregate.",
    )


class EquityPoint(_AliasedModel):
    """Daily snapshot of bankroll and P&L — one row per settled day."""

    date: date_type = Field(description="Settlement date for this snapshot.")
    bankroll_eur: float = Field(
        alias="bankrollEur",
        description="Running bankroll in EUR at end of day.",
    )
    pnl_eur: float = Field(
        alias="pnlEur",
        description="Cumulative profit/loss in EUR since ``since_date``.",
    )
    clv_percent: float = Field(
        alias="clvPercent",
        description="Cumulative average CLV in percent up to this date.",
    )
    bets: int = Field(description="Cumulative bet count through this date.", ge=0)


class MonthlyStat(_AliasedModel):
    """Per-month breakdown of the aggregate stats."""

    month: str = Field(
        description="Calendar month in ``YYYY-MM`` form.",
        pattern=r"^\d{4}-\d{2}$",
    )
    bets: int = Field(description="Settled bets in the month.", ge=0)
    win_rate: float = Field(alias="winRate", ge=0.0, le=1.0)
    roi_percent: float = Field(alias="roiPercent")
    clv_percent: float = Field(alias="clvPercent")
    profit_eur: float = Field(alias="profitEur")


class LeagueStat(_AliasedModel):
    """Per-league breakdown of the aggregate stats."""

    league: str = Field(description="Human-readable competition name.")
    bets: int = Field(description="Settled bets on this league.", ge=0)
    win_rate: float = Field(alias="winRate", ge=0.0, le=1.0)
    roi_percent: float = Field(alias="roiPercent")
    clv_percent: float = Field(alias="clvPercent")
    profit_eur: float = Field(alias="profitEur")

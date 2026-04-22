"""Pydantic models for predictions endpoints.

Schema mirrors ``sportslab-web/lib/mock-data/types.ts`` (single source of
truth for the frontend). Every camelCase-on-the-wire field is declared
with an explicit ``alias`` so Python code can keep snake_case internally
while serializing to the exact shape the Next.js app expects.

All models set ``populate_by_name=True`` so constructors accept both the
snake_case and camelCase name — important for test fixtures and when
decoding payloads coming back from the frontend (round-trip).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _AliasedModel(BaseModel):
    """Shared base: camelCase on the wire, snake_case in Python.

    ``protected_namespaces=()`` is required because ``BetRecommendation``
    uses ``model_probability`` — Pydantic v2 otherwise warns about any
    field name starting with ``model_`` since that prefix is reserved
    for its own internals (``model_dump``, ``model_validate``, ...).
    We are intentionally mirroring the frontend schema here.
    """

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())


class Team(_AliasedModel):
    """Football club / national team reference."""

    id: str = Field(description="Stable identifier (e.g. ``team_mancity``).")
    name: str = Field(description="Full display name, e.g. ``Manchester City``.")
    short_name: str = Field(
        alias="shortName",
        description="Short form for compact UIs, e.g. ``Man City``.",
    )


class Match(_AliasedModel):
    """Scheduled fixture a recommendation refers to."""

    id: str = Field(description="Match identifier.")
    kickoff_utc: datetime = Field(
        alias="kickoffUtc",
        description="Kick-off time in UTC (ISO-8601 on the wire).",
    )
    league: str = Field(description="Human-readable competition, e.g. ``Premier League``.")
    home: Team
    away: Team


Confidence = Literal["low", "medium", "high"]
BetStatus = Literal["won", "lost", "void", "pending"]


class BetRecommendation(_AliasedModel):
    """Published value-bet recommendation for a single match/market/selection."""

    id: str = Field(description="Unique recommendation id.")
    match: Match
    market: str = Field(description="Market key, e.g. ``1X2`` or ``OU_2.5``.")
    selection: str = Field(description="Selection label, e.g. ``HOME`` / ``OVER``.")
    model_probability: float = Field(
        alias="modelProbability",
        description="Model-predicted probability of the selection (0..1).",
        ge=0.0,
        le=1.0,
    )
    bookmaker_probability: float = Field(
        alias="bookmakerProbability",
        description="Implied probability from the best bookmaker price (0..1).",
        ge=0.0,
        le=1.0,
    )
    edge_percent: float = Field(
        alias="edgePercent",
        description="Relative edge in percent, i.e. (model - implied) / implied * 100.",
    )
    best_odds: float = Field(
        alias="bestOdds",
        description="Best decimal odds found across tracked bookmakers.",
        gt=1.0,
    )
    bookmaker: str = Field(description="Bookmaker that currently offers ``best_odds``.")
    kelly_stake: float = Field(
        alias="kellyStake",
        description="Recommended stake in EUR after ECE-dampened Kelly.",
        ge=0.0,
    )
    kelly_fraction: float = Field(
        alias="kellyFraction",
        description="Kelly fraction applied (0..1 of full Kelly).",
        ge=0.0,
        le=1.0,
    )
    confidence: Confidence = Field(description="Discretized calibration confidence tier.")
    ece: float = Field(
        description="Expected Calibration Error at publication time (lower is better).",
        ge=0.0,
    )
    published: datetime = Field(description="Publication timestamp (ISO-8601 UTC).")


class BetResult(_AliasedModel):
    """Settled outcome of a previously published recommendation."""

    id: str = Field(description="Result id (1:1 with the recommendation).")
    recommendation: BetRecommendation
    status: BetStatus = Field(description="Settlement status.")
    placed_at_odds: float = Field(
        alias="placedAtOdds",
        description="Odds actually placed at (may differ from ``best_odds`` at publish).",
        gt=1.0,
    )
    stake_eur: float = Field(
        alias="stakeEur",
        description="Stake placed in EUR.",
        ge=0.0,
    )
    profit_eur: float = Field(
        alias="profitEur",
        description="Net profit/loss in EUR (negative = loss, 0 = void).",
    )
    clv: float = Field(
        description="Closing-line value: (placed_odds / closing_odds - 1). Positive = beat the close.",
    )
    settled_at: datetime = Field(
        alias="settledAt",
        description="Settlement timestamp.",
    )

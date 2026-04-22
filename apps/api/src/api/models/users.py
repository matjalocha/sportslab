"""User profile, preferences, onboarding, and bet-tracking payloads.

These schemas mirror ``sportslab-web``'s TypeScript types so the generated
OpenAPI client round-trips cleanly. Field aliases keep snake_case on the
Python side and camelCase on the wire -- ``populate_by_name=True`` on every
model means callers may send either shape.

Scope caveat: the models are the contract. Persistence (Postgres users /
user_bets tables, Alembic migrations, FK to ``auth_users``) lands in
A-09 (SQLite -> Postgres). Until then :class:`StubUsersProvider` backs
these with in-memory dicts for dev and tests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Plan = Literal["alpha", "pro", "enterprise"]
Role = Literal["user", "admin"]
OddsFormat = Literal["decimal", "fractional", "american"]
BankrollTier = Literal["under_1k", "1k_5k", "5k_25k", "25k_plus"]
ExperienceLevel = Literal["beginner", "intermediate", "experienced", "professional"]
BetOutcome = Literal["pending", "won", "lost", "push", "void"]


class NotificationPrefs(BaseModel):
    """Per-user toggles for outbound alerts (telegram / email)."""

    model_config = ConfigDict(populate_by_name=True)

    telegram: bool = True
    email: bool = False
    daily_slip: bool = Field(True, alias="dailySlip")
    calibration_drift: bool = Field(True, alias="calibrationDrift")
    large_edge: bool = Field(True, alias="largeEdge")


class UserProfile(BaseModel):
    """Full profile returned by ``GET /users/me``.

    ``id`` matches the Clerk subject claim -- NOT a Postgres surrogate key.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    email: EmailStr
    full_name: str | None = Field(None, alias="fullName")
    telegram_handle: str | None = Field(None, alias="telegramHandle")
    plan: Plan
    role: Role
    bankroll_eur: float = Field(..., alias="bankrollEur")
    leagues_selected: list[str] = Field(default_factory=list, alias="leaguesSelected")
    markets_selected: list[str] = Field(default_factory=list, alias="marketsSelected")
    odds_format: OddsFormat = Field("decimal", alias="oddsFormat")
    notifications: NotificationPrefs = Field(default_factory=NotificationPrefs)
    created_at: datetime = Field(..., alias="createdAt")


class UserProfileUpdate(BaseModel):
    """Partial update body for ``PATCH /users/me``.

    Every field is optional; ``None`` means "leave untouched". We do not
    use ``exclude_unset`` on the response because the response is the full
    profile -- only the request body distinguishes "unset" from "null".
    """

    model_config = ConfigDict(populate_by_name=True)

    full_name: str | None = Field(None, alias="fullName")
    telegram_handle: str | None = Field(None, alias="telegramHandle")
    bankroll_eur: float | None = Field(None, alias="bankrollEur")
    leagues_selected: list[str] | None = Field(None, alias="leaguesSelected")
    markets_selected: list[str] | None = Field(None, alias="marketsSelected")
    odds_format: OddsFormat | None = Field(None, alias="oddsFormat")
    notifications: NotificationPrefs | None = None


class OnboardRequest(BaseModel):
    """Body for ``POST /users/onboard``.

    Tier buckets (rather than exact bankroll) keep the funnel short; the
    exact number can be edited from settings later.
    """

    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    telegram_handle: str | None = Field(None, alias="telegramHandle")
    bankroll_tier: BankrollTier = Field(..., alias="bankrollTier")
    experience_level: ExperienceLevel = Field(..., alias="experienceLevel")


class UserBet(BaseModel):
    """A single user-tracked bet (placed, settled, or still pending).

    ``follows_model`` indicates whether the bet matches a SportsLab pick --
    critical for attribution: users asking "did I make money following
    your picks?" need this flag separable from off-book wagers.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    match_id: str = Field(..., alias="matchId")
    market: str
    selection: str
    stake_eur: float = Field(..., alias="stakeEur")
    odds: float
    bookmaker: str
    placed_at: datetime = Field(..., alias="placedAt")
    outcome: BetOutcome
    pnl_eur: float | None = Field(None, alias="pnlEur")
    follows_model: bool = Field(..., alias="followsModel")


class UserBetCreate(BaseModel):
    """Request body for ``POST /users/me/bets``.

    ``outcome`` defaults to ``pending`` and ``placed_at`` is set server-
    side to avoid timezone drift from untrusted client clocks.
    """

    model_config = ConfigDict(populate_by_name=True)

    match_id: str = Field(..., alias="matchId")
    market: str
    selection: str
    stake_eur: float = Field(..., alias="stakeEur")
    odds: float
    bookmaker: str

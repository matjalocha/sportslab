"""SQLAlchemy ORM models for SportsLab API persistence.

Scope for SPO-144 / A-09 prep:

- :class:`User`          -- profile + preferences keyed on the Clerk ``sub``.
- :class:`UserBet`       -- bet slips users log for their personal track record.
- :class:`WebhookEvent`  -- idempotency ledger replacing the in-memory store.

All timestamps are timezone-aware (``DateTime(timezone=True)``) because the
API serves a multi-region user base (PL + international odds feeds) and we
never want to rely on the server's local TZ. Row-level defaults use
``server_default=func.now()`` so a direct ``INSERT`` from Alembic data
migrations or ad-hoc SQL gets the same semantics as the ORM.

JSON-typed columns (``leagues_selected``, ``markets_selected``,
``notifications``) use SQLAlchemy's portable :class:`sa.JSON` so the same
models run against SQLite locally (``JSON1`` extension) and Postgres in
prod (native ``jsonb``). Alembic's autogenerate emits ``sa.JSON()`` which
each dialect maps to the right underlying type.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class User(Base):
    """Registered SportsLab user, keyed by their Clerk ``sub``.

    Writes flow in from the Clerk webhook (``user.created`` / ``user.updated``)
    and from the profile/preferences endpoints. Soft-delete via ``status``
    (``active`` | ``disabled`` | ``invited``) rather than row removal so
    historical bets keep their FK target.

    Attributes mirror the Pydantic ``UserProfile`` / ``UserPreferences``
    shapes exposed by ``/api/v1/users`` -- same field names, snake_case,
    with JSON columns for the list/dict fields that keep the schema flat.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200))
    telegram_handle: Mapped[str | None] = mapped_column(String(100))
    plan: Mapped[str] = mapped_column(
        String(32), nullable=False, default="alpha", server_default="alpha"
    )
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="user", server_default="user"
    )
    bankroll_eur: Mapped[float] = mapped_column(
        Float, nullable=False, default=1000.0, server_default="1000.0"
    )
    leagues_selected: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    markets_selected: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    odds_format: Mapped[str] = mapped_column(
        String(16), nullable=False, default="decimal", server_default="decimal"
    )
    notifications: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    bets: Mapped[list[UserBet]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_status", "status"),
        Index("ix_users_plan", "plan"),
    )


class UserBet(Base):
    """Bet slip logged by a user for personal track-record computation.

    The aggregate endpoints (:mod:`api.routers.track_record`) read from
    this table once the stub provider is replaced in SPO-A-09. ``outcome``
    stays ``pending`` until the match settles; the scheduler flips it to
    ``won`` | ``lost`` | ``void`` and fills ``pnl_eur`` in one atomic UPDATE.

    ``follows_model`` flags bets placed on a SportsLab recommendation -- used
    to compute model-vs-freestyle performance deltas on the dashboard.
    """

    __tablename__ = "user_bets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(64), nullable=False)
    selection: Mapped[str] = mapped_column(String(64), nullable=False)
    stake_eur: Mapped[float] = mapped_column(Float, nullable=False)
    odds: Mapped[float] = mapped_column(Float, nullable=False)
    bookmaker: Mapped[str] = mapped_column(String(64), nullable=False)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    pnl_eur: Mapped[float | None] = mapped_column(Float)
    follows_model: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    user: Mapped[User] = relationship(back_populates="bets")

    __table_args__ = (
        Index("ix_user_bets_user_placed_at", "user_id", "placed_at"),
        Index("ix_user_bets_outcome", "outcome"),
    )


class WebhookEvent(Base):
    """Idempotency ledger for provider webhook deliveries.

    Replaces :class:`api.routers.webhooks.InMemoryIdempotencyStore` once the
    Postgres migration lands -- the ``UNIQUE(provider, event_id)`` constraint
    is what makes multi-worker deployments correct. The ``id`` column is a
    plain autoincrement surrogate; we never key off it externally.

    The row itself is the idempotency signal -- presence means "already
    processed". We intentionally don't store the event payload here; that's
    a separate concern (append-only audit log) and would bloat the hot path.
    """

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_provider_event"),
        Index("ix_webhook_events_provider_received", "provider", "received_at"),
    )

"""Initial schema -- users, user_bets, webhook_events.

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-22

Notes:
    - Three tables land together because the webhook idempotency store
      (``webhook_events``) and the bet ledger (``user_bets``) both depend on
      a stable ``users`` row, and splitting the initial migration adds no
      reversibility benefit: a rollback of the initial migration is always
      ``DROP TABLE`` of all three.
    - JSON columns use the portable ``sa.JSON`` type so the same migration
      applies to SQLite (dev) and Postgres (prod). On Postgres the
      underlying storage is ``jsonb``; on SQLite it's ``TEXT`` with JSON1
      helpers.
    - Timestamps are timezone-aware (``DateTime(timezone=True)``). Postgres
      stores them as ``timestamptz``; SQLite treats them as ISO-8601 text.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create users, user_bets, webhook_events with their indices + FKs."""
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("telegram_handle", sa.String(length=100), nullable=True),
        sa.Column(
            "plan",
            sa.String(length=32),
            nullable=False,
            server_default="alpha",
        ),
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default="user",
        ),
        sa.Column(
            "bankroll_eur",
            sa.Float(),
            nullable=False,
            server_default="1000.0",
        ),
        sa.Column("leagues_selected", sa.JSON(), nullable=False),
        sa.Column("markets_selected", sa.JSON(), nullable=False),
        sa.Column(
            "odds_format",
            sa.String(length=16),
            nullable=False,
            server_default="decimal",
        ),
        sa.Column("notifications", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_plan", "users", ["plan"])

    op.create_table(
        "user_bets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_id", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=False),
        sa.Column("selection", sa.String(length=64), nullable=False),
        sa.Column("stake_eur", sa.Float(), nullable=False),
        sa.Column("odds", sa.Float(), nullable=False),
        sa.Column("bookmaker", sa.String(length=64), nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "outcome",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("pnl_eur", sa.Float(), nullable=True),
        sa.Column(
            "follows_model",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_index("ix_user_bets_user_id", "user_bets", ["user_id"])
    op.create_index("ix_user_bets_match_id", "user_bets", ["match_id"])
    op.create_index("ix_user_bets_placed_at", "user_bets", ["placed_at"])
    op.create_index(
        "ix_user_bets_user_placed_at", "user_bets", ["user_id", "placed_at"]
    )
    op.create_index("ix_user_bets_outcome", "user_bets", ["outcome"])

    op.create_table(
        "webhook_events",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "provider", "event_id", name="uq_provider_event"
        ),
    )
    op.create_index(
        "ix_webhook_events_provider_received",
        "webhook_events",
        ["provider", "received_at"],
    )


def downgrade() -> None:
    """Drop every table created in ``upgrade`` in reverse dependency order."""
    op.drop_index("ix_webhook_events_provider_received", table_name="webhook_events")
    op.drop_table("webhook_events")

    op.drop_index("ix_user_bets_outcome", table_name="user_bets")
    op.drop_index("ix_user_bets_user_placed_at", table_name="user_bets")
    op.drop_index("ix_user_bets_placed_at", table_name="user_bets")
    op.drop_index("ix_user_bets_match_id", table_name="user_bets")
    op.drop_index("ix_user_bets_user_id", table_name="user_bets")
    op.drop_table("user_bets")

    op.drop_index("ix_users_plan", table_name="users")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_table("users")

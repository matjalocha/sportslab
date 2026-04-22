"""Smoke tests for the Alembic scaffolding.

The goal is not to exhaustively test every column -- SQLAlchemy does that
for us -- but to confirm the wiring is alive:

- ``env.py`` can resolve a DB URL and connect.
- The initial migration applies cleanly.
- ``downgrade`` undoes everything, so the migration is reversible.
- Every ORM model ends up registered on the generated schema.

These tests run against an ephemeral SQLite DB per case so they stay
hermetic and fast; the same migration targets Postgres in prod thanks to
``sa.JSON`` / ``DateTime(timezone=True)`` being dialect-portable.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

_API_ROOT = Path(__file__).resolve().parents[1]
_ALEMBIC_INI = _API_ROOT / "alembic.ini"

_EXPECTED_TABLES = {"users", "user_bets", "webhook_events", "alembic_version"}


@pytest.fixture
def alembic_config(tmp_path: Path) -> Iterator[tuple[Config, str]]:
    """Return an Alembic Config wired to a throwaway SQLite DB.

    ``script_location`` is pinned to the real migrations directory so the
    initial migration is exercised. ``sqlalchemy.url`` points at a temp
    file so each test gets a clean slate.
    """
    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_path}"

    config = Config(str(_ALEMBIC_INI))
    # Override script_location to an absolute path -- tests may run from any cwd.
    config.set_main_option("script_location", str(_API_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", db_url)
    # env.py honours -x db_url= first, then SPORTSLAB_DATABASE_URL. Force
    # the URL via -x so we don't depend on ambient env vars.
    config.cmd_opts = type("_O", (), {"x": [f"db_url={db_url}"]})()

    yield config, db_url


def test_upgrade_head_creates_all_tables(
    alembic_config: tuple[Config, str],
) -> None:
    """``upgrade head`` lands every ORM-declared table plus the version row."""
    config, db_url = alembic_config

    command.upgrade(config, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    assert _EXPECTED_TABLES.issubset(actual_tables), (
        f"missing tables: {_EXPECTED_TABLES - actual_tables}"
    )


def test_downgrade_base_removes_all_tables(
    alembic_config: tuple[Config, str],
) -> None:
    """``downgrade base`` is a true inverse -- no leftover tables."""
    config, db_url = alembic_config

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    remaining = set(inspector.get_table_names())
    # Only Alembic's version table may survive -- everything else must go.
    assert remaining <= {"alembic_version"}, f"leftover tables: {remaining}"


def test_users_table_has_expected_columns(
    alembic_config: tuple[Config, str],
) -> None:
    """Column names on ``users`` match the ORM declaration.

    Guards against migrations drifting from models without anyone noticing.
    """
    config, db_url = alembic_config

    command.upgrade(config, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("users")}
    expected_subset = {
        "id",
        "email",
        "full_name",
        "telegram_handle",
        "plan",
        "role",
        "bankroll_eur",
        "leagues_selected",
        "markets_selected",
        "odds_format",
        "notifications",
        "status",
        "created_at",
        "last_active_at",
    }
    assert expected_subset.issubset(columns), (
        f"missing user columns: {expected_subset - columns}"
    )


def test_webhook_events_unique_constraint(
    alembic_config: tuple[Config, str],
) -> None:
    """``uq_provider_event`` is what dedupes webhook retries -- it must exist."""
    config, db_url = alembic_config

    command.upgrade(config, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    uniques = inspector.get_unique_constraints("webhook_events")
    assert any(u["name"] == "uq_provider_event" for u in uniques), (
        f"uq_provider_event missing from: {uniques}"
    )

"""Alembic environment for the SportsLab API.

Loads the database URL from the ``SPORTSLAB_DATABASE_URL`` env var (same
name ``api.config.Settings`` reads) so migrations always target the same
database as the running service -- no duplicate ini files, no drift.

Key behaviours:

- **Sync engine only.** Alembic's programmatic API is sync; we run
  migrations against the sync variant of the configured URL (e.g.
  ``postgresql+asyncpg://...`` -> ``postgresql+psycopg://...``). The
  production app still uses the async URL at runtime.
- **Target metadata** is :data:`api.db.Base.metadata` -- importing
  ``api.db.models`` registers every model, which is what makes
  ``--autogenerate`` see the full schema.
- **SQLite safety.** Renames/ALTERs on SQLite need batch mode; we pass
  ``render_as_batch=True`` when the URL dialect is sqlite so generated
  migrations work against the dev DB.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context

# Register all ORM models on Base.metadata. The import is required even
# though the symbol is only used via ``Base.metadata`` -- without it,
# autogenerate sees an empty schema.
from api.db import Base
from api.db import models as _models  # noqa: F401
from sqlalchemy import engine_from_config, pool

# Alembic Config object — pulls values from alembic.ini.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _resolve_database_url() -> str:
    """Pick the database URL for the migration run.

    Priority:
        1. ``-x db_url=...`` override passed on the command line.
        2. ``SPORTSLAB_DATABASE_URL`` environment variable.
        3. Local-dev fallback ``sqlite:///./local.db``.

    We also coerce the async drivers we ship with the app (``+asyncpg``,
    ``+aiosqlite``) to their sync equivalents because Alembic's programmatic
    API is synchronous. The prod runtime connection string is untouched.
    """
    x_args = context.get_x_argument(as_dictionary=True)
    url = x_args.get("db_url") or os.environ.get("SPORTSLAB_DATABASE_URL") or "sqlite:///./local.db"
    # Drop async drivers -- Alembic needs a sync engine.
    url = url.replace("postgresql+asyncpg", "postgresql+psycopg")
    url = url.replace("sqlite+aiosqlite", "sqlite")
    return url


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to a database.

    Useful for generating DDL to hand to a DBA or to diff in code review.
    """
    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Open a live connection and run migrations inside a transaction."""
    url = _resolve_database_url()
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=url.startswith("sqlite"),
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

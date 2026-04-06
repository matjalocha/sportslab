"""Alembic environment configuration for ml_in_sports.

Supports both SQLite (current) and Postgres (future R4 migration).
Database URL priority:
    1. ``ML_IN_SPORTS_DATABASE_URL`` environment variable
    2. ``sqlalchemy.url`` in ``alembic.ini``
"""

import os
from logging.config import fileConfig

from alembic import context
from ml_in_sports.db.models import Base
from sqlalchemy import engine_from_config, pool

# Alembic Config object -- provides access to .ini values.
config = context.config

# Override sqlalchemy.url from environment if set.
database_url = os.environ.get("ML_IN_SPORTS_DATABASE_URL")
if database_url is not None:
    config.set_main_option("sqlalchemy.url", database_url)

# Python logging from config file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData for autogenerate support.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a live connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live database connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

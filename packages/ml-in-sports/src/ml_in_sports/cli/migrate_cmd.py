"""Database migration CLI tools."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from importlib import import_module
from pathlib import Path
from typing import Annotated, Any

import structlog
import typer

from ml_in_sports.settings import get_settings
from ml_in_sports.utils.database import _TABLES_SQL

logger = structlog.get_logger(__name__)

migrate_app = typer.Typer(no_args_is_help=True)

_TABLES: tuple[str, ...] = tuple(_TABLES_SQL.keys())
_BATCH_SIZE = 1000


@migrate_app.command("sqlite-to-postgres")
def sqlite_to_postgres(
    sqlite_path: Annotated[
        Path,
        typer.Option("--sqlite-path", help="Path to the source SQLite database."),
    ] = Path("data/football.db"),
) -> None:
    """Migrate all SportsLab tables from SQLite to Postgres."""
    database_url = get_settings().database_url
    if not database_url:
        raise typer.BadParameter("ML_IN_SPORTS_DATABASE_URL must be set for Postgres migration.")

    _run_alembic_upgrade(database_url)
    source_conn = sqlite3.connect(str(sqlite_path))
    source_conn.row_factory = sqlite3.Row
    target_conn = _connect_postgres(database_url)

    try:
        for table in _TABLES:
            count = migrate_table(source_conn, target_conn, table)
            logger.info("table_migrated", table=table, rows=count)
            typer.echo(f"Migrated {table}: {count} rows")
            source_count = _count_rows(source_conn, table)
            target_count = _count_rows(target_conn, table)
            if source_count != target_count:
                raise RuntimeError(
                    f"Count mismatch for {table}: sqlite={source_count}, postgres={target_count}"
                )
    finally:
        source_conn.close()
        target_conn.close()


def migrate_table(
    source_conn: Any,
    target_conn: Any,
    table: str,
    *,
    placeholder: str = "%s",
    batch_size: int = _BATCH_SIZE,
) -> int:
    """Migrate a single table from one DB-API connection to another.

    Args:
        source_conn: Source DB-API connection.
        target_conn: Target DB-API connection.
        table: Table name to migrate.
        placeholder: Target placeholder style.
        batch_size: Number of rows per insert batch.

    Returns:
        Number of migrated rows.
    """
    source_cursor = source_conn.execute(f"SELECT * FROM {table}")
    columns = [description[0] for description in source_cursor.description]
    placeholders = ", ".join([placeholder] * len(columns))
    col_names = ", ".join(columns)
    insert_sql = (
        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
        "ON CONFLICT DO NOTHING"
    )

    migrated = 0
    while True:
        rows = source_cursor.fetchmany(batch_size)
        if not rows:
            break
        values = [_row_values(row) for row in rows]
        target_cursor = target_conn.cursor()
        target_cursor.executemany(insert_sql, values)
        target_conn.commit()
        migrated += len(values)
    return migrated


def _row_values(row: Any) -> tuple[Any, ...]:
    if isinstance(row, sqlite3.Row):
        return tuple(row)
    if isinstance(row, Sequence) and not isinstance(row, str | bytes):
        return tuple(row)
    raise TypeError(f"Unsupported row type: {type(row)!r}")


def _count_rows(conn: Any, table: str) -> int:
    cursor = conn.cursor() if hasattr(conn, "cursor") else conn
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    row = cursor.fetchone()
    return int(row[0])


def _connect_postgres(database_url: str) -> Any:
    psycopg2 = import_module("psycopg2")
    return psycopg2.connect(database_url)


def _run_alembic_upgrade(database_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    package_root = Path(__file__).resolve().parents[3]
    config = Config(str(package_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

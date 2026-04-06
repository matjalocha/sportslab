"""Tests for database migration helpers."""

from __future__ import annotations

import sqlite3

from ml_in_sports.cli.migrate_cmd import migrate_table


def test_migrate_table_sqlite_to_sqlite_in_memory() -> None:
    """Migration helper can copy rows between DB-API connections."""
    source = sqlite3.connect(":memory:")
    target = sqlite3.connect(":memory:")
    try:
        source.execute(
            "CREATE TABLE scrape_log ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "source TEXT NOT NULL, league TEXT, season TEXT, scraped_at TEXT NOT NULL, "
            "row_count INTEGER, status TEXT NOT NULL, UNIQUE(source, league, season))"
        )
        target.execute(
            "CREATE TABLE scrape_log ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "source TEXT NOT NULL, league TEXT, season TEXT, scraped_at TEXT NOT NULL, "
            "row_count INTEGER, status TEXT NOT NULL, UNIQUE(source, league, season))"
        )
        source.execute(
            "INSERT INTO scrape_log "
            "(source, league, season, scraped_at, row_count, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("understat", "ENG-Premier League", "2324", "2024-01-01", 10, "success"),
        )
        source.commit()

        migrated = migrate_table(source, target, "scrape_log", placeholder="?")

        assert migrated == 1
        row = target.execute("SELECT source, row_count FROM scrape_log").fetchone()
        assert row == ("understat", 10)
    finally:
        source.close()
        target.close()

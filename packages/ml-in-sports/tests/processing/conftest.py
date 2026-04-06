"""Fixtures shared across processing test modules.

Ported from the research codebase during SPO-40 (pipeline.py migration).
"""

from pathlib import Path

import pytest
from ml_in_sports.utils.database import FootballDatabase


@pytest.fixture
def db(tmp_path: Path) -> FootballDatabase:
    """Create a temporary test database."""
    database = FootballDatabase(db_path=tmp_path / "test.db")
    database.create_tables()
    return database

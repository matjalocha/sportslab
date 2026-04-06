"""Tests for the SQLite database layer."""

from pathlib import Path

import pandas as pd
import pytest
from ml_in_sports.utils.database import FootballDatabase


@pytest.fixture
def db(tmp_path: Path) -> FootballDatabase:
    """Create a temporary test database."""
    db_path = tmp_path / "test.db"
    database = FootballDatabase(db_path=db_path)
    database.create_tables()
    return database


class TestCreateTables:
    """Tests for table creation."""

    def test_creates_all_tables(self, db: FootballDatabase) -> None:
        """All 5 tables are created."""
        cursor = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        expected = {"matches", "player_matches", "league_tables",
                    "elo_ratings", "scrape_log"}
        assert expected.issubset(tables)

    def test_idempotent(self, db: FootballDatabase) -> None:
        """Calling create_tables twice doesn't error."""
        db.create_tables()


class TestUpsertDataframe:
    """Tests for upsert_dataframe."""

    def test_inserts_rows(self, db: FootballDatabase) -> None:
        """Insert rows into matches table."""
        df = pd.DataFrame([{
            "league": "ENG-Premier League",
            "season": "2324",
            "game": "2024-01-01 Arsenal-Chelsea",
            "date": "2024-01-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_goals": 2,
            "away_goals": 1,
        }])
        count = db.upsert_dataframe("matches", df)
        assert count == 1

    def test_upsert_replaces_on_conflict(
        self, db: FootballDatabase,
    ) -> None:
        """Duplicate key replaces existing row."""
        row = {
            "league": "ENG-Premier League",
            "season": "2324",
            "game": "2024-01-01 Arsenal-Chelsea",
            "date": "2024-01-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_goals": 2,
            "away_goals": 1,
        }
        db.upsert_dataframe("matches", pd.DataFrame([row]))

        row["home_goals"] = 3
        db.upsert_dataframe("matches", pd.DataFrame([row]))

        result = db.read_table("matches")
        assert len(result) == 1
        assert result.iloc[0]["home_goals"] == 3

    def test_empty_dataframe_returns_zero(
        self, db: FootballDatabase,
    ) -> None:
        """Empty DataFrame upserts 0 rows."""
        assert db.upsert_dataframe("matches", pd.DataFrame()) == 0


class TestReadTable:
    """Tests for read_table."""

    def test_reads_all_rows(self, db: FootballDatabase) -> None:
        """Read all rows without filters."""
        df = pd.DataFrame([
            {"league": "ENG-Premier League", "season": "2324",
             "game": "g1", "date": "2024-01-01",
             "home_team": "A", "away_team": "B"},
            {"league": "ESP-La Liga", "season": "2324",
             "game": "g2", "date": "2024-01-01",
             "home_team": "C", "away_team": "D"},
        ])
        db.upsert_dataframe("matches", df)
        result = db.read_table("matches")
        assert len(result) == 2

    def test_filters_by_league(self, db: FootballDatabase) -> None:
        """Read filtered by league."""
        df = pd.DataFrame([
            {"league": "ENG-Premier League", "season": "2324",
             "game": "g1", "date": "2024-01-01",
             "home_team": "A", "away_team": "B"},
            {"league": "ESP-La Liga", "season": "2324",
             "game": "g2", "date": "2024-01-01",
             "home_team": "C", "away_team": "D"},
        ])
        db.upsert_dataframe("matches", df)
        result = db.read_table("matches", league="ESP-La Liga")
        assert len(result) == 1
        assert result.iloc[0]["league"] == "ESP-La Liga"


class TestScrapeLog:
    """Tests for scrape_log operations."""

    def test_not_scraped_initially(self, db: FootballDatabase) -> None:
        """Nothing is scraped initially."""
        assert not db.is_scraped("understat", "ENG-Premier League", "2324")

    def test_log_scrape_marks_as_scraped(
        self, db: FootballDatabase,
    ) -> None:
        """After logging success, is_scraped returns True."""
        db.log_scrape("understat", "ENG-Premier League", "2324", 380, "success")
        assert db.is_scraped("understat", "ENG-Premier League", "2324")

    def test_failed_scrape_not_marked(
        self, db: FootballDatabase,
    ) -> None:
        """Failed scrape does not count as scraped."""
        db.log_scrape("understat", "ENG-Premier League", "2324", 0, "failed")
        assert not db.is_scraped("understat", "ENG-Premier League", "2324")

    def test_log_scrape_upserts(self, db: FootballDatabase) -> None:
        """Re-logging overwrites previous entry."""
        db.log_scrape("understat", "ENG-Premier League", "2324", 0, "failed")
        db.log_scrape("understat", "ENG-Premier League", "2324", 380, "success")
        assert db.is_scraped("understat", "ENG-Premier League", "2324")

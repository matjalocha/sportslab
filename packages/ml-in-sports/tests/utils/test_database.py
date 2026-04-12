"""Tests for the SQLite database layer."""

from pathlib import Path

import pandas as pd
import pytest
from ml_in_sports.settings import get_settings
from ml_in_sports.utils.database import (
    FootballDatabase,
    _convert_insert_or_replace,
    _unique_columns,
)


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


class _FakePostgresCursor:
    """Minimal psycopg-like cursor for database backend tests."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
        """Record executed SQL."""
        self.executed.append((sql, params))

    def executemany(self, sql: str, rows: list[list[object]]) -> None:
        """Record batch SQL."""
        self.executed.append((sql, tuple(rows[0]) if rows else ()))

    def fetchone(self) -> tuple[str] | None:
        """Return no rows by default."""
        return None


class _FakePostgresConnection:
    """Minimal psycopg-like connection for database backend tests."""

    def __init__(self) -> None:
        self.cursor_obj = _FakePostgresCursor()
        self.commits = 0
        self.closed = False

    def cursor(self) -> _FakePostgresCursor:
        """Return a reusable cursor."""
        return self.cursor_obj

    def commit(self) -> None:
        """Record commit calls."""
        self.commits += 1

    def close(self) -> None:
        """Record close calls."""
        self.closed = True


class _FakePsycopg2:
    """Minimal psycopg2 module replacement."""

    def __init__(self, connection: _FakePostgresConnection) -> None:
        self.connection = connection

    def connect(self, database_url: str) -> _FakePostgresConnection:
        """Return the fake connection."""
        assert database_url == "postgresql://user:pass@localhost:5432/db"
        return self.connection


def test_postgres_path_uses_mock_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Postgres mode should initialize through psycopg2 without a real server."""
    fake_connection = _FakePostgresConnection()
    fake_psycopg2 = _FakePsycopg2(fake_connection)
    monkeypatch.setenv(
        "ML_IN_SPORTS_DATABASE_URL",
        "postgresql://user:pass@localhost:5432/db",
    )
    get_settings.cache_clear()
    monkeypatch.setattr(
        "ml_in_sports.utils.database.import_module",
        lambda name: fake_psycopg2 if name == "psycopg2" else None,
    )

    database = FootballDatabase()
    database.log_scrape("understat", "ENG-Premier League", "2324", 1, "success")

    assert fake_connection.commits > 0
    assert fake_connection.cursor_obj.executed
    assert "%s" in fake_connection.cursor_obj.executed[0][0]
    database.close()
    assert fake_connection.closed
    monkeypatch.delenv("ML_IN_SPORTS_DATABASE_URL", raising=False)
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# C1: INSERT OR REPLACE -> ON CONFLICT translation
# ---------------------------------------------------------------------------


class TestUniqueColumns:
    """Tests for _unique_columns() extraction from DDL."""

    @pytest.mark.parametrize(
        ("table", "expected"),
        [
            ("matches", ["league", "season", "game"]),
            ("player_matches", ["league", "season", "game", "team", "player"]),
            ("league_tables", ["league", "season", "team"]),
            ("elo_ratings", ["team", "date"]),
            ("fifa_ratings", ["player_name", "club_name", "fifa_version"]),
            ("tm_players", ["player_id"]),
            ("tm_player_valuations", ["player_id", "date"]),
            ("tm_games", ["game_id"]),
            ("match_odds", ["league", "season", "game"]),
            ("shots", ["shot_id"]),
            ("scrape_log", ["source", "league", "season"]),
        ],
    )
    def test_extracts_unique_columns_for_each_table(
        self, table: str, expected: list[str],
    ) -> None:
        """Every table in _TABLES_SQL has the expected UNIQUE columns."""
        assert _unique_columns(table) == expected

    def test_unknown_table_returns_empty(self) -> None:
        """Unknown table name yields empty list."""
        assert _unique_columns("nonexistent_table") == []


class TestConvertInsertOrReplace:
    """Tests for _convert_insert_or_replace()."""

    def test_scrape_log_translation(self) -> None:
        """The exact SQL used in log_scrape() translates correctly."""
        sql = (
            "INSERT OR REPLACE INTO scrape_log "
            "(source, league, season, scraped_at, row_count, status) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        result = _convert_insert_or_replace(sql)
        assert "INSERT OR REPLACE" not in result
        assert "INSERT INTO scrape_log" in result
        assert "ON CONFLICT (source, league, season)" in result
        assert "DO UPDATE SET" in result
        assert "scraped_at = EXCLUDED.scraped_at" in result
        assert "row_count = EXCLUDED.row_count" in result
        assert "status = EXCLUDED.status" in result
        # Conflict columns must NOT appear in SET clause
        assert "source = EXCLUDED.source" not in result
        assert "league = EXCLUDED.league" not in result
        assert "season = EXCLUDED.season" not in result

    def test_no_match_falls_back_to_plain_insert(self) -> None:
        """Malformed INSERT OR REPLACE without INTO is returned as-is."""
        sql = "INSERT OR REPLACE VALUES (%s)"
        result = _convert_insert_or_replace(sql)
        # Cannot determine table name, so returned unchanged
        assert result == sql

    def test_missing_into_keyword_with_table(self) -> None:
        """INSERT OR REPLACE INTO with known table but missing columns list."""
        sql = "INSERT OR REPLACE INTO scrape_log VALUES (%s, %s, %s)"
        result = _convert_insert_or_replace(sql)
        # No column-list match -> plain INSERT (no ON CONFLICT appended)
        assert result == "INSERT INTO scrape_log VALUES (%s, %s, %s)"

    def test_table_without_unique_constraint(self) -> None:
        """A hypothetical table with no UNIQUE gives a plain INSERT."""
        sql = (
            "INSERT OR REPLACE INTO unknown_table (a, b) VALUES (%s, %s)"
        )
        result = _convert_insert_or_replace(sql)
        assert result == "INSERT INTO unknown_table (a, b) VALUES (%s, %s)"

    def test_single_unique_column(self) -> None:
        """Table with one UNIQUE column (e.g. tm_players by player_id)."""
        sql = (
            "INSERT OR REPLACE INTO tm_players "
            "(player_id, name, position) VALUES (%s, %s, %s)"
        )
        result = _convert_insert_or_replace(sql)
        assert "ON CONFLICT (player_id)" in result
        assert "name = EXCLUDED.name" in result
        assert "position = EXCLUDED.position" in result
        assert "player_id = EXCLUDED.player_id" not in result


class TestAdaptSqlPostgres:
    """Tests for _adapt_sql() Postgres path, including INSERT OR REPLACE."""

    @pytest.fixture
    def pg_db(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> FootballDatabase:
        """Create a FootballDatabase in Postgres mode (no real connection)."""
        fake_conn = _FakePostgresConnection()
        fake_psycopg2 = _FakePsycopg2(fake_conn)
        monkeypatch.setenv(
            "ML_IN_SPORTS_DATABASE_URL",
            "postgresql://user:pass@localhost:5432/db",
        )
        get_settings.cache_clear()
        monkeypatch.setattr(
            "ml_in_sports.utils.database.import_module",
            lambda name: fake_psycopg2 if name == "psycopg2" else None,
        )
        database = FootballDatabase()
        yield database
        database.close()
        monkeypatch.delenv("ML_IN_SPORTS_DATABASE_URL", raising=False)
        get_settings.cache_clear()

    def test_log_scrape_no_insert_or_replace(
        self, pg_db: FootballDatabase,
    ) -> None:
        """log_scrape on Postgres must not emit INSERT OR REPLACE."""
        pg_db.log_scrape("understat", "ENG-Premier League", "2324", 1, "ok")
        executed_sql = pg_db.connection.cursor_obj.executed[0][0]
        assert "INSERT OR REPLACE" not in executed_sql
        assert "ON CONFLICT" in executed_sql

    def test_create_tables_no_autoincrement(
        self, pg_db: FootballDatabase,
    ) -> None:
        """CREATE TABLE on Postgres must not contain AUTOINCREMENT."""
        pg_db.create_tables()
        for sql, _params in pg_db.connection.cursor_obj.executed:
            assert "AUTOINCREMENT" not in sql, (
                f"AUTOINCREMENT found in Postgres DDL: {sql[:80]}..."
            )

    def test_placeholder_replacement(
        self, pg_db: FootballDatabase,
    ) -> None:
        """Question-mark placeholders become %s."""
        adapted = pg_db._adapt_sql("SELECT * FROM t WHERE a = ? AND b = ?")
        assert "?" not in adapted
        assert "%s" in adapted

    def test_sqlite_mode_returns_sql_unchanged(
        self, db: FootballDatabase,
    ) -> None:
        """SQLite backend returns SQL as-is."""
        original = "INSERT OR REPLACE INTO scrape_log (a) VALUES (?)"
        assert db._adapt_sql(original) == original

"""SQLite database for persistent football data storage.

Stores scraped data so it only needs to be fetched once.
Uses UPSERT (INSERT OR REPLACE) to handle re-runs gracefully.
"""

import sqlite3
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

import pandas as pd
import structlog

from ml_in_sports.settings import get_settings

logger = structlog.get_logger(__name__)


def _default_db_path() -> Path:
    """Resolve the database path from settings at call time."""
    return get_settings().db_path

_TABLES_SQL = {
    "matches": """
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league TEXT NOT NULL,
            season TEXT NOT NULL,
            game TEXT NOT NULL,
            date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_goals INTEGER,
            away_goals INTEGER,
            home_xg REAL,
            away_xg REAL,
            home_np_xg REAL,
            away_np_xg REAL,
            home_expected_points REAL,
            away_expected_points REAL,
            home_ppda REAL,
            away_ppda REAL,
            home_deep_completions INTEGER,
            away_deep_completions INTEGER,
            home_possession REAL,
            away_possession REAL,
            home_total_shots INTEGER,
            away_total_shots INTEGER,
            home_shots_on_target INTEGER,
            away_shots_on_target INTEGER,
            home_effective_tackles INTEGER,
            away_effective_tackles INTEGER,
            home_total_tackles INTEGER,
            away_total_tackles INTEGER,
            home_accurate_passes INTEGER,
            away_accurate_passes INTEGER,
            home_total_passes INTEGER,
            away_total_passes INTEGER,
            home_accurate_crosses INTEGER,
            away_accurate_crosses INTEGER,
            home_effective_clearance INTEGER,
            away_effective_clearance INTEGER,
            home_interceptions INTEGER,
            away_interceptions INTEGER,
            home_saves INTEGER,
            away_saves INTEGER,
            home_fouls INTEGER,
            away_fouls INTEGER,
            home_yellow_cards INTEGER,
            away_yellow_cards INTEGER,
            home_red_cards INTEGER,
            away_red_cards INTEGER,
            home_won_corners INTEGER,
            away_won_corners INTEGER,
            home_offsides INTEGER,
            away_offsides INTEGER,
            home_blocked_shots INTEGER,
            away_blocked_shots INTEGER,
            home_total_crosses INTEGER,
            away_total_crosses INTEGER,
            home_total_long_balls INTEGER,
            away_total_long_balls INTEGER,
            home_accurate_long_balls INTEGER,
            away_accurate_long_balls INTEGER,
            home_total_clearance INTEGER,
            away_total_clearance INTEGER,
            home_penalty_kick_goals INTEGER,
            away_penalty_kick_goals INTEGER,
            home_penalty_kick_shots INTEGER,
            away_penalty_kick_shots INTEGER,
            home_attendance INTEGER,
            away_attendance INTEGER,
            round INTEGER,
            week INTEGER,
            home_elo REAL,
            away_elo REAL,
            source_updated_at TEXT,
            UNIQUE(league, season, game)
        )
    """,
    "player_matches": """
        CREATE TABLE IF NOT EXISTS player_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league TEXT NOT NULL,
            season TEXT NOT NULL,
            game TEXT NOT NULL,
            team TEXT NOT NULL,
            player TEXT NOT NULL,
            position TEXT,
            minutes INTEGER,
            goals INTEGER,
            shots INTEGER,
            xg REAL,
            xa REAL,
            key_passes INTEGER,
            xg_chain REAL,
            xg_buildup REAL,
            own_goals INTEGER,
            assists INTEGER,
            fouls_committed INTEGER,
            fouls_suffered INTEGER,
            saves INTEGER,
            offsides INTEGER,
            total_shots_espn INTEGER,
            shots_on_target_espn INTEGER,
            sub_in INTEGER,
            sub_out INTEGER,
            yellow_cards INTEGER,
            red_cards INTEGER,
            source_updated_at TEXT,
            UNIQUE(league, season, game, team, player)
        )
    """,
    "league_tables": """
        CREATE TABLE IF NOT EXISTS league_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league TEXT NOT NULL,
            season TEXT NOT NULL,
            team TEXT NOT NULL,
            matches_played INTEGER,
            wins INTEGER,
            draws INTEGER,
            losses INTEGER,
            goals_for INTEGER,
            goals_against INTEGER,
            goal_difference INTEGER,
            points INTEGER,
            UNIQUE(league, season, team)
        )
    """,
    "elo_ratings": """
        CREATE TABLE IF NOT EXISTS elo_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT NOT NULL,
            date TEXT NOT NULL,
            elo REAL,
            rank INTEGER,
            country TEXT,
            league TEXT,
            UNIQUE(team, date)
        )
    """,
    "fifa_ratings": """
        CREATE TABLE IF NOT EXISTS fifa_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            long_name TEXT,
            age INTEGER,
            nationality TEXT,
            club_name TEXT,
            league_name TEXT,
            overall INTEGER,
            potential INTEGER,
            value_eur INTEGER,
            wage_eur INTEGER,
            preferred_foot TEXT,
            height_cm INTEGER,
            weight_kg INTEGER,
            positions TEXT,
            pace INTEGER,
            shooting INTEGER,
            passing INTEGER,
            dribbling INTEGER,
            defending INTEGER,
            physic INTEGER,
            skill_moves INTEGER,
            weak_foot INTEGER,
            fifa_version TEXT,
            source_updated_at TEXT,
            UNIQUE(player_name, club_name, fifa_version)
        )
    """,
    "tm_players": """
        CREATE TABLE IF NOT EXISTS tm_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            name TEXT,
            first_name TEXT,
            last_name TEXT,
            position TEXT,
            sub_position TEXT,
            foot TEXT,
            height_in_cm REAL,
            date_of_birth TEXT,
            country_of_citizenship TEXT,
            current_club_id INTEGER,
            current_club_name TEXT,
            market_value_in_eur INTEGER,
            highest_market_value_in_eur INTEGER,
            contract_expiration_date TEXT,
            source_updated_at TEXT,
            UNIQUE(player_id)
        )
    """,
    "tm_player_valuations": """
        CREATE TABLE IF NOT EXISTS tm_player_valuations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            market_value_in_eur INTEGER,
            current_club_id INTEGER,
            current_club_name TEXT,
            source_updated_at TEXT,
            UNIQUE(player_id, date)
        )
    """,
    "tm_games": """
        CREATE TABLE IF NOT EXISTS tm_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            competition_id TEXT,
            season TEXT,
            round TEXT,
            date TEXT,
            home_club_id INTEGER,
            away_club_id INTEGER,
            home_club_name TEXT,
            away_club_name TEXT,
            home_club_goals INTEGER,
            away_club_goals INTEGER,
            home_club_manager_name TEXT,
            away_club_manager_name TEXT,
            stadium TEXT,
            attendance INTEGER,
            referee TEXT,
            home_club_formation TEXT,
            away_club_formation TEXT,
            source_updated_at TEXT,
            UNIQUE(game_id)
        )
    """,
    "match_odds": """
        CREATE TABLE IF NOT EXISTS match_odds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league TEXT NOT NULL,
            season TEXT NOT NULL,
            game TEXT NOT NULL,
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            ft_home_goals INTEGER,
            ft_away_goals INTEGER,
            ft_result TEXT,
            ht_home_goals INTEGER,
            ht_away_goals INTEGER,
            ht_result TEXT,
            referee TEXT,
            home_shots INTEGER,
            away_shots INTEGER,
            home_shots_on_target INTEGER,
            away_shots_on_target INTEGER,
            home_fouls INTEGER,
            away_fouls INTEGER,
            home_corners INTEGER,
            away_corners INTEGER,
            home_yellow_cards INTEGER,
            away_yellow_cards INTEGER,
            home_red_cards INTEGER,
            away_red_cards INTEGER,
            b365_home REAL,
            b365_draw REAL,
            b365_away REAL,
            bw_home REAL,
            bw_draw REAL,
            bw_away REAL,
            iw_home REAL,
            iw_draw REAL,
            iw_away REAL,
            ps_home REAL,
            ps_draw REAL,
            ps_away REAL,
            wh_home REAL,
            wh_draw REAL,
            wh_away REAL,
            vc_home REAL,
            vc_draw REAL,
            vc_away REAL,
            max_home REAL,
            max_draw REAL,
            max_away REAL,
            avg_home REAL,
            avg_draw REAL,
            avg_away REAL,
            b365_over_25 REAL,
            b365_under_25 REAL,
            ps_over_25 REAL,
            ps_under_25 REAL,
            max_over_25 REAL,
            max_under_25 REAL,
            avg_over_25 REAL,
            avg_under_25 REAL,
            ah_handicap REAL,
            b365_ah_home REAL,
            b365_ah_away REAL,
            ps_ah_home REAL,
            ps_ah_away REAL,
            max_ah_home REAL,
            max_ah_away REAL,
            avg_ah_home REAL,
            avg_ah_away REAL,
            b365c_home REAL,
            b365c_draw REAL,
            b365c_away REAL,
            bwc_home REAL,
            bwc_draw REAL,
            bwc_away REAL,
            iwc_home REAL,
            iwc_draw REAL,
            iwc_away REAL,
            psc_home REAL,
            psc_draw REAL,
            psc_away REAL,
            whc_home REAL,
            whc_draw REAL,
            whc_away REAL,
            vcc_home REAL,
            vcc_draw REAL,
            vcc_away REAL,
            maxc_home REAL,
            maxc_draw REAL,
            maxc_away REAL,
            avgc_home REAL,
            avgc_draw REAL,
            avgc_away REAL,
            b365c_over_25 REAL,
            b365c_under_25 REAL,
            psc_over_25 REAL,
            psc_under_25 REAL,
            maxc_over_25 REAL,
            maxc_under_25 REAL,
            avgc_over_25 REAL,
            avgc_under_25 REAL,
            ahc_handicap REAL,
            b365c_ah_home REAL,
            b365c_ah_away REAL,
            psc_ah_home REAL,
            psc_ah_away REAL,
            maxc_ah_home REAL,
            maxc_ah_away REAL,
            avgc_ah_home REAL,
            avgc_ah_away REAL,
            source_updated_at TEXT,
            UNIQUE(league, season, game)
        )
    """,
    "shots": """
        CREATE TABLE IF NOT EXISTS shots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league TEXT NOT NULL,
            season TEXT NOT NULL,
            game TEXT NOT NULL,
            team TEXT NOT NULL,
            player TEXT NOT NULL,
            shot_id INTEGER NOT NULL,
            date TEXT,
            xg REAL,
            location_x REAL,
            location_y REAL,
            minute INTEGER,
            body_part TEXT,
            situation TEXT,
            result TEXT,
            assist_player TEXT,
            player_id INTEGER,
            assist_player_id INTEGER,
            source_updated_at TEXT,
            UNIQUE(shot_id)
        )
    """,
    "scrape_log": """
        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            league TEXT,
            season TEXT,
            scraped_at TEXT NOT NULL,
            row_count INTEGER,
            status TEXT NOT NULL,
            UNIQUE(source, league, season)
        )
    """,
}


_VALID_TABLES: frozenset[str] = frozenset(_TABLES_SQL.keys())


def _validate_table_name(table: str) -> None:
    """Validate that table name is in the known set.

    Args:
        table: Table name to validate.

    Raises:
        ValueError: If table name is not in the known set.
    """
    if table not in _VALID_TABLES:
        raise ValueError(
            f"Unknown table '{table}'. "
            f"Valid tables: {sorted(_VALID_TABLES)}"
        )


class FootballDatabase:
    """SQLite database for football data storage.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        settings = get_settings()
        self._database_url = settings.database_url
        self._is_postgres = bool(self._database_url)
        self._connection: Any | None = None

        if self._is_postgres:
            self._db_path: Path | None = None
        else:
            if db_path is None:
                db_path = _default_db_path()
            self._db_path = Path(db_path)
            self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "FootballDatabase":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object) -> None:
        """Exit context manager and close connection."""
        self.close()

    @property
    def connection(self) -> Any:
        """Lazy connection to the configured database."""
        if self._connection is None:
            if self._is_postgres:
                psycopg2 = import_module("psycopg2")
                self._connection = psycopg2.connect(self._database_url)
            else:
                if self._db_path is None:
                    raise RuntimeError("SQLite db_path is not configured")
                self._connection = sqlite3.connect(str(self._db_path))
                self._connection.row_factory = sqlite3.Row
        return self._connection

    def create_tables(self) -> None:
        """Create all tables if they don't exist."""
        for table_name, sql in _TABLES_SQL.items():
            self._execute(sql)
            logger.info(f"Ensured table exists: {table_name}")
        self._commit()

    def upsert_dataframe(
        self, table: str, df: pd.DataFrame,
    ) -> int:
        """Insert or replace rows from a DataFrame into a table.

        Args:
            table: Target table name.
            df: DataFrame with columns matching the table schema.

        Returns:
            Number of rows upserted.
        """
        if df.empty:
            return 0

        _validate_table_name(table)

        prepared = df.copy()
        for col in prepared.columns:
            if pd.api.types.is_datetime64_any_dtype(prepared[col]):
                prepared[col] = prepared[col].dt.strftime("%Y-%m-%d %H:%M:%S")

        columns = prepared.columns.tolist()
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        if self._is_postgres:
            sql = _postgres_upsert_sql(table, columns, placeholders)
        else:
            sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"

        for col in prepared.columns:
            if pd.api.types.is_extension_array_dtype(prepared[col]):
                prepared[col] = prepared[col].astype(object)
        rows = prepared.where(prepared.notna(), None).values.tolist()  # type: ignore[call-overload]  # pandas-stubs: None is valid at runtime
        self._executemany(sql, rows)
        self._commit()

        logger.info(f"Upserted {len(rows)} rows into {table}")
        return len(rows)

    def read_table(
        self, table: str, league: str | None = None,
        season: str | None = None,
    ) -> pd.DataFrame:
        """Read data from a table with optional filters.

        Args:
            table: Table name to query.
            league: Filter by league.
            season: Filter by season.

        Returns:
            DataFrame with query results.
        """
        _validate_table_name(table)

        query = f"SELECT * FROM {table}"
        params: list[str] = []
        conditions: list[str] = []

        if league:
            conditions.append("league = ?")
            params.append(league)
        if season:
            conditions.append("season = ?")
            params.append(season)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query = self._adapt_sql(query)
        return pd.read_sql_query(query, self.connection, params=params)  # type: ignore[arg-type]  # pandas-stubs: list[str] is invariant but safe here

    def is_scraped(self, source: str, league: str, season: str) -> bool:
        """Check if a source/league/season was already scraped successfully.

        Args:
            source: Data source name.
            league: League identifier.
            season: Season code.

        Returns:
            True if already scraped with status 'success'.
        """
        cursor = self._execute(
            "SELECT status FROM scrape_log "
            "WHERE source = ? AND league = ? AND season = ?",
            (source, league, season),
        )
        row = cursor.fetchone()
        if row is None:
            return False
        status = row["status"] if isinstance(row, sqlite3.Row) else row[0]
        return str(status) == "success"

    def log_scrape(
        self, source: str, league: str, season: str,
        row_count: int, status: str,
    ) -> None:
        """Log a scraping operation to scrape_log.

        Args:
            source: Data source name.
            league: League identifier.
            season: Season code.
            row_count: Number of rows scraped.
            status: Result status ('success', 'failed', 'partial').
        """
        now = datetime.now(UTC).isoformat()
        self._execute(
            "INSERT OR REPLACE INTO scrape_log "
            "(source, league, season, scraped_at, row_count, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (source, league, season, now, row_count, status),
        )
        self._commit()

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        """Execute SQL on either SQLite or Postgres."""
        if self._is_postgres:
            cursor = self.connection.cursor()
            cursor.execute(self._adapt_sql(sql), params)
            self._commit()
            return cursor
        return self.connection.execute(sql, params)

    def _executemany(self, sql: str, rows: list[list[Any]]) -> Any:
        """Execute a batch insert/update on either SQLite or Postgres."""
        if self._is_postgres:
            cursor = self.connection.cursor()
            cursor.executemany(self._adapt_sql(sql), rows)
            self._commit()
            return cursor
        return self.connection.executemany(sql, rows)

    def _adapt_sql(self, sql: str) -> str:
        """Adapt SQLite-style SQL to the active backend."""
        if not self._is_postgres:
            return sql
        adapted = sql.replace("?", "%s")
        adapted = adapted.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        return adapted

    def _commit(self) -> None:
        """Commit the active connection."""
        self.connection.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None


def _postgres_upsert_sql(table: str, columns: list[str], placeholders: str) -> str:
    """Build a simple Postgres upsert statement for a known table."""
    col_names = ", ".join(columns)
    conflict_cols = _unique_columns(table)
    if not conflict_cols:
        return f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    conflict_target = ", ".join(conflict_cols)
    update_cols = [col for col in columns if col not in conflict_cols and col != "id"]
    if not update_cols:
        return (
            f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_target}) DO NOTHING"
        )
    updates = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_cols)
    return (
        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT ({conflict_target}) DO UPDATE SET {updates}"
    )


def _unique_columns(table: str) -> list[str]:
    """Return the first UNIQUE column group from a table DDL statement."""
    sql = _TABLES_SQL.get(table, "")
    marker = "UNIQUE("
    start = sql.find(marker)
    if start == -1:
        return []
    start += len(marker)
    end = sql.find(")", start)
    if end == -1:
        return []
    return [col.strip() for col in sql[start:end].split(",")]

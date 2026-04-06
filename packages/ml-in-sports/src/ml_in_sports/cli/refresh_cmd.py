"""CLI command: refresh current season data.

Wraps the research script ``scripts/refresh_current_season.py`` using
production imports from ``ml_in_sports.processing.pipeline``.
"""

import time
from typing import Annotated

import structlog
import typer

from ml_in_sports.processing.extractors import ALL_LEAGUES
from ml_in_sports.processing.pipeline import (
    build_fifa_ratings,
    build_match_base,
    build_odds_dataset,
    build_player_base,
    build_shot_dataset,
    build_transfermarkt_datasets,
    enrich_matches_espn,
    enrich_players_espn,
)
from ml_in_sports.utils.database import FootballDatabase
from ml_in_sports.utils.seasons import current_season_code

logger = structlog.get_logger(__name__)

refresh_app = typer.Typer(no_args_is_help=True)


def _clear_scrape_log(
    db: FootballDatabase,
    season: str,
    leagues: list[str],
) -> int:
    """Delete scrape_log entries for the season so data gets re-fetched.

    Clears per-season entries (Understat, ESPN, etc.) and also
    Transfermarkt (season='all') and FIFA (season=version) so
    they get re-downloaded when new data is available.
    """
    conn = db.connection
    total = 0

    cursor = conn.execute(
        "DELETE FROM scrape_log WHERE season = ?",
        (season,),
    )
    total += cursor.rowcount

    for league in leagues:
        cursor = conn.execute(
            "DELETE FROM scrape_log WHERE source LIKE 'transfermarkt%' AND league = ?",
            (league,),
        )
        total += cursor.rowcount

    cursor = conn.execute(
        "DELETE FROM scrape_log WHERE source = 'fifa_ratings'",
    )
    total += cursor.rowcount

    conn.commit()
    logger.info("scrape_log_cleared", deleted_count=total)
    return total


def _run_refresh(
    leagues: list[str],
    season: str,
    db: FootballDatabase,
) -> None:
    """Run the full pipeline for the given leagues and season."""
    logger.info(
        "refresh_pipeline_start",
        league_count=len(leagues),
        season=season,
    )

    for league in leagues:
        start = time.monotonic()
        logger.info("refresh_league_start", league=league, season=season)

        build_match_base(league, season, db)
        build_player_base(league, season, db)
        build_shot_dataset(league, season, db)
        build_odds_dataset(league, season, db)
        enrich_matches_espn(league, season, db)
        enrich_players_espn(league, season, db)

        elapsed = time.monotonic() - start
        logger.info(
            "refresh_league_done",
            league=league,
            season=season,
            elapsed_s=round(elapsed, 1),
        )

    logger.info("refresh_transfermarkt_start")
    for league in leagues:
        start = time.monotonic()
        build_transfermarkt_datasets(league, db)
        elapsed = time.monotonic() - start
        logger.info(
            "transfermarkt_league_done",
            league=league,
            elapsed_s=round(elapsed, 1),
        )

    logger.info("refresh_fifa_start")
    start = time.monotonic()
    build_fifa_ratings(db, leagues=leagues)
    elapsed = time.monotonic() - start
    logger.info("fifa_ratings_done", elapsed_s=round(elapsed, 1))


def _log_table_counts(db: FootballDatabase, season: str) -> None:
    """Log row counts per table for the given season."""
    tables = [
        "matches",
        "player_matches",
        "shots",
        "match_odds",
        "scrape_log",
    ]
    for table in tables:
        df = db.read_table(table, season=season)
        logger.info(
            "season_table_count",
            table=table,
            season=season,
            row_count=len(df),
        )


@refresh_app.command("run")
def run(
    leagues: Annotated[
        list[str] | None,
        typer.Option("--leagues", help="Specific leagues to refresh (default: all)."),
    ] = None,
) -> None:
    """Refresh current season data by clearing scrape_log and re-running."""
    season = current_season_code()
    resolved_leagues = leagues if leagues else list(ALL_LEAGUES)

    logger.info(
        "refresh_start",
        season=season,
        leagues=resolved_leagues,
    )

    with FootballDatabase() as db:
        db.create_tables()

        total_start = time.monotonic()

        _clear_scrape_log(db, season, resolved_leagues)
        _run_refresh(resolved_leagues, season, db)

        total_elapsed = time.monotonic() - total_start
        logger.info("refresh_complete", elapsed_s=round(total_elapsed, 1))
        _log_table_counts(db, season)

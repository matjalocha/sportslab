"""CLI command: run the data pipeline for football leagues.

Wraps the research script ``scripts/run_pipeline.py`` using
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
from ml_in_sports.utils.seasons import all_season_codes

logger = structlog.get_logger(__name__)

pipeline_app = typer.Typer(no_args_is_help=True)


def _run_base_pipeline(
    leagues: list[str],
    seasons: list[str],
    db: FootballDatabase,
) -> None:
    """Run fast-pass pipeline for all league/season combinations."""
    total = len(leagues) * len(seasons)
    logger.info(
        "base_pipeline_start",
        league_count=len(leagues),
        season_count=len(seasons),
        total_combos=total,
    )

    for league in leagues:
        for season in seasons:
            start = time.monotonic()
            logger.info("base_step_start", league=league, season=season)

            matches = build_match_base(league, season, db)
            players = build_player_base(league, season, db)
            shots = build_shot_dataset(league, season, db)
            odds = build_odds_dataset(league, season, db)

            counts = {
                "matches": len(matches) if matches is not None else 0,
                "players": len(players) if players is not None else 0,
                "shots": len(shots) if shots is not None else 0,
                "odds": len(odds) if odds is not None else 0,
            }
            elapsed = time.monotonic() - start
            logger.info(
                "base_step_done",
                league=league,
                season=season,
                elapsed_s=round(elapsed, 1),
                **counts,
            )


def _run_espn_enrichment(
    leagues: list[str],
    seasons: list[str],
    db: FootballDatabase,
) -> None:
    """Run ESPN enrichment for all league/season combinations."""
    total = len(leagues) * len(seasons)
    logger.info("espn_enrichment_start", total_combos=total)

    for league in leagues:
        for season in seasons:
            start = time.monotonic()
            logger.info("espn_step_start", league=league, season=season)

            enrich_matches_espn(league, season, db)
            enrich_players_espn(league, season, db)

            elapsed = time.monotonic() - start
            logger.info(
                "espn_step_done",
                league=league,
                season=season,
                elapsed_s=round(elapsed, 1),
            )


def _run_transfermarkt(
    leagues: list[str],
    db: FootballDatabase,
) -> None:
    """Run Transfermarkt bulk download for each league."""
    logger.info("transfermarkt_start", league_count=len(leagues))

    for league in leagues:
        start = time.monotonic()
        tm_results = build_transfermarkt_datasets(league, db)
        for table_name, df in tm_results.items():
            count = len(df) if df is not None else 0
            logger.info(
                "transfermarkt_table",
                league=league,
                table=table_name,
                row_count=count,
            )
        elapsed = time.monotonic() - start
        logger.info(
            "transfermarkt_league_done",
            league=league,
            elapsed_s=round(elapsed, 1),
        )


def _run_fifa_ratings(
    leagues: list[str],
    db: FootballDatabase,
) -> None:
    """Load FIFA ratings for all configured leagues."""
    logger.info("fifa_ratings_start")
    start = time.monotonic()

    fifa_results = build_fifa_ratings(db, leagues=leagues)
    for version, df in fifa_results.items():
        count = len(df) if df is not None else 0
        logger.info("fifa_version", version=version, player_count=count)

    elapsed = time.monotonic() - start
    logger.info("fifa_ratings_done", elapsed_s=round(elapsed, 1))


def _log_summary(db: FootballDatabase) -> None:
    """Log row counts for all tables."""
    tables = [
        "matches",
        "player_matches",
        "shots",
        "match_odds",
        "fifa_ratings",
        "tm_players",
        "tm_player_valuations",
        "tm_games",
        "elo_ratings",
        "league_tables",
        "scrape_log",
    ]
    for table in tables:
        df = db.read_table(table)
        logger.info("table_summary", table=table, row_count=len(df))


@pipeline_app.command("run")
def run(
    fast: Annotated[
        bool,
        typer.Option("--fast", help="Skip ESPN enrichment (fast sources only)."),
    ] = False,
    seasons: Annotated[
        list[str] | None,
        typer.Option("--seasons", help="Season codes to process (e.g. 2324)."),
    ] = None,
    leagues: Annotated[
        list[str] | None,
        typer.Option("--leagues", help="League identifiers to process."),
    ] = None,
) -> None:
    """Run the full data pipeline for selected leagues and seasons."""
    resolved_seasons = seasons if seasons else all_season_codes()
    resolved_leagues = leagues if leagues else list(ALL_LEAGUES)

    with FootballDatabase() as db:
        db.create_tables()

        total_start = time.monotonic()

        _run_base_pipeline(resolved_leagues, resolved_seasons, db)
        _run_transfermarkt(resolved_leagues, db)
        _run_fifa_ratings(resolved_leagues, db)

        if not fast:
            _run_espn_enrichment(
                resolved_leagues,
                resolved_seasons,
                db,
            )

        total_elapsed = time.monotonic() - total_start
        logger.info("pipeline_complete", elapsed_s=round(total_elapsed, 1))
        _log_summary(db)

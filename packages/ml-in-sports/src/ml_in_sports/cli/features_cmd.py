"""CLI command: materialize features to Parquet.

Wraps the research script ``scripts/materialize_features.py`` using
production imports from ``ml_in_sports.features``.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import pandas as pd
import structlog
import typer

from ml_in_sports.features.betting_features import add_betting_features
from ml_in_sports.features.build_features import build_master_dataframe
from ml_in_sports.features.contextual_features import add_contextual_features
from ml_in_sports.features.derived_features import add_derived_features
from ml_in_sports.features.form_features import add_form_features
from ml_in_sports.features.formation_features import add_formation_features
from ml_in_sports.features.match_player_quality import add_match_player_quality
from ml_in_sports.features.new_features import add_new_features
from ml_in_sports.features.player_rolling_features import (
    add_player_rolling_features,
)
from ml_in_sports.features.rolling_features import add_rolling_features
from ml_in_sports.features.setpiece_features import add_setpiece_features
from ml_in_sports.features.tactical_features import add_tactical_features
from ml_in_sports.features.targets import add_all_targets
from ml_in_sports.utils.database import FootballDatabase

logger = structlog.get_logger(__name__)

features_app = typer.Typer(no_args_is_help=True)


def _get_leagues_and_seasons(
    db: FootballDatabase,
) -> dict[str, list[str]]:
    """Query all leagues with their seasons from the matches table."""
    query = "SELECT DISTINCT league, season FROM matches ORDER BY league, season"
    rows = pd.read_sql_query(query, db.connection)
    result: dict[str, list[str]] = {}
    for league, season in rows.itertuples(index=False, name=None):
        result.setdefault(league, []).append(season)
    return result


def _build_league_master(
    league: str,
    seasons: list[str],
    db: FootballDatabase,
) -> tuple[pd.DataFrame, list[str]]:
    """Build and concatenate master DataFrames for one league."""
    frames: list[pd.DataFrame] = []
    skipped: list[str] = []

    for season in seasons:
        try:
            df = build_master_dataframe(league, season, db)
            if df.empty:
                skipped.append(f"{league} {season} (empty)")
                continue
            frames.append(df)
        except Exception as exc:
            logger.warning(
                "master_df_failed",
                league=league,
                season=season,
                error=str(exc),
            )
            skipped.append(f"{league} {season} ({exc})")

    if not frames:
        return pd.DataFrame(), skipped

    combined = pd.concat(frames, ignore_index=True)
    return combined, skipped


def _load_league_tables(
    db: FootballDatabase,
    league: str,
) -> dict[str, pd.DataFrame]:
    """Load heavy tables from DB filtered to a single league."""
    logger.info("loading_league_tables", league=league)
    league_filtered = ("player_matches", "shots", "matches")
    result: dict[str, pd.DataFrame] = {}
    for name in league_filtered:
        result[name] = db.read_table(name, league=league)
        logger.info("table_loaded", table=name, row_count=len(result[name]))
    result["tm_games"] = db.read_table("tm_games")
    logger.info("table_loaded", table="tm_games", row_count=len(result["tm_games"]))
    return result


def _run_feature_pipeline(
    df: pd.DataFrame,
    db: FootballDatabase,
    league_tables: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Run all feature modules and targets on a DataFrame."""
    pm = league_tables["player_matches"]
    shots = league_tables["shots"]
    matches = league_tables["matches"]
    tm_games = league_tables["tm_games"]

    df = add_rolling_features(df)
    df = add_tactical_features(df)
    df = add_form_features(df, db, shots_df=shots, player_matches_df=pm)
    df = add_contextual_features(df)
    df = add_betting_features(df)
    df = add_match_player_quality(df, db, player_matches_df=pm)
    df = add_player_rolling_features(df, db, player_matches_df=pm)
    df = add_setpiece_features(df, db, shots_df=shots, matches_df=matches)
    df = add_formation_features(df, tm_games_df=tm_games)
    df = add_derived_features(df)
    df = add_all_targets(df)
    return df


def _save_metadata(
    output_dir: Path,
    total_df: pd.DataFrame,
    skipped: list[str],
) -> None:
    """Save metadata JSON alongside the Parquet file."""
    metadata_path = output_dir / "metadata.json"
    metadata = {
        "timestamp": datetime.now(UTC).isoformat(),
        "row_count": len(total_df),
        "column_count": len(total_df.columns),
        "leagues": sorted(total_df["league"].unique().tolist()),
        "seasons": sorted(total_df["season"].unique().tolist()),
        "skipped_combos": skipped,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("metadata_saved", path=str(metadata_path))


@features_app.command("build")
def build(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            help="Output Parquet path.",
        ),
    ] = Path("data/features/all_features.parquet"),
    leagues: Annotated[
        list[str] | None,
        typer.Option("--leagues", help="Specific leagues (default: all in DB)."),
    ] = None,
) -> None:
    """Materialize all features for every league-season combo."""
    output_dir = output.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    all_frames: list[pd.DataFrame] = []
    all_skipped: list[str] = []

    with FootballDatabase() as db:
        league_seasons = _get_leagues_and_seasons(db)

        if leagues:
            league_seasons = {
                league: seasons for league, seasons in league_seasons.items() if league in leagues
            }

        total_combos = sum(len(s) for s in league_seasons.values())
        logger.info(
            "feature_build_start",
            league_count=len(league_seasons),
            total_combos=total_combos,
        )

        for league, seasons in league_seasons.items():
            logger.info(
                "building_league",
                league=league,
                season_count=len(seasons),
            )

            league_df, skipped = _build_league_master(league, seasons, db)
            all_skipped.extend(skipped)

            if league_df.empty:
                logger.warning("league_empty", league=league)
                continue

            logger.info(
                "league_master_built",
                league=league,
                row_count=len(league_df),
            )

            league_tables = _load_league_tables(db, league)

            try:
                featured = _run_feature_pipeline(league_df, db, league_tables)
                all_frames.append(featured)
                logger.info(
                    "league_features_done",
                    league=league,
                    rows=len(featured),
                    cols=len(featured.columns),
                )
            except Exception as exc:
                logger.warning(
                    "feature_pipeline_failed",
                    league=league,
                    error=str(exc),
                )
                all_skipped.append(f"{league} (pipeline: {exc})")

    if not all_frames:
        logger.error("no_data_produced")
        raise typer.Exit(code=1)

    total = pd.concat(all_frames, ignore_index=True)
    total = total.sort_values("date").reset_index(drop=True)

    logger.info("adding_new_features")
    total = add_new_features(total)
    logger.info("new_features_added", col_count=len(total.columns))

    total.to_parquet(output, index=False)
    logger.info(
        "parquet_saved",
        path=str(output),
        rows=len(total),
        cols=len(total.columns),
    )

    _save_metadata(output_dir, total, all_skipped)

    if all_skipped:
        logger.warning(
            "combos_skipped",
            count=len(all_skipped),
            details=all_skipped,
        )

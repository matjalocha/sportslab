"""CLI command: update ELO ratings in features parquet.

Fetches ClubElo snapshots, matches them to the features parquet,
computes derived ELO features, and saves the updated parquet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import pandas as pd
import structlog
import typer

from ml_in_sports.processing.elo_integration import (
    compute_elo_features,
    fetch_elo_for_date_range,
    match_elo_to_features,
)

logger = structlog.get_logger(__name__)

elo_app = typer.Typer(no_args_is_help=True)


@elo_app.command("update")
def update(
    parquet_path: Annotated[
        Path,
        typer.Option(
            "--parquet",
            help="Path to features parquet file.",
        ),
    ] = Path("data/features/all_features.parquet"),
    cache_dir: Annotated[
        Path,
        typer.Option(
            "--cache-dir",
            help="Directory for cached ELO CSV snapshots.",
        ),
    ] = Path("data/elo"),
    step_days: Annotated[
        int,
        typer.Option(
            "--step-days",
            help="Days between ELO snapshots.",
        ),
    ] = 7,
    start_date: Annotated[
        str | None,
        typer.Option(
            "--start-date",
            help="Override start date (YYYY-MM-DD). Default: earliest in parquet.",
        ),
    ] = None,
    end_date: Annotated[
        str | None,
        typer.Option(
            "--end-date",
            help="Override end date (YYYY-MM-DD). Default: latest in parquet.",
        ),
    ] = None,
) -> None:
    """Fetch ELO ratings, match to features, compute derived features."""
    logger.info("loading_parquet", path=str(parquet_path))
    features = pd.read_parquet(parquet_path)
    features["date"] = pd.to_datetime(features["date"])
    logger.info(
        "parquet_loaded",
        rows=len(features),
        cols=len(features.columns),
    )

    # Determine date range from parquet if not overridden
    if start_date is None:
        start_date = features["date"].min().strftime("%Y-%m-%d")
    if end_date is None:
        end_date = features["date"].max().strftime("%Y-%m-%d")

    logger.info(
        "fetching_elo_range",
        start=start_date,
        end=end_date,
        step_days=step_days,
    )

    elo_df = fetch_elo_for_date_range(
        start_date=start_date,
        end_date=end_date,
        step_days=step_days,
        cache_dir=cache_dir,
    )

    if elo_df.empty:
        logger.error("no_elo_data_available")
        raise typer.Exit(code=1)

    logger.info("matching_elo_to_features")
    # Drop existing ELO columns to recompute cleanly
    elo_columns_to_drop = [
        c for c in features.columns
        if "elo" in c.lower() and c not in ("home_team", "away_team")
    ]
    if elo_columns_to_drop:
        logger.info(
            "dropping_old_elo_columns",
            columns=elo_columns_to_drop,
        )
        features = features.drop(columns=elo_columns_to_drop)

    features = match_elo_to_features(features, elo_df)

    logger.info("computing_elo_features")
    features = compute_elo_features(features)

    # Report fill rates per league
    _report_fill_rates(features)

    # Save
    features.to_parquet(parquet_path, index=False)
    logger.info(
        "parquet_saved",
        path=str(parquet_path),
        rows=len(features),
        cols=len(features.columns),
    )


def _report_fill_rates(df: pd.DataFrame) -> None:
    """Log ELO fill rate per league."""
    for league in sorted(df["league"].unique()):
        league_df = df[df["league"] == league]
        total = len(league_df)
        both_filled = (
            league_df["home_elo"].notna()
            & league_df["away_elo"].notna()
        ).sum()
        pct = round(both_filled / total * 100, 1) if total > 0 else 0.0
        logger.info(
            "elo_fill_rate",
            league=league,
            filled=int(both_filled),
            total=total,
            pct=pct,
        )

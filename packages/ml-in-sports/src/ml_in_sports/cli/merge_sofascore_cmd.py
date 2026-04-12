"""CLI command: merge Sofascore match statistics into features parquet.

Loads cached Sofascore JSON files, matches them to the features parquet
by team name + date, computes rolling features, and saves the result.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import structlog
import typer

logger = structlog.get_logger(__name__)

merge_sofascore_app = typer.Typer(no_args_is_help=True)


@merge_sofascore_app.command("run")
def run(
    parquet_path: Annotated[
        Path,
        typer.Option(
            "--parquet",
            help="Path to features parquet file.",
        ),
    ] = Path("data/features/all_features.parquet"),
    sofascore_dir: Annotated[
        Path,
        typer.Option(
            "--sofascore-dir",
            help="Root directory for Sofascore JSON cache.",
        ),
    ] = Path("data/sofascore"),
    windows: Annotated[
        list[int],
        typer.Option(
            "--window",
            help="Rolling window sizes (can be specified multiple times).",
        ),
    ] = [3, 5, 10],  # noqa: B006 — typer requires mutable default
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--no-dry-run",
            help="Parse and match but do not save the parquet.",
        ),
    ] = False,
) -> None:
    """Merge Sofascore stats and compute rolling features."""
    from ml_in_sports.processing.sofascore_merge import run_sofascore_merge

    logger.info(
        "merge_sofascore_start",
        parquet=str(parquet_path),
        sofascore_dir=str(sofascore_dir),
        windows=windows,
        dry_run=dry_run,
    )

    run_sofascore_merge(
        parquet_path=parquet_path,
        sofascore_dir=sofascore_dir,
        windows=windows,
        dry_run=dry_run,
    )

    typer.echo("Done.")

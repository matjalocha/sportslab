"""Merge scraped Sofascore stats into features parquet.

Reads all cached JSON files from the background scraper, normalizes team
names, matches to the features parquet by (home_team, away_team, date +/-1 day),
and adds new ``sofa_*`` columns plus rolling features.

The background scraper produces JSON files in::

    data/sofascore/{league_safe}/{season_id}/{game_id}.json

Each file has structure::

    {
      "game_id": 12469701,
      "home_team": "Blackburn Rovers",
      "away_team": "Derby County",
      "timestamp": 1723230000,
      "stats": {
        "home_expectedGoals": 2.05,
        "away_ballPossession": 53,
        ...
      }
    }

Usage::

    uv run python scripts/merge_sofascore.py
    uv run python scripts/merge_sofascore.py --parquet data/features/all_features.parquet
    uv run python scripts/merge_sofascore.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import structlog

# Ensure the package is importable when run as a script
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "packages" / "ml-in-sports" / "src"))

from ml_in_sports.processing.sofascore_merge import run_sofascore_merge  # noqa: E402

logger = structlog.get_logger(__name__)


def main() -> None:
    """Parse arguments and run the Sofascore merge pipeline."""
    parser = argparse.ArgumentParser(
        description="Merge scraped Sofascore stats into features parquet.",
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=Path("data/features/all_features.parquet"),
        help="Path to features parquet file.",
    )
    parser.add_argument(
        "--sofascore-dir",
        type=Path,
        default=Path("data/sofascore"),
        help="Root directory for Sofascore JSON cache.",
    )
    parser.add_argument(
        "--windows",
        type=int,
        nargs="+",
        default=[3, 5, 10],
        help="Rolling window sizes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and match but do not save the parquet.",
    )

    args = parser.parse_args()

    run_sofascore_merge(
        parquet_path=args.parquet,
        sofascore_dir=args.sofascore_dir,
        windows=args.windows,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

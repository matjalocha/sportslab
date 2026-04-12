#!/usr/bin/env python3
"""Ingest all downloaded league CSVs into features parquet.

Usage:
    uv run python scripts/ingest_all_leagues.py

Processes all 11 expansion leagues (beyond Top-5 which are already in parquet).
Computes basic features (rolling goals, form, odds-implied) and appends to parquet.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "ml-in-sports" / "src"))

from ml_in_sports.processing.league_ingestion import ingest_league

OUTPUT = Path("data/features/all_features.parquet")
ODDS_DIR = Path("data/odds")

# Expansion leagues (Top-5 already in parquet from research repo)
EXPANSION_LEAGUES = [
    "ENG-Championship",
    "NED-Eredivisie",
    "GER-Bundesliga 2",
    "ITA-Serie B",
    "POR-Primeira Liga",
    "BEL-Jupiler Pro League",
    "TUR-Süper Lig",
    "GRE-Super League",
    "SCO-Premiership",
    "ESP-Segunda",
    "FRA-Ligue 2",
]

# Seasons with Pinnacle odds (2012/13+) — most useful for CLV
SEASONS = [
    "1213", "1314", "1415", "1516", "1617",
    "1718", "1819", "1920", "2021", "2122",
    "2223", "2324", "2425",
]


def main() -> None:
    total_added = 0

    for league in EXPANSION_LEAGUES:
        print(f"\n--- {league} ---")
        try:
            n = ingest_league(
                league=league,
                seasons=SEASONS,
                odds_dir=ODDS_DIR,
                output_parquet=OUTPUT,
            )
            total_added += n
            print(f"  Added {n} matches")
        except Exception as exc:
            print(f"  ERROR: {exc}")

    print(f"\nDONE: {total_added} matches added to {OUTPUT}")

    # Verify
    import pandas as pd
    df = pd.read_parquet(OUTPUT)
    print(f"Total parquet: {len(df)} rows, {len(df.columns)} columns")
    print(f"Leagues: {sorted(df['league'].unique().tolist())}")


if __name__ == "__main__":
    main()

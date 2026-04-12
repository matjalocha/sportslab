#!/usr/bin/env python3
"""Download all league data from football-data.co.uk with retry logic.

Usage:
    uv run python scripts/download_all_leagues.py

Downloads CSVs for all 16 registered leagues, seasons 1415-2526.
Retries failed downloads up to 5 times with exponential backoff.
Skips already-downloaded files.
"""

import sys
import time
from pathlib import Path

# Add project root so imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "ml-in-sports" / "src"))

from ml_in_sports.processing.leagues import LEAGUE_REGISTRY
from ml_in_sports.processing.odds.pinnacle import FOOTBALL_DATA_LEAGUE_MAP, download_season_csv

OUTPUT_DIR = Path("data/odds")
MAX_RETRIES = 5
BASE_DELAY = 3.0  # seconds between requests
RETRY_DELAY = 30.0  # seconds on failure

# All seasons from 2005/06 to 2025/26
ALL_SEASONS = [
    "0506", "0607", "0708", "0809", "0910",
    "1011", "1112", "1213", "1314", "1415",
    "1516", "1617", "1718", "1819", "1920",
    "2021", "2122", "2223", "2324", "2425", "2526",
]

# Map canonical league name → football-data code
LEAGUE_TO_CODE: dict[str, str] = {v: k for k, v in FOOTBALL_DATA_LEAGUE_MAP.items()}


def main() -> None:
    """Download all leagues with retry logic."""
    total = 0
    skipped = 0
    failed_final: list[str] = []
    downloaded = 0

    leagues = [
        (name, LEAGUE_TO_CODE[name])
        for name in LEAGUE_REGISTRY
        if name in LEAGUE_TO_CODE
    ]

    print(f"Downloading {len(leagues)} leagues × {len(ALL_SEASONS)} seasons")
    print(f"Output: {OUTPUT_DIR.resolve()}")
    print(f"Rate limit: {BASE_DELAY}s between requests, {MAX_RETRIES} retries on failure")
    print("=" * 70)

    for league_name, code in leagues:
        print(f"\n--- {league_name} ({code}) ---")

        for season in ALL_SEASONS:
            total += 1
            dest = OUTPUT_DIR / code / f"{season}.csv"

            if dest.exists() and dest.stat().st_size > 100:
                skipped += 1
                continue

            success = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    time.sleep(BASE_DELAY)
                    download_season_csv(code, season, OUTPUT_DIR)
                    downloaded += 1
                    print(f"  OK {code}/{season}.csv")
                    success = True
                    break
                except RuntimeError as exc:
                    error_str = str(exc)
                    if "404" in error_str:
                        # Season doesn't exist for this league — skip permanently
                        print(f"  - {code}/{season}.csv (not available)")
                        success = True  # not a retry-able failure
                        break
                    else:
                        delay = RETRY_DELAY * attempt
                        print(f"  FAIL {code}/{season}.csv attempt {attempt}/{MAX_RETRIES}: {error_str[:80]}")
                        if attempt < MAX_RETRIES:
                            print(f"    Retrying in {delay:.0f}s...")
                            time.sleep(delay)
                except Exception as exc:
                    delay = RETRY_DELAY * attempt
                    print(f"  FAIL {code}/{season}.csv attempt {attempt}/{MAX_RETRIES}: {exc!r}")
                    if attempt < MAX_RETRIES:
                        print(f"    Retrying in {delay:.0f}s...")
                        time.sleep(delay)

            if not success:
                failed_final.append(f"{code}/{season}")

    print("\n" + "=" * 70)
    print(f"DONE: {downloaded} downloaded, {skipped} skipped (already exist), {len(failed_final)} failed")

    if failed_final:
        print(f"\nFAILED ({len(failed_final)}):")
        for f in failed_final:
            print(f"  {f}")

    # Summary file
    summary_path = OUTPUT_DIR / "download_summary.txt"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        f.write(f"Downloaded: {downloaded}\n")
        f.write(f"Skipped: {skipped}\n")
        f.write(f"Failed: {len(failed_final)}\n")
        if failed_final:
            f.write("Failed items:\n")
            for item in failed_final:
                f.write(f"  {item}\n")
    print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    main()

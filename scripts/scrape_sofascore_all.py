#!/usr/bin/env python3
"""Bulk scrape Sofascore match statistics for all expansion leagues.

Uses soccerdata TLS session for API access (works on Windows).
Caches everything to data/sofascore/{league}/{season_id}/{game_id}.json.
Rate limit: 2 seconds between requests.
Seasons: 14/15 to 25/26 (same as Top-5).

Usage:
    uv run python scripts/scrape_sofascore_all.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "ml-in-sports" / "src"))

import soccerdata as sd

# Tournament IDs from Sofascore
TOURNAMENTS = {
    "ENG-Championship": 18,
    "NED-Eredivisie": 37,
    "GER-Bundesliga 2": 44,
    "ITA-Serie B": 53,
    "POR-Primeira Liga": 238,
    "BEL-Jupiler Pro League": 38,
    "TUR-Super Lig": 52,
    "GRE-Super League": 185,
    "SCO-Premiership": 36,
    "ESP-Segunda": 54,
    "FRA-Ligue 2": 182,
}

# Our target seasons (matching Top-5 range: 14/15 to 25/26)
TARGET_SEASON_NAMES = [
    "14/15", "15/16", "16/17", "17/18", "18/19",
    "19/20", "20/21", "21/22", "22/23", "23/24", "24/25", "25/26",
]

CACHE_DIR = Path("data/sofascore")
RATE_LIMIT = 2.0  # seconds between API calls


def get_session():
    """Get authenticated soccerdata TLS session."""
    sf = sd.Sofascore(leagues="ENG-Championship", seasons="2425")
    return sf._session


def get_season_ids(session, tournament_id):
    """Fetch all season IDs for a tournament."""
    resp = session.get(f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/seasons")
    if resp.status_code != 200:
        return {}
    seasons = resp.json().get("seasons", [])
    return {s["year"]: s["id"] for s in seasons if s.get("year")}


def get_match_ids(session, tournament_id, season_id):
    """Fetch all finished match IDs for a tournament/season."""
    match_ids = []
    page = 0
    while True:
        url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/last/{page}"
        resp = session.get(url)
        if resp.status_code != 200:
            break
        events = resp.json().get("events", [])
        if not events:
            break
        for e in events:
            match_ids.append({
                "id": e["id"],
                "home": e.get("homeTeam", {}).get("name", "?"),
                "away": e.get("awayTeam", {}).get("name", "?"),
                "date": e.get("startTimestamp", 0),
            })
        if not resp.json().get("hasNextPage", False):
            break
        page += 1
        time.sleep(RATE_LIMIT)
    return match_ids


def fetch_match_stats(session, game_id):
    """Fetch statistics for a single match."""
    resp = session.get(f"https://api.sofascore.com/api/v1/event/{game_id}/statistics")
    if resp.status_code != 200:
        return None

    data = resp.json()
    stats = {}
    for period in data.get("statistics", []):
        if period.get("period") != "ALL":
            continue
        for group in period.get("groups", []):
            for item in group.get("statisticsItems", []):
                key = item["key"]
                stats[f"home_{key}"] = item.get("homeValue")
                stats[f"away_{key}"] = item.get("awayValue")
    return stats


def main():
    print("Initializing soccerdata session...")
    session = get_session()

    total_fetched = 0
    total_cached = 0
    total_failed = 0

    for league, tournament_id in TOURNAMENTS.items():
        print(f"\n{'='*60}")
        print(f"  {league} (tournament {tournament_id})")
        print(f"{'='*60}")

        # Get available seasons
        season_map = get_season_ids(session, tournament_id)
        if not season_map:
            print(f"  ERROR: No seasons found")
            continue

        # Filter to our target seasons
        target = {name: sid for name, sid in season_map.items() if name in TARGET_SEASON_NAMES}
        print(f"  Available: {len(season_map)} seasons, Target: {len(target)} seasons")

        for season_name, season_id in sorted(target.items()):
            league_safe = league.replace(" ", "_").replace("/", "_")
            cache_path = CACHE_DIR / league_safe / str(season_id)
            cache_path.mkdir(parents=True, exist_ok=True)

            # Check how many already cached
            cached_files = list(cache_path.glob("*.json"))

            # Get match IDs
            print(f"\n  Season {season_name} (id={season_id})...")
            time.sleep(RATE_LIMIT)
            matches = get_match_ids(session, tournament_id, season_id)
            print(f"    Matches: {len(matches)}, Already cached: {len(cached_files)}")

            for match in matches:
                gid = match["id"]
                match_cache = cache_path / f"{gid}.json"

                if match_cache.exists():
                    total_cached += 1
                    continue

                time.sleep(RATE_LIMIT)
                stats = fetch_match_stats(session, gid)

                if stats:
                    # Save with metadata
                    result = {
                        "game_id": gid,
                        "home_team": match["home"],
                        "away_team": match["away"],
                        "timestamp": match["date"],
                        "stats": stats,
                    }
                    match_cache.write_text(json.dumps(result, indent=2), encoding="utf-8")
                    total_fetched += 1

                    if total_fetched % 50 == 0:
                        print(f"    ... fetched {total_fetched} matches so far")
                else:
                    total_failed += 1

            print(f"    Done: +{total_fetched} fetched, {total_cached} cached, {total_failed} failed")

    print(f"\n{'='*60}")
    print(f"COMPLETE: {total_fetched} fetched, {total_cached} cached, {total_failed} failed")

    # Write summary
    summary = CACHE_DIR / "scrape_summary.txt"
    summary.write_text(
        f"Fetched: {total_fetched}\nCached: {total_cached}\nFailed: {total_failed}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

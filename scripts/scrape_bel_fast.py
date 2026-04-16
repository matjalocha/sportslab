#!/usr/bin/env python3
"""Fast targeted scrape for BEL-Jupiler Pro League only.

Fetches only seasons with uncached matches that have stats.
Rate: 1s (vs 3s in main scraper). Concurrent: 3 threads.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "ml-in-sports" / "src"))

import soccerdata as sd

CACHE_DIR = Path("data/sofascore/BEL-Jupiler_Pro_League")
RATE_LIMIT = 1.0
TOURNAMENT_ID = 38
WORKERS = 3

# Only seasons confirmed to have uncached stats (from manual probe)
TARGET_SEASONS = {
    "14/15": 8168,
    "15/16": 10335,
    "16/17": 11829,
    "17/18": 13375,
    "18/19": 17343,
    "19/20": 24097,
    "20/21": 28216,
    "21/22": 36894,
    "22/23": 42404,
    "23/24": 52383,
    "24/25": 61459,
    "25/26": 77040,
}


def get_session():
    sf = sd.Sofascore(leagues="ENG-Championship", seasons="2425")
    return sf._session


def get_match_ids(session, season_id: int) -> list[dict]:
    match_ids = []
    page = 0
    while True:
        url = f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{season_id}/events/last/{page}"
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
                "timestamp": e.get("startTimestamp", 0),
            })
        if not resp.json().get("hasNextPage", False):
            break
        page += 1
        time.sleep(RATE_LIMIT)
    return match_ids


def fetch_and_save(session, match: dict, season_cache: Path) -> str:
    gid = match["id"]
    path = season_cache / f"{gid}.json"
    if path.exists():
        return "cached"
    time.sleep(RATE_LIMIT)
    resp = session.get(f"https://api.sofascore.com/api/v1/event/{gid}/statistics")
    if resp.status_code != 200 or not resp.json().get("statistics"):
        return "no_stats"
    stats = {}
    for period in resp.json().get("statistics", []):
        if period.get("period") != "ALL":
            continue
        for group in period.get("groups", []):
            for item in group.get("statisticsItems", []):
                key = item["key"]
                stats[f"home_{key}"] = item.get("homeValue")
                stats[f"away_{key}"] = item.get("awayValue")
    result = {
        "game_id": gid,
        "home_team": match["home"],
        "away_team": match["away"],
        "timestamp": match["timestamp"],
        "stats": stats,
    }
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return "fetched"


def main() -> None:
    print("BEL fast scraper — 1s rate, 3 workers")
    session = get_session()

    total_fetched = 0
    total_cached = 0
    total_no_stats = 0

    for season_name, season_id in TARGET_SEASONS.items():
        season_cache = CACHE_DIR / str(season_id)
        season_cache.mkdir(parents=True, exist_ok=True)

        print(f"\n{season_name} (id={season_id})...")
        time.sleep(RATE_LIMIT)
        matches = get_match_ids(session, season_id)
        already_cached = len(list(season_cache.glob("*.json")))
        uncached = [m for m in matches if not (season_cache / f"{m['id']}.json").exists()]
        print(f"  Total: {len(matches)}, cached: {already_cached}, to fetch: {len(uncached)}")

        if not uncached:
            total_cached += already_cached
            continue

        fetched = 0
        no_stats = 0
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {pool.submit(fetch_and_save, session, m, season_cache): m for m in uncached}
            for future in as_completed(futures):
                result = future.result()
                if result == "fetched":
                    fetched += 1
                    total_fetched += 1
                    if total_fetched % 50 == 0:
                        print(f"  ... {total_fetched} fetched total")
                elif result == "cached":
                    total_cached += 1
                elif result == "no_stats":
                    no_stats += 1
                    total_no_stats += 1

        print(f"  Done: +{fetched} fetched, {no_stats} no_stats")

    total_on_disk = len(list(CACHE_DIR.rglob("*.json")))
    print(f"\n{'='*50}")
    print(f"COMPLETE: {total_fetched} fetched, {total_no_stats} no_stats")
    print(f"BEL total on disk: {total_on_disk}")


if __name__ == "__main__":
    main()

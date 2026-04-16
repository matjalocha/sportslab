#!/usr/bin/env python3
"""Watchdog for Sofascore scrape — auto-restarts on IP block / crash.

Loop:
  1. Run scripts/scrape_sofascore_all.py as subprocess
  2. Count JSONs before and after
  3. If progress > 0 and scrape completed cleanly (exit 0) → check if done
  4. If progress == 0 (IP blocked) → cooldown and retry
  5. Stop when: all leagues ≥ threshold OR N consecutive no-progress runs OR max total runs

Rationale: scrape_sofascore_all.py skips cached files on restart, so re-running
is safe and idempotent. IP blocks lift after ~30-60 min of idle.

Usage:
    uv run python scripts/scrape_sofascore_watchdog.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "sofascore"
SCRAPE_SCRIPT = ROOT / "scripts" / "scrape_sofascore_all.py"
LOG_FILE = ROOT / "data" / "sofascore_watchdog.log"

# Expected minimum JSONs per league to call it "done" (conservative estimate).
# Lower than theoretical max because ~10-15% of older seasons lack stats.
MIN_PER_LEAGUE = {
    "ENG-Championship": 5500,
    "ESP-Segunda": 4500,
    "ITA-Serie_B": 3800,
    "TUR-Süper_Lig": 3500,
    "FRA-Ligue_2": 3500,
    "NED-Eredivisie": 3000,
    "GER-Bundesliga_2": 3000,
    "POR-Primeira_Liga": 3000,
    "BEL-Jupiler_Pro_League": 2500,
    "SCO-Premiership": 1750,  # API max ~1762, no more stats available beyond this
    "GRE-Super_League": 1800,
}

# Cooldown schedule (minutes). If the Nth run makes no progress, wait this long.
COOLDOWN_SCHEDULE_MIN = [5, 15, 30, 45, 60, 90, 120]
MAX_RUNS = 30  # hard cap on total scrape attempts


def log(message: str) -> None:
    """Write timestamped line to both stdout and log file."""
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def count_jsons_per_league() -> dict[str, int]:
    """Return mapping league_dir_name -> json file count."""
    if not CACHE_DIR.exists():
        return {}
    counts = {}
    for league_dir in CACHE_DIR.iterdir():
        if not league_dir.is_dir():
            continue
        counts[league_dir.name] = sum(1 for _ in league_dir.rglob("*.json"))
    return counts


def total_count(counts: dict[str, int]) -> int:
    return sum(counts.values())


def all_leagues_satisfied(counts: dict[str, int]) -> bool:
    """True when every target league has >= its minimum threshold."""
    for league, minimum in MIN_PER_LEAGUE.items():
        if counts.get(league, 0) < minimum:
            return False
    return True


def remaining_leagues(counts: dict[str, int]) -> list[tuple[str, int, int]]:
    """List of (league, current, needed) for leagues below threshold."""
    return [
        (league, counts.get(league, 0), minimum)
        for league, minimum in MIN_PER_LEAGUE.items()
        if counts.get(league, 0) < minimum
    ]


def run_scrape_once() -> int:
    """Run scrape_sofascore_all.py to completion. Return exit code."""
    log(f"  Starting: uv run python {SCRAPE_SCRIPT.name}")
    try:
        result = subprocess.run(
            ["uv", "run", "python", str(SCRAPE_SCRIPT)],
            cwd=str(ROOT),
            capture_output=False,
            timeout=9000,  # 2.5h hard timeout per run
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        log("  TIMEOUT — scrape exceeded 4h, killed")
        return -1
    except Exception as error:
        log(f"  EXCEPTION — {error}")
        return -2


def cooldown_seconds(consecutive_no_progress: int) -> int:
    """Select cooldown duration based on streak of failed attempts."""
    index = min(consecutive_no_progress, len(COOLDOWN_SCHEDULE_MIN) - 1)
    return COOLDOWN_SCHEDULE_MIN[index] * 60


def main() -> int:
    log("=" * 60)
    log("Sofascore scrape watchdog starting")
    log("=" * 60)

    consecutive_no_progress = 0

    for run_number in range(1, MAX_RUNS + 1):
        counts_before = count_jsons_per_league()
        total_before = total_count(counts_before)

        log(f"\n--- Run {run_number}/{MAX_RUNS} ---")
        log(f"Total JSONs: {total_before}")
        remaining = remaining_leagues(counts_before)
        if remaining:
            log(f"Remaining: {len(remaining)} leagues below threshold")
            for league, current, needed in remaining:
                log(f"  {league}: {current}/{needed}")
        else:
            log("All leagues satisfied — exiting.")
            return 0

        exit_code = run_scrape_once()

        counts_after = count_jsons_per_league()
        total_after = total_count(counts_after)
        delta = total_after - total_before

        log(f"Run {run_number} finished: exit={exit_code}, delta=+{delta}, total={total_after}")

        if all_leagues_satisfied(counts_after):
            log("All leagues satisfied after this run — DONE.")
            return 0

        if delta == 0:
            consecutive_no_progress += 1
            wait_s = cooldown_seconds(consecutive_no_progress)
            log(
                f"No progress ({consecutive_no_progress} consecutive). "
                f"Cooling down {wait_s // 60} min before retry."
            )
            if consecutive_no_progress >= len(COOLDOWN_SCHEDULE_MIN) + 2:
                log("Too many consecutive no-progress runs — giving up.")
                return 1
            time.sleep(wait_s)
        else:
            consecutive_no_progress = 0
            short_wait = 60
            log(f"Progress made. Short pause ({short_wait}s) to avoid rate spike.")
            time.sleep(short_wait)

    log(f"Reached MAX_RUNS={MAX_RUNS} — stopping.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

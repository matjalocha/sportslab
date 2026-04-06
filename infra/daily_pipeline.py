#!/usr/bin/env python3
"""Daily pipeline: scrape -> features -> predict -> notify.

Designed to be called by cron:
  0 6 * * * cd /app && python infra/daily_pipeline.py 2>&1 >> /var/log/sportslab/pipeline.log
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

import structlog

logger = structlog.get_logger("daily_pipeline")

STEPS: list[tuple[str, list[str]]] = [
    ("scrape", ["uv", "run", "sl", "pipeline", "run", "--fast"]),
    ("features", ["uv", "run", "sl", "features", "build"]),
    ("predict", ["uv", "run", "sl", "predict", "run"]),
    ("notify_slip", ["uv", "run", "sl", "notify", "bet-slip"]),
]

EVENING_STEPS: list[tuple[str, list[str]]] = [
    ("results", ["uv", "run", "sl", "results", "run"]),
    ("notify_results", ["uv", "run", "sl", "notify", "results"]),
]


def run_step(name: str, cmd: list[str]) -> bool:
    """Run a pipeline step, return True if success."""
    logger.info("step_start", step=name, cmd=cmd)
    start = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    elapsed = time.monotonic() - start
    if result.returncode != 0:
        logger.error(
            "step_failed",
            step=name,
            elapsed=elapsed,
            stderr=result.stderr[-500:],
        )
        return False
    logger.info("step_complete", step=name, elapsed=elapsed)
    return True


def ping_healthcheck(check_id: str, status: str = "") -> None:
    """Ping healthchecks.io after pipeline completion."""
    import httpx

    url = f"https://hc-ping.com/{check_id}"
    if status == "fail":
        url += "/fail"
    try:
        httpx.get(url, timeout=5)
    except Exception:
        logger.warning("healthcheck_ping_failed")


def main() -> None:
    """Run the morning or evening pipeline."""
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    steps = STEPS if mode == "morning" else EVENING_STEPS

    all_ok = True
    for name, cmd in steps:
        if not run_step(name, cmd):
            all_ok = False
            break

    check_id = os.environ.get("HEALTHCHECK_ID", "")
    if check_id:
        ping_healthcheck(check_id, "" if all_ok else "fail")

    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

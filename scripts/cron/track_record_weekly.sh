#!/usr/bin/env bash
# Weekly track-record JSON export for the landing page.
#
# Installed via:
#     crontab -e
#
#     # m h  dom mon dow  command
#     0 7 * * 1 /app/scripts/cron/track_record_weekly.sh
#
# Before SPO-A-09 lands we run with --force-stub so the output is the
# "starting soon" placeholder. Flip to the real mode by removing the flag
# once the bets table has real data.
set -euo pipefail

REPO_ROOT="${SPORTSLAB_REPO_ROOT:-/app}"
OUTPUT_PATH="${SPORTSLAB_TRACK_RECORD_OUTPUT:-${REPO_ROOT}/reports/track_record_latest.json}"
PYTHON_BIN="${SPORTSLAB_PYTHON_BIN:-python3}"

cd "${REPO_ROOT}"

# ``--force-stub`` is the alpha-pre-launch safety net. Remove after A-10.
"${PYTHON_BIN}" scripts/export_track_record.py \
    --output "${OUTPUT_PATH}" \
    --force-stub

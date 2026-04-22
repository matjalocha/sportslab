# Scheduled jobs -- cron reference

Canonical list of batch jobs that run on the SportsLab production host.
Each entry documents the schedule, what it does, where logs land, and
which Linear task owns it. When a new job lands, update this file in the
same PR that adds the script.

## Jobs

### Track Record JSON exporter

- **Script:** `scripts/export_track_record.py`
- **Schedule:** Weekly, Monday 07:00 UTC
- **Purpose:** Aggregate settled bets into `reports/track_record_latest.json`
  for the landing-page "Track Record" widget (SPO-A-37). Pre-launch the
  script emits a `status: "starting_soon"` stub so the widget never hits a
  404; post-launch it pulls real numbers from the `user_bets` table.
- **Outputs:** `/app/reports/track_record_latest.json` (mounted to the
  landing server or pushed to CDN by a follow-up step).
- **Linear:** SPO-A-38 (this script) + SPO-A-37 (landing widget).

Crontab entry (see `scripts/cron/track_record_weekly.sh`):

```cron
# m h  dom mon dow  command
0 7 * * 1 cd /app && python scripts/export_track_record.py \
    --output /app/reports/track_record_latest.json \
    >> /var/log/sportslab/track_record.log 2>&1
```

The script reads `SPORTSLAB_DATABASE_URL` from the environment, same as
the API. Before SPO-A-09 lands we run with `--force-stub` so the cron
output is the "starting soon" placeholder.

## Conventions

- **UTC everywhere.** The host is `Etc/UTC`; schedules in this file are
  UTC, not local. Document local-time equivalents in job descriptions if
  relevant (e.g. "Monday 07:00 UTC = 08:00 CET").
- **Log rotation** via `/etc/logrotate.d/sportslab` (14-day retention).
- **Locking:** scripts that must not overlap use `flock -n` at the cron
  level. Track-record export is idempotent so no lock is needed.
- **Alerting:** non-zero exit from any cron job triggers a Grafana alert
  via the Prometheus `cron_last_exit_code` metric scraped by the
  `cron_exporter` sidecar (SPO-A-10 deliverable).

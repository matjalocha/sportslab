# Codex Prompts — R4 Automation

> Realizuj TASK-R4-01 do R4-06 sekwencyjnie.
> Testy uruchom RAZ na końcu (nie po każdym tasku):
> ```bash
> uv run ruff check packages/ml-in-sports --fix
> uv run mypy packages
> uv run pytest packages/ml-in-sports -q
> ```
> Po zakończeniu każdego tasku zapisz w `docs/codex_status_r4.md`:
> ```
> TASK-R4-XX: DONE | pliki: [lista] | uwagi: [jeśli są]
> ```

---

## TASK-R4-01: Dockerfile + docker-compose.yml

```
Stwórz Docker setup dla SportsLab pipeline.

Pliki do stworzenia:
- infra/Dockerfile
- infra/docker-compose.yml
- infra/.env.example

Dockerfile:
- Base: python:3.11-slim
- Install: uv (curl from astral.sh)
- WORKDIR: /app
- COPY: pyproject.toml, uv.lock, packages/
- RUN: uv sync --all-extras --no-dev (production, no test deps)
- ENTRYPOINT: ["uv", "run", "sl"]

docker-compose.yml:
- service "pipeline":
    build: context: ., dockerfile: infra/Dockerfile
    env_file: infra/.env
    volumes:
      - ./data:/app/data
      - ./reports:/app/reports
      - ./predictions:/app/predictions
    depends_on: [postgres]
- service "postgres":
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: sportslab
      POSTGRES_USER: sportslab
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports: ["5432:5432"]
- volumes: pgdata:

.env.example:
```
POSTGRES_PASSWORD=changeme
ML_IN_SPORTS_DATABASE_URL=postgresql://sportslab:changeme@postgres:5432/sportslab
ML_IN_SPORTS_DB_PATH=data/football.db
ML_IN_SPORTS_PINNACLE_ODDS_DIR=data/odds
ML_IN_SPORTS_TELEGRAM_BOT_TOKEN=
ML_IN_SPORTS_TELEGRAM_CHAT_ID=
ML_IN_SPORTS_LOG_JSON=true
ML_IN_SPORTS_LOG_LEVEL=INFO
```

Zasady:
- .env NIE commitować (dodaj do .gitignore jeśli nie ma)
- Dockerfile powinien cachować uv sync (COPY pyproject.toml before source)
- Multi-stage NIE potrzebny (prosty setup)
```

---

## TASK-R4-02: Postgres support w database.py + settings.py

```
Dodaj obsługę Postgres obok istniejącego SQLite w database.py.

Pliki do modyfikacji:
- packages/ml-in-sports/src/ml_in_sports/settings.py
- packages/ml-in-sports/src/ml_in_sports/utils/database.py

settings.py — dodaj:
```python
database_url: str = ""  # postgresql://user:pass@host:5432/db. Empty = SQLite fallback
```

database.py — zmień FootballDatabase.__init__:
```python
def __init__(self, db_path: Path | str | None = None) -> None:
    settings = get_settings()
    if settings.database_url:
        # Postgres mode
        import psycopg2
        self._conn = psycopg2.connect(settings.database_url)
        self._is_postgres = True
    else:
        # SQLite mode (existing behavior)
        if db_path is None:
            db_path = _default_db_path()
        ...
```

UWAGA: FootballDatabase używa sqlite3 API bezpośrednio (conn.execute, cursor).
Zamiast pełnego refactora — dodaj cienką warstwę abstrakcji:

```python
def _execute(self, sql: str, params: tuple = ()) -> Any:
    """Execute SQL on either SQLite or Postgres."""
    if self._is_postgres:
        # Postgres: %s placeholders, autocommit
        sql = sql.replace("?", "%s")
        sql = sql.replace("INSERT OR REPLACE", "INSERT ... ON CONFLICT ... DO UPDATE")
        cursor = self._conn.cursor()
        cursor.execute(sql, params)
        self._conn.commit()
        return cursor
    else:
        return self._conn.execute(sql, params)
```

Dodaj psycopg2 do optional deps:
```toml
# pyproject.toml [project.optional-dependencies]
postgres = ["psycopg2-binary>=2.9,<3.0"]
```

Testy: dodaj test z SQLite (istniejący) + test że Postgres path nie crashuje na import.
NIE testuj z prawdziwym Postgres (wymaga serwera) — mock connection.
```

---

## TASK-R4-03: SQLite → Postgres data migration script

```
Stwórz skrypt migracji danych z SQLite do Postgres.

Plik do stworzenia:
- packages/ml-in-sports/src/ml_in_sports/cli/migrate_cmd.py

CLI: `sl migrate sqlite-to-postgres --sqlite-path data/football.db`

Co robi:
1. Connect do SQLite (--sqlite-path)
2. Connect do Postgres (z ML_IN_SPORTS_DATABASE_URL env var)
3. Alembic upgrade head na Postgres (create tables)
4. Dla każdej z 11 tabel:
   a. SELECT * FROM table w SQLite
   b. INSERT INTO table w Postgres (batch po 1000 rows)
   c. Log: "Migrated {table}: {n} rows"
5. Verify: count(*) match między SQLite i Postgres

Zarejestruj w cli/main.py:
```python
from ml_in_sports.cli.migrate_cmd import migrate_app
app.add_typer(migrate_app, name="migrate", help="Database migration tools.")
```

Testy: test z SQLite in-memory → SQLite in-memory (mock Postgres path).
```

---

## TASK-R4-04: Cron wrapper script + daily pipeline

```
Stwórz wrapper script dla cron daily pipeline.

Plik do stworzenia:
- infra/daily_pipeline.py

Script uruchamiany przez cron:
```python
#!/usr/bin/env python3
"""Daily pipeline: scrape → features → predict → notify.

Designed to be called by cron:
  0 6 * * * cd /app && python infra/daily_pipeline.py 2>&1 >> /var/log/sportslab/pipeline.log
"""

import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import structlog

logger = structlog.get_logger("daily_pipeline")

STEPS = [
    ("scrape", ["uv", "run", "sl", "pipeline", "run", "--fast"]),
    ("features", ["uv", "run", "sl", "features", "build"]),
    ("predict", ["uv", "run", "sl", "predict", "run"]),
    ("notify_slip", ["uv", "run", "sl", "notify", "bet-slip"]),
]

EVENING_STEPS = [
    ("results", ["uv", "run", "sl", "results", "run"]),
    ("notify_results", ["uv", "run", "sl", "notify", "results"]),
]

def run_step(name: str, cmd: list[str]) -> bool:
    """Run a pipeline step, return True if success."""
    logger.info("step_start", step=name)
    start = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.monotonic() - start
    if result.returncode != 0:
        logger.error("step_failed", step=name, elapsed=elapsed, 
                     stderr=result.stderr[-500:])
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
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    steps = STEPS if mode == "morning" else EVENING_STEPS
    
    all_ok = True
    for name, cmd in steps:
        if not run_step(name, cmd):
            all_ok = False
            break  # stop on first failure
    
    # Ping healthcheck
    check_id = os.environ.get("HEALTHCHECK_ID", "")
    if check_id:
        ping_healthcheck(check_id, "" if all_ok else "fail")

if __name__ == "__main__":
    main()
```

Dodaj też:
- infra/crontab.example:
```
# Morning pipeline (06:00 UTC)
0 6 * * * cd /app && python infra/daily_pipeline.py morning >> /var/log/sportslab/morning.log 2>&1

# Evening results (00:30 UTC+1 = 23:30 UTC)
30 23 * * * cd /app && python infra/daily_pipeline.py evening >> /var/log/sportslab/evening.log 2>&1

# Weekly report (Sunday 23:59 UTC)
59 23 * * 0 cd /app && uv run sl weekly run >> /var/log/sportslab/weekly.log 2>&1

# Backup (02:00 UTC)
0 2 * * * /app/infra/backup.sh >> /var/log/sportslab/backup.log 2>&1
```
```

---

## TASK-R4-05: Backup script (Postgres dump → B2)

```
Stwórz backup script.

Plik do stworzenia:
- infra/backup.sh

```bash
#!/bin/bash
# Daily Postgres backup to Backblaze B2
# Requires: b2 CLI tool, POSTGRES_PASSWORD, B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET env vars

set -euo pipefail

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/tmp/sportslab-backups"
BACKUP_FILE="${BACKUP_DIR}/sportslab_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Dump Postgres
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h localhost -U sportslab sportslab | gzip > "$BACKUP_FILE"

# Upload to B2
b2 upload-file "${B2_BUCKET}" "$BACKUP_FILE" "backups/daily/sportslab_${DATE}.sql.gz"

# Cleanup local
rm -f "$BACKUP_FILE"

# Cleanup old B2 backups (keep 7 daily + 4 weekly)
# Weekly: keep Sunday backups for 4 weeks
# Daily: delete anything older than 7 days
echo "Backup complete: sportslab_${DATE}.sql.gz"
```

Dodaj też:
- infra/restore.sh (restore from B2 backup):
```bash
#!/bin/bash
# Restore from B2 backup
# Usage: ./restore.sh 2024-04-06
DATE=${1:?Usage: ./restore.sh YYYY-MM-DD}
b2 download-file-by-name "${B2_BUCKET}" "backups/daily/sportslab_${DATE}.sql.gz" "/tmp/restore.sql.gz"
gunzip -c /tmp/restore.sql.gz | PGPASSWORD="${POSTGRES_PASSWORD}" psql -h localhost -U sportslab sportslab
```
```

---

## TASK-R4-06: Monitoring setup (healthchecks.io integration)

```
Dodaj monitoring integration.

Pliki do modyfikacji:
- packages/ml-in-sports/src/ml_in_sports/settings.py
- packages/ml-in-sports/src/ml_in_sports/notification/telegram.py

settings.py — dodaj:
```python
healthcheck_id: str = ""  # healthchecks.io check UUID
```

Stwórz:
- packages/ml-in-sports/src/ml_in_sports/notification/healthcheck.py:

```python
"""Healthchecks.io integration for pipeline monitoring."""

import structlog
from ml_in_sports.settings import get_settings

logger = structlog.get_logger(__name__)

def ping_success() -> None:
    """Ping healthchecks.io on successful pipeline run."""
    hc_id = get_settings().healthcheck_id
    if not hc_id:
        return
    import httpx
    try:
        httpx.get(f"https://hc-ping.com/{hc_id}", timeout=5)
        logger.info("healthcheck_pinged", status="success")
    except Exception as exc:
        logger.warning("healthcheck_failed", error=str(exc))

def ping_failure(error_message: str = "") -> None:
    """Ping healthchecks.io on pipeline failure."""
    hc_id = get_settings().healthcheck_id
    if not hc_id:
        return
    import httpx
    try:
        httpx.post(
            f"https://hc-ping.com/{hc_id}/fail",
            content=error_message[:10000],
            timeout=5,
        )
        logger.info("healthcheck_pinged", status="fail")
    except Exception as exc:
        logger.warning("healthcheck_failed", error=str(exc))
```

Dodaj httpx do deps jeśli jeszcze nie ma.

Testy: mock httpx, test ping_success/ping_failure bez prawdziwych requestów.

Po zakończeniu WSZYSTKICH tasków R4, uruchom:
```bash
uv run ruff check packages/ml-in-sports --fix
uv run mypy packages
uv run pytest packages/ml-in-sports -q
```

Zapisz wynik w docs/codex_status_r4.md.
```

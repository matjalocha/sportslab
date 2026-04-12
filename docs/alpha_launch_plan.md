# SportsLab Alpha Launch Plan

- **Status**: Accepted
- **Date**: 2026-04-06
- **Author**: System Architect
- **Audience**: Solo founder (Mateusz) + Claude Code subagents

---

## 0. Executive Summary

SportsLab has a production-ready prediction engine: 95k matches, 935 features, walk-forward
backtesting, calibrated ensemble models, Portfolio Kelly staking, CLV tracking, drift detection,
daily pipeline CLI, Telegram notifications, Docker + Postgres, and 1349 tests.

The alpha launch packages this engine into a product that early users can evaluate.
The alpha is NOT a SaaS with billing. It is a **closed Telegram channel + landing page + public
track record** that proves the system works live and builds a waitlist for the paid API (R6).

**Architecture**: dual-machine setup (ADR-0017). Raspberry Pi 4 (4 GB RAM, ARM) runs the daily
production pipeline (inference, Postgres, Telegram). Dev PC handles training, experiments, and
MLflow. Models promoted in MLflow are deployed to the Pi via SCP. Monthly cost: ~2 EUR.

Timeline: **4 weeks** from decision to go.

---

## 1. What Is the Alpha Product?

### 1.1 Product definition

The alpha delivers one thing: **daily value bet recommendations for European football, delivered
via a private Telegram channel, backed by a public track record on the landing page.**

Concrete deliverables per day:

| Time | Delivery | Format |
|------|----------|--------|
| 08:00 CET | Morning bet slip | Telegram message: match, market, model prob, edge, Kelly stake, best odds, bookmaker |
| 22:00 CET | Evening results | Telegram message: W/L per bet, daily P&L, running ROI, running bankroll |
| Monday 08:00 | Weekly report | Telegram message + HTML report link: week summary, CLV, cumulative equity curve |

### 1.2 What the user gets

- Access to a **private Telegram channel** (invite-only)
- Daily bet slip (1X2 market, 14 leagues, Kelly-sized stakes)
- Daily results tracking
- Weekly performance report with charts
- Link to public track record page on the landing site (updated weekly)

### 1.3 Target user (alpha)

| Segment | Why alpha | Expected count |
|---------|-----------|----------------|
| Polish tipsters (Telegram/Twitter) | Understand value betting, can evaluate CLV | 10-20 |
| ML enthusiasts (Reddit r/SoccerBetting, r/sportsbook) | Appreciate transparent methodology | 10-20 |
| Personal network | Trust factor, early feedback | 5-10 |

Total alpha: **25-50 users**.

### 1.4 Pricing

**Free alpha. No billing.** Rationale:

1. We have zero live track record. Nobody will pay for unproven predictions.
2. Alpha users provide feedback and social proof for R6 paid launch.
3. Running cost is under 30 EUR/month. Not worth billing infrastructure overhead.
4. Converting free alpha users to paid later (with 3+ months of track record) is easier
   than acquiring cold paid users.

Alpha users sign up via a **waitlist form** on the landing page. Founder manually approves
and adds to the Telegram channel. This is intentional friction that filters for quality users.

### 1.5 Markets and leagues

**Markets**: 1X2 only. This is what the model is trained on and backtested for. O/U 2.5 and
BTTS are technically possible (targets exist in `features/targets.py`) but adding them
increases surface area without adding signal confidence. **[HIPOTEZA]** O/U could be added
in week 3-4 if 1X2 pipeline proves stable.

**Leagues** (14, matching `experiments/all_14_leagues.yaml`):

| Tier | Leagues | Data quality |
|------|---------|-------------|
| Tier 1 | Premier League, La Liga, Bundesliga, Serie A, Ligue 1 | Full xG + tactical stats |
| Tier 2 | Championship, Eredivisie, Bundesliga 2, Serie B, Primeira Liga, Jupiler Pro League, Super Lig, Super League Greece, Scottish Premiership | Basic stats + odds |

### 1.6 What we explicitly do NOT ship in alpha

- No API endpoints (FastAPI deferred to R6)
- No web dashboard (deferred to R6)
- No user authentication (Telegram invite = auth)
- No Stripe billing
- No multi-sport (football only)
- No custom alerts or filters per user

---

## 2. Production Infrastructure

### 2.1 Dual-machine architecture

**Decision**: Raspberry Pi 4 (production) + Dev PC (training/experiments). See ADR-0017 for
full rationale. This replaces the original Hetzner CX32 plan.

```
DEV PC (Windows/Linux, powerful):
+-- Python 3.11 + uv
+-- MLflow server (mlflow ui --port 5000)
+-- Full ml-in-sports package (with TabPFN optional)
+-- Training: sl backtest run --> logs to MLflow
+-- Feature experiments: new features --> backtest --> compare in MLflow
+-- Sofascore scraping (headless Chrome -- needs x86_64 + RAM)
+-- Access: localhost:5000 (MLflow UI)

RASPBERRY PI 4 (4 GB RAM, Ubuntu Server 24.04 ARM aarch64):
+-- Postgres 16 (apt install postgresql)
+-- Python 3.11 + uv (ARM build)
+-- ml-in-sports package (inference-only, no TabPFN -- see ADR-0014)
+-- Cron pipeline:
|     06:00  sl pipeline run --fast          (scrape latest data)
|     06:30  sl features build               (materialize features)
|     07:00  sl predict run --model-path /app/models/production/model.pkl
|     07:01  sl notify bet-slip              (Telegram push)
|     23:30  sl results run --> sl notify results
|     Sunday: sl weekly run
+-- Model sync: pull latest "Production" model from dev PC via SCP
+-- Cloudflare Tunnel (optional, for future API access)
+-- Backup: daily pg_dump --> Backblaze B2
+-- SSD via USB3 (recommended, ~20 EUR one-time)
```

**Why dual-machine over Hetzner VPS**:
- Cost drops from ~23 EUR/month to ~1 EUR/month (domain only)
- Pi 4 and dev PC already owned -- zero hardware investment beyond a 20 EUR SSD
- Dev PC provides more compute for training than CX32 (local GPU, more RAM)
- MLflow comes free on the dev PC (no server to pay for)
- Pi's 5W power consumption is negligible

**Why NOT train on the Pi**:
- 4 GB RAM is shared between OS (~0.5 GB), Postgres (~0.5-1 GB), and the application
- LightGBM training on 95k rows needs ~2-3 GB RAM -- too tight alongside Postgres
- TabPFN requires PyTorch (~2 GB) which does not fit at all
- Training takes 5-10x longer on ARM vs x86_64

### 2.2 Raspberry Pi setup checklist

```
1. Flash Ubuntu Server 24.04 LTS (ARM64) to microSD or USB SSD
2. Boot Pi, configure WiFi/Ethernet, set static IP on LAN
3. SSH key auth only (disable password auth)
4. UFW firewall: allow 22 (SSH), deny all else (Telegram is outbound only)
5. Install Postgres 16: sudo apt install postgresql postgresql-client
6. Configure Postgres for 4 GB RAM:
     shared_buffers = 256MB
     work_mem = 32MB
     effective_cache_size = 1GB
     max_connections = 20
7. Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh
8. Clone sportslab repo: git clone <deploy-key-url> /app/sportslab
9. Install deps (inference-only): cd /app/sportslab && uv sync --no-dev
10. Create .env from template (chmod 600)
11. Run Alembic migrations: uv run alembic upgrade head
12. Initial data load (see 2.4)
13. Create /app/models/production/ directory for model artifacts
14. SCP initial model from dev PC (see 3.4)
15. Set up cron jobs (see 2.5)
16. Set up healthchecks.io pings
17. Set up daily Postgres backup to Backblaze B2
18. Smoke test: trigger morning pipeline manually, verify Telegram message
```

### 2.3 Dev PC setup checklist

```
1. Python 3.11 + uv (already installed)
2. Install MLflow: uv add mlflow (in dev dependencies)
3. Start MLflow: mlflow ui --port 5000 --backend-store-uri sqlite:///mlflow.db
4. Verify: open http://localhost:5000
5. Configure SSH key for Pi: ssh-copy-id pi@<pi-ip>
6. Add deploy script to PATH (see scripts/deploy_model_to_pi.sh)
```

### 2.4 Database (Postgres on Pi)

**Postgres 16** running directly on the Pi (not in Docker). Reasons:
- One fewer moving part. Docker on ARM adds complexity for zero benefit at this scale.
- Direct filesystem access for backup scripts.
- Alembic migrations already support Postgres (`ML_IN_SPORTS_DATABASE_URL` env var).

Schema: 11 tables from Alembic migration `ecd448bb1220_initial_schema_with_11_tables.py`.
Already tested. No schema changes needed for alpha.

Connection: `ML_IN_SPORTS_DATABASE_URL=postgresql://sportslab:$PG_PASSWORD@localhost:5432/sportslab`

**Postgres tuning for 4 GB RAM Pi**:

```ini
# /etc/postgresql/16/main/postgresql.conf
shared_buffers = 256MB       # 6.25% of RAM (default 128MB is too low)
work_mem = 32MB              # Per-operation sort memory
effective_cache_size = 1GB   # OS cache hint for query planner
max_connections = 20         # Only local connections, no need for 100
maintenance_work_mem = 128MB # For VACUUM, CREATE INDEX
```

**[RYZYKO]** If Postgres + inference exceeds ~3.5 GB combined, the Linux OOM killer will fire.
The conservative Postgres settings above keep Postgres under 1 GB. Inference (LightGBM predict
on ~50 matches) uses <200 MB. Total: ~1.7 GB application + ~0.5 GB OS = ~2.2 GB. Headroom
of ~1.8 GB is sufficient but not lavish.

### 2.5 Initial data load

The current data lives in SQLite (`data/football.db`) and Parquet files on the dev PC.
Transfer strategy:

```
1. On dev PC: export SQLite tables to CSV (existing utility in database.py)
2. SCP CSVs to Pi: scp data/*.csv pi@<pi-ip>:/tmp/sportslab-import/
3. On Pi: COPY FROM CSV into Postgres tables
4. Verify row counts match (95,374 matches, check player_matches, odds, etc.)
5. Run: uv run sl features build  (materialize features Parquet on Pi)
6. Run one prediction to verify: uv run sl predict run --model-path /app/models/production/model.pkl
```

**Time estimate**: 2-3 hours (data transfer + verification).

**[DO SPRAWDZENIE]** Pi's USB SSD vs microSD performance for Postgres. USB3 SSD is strongly
recommended -- microSD has limited write endurance and poor random I/O. A 120 GB SSD costs
~20 EUR and lasts years.

### 2.6 Daily pipeline (cron on Pi)

The `infra/daily_pipeline.py` is already built and tested. Cron schedule on Pi:

```cron
# Morning pipeline: scrape -> features -> predict (inference only) -> notify bet slip
0 6 * * * cd /app/sportslab && /home/pi/.local/bin/uv run python infra/daily_pipeline.py morning >> /var/log/sportslab/morning.log 2>&1

# Evening pipeline: fetch results -> notify results
30 23 * * * cd /app/sportslab && /home/pi/.local/bin/uv run python infra/daily_pipeline.py evening >> /var/log/sportslab/evening.log 2>&1

# Weekly report (Monday morning)
30 7 * * 1 cd /app/sportslab && /home/pi/.local/bin/uv run sl weekly run --week $(date -d 'last monday' +\%Y-\%m-\%d) >> /var/log/sportslab/weekly.log 2>&1

# Weekly odds download (Tuesday -- football-data.co.uk updates Monday)
0 6 * * 2 cd /app/sportslab && /home/pi/.local/bin/uv run sl download-odds run >> /var/log/sportslab/odds.log 2>&1

# Weekly ClubElo update (Wednesday -- new ratings published weekly)
0 6 * * 3 cd /app/sportslab && /home/pi/.local/bin/uv run sl elo update >> /var/log/sportslab/elo.log 2>&1

# Nightly Postgres backup to B2
0 3 * * * /app/sportslab/scripts/backup_postgres.sh >> /var/log/sportslab/backup.log 2>&1

# Log rotation
0 0 * * 0 find /var/log/sportslab -name '*.log' -mtime +30 -delete
```

**Key difference from VPS plan**: the morning pipeline uses `--model-path` to load a
pre-trained model file instead of training from scratch. Training happens on the dev PC.

### 2.7 Data feed automation

| Source | Frequency | CLI command | Runs on | Automated? | Notes |
|--------|-----------|-------------|---------|-----------|-------|
| football-data.co.uk | Weekly (Tue) | `sl download-leagues run` | Pi (cron) | Yes | CSVs with results + odds, 14 leagues |
| Pinnacle closing odds | Weekly (Tue) | `sl download-odds run` | Pi (cron) | Yes | Via football-data.co.uk CSVs |
| ClubElo | Weekly (Wed) | `sl elo update` | Pi (cron) | Yes | HTTP fetch, no scraping required |
| STS.pl odds | Daily (06:00) | `sl pipeline run --fast` | Pi (cron) | Yes | Current match odds for bet slip |
| Sofascore | Weekly (manual) | `sl scrape-sofascore run` | **Dev PC** | **No** -- manual | Needs headless Chrome + RAM, not feasible on Pi |
| Understat | On refresh | `sl refresh run` | Dev PC | Semi-auto | Current season update |
| ESPN | On refresh | `sl refresh run` | Dev PC | Semi-auto | Current season update |
| FIFA ratings | Yearly | `sl ingest fifa` | Dev PC | Manual | New FC game = new data |
| Transfermarkt | Monthly | Manual CSV import | Dev PC | Manual | Formations + market values |

**Note**: Sofascore scraping runs exclusively on the dev PC (headless Chrome requires x86_64
and significant RAM). After scraping, updated data is pushed to the Pi via SCP or the dev PC
writes directly to the Pi's Postgres (if the dev PC has the Pi's `DATABASE_URL` configured).

**[RYZYKO]** Sofascore scraping is 4% complete (2000/52000). Alpha will run WITHOUT Sofascore
tactical stats for most matches. This is acceptable because the model still has 935 features
from other sources. Sofascore scraping continues in background during alpha.

### 2.8 Secrets management

**`.env` file on Pi** with restricted permissions (`chmod 600`). No Doppler, no 1Password
Connect. Rationale: solo founder, LAN-only device, not worth the tooling overhead.

Required secrets on Pi:

```env
ML_IN_SPORTS_DATABASE_URL=postgresql://sportslab:XXX@localhost:5432/sportslab
ML_IN_SPORTS_TELEGRAM_BOT_TOKEN=XXX
ML_IN_SPORTS_TELEGRAM_CHAT_ID=XXX
ML_IN_SPORTS_HEALTHCHECK_ID=XXX
B2_APPLICATION_KEY_ID=XXX
B2_APPLICATION_KEY=XXX
```

Required env on dev PC (in `.env` or shell profile):

```env
MLFLOW_TRACKING_URI=sqlite:///mlflow.db
PI_HOST=pi@192.168.x.x
```

**[RYZYKO]** Two `.env` files on two machines. Pi is on LAN only (no public IP unless
Cloudflare Tunnel is enabled), so exposure risk is lower than a VPS. Acceptable for alpha.

### 2.9 Monitoring

**healthchecks.io** (free tier: 20 checks). One check per cron job:

| Check | Expected | Alert after |
|-------|----------|-------------|
| Morning pipeline | Daily 06:00 | 2 hours late |
| Evening pipeline | Daily 23:30 | 2 hours late |
| Weekly report | Monday 07:30 | 12 hours late |
| Postgres backup | Daily 03:00 | 24 hours late |

Alert channel: **Telegram DM to founder** (healthchecks.io supports Telegram integration).

No Grafana, no Prometheus, no Loki. Logs are plain files on Pi disk, rotated weekly.
`structlog` JSON output makes them `grep`-able. SSH into Pi to inspect logs.

### 2.10 Backup and disaster recovery

**Postgres**: nightly `pg_dump` compressed, uploaded to Backblaze B2 (10 GB free).

```bash
#!/bin/bash
# scripts/backup_postgres.sh (runs on Pi)
BACKUP_DIR="/tmp/sportslab_backup"
FILENAME="sportslab_$(date +%Y%m%d_%H%M%S).sql.gz"
mkdir -p "$BACKUP_DIR"
pg_dump -U sportslab -d sportslab | gzip > "$BACKUP_DIR/$FILENAME"
b2 upload-file sportslab-backups "$BACKUP_DIR/$FILENAME" "postgres/$FILENAME"
rm -f "$BACKUP_DIR/$FILENAME"
# Keep last 30 days in B2 (lifecycle rule configured in B2 console)
```

**Features Parquet + models**: stored on Pi SSD, regenerated from database.
Not backed up separately (can be rebuilt in ~10 minutes from `sl features build`).
Production model is a copy of an artifact in MLflow on dev PC -- not a single point of failure.

**Predictions JSON + results JSON**: backed up to B2 alongside Postgres (small files, append-only).

**Recovery scenarios**:

| Failure | Recovery | Time |
|---------|----------|------|
| Pi SD card / SSD dies | Flash new Ubuntu, restore from B2 backup, SCP model from dev PC | ~2 hours |
| Pi hardware failure | Buy replacement Pi (~50 EUR) or fall back to Hetzner CX32 | 1 day (hardware) or 1 hour (Hetzner) |
| Dev PC dies | MLflow data is local only -- lost. Models on Pi still work. Retrain from scratch on new dev PC. | ~4 hours |
| Both machines die | Restore Postgres from B2 to any machine. Retrain model. | ~6 hours |

**[RYZYKO]** MLflow experiment history on the dev PC is not backed up. Acceptable for alpha
(experiments are exploratory, not irreplaceable). If this becomes valuable, add MLflow DB to
B2 backup in a later phase.

---

## 3. Model Registry (MLflow on Dev PC)

### 3.1 MLflow setup

MLflow runs on the dev PC as the single source of truth for model experiments and the model
registry. See ADR-0017 for why MLflow was pulled forward from R5.

```
MLflow on dev PC:
+-- Tracking URI: sqlite:///mlflow.db (zero maintenance)
+-- Artifact store: ./mlflow-artifacts/ (local filesystem)
+-- Experiments:
|     "football-1x2-lgb-v1"       --> runs with different hyperparams
|     "football-1x2-xgb-v2"       --> XGBoost experiments
|     "football-1x2-ensemble-v1"  --> stacking ensemble experiments
|     "football-ou25-lgb-v1"      --> O/U 2.5 market experiments (future)
+-- Model registry:
|     "football-1x2-predictor"    --> versions 1, 2, 3...
|       Version 1: stage=Archived
|       Version 2: stage=Staging
|       Version 3: stage=Production  <-- Pi uses this
|     "football-ou25-predictor"   --> versions... (future)
+-- Logged per run:
|     Params: n_estimators, learning_rate, features_count, leagues, seasons
|     Metrics: log_loss, ece, clv_mean, roi, sharpe, max_drawdown, n_bets
|     Artifacts: model.pkl, backtest_report.html, feature_importance.png
|     Tags: market=1x2, calibration=platt, kelly_fraction=0.25
+-- UI: http://localhost:5000
```

**Starting MLflow**:
```bash
cd ~/sportslab
mlflow ui --port 5000 --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlflow-artifacts
```

### 3.2 Model versioning and promotion

The MLflow Model Registry provides versioned model management:

1. **Training** (dev PC): `sl backtest run experiments/config.yaml --mlflow` trains a model,
   logs metrics/params/artifacts to MLflow, and registers the model.
2. **Staging**: new models are registered as version N with stage "None." The founder reviews
   metrics in MLflow UI and manually transitions to "Staging" for testing.
3. **Production**: after validation, the founder promotes to "Production":
   ```bash
   mlflow models transition --name "football-1x2-predictor" --version 3 --stage Production
   ```
4. **Deploy to Pi**: SCP the production model artifact to the Pi (see 3.4).
5. **Archival**: previous production versions are moved to "Archived" automatically by MLflow
   when a new version takes the "Production" stage.

**Naming convention**: `football-<market>-predictor` (e.g., `football-1x2-predictor`,
`football-ou25-predictor`).

### 3.3 Model sync: Dev PC to Pi

**SCP over SSH** is the transfer mechanism. After promoting a model to "Production":

```bash
# Option A: manual SCP
scp ./mlflow-artifacts/<run-id>/artifacts/model/model.pkl \
    pi@192.168.x.x:/app/models/production/model.pkl

# Option B: deploy script (recommended -- see scripts/deploy_model_to_pi.sh)
./scripts/deploy_model_to_pi.sh ./mlflow-artifacts/<run-id>/artifacts/model/model.pkl
```

The deploy script (`scripts/deploy_model_to_pi.sh`):

```bash
#!/bin/bash
set -euo pipefail
MODEL_PATH="${1:?Usage: deploy_model_to_pi.sh <model-path>}"
PI_HOST="${PI_HOST:-pi@raspberrypi.local}"
REMOTE_DIR="/app/models/production"

echo "Deploying model to $PI_HOST:$REMOTE_DIR"
scp "$MODEL_PATH" "$PI_HOST:$REMOTE_DIR/model.pkl"
scp "${MODEL_PATH%/*}/metadata.json" "$PI_HOST:$REMOTE_DIR/metadata.json" 2>/dev/null || true
echo "Model deployed. Pi will use it on next cron run."
echo "Verify: ssh $PI_HOST 'ls -la $REMOTE_DIR/model.pkl'"
```

**Why not other sync methods**:
- Shared network folder (SMB/NFS): config complexity not worth it for one file transfer
- MLflow model serving over HTTP: requires MLflow on Pi or dev PC always-on -- neither works
- Git-LFS: bloats repo history with binary artifacts
- Rsync: SCP is sufficient for a single file; rsync adds nothing here

**Pi storage structure**:

```
/app/models/
  production/
    model.pkl              # Current production model (LightGBM/XGBoost)
    metadata.json          # Training date, metrics, git hash, config name
  archive/                 # Previous models (optional, manual retention)
    2026-04-07_model.pkl
    2026-04-08_model.pkl
```

### 3.4 Retraining schedule

**No daily retrain on the Pi.** The Pi only does inference: it loads the model file from
`/app/models/production/model.pkl` and calls `model.predict()`.

Retraining happens on the dev PC on the founder's schedule:
- **After weekly data updates** (Tuesday odds download, Wednesday ELO update): retrain with
  latest data, compare metrics in MLflow, promote if improved.
- **After feature engineering changes**: new features --> backtest --> compare --> promote.
- **After code changes to the model pipeline**: verify model quality has not regressed.

**[HIPOTEZA]** Weekly retraining is sufficient for alpha. The model's edge comes from
structural features (team quality, form, ELO) that change slowly, not from high-frequency
signals. If live monitoring shows degradation mid-week, retrain and deploy sooner.

**When to add automated retraining**: if the founder finds manual retraining burdensome
(>1 hour/week of active attention), automate with a cron job on the dev PC that trains,
evaluates, and auto-promotes if metrics improve. Not needed at alpha scale.

### 3.5 Quality monitoring

**What to track (daily, automated on Pi):**

| Metric | Source | Alert threshold | How |
|--------|--------|----------------|-----|
| ECE (calibration) | predictions vs results | ECE > 0.08 for 7 consecutive days | Python check in evening pipeline |
| CLV (closing line value) | model prob vs Pinnacle closing | CLV < 0 for 14 consecutive days | Weekly report check |
| Hit rate | results tracker | Hit rate < 30% for 14 days | Weekly report check |
| PSI (feature drift) | drift detection module | PSI > 0.2 on any top-20 feature | Weekly check |
| Prediction count | daily pipeline | 0 predictions for 3 consecutive match days | healthchecks.io |
| Model file age | `metadata.json` timestamp | Model older than 14 days | Morning pipeline check |

**What to track (weekly, in weekly report):**

- Cumulative ROI curve
- Rolling 30-day CLV
- Rolling 30-day ECE per league
- Max drawdown (current vs historical)
- Sharpe ratio (rolling 90-day)
- Feature importance stability (top-20 features week-over-week)

**What to track (per experiment, in MLflow on dev PC):**

- log_loss, ECE, CLV mean, ROI, Sharpe ratio, max drawdown, number of bets
- Feature importance plot (logged as artifact)
- Backtest HTML report (logged as artifact)

**Alert channel**: Telegram DM to founder. No PagerDuty, no Opsgenie. It is one person.

**New alert: model staleness.** The morning pipeline on Pi reads `metadata.json` and warns
(Telegram DM) if the model is older than 14 days. This catches the case where the founder
forgets to retrain and deploy after data updates.

---

## 4. Experiment Framework (MLflow-integrated)

### 4.1 Experiment workflow (dev PC)

The experiment framework combines the existing YAML-based backtest runner with MLflow tracking.
All experiments run on the dev PC.

**Full experiment loop:**

```
1. Create YAML config: experiments/new_experiment.yaml
   (defines: leagues, seasons, models, calibration, Kelly params, evaluation metrics)

2. Run backtest with MLflow logging:
   sl backtest run experiments/new_experiment.yaml --mlflow

3. MLflow automatically logs:
   - Params: n_estimators, learning_rate, features_count, leagues, seasons, calibration_method
   - Metrics: log_loss, ece, clv_mean, roi, sharpe, max_drawdown, n_bets
   - Artifacts: model.pkl, backtest_report.html, feature_importance.png
   - Tags: market=1x2, config_file=new_experiment.yaml

4. Compare runs in MLflow UI:
   Open http://localhost:5000 --> Experiments --> sort by CLV or ROI
   Compare two runs side-by-side (MLflow built-in feature)

5. If the new model is better, promote to Production:
   mlflow models transition --name "football-1x2-predictor" --version N --stage Production

6. Deploy to Pi:
   ./scripts/deploy_model_to_pi.sh ./mlflow-artifacts/<run-id>/artifacts/model/model.pkl

7. Pi picks up the new model on its next cron run (06:00 next morning)
```

### 4.2 What MLflow adds over the previous approach

The old plan used HTML reports compared side-by-side in a browser. MLflow replaces and
improves this:

| Capability | Before (HTML only) | After (MLflow + HTML) |
|-----------|-------------------|----------------------|
| Metrics comparison | Open two HTML files, eyeball numbers | MLflow table: sort, filter, chart any metric |
| Parameter tracking | Implicit in YAML config name | Explicit: every hyperparam logged and searchable |
| Artifact storage | Files on disk, no organization | MLflow artifact store, linked to run |
| Model versioning | Manual `YYYY-MM-DD_type_vN` directories | MLflow Model Registry with stages |
| Run history | Git log + file timestamps | Full experiment history with metadata |
| Reproducibility | Git hash + YAML config | Git hash + YAML config + all params/metrics in MLflow |

The HTML reports are still generated (they provide interactive Plotly charts that MLflow's UI
does not). They are now logged as MLflow artifacts alongside the model.

### 4.3 Feature experiments

To test a new feature:

```
1. Implement feature in features/ module
2. Run leakage check: sl leakage-check run
3. Run backtest with new feature: sl backtest run experiments/new_feature.yaml --mlflow
4. Compare in MLflow UI: new run vs baseline (sort by CLV, filter by tag "market=1x2")
5. If better: merge feature code to main, promote model in MLflow, deploy to Pi
6. If worse: archive the MLflow run (it is still there for reference), discard feature branch
```

No A/B testing infrastructure needed. Walk-forward backtest IS the A/B test (on historical
data). Live A/B testing requires two parallel prediction pipelines; not worth the complexity
for alpha.

### 4.4 Reproducibility

Each experiment is reproducible via:
- **Git hash** (logged as MLflow tag + in `metadata.json`)
- **YAML config** (checked into `experiments/`, logged as MLflow artifact)
- **MLflow run ID** (unique, links to all params/metrics/artifacts)
- **Data snapshot** (deterministic -- given the same database state, `sl features build`
  produces the same Parquet)
- **Random seed** (42, hardcoded in model configs, logged as MLflow param)

### 4.5 MLflow experiment naming convention

```
Experiment name format: "football-<market>-<model>-v<N>"

Examples:
  football-1x2-lgb-v1          # LightGBM baseline for 1X2
  football-1x2-xgb-v1          # XGBoost for 1X2
  football-1x2-ensemble-v1     # Stacking ensemble for 1X2
  football-ou25-lgb-v1          # LightGBM for O/U 2.5 (future)

Run naming: auto-generated by MLflow (adjective-noun-NNN)
Run tags:
  market:        1x2 | ou25 | btts
  calibration:   platt | temperature | isotonic | none
  kelly_fraction: 0.25 | 0.5 | 1.0
  config_file:   experiments/<name>.yaml
```

---

## 5. Landing Page (Lovable)

### 5.1 Purpose

The landing page has three jobs:
1. **Explain** what SportsLab does (30-second pitch)
2. **Prove** it works (public track record)
3. **Capture** interested users (waitlist form)

It does NOT sell a product. There is no pricing page. There is no "Sign Up" button with
Stripe. The call to action is "Join the alpha waitlist."

### 5.2 Page structure

| Section | Content | Priority |
|---------|---------|----------|
| **Hero** | Headline + subheadline + waitlist CTA + hero image | Must |
| **How it works** | 3-step visual: Data -> Model -> Bet Slip | Must |
| **Track record** | Live stats: total bets, hit rate, ROI, CLV, equity curve chart | Must |
| **Methodology** | What makes SportsLab different (935 features, calibration, Kelly, CLV) | Must |
| **Coverage** | 14 leagues with team logos grid | Should |
| **Alpha access** | What you get + waitlist form (name, email, Telegram handle) | Must |
| **FAQ** | Is this financial advice? How often? What markets? Free? | Should |
| **Footer** | Legal disclaimer + contact email + social links | Must |

### 5.3 Hero section

**Headline**: "Sports predictions backed by 95,000 matches and mathematical edge."

**Subheadline**: "SportsLab uses machine learning, probability calibration, and Kelly criterion
to find value bets across 14 European football leagues. Join the free alpha."

**CTA button**: "Join the Waitlist" (scrolls to waitlist form)

**Hero image**: AI-generated (Nanobanana 2) — dark theme, abstract data visualization with
football elements, green/blue accent colors, clean and professional.

### 5.4 Track record section

This section updates weekly (manually or via script that pushes a JSON to the landing page).

Display:

```
[Total Bets: 0]  [Hit Rate: --]  [ROI: --]  [CLV: --]

"Track record starts [launch date]. Updated weekly."
```

After accumulating data (week 2+):

```
[Total Bets: 47]  [Hit Rate: 38.3%]  [ROI: +4.2%]  [CLV: +1.8%]

[Interactive equity curve chart — embedded from backtest report]
```

**[PEWNE]** The track record section is the single most important element for conversion.
Transparent, verifiable performance data is the only way to differentiate from the thousands
of Telegram tipster channels that claim 85% win rates.

### 5.5 Methodology section

Four cards:

1. **935 Features** — "xG, tactical stats, ELO ratings, FIFA squad quality, formations,
   market values, and 900+ more features from 7 data sources."
2. **Calibrated Probabilities** — "Our models don't just predict outcomes. Temperature
   scaling, Platt scaling, and isotonic regression ensure probabilities are honest."
3. **Portfolio Kelly Staking** — "Optimal stake sizing with exposure constraints.
   No gut feeling, no flat bets. Mathematics decides how much to risk."
4. **Closing Line Value** — "We track whether our predictions beat the closing line.
   CLV > 0 is the gold standard proof of profitable betting."

### 5.6 Waitlist form

Fields:
- Name (text, required)
- Email (email, required)
- Telegram handle (text, required — this is how we add them to the channel)
- "How did you hear about us?" (dropdown: Reddit, Twitter, friend, other)

Backend: Lovable form -> email notification to founder (or Tally.so embed if Lovable forms
are limited). No CRM, no Mailchimp. Manual invite process is fine for 50 users.

### 5.7 Design direction

- **Dark theme** (black/dark navy background, white text, green accents)
- **Data-forward aesthetic** — charts, numbers, grids. Not stock photos of stadiums.
- **Professional, not flashy** — target audience is technical (tipsters, ML people)
- **Mobile-first** — Telegram users will click the link on mobile
- **Reference**: score-sight-strategies.lovable.app style but darker, more data-heavy
- **No gambling imagery** (no dice, no slot machines). This is analytics, not luck.

### 5.8 Nanobanana 2 asset list

| Asset | Description | Size | Priority |
|-------|-------------|------|----------|
| Hero image | Dark theme, abstract data viz + football, green/blue | 1920x1080 | Must |
| OG image | Social share card (Twitter, Discord) | 1200x630 | Must |
| Favicon | SL monogram, green on dark | 32x32 + 192x192 | Must |
| Methodology icons (x4) | Features, Calibration, Kelly, CLV | 120x120 each | Should |
| Coverage map | Europe map with highlighted league countries | 800x600 | Nice |

### 5.9 Domain

**sportslab.dev** or **sportslab.app** (check availability).
Alternatively: **getsportslab.com** or **sportslab.io**.

**[DO SPRAWDZENIE]** Register domain before building the landing page. Lovable supports
custom domains.

Temporary (free): `sportslab.lovable.app` works for alpha launch. Custom domain can be
added later without breaking links if we set up redirects.

---

## 6. API (NOT for Alpha)

**No API for alpha.** Rationale:

1. Telegram delivery covers the alpha use case (daily bet slip to <50 users)
2. FastAPI + auth + rate limiting + docs = 2+ weeks of work that delays launch
3. Alpha users do not need programmatic access
4. Building an API before validating that predictions are profitable risks building
   infrastructure for a product nobody wants

**When to build**: R6, after 3+ months of positive CLV track record.

### 6.1 Pre-alpha API prep (zero effort now, pays off later)

The `BetRecommendation` dataclass in `prediction/models.py` is already the API response
schema. When we build FastAPI in R6, the endpoint is:

```python
@app.get("/v1/predictions/{date}")
def get_predictions(date: str) -> list[BetRecommendation]:
    predictor = DailyPredictor(...)
    return predictor.predict(dt.date.fromisoformat(date))
```

The data model is API-ready. The delivery channel (Telegram vs HTTP) is the only thing
that changes.

---

## 7. Timeline (4-Week Sprint)

### Week 1: Pi Setup + Postgres + Data Migration + Cron Pipeline

| Day | Task | Owner | Tool |
|-----|------|-------|------|
| Mon | Flash Ubuntu Server 24.04 on Pi, SSH setup, static IP, UFW | Founder | Manual |
| Mon | Register domain | Founder | Manual |
| Mon | Create Telegram bot + alpha channel | Founder | Manual |
| Tue | Install Postgres 16 on Pi, tune for 4 GB RAM (see 2.4) | Founder + Claude Code | SSH |
| Tue | Clone repo on Pi, `uv sync --no-dev`, verify `sl --help` works | Founder + Claude Code | SSH |
| Wed | Export SQLite data from dev PC, SCP to Pi, load into Postgres | Claude Code (dataeng) | Script |
| Wed | Run `sl features build` on Pi + smoke test prediction | Claude Code (dataeng) | CLI |
| Thu | Train initial model on dev PC, SCP to Pi `/app/models/production/` | Claude Code (mleng) | Code |
| Thu | Set up cron jobs on Pi (morning, evening, weekly, backup) | Claude Code (dataeng) | SSH |
| Fri | Set up healthchecks.io (4 checks + Telegram alerts) | Founder | Manual |
| Fri | Set up Backblaze B2 bucket + backup script on Pi | Claude Code (dataeng) | Script |
| Fri | End-to-end test: trigger morning pipeline on Pi, verify Telegram message | Founder | Manual |

**Week 1 exit criteria**: Pi running, Postgres loaded, model deployed, daily pipeline
executes from cron, Telegram messages delivered, healthchecks pinging, backups working.

### Week 2: MLflow Integration + Model Persistence + Deploy Script

| Day | Task | Owner | Tool |
|-----|------|-------|------|
| Mon | Set up MLflow on dev PC (sqlite backend, local artifacts) | Claude Code (mleng) | Code |
| Mon | Implement `--mlflow` flag in backtest runner (log params/metrics/artifacts) | Claude Code (mleng) | Code |
| Tue | Run full 14-league backtest on dev PC with MLflow, log baseline model | Claude Code (mleng) | CLI |
| Tue | Register baseline model in MLflow, promote to "Production" | Claude Code (mleng) | CLI |
| Wed | Write `scripts/deploy_model_to_pi.sh` (SCP model + metadata to Pi) | Claude Code (dataeng) | Code |
| Wed | Implement `--model-path` flag in DailyPredictor (load pre-trained model) | Claude Code (mleng) | Code |
| Wed | Deploy model to Pi via script, verify inference works | Founder | Manual |
| Thu | Add model staleness alert to morning pipeline (warn if model >14 days old) | Claude Code (mleng) | Code |
| Thu | Add quality checks to evening pipeline on Pi (ECE, CLV alerts) | Claude Code (mleng) | Code |
| Fri | First live morning pipeline on Pi with pre-trained model | Auto (cron) | Pipeline |
| Fri | First live evening results (if matches played) | Auto (cron) | Pipeline |

**Week 2 exit criteria**: MLflow running on dev PC, model trained and deployed to Pi via
script, inference-only pipeline live on Pi, quality monitoring active.

### Week 3: Landing Page (Lovable) + Track Record Page + Waitlist

| Day | Task | Owner | Tool |
|-----|------|-------|------|
| Mon | Write all section copy (hero, how it works, methodology, FAQ) | Founder + Grok | Text |
| Mon | Generate Nanobanana 2 images (hero, OG, favicon, icons) | Founder | Nanobanana |
| Tue | Build landing page in Lovable (all sections) | Founder | Lovable |
| Tue | Connect custom domain (or use lovable.app subdomain) | Founder | Lovable |
| Wed | Embed waitlist form (Tally.so or Lovable native) | Founder | Lovable |
| Wed | Add track record section (initially with "starting soon" message) | Founder | Lovable |
| Thu | Build track record JSON exporter (weekly metrics for landing page) | Claude Code (swe) | Code |
| Thu | Write announcement post (Reddit r/SoccerBetting, Twitter) | Founder + Grok | Text |
| Fri | Internal review: full user journey (landing -> waitlist -> Telegram -> bet slip -> results) | Founder | Manual |

**Week 3 exit criteria**: Landing page live, waitlist form working, announcement drafted,
full pipeline running on Pi for 5+ days, track record section ready.

### Week 4: Testing + 5-10 Beta Users on Telegram

| Day | Task | Owner | Tool |
|-----|------|-------|------|
| Mon | Fix any pipeline issues from week 2-3 live running | Claude Code | Code |
| Mon | Update track record on landing page with first 1-2 weeks of data | Founder | Lovable |
| Tue | Invite 5-10 friends/contacts to alpha Telegram channel (beta-beta) | Founder | Manual |
| Tue | Collect feedback, iterate on bet slip format | Founder | Manual |
| Wed | Post announcement on Reddit (r/SoccerBetting), Twitter | Founder | Manual |
| Wed | Open waitlist on landing page | Founder | Lovable |
| Thu | Process first waitlist signups, manually invite to Telegram | Founder | Manual |
| Thu | Run a second model iteration on dev PC (if new data warrants it), deploy to Pi | Founder | MLflow + SCP |
| Fri | Alpha is LIVE. Pipeline running on Pi, users receiving predictions. | -- | -- |

**Week 4 exit criteria**: Alpha launched, 10+ users in Telegram channel, pipeline stable
for 10+ consecutive days on Pi, no missed predictions, at least one model promotion cycle
completed (train on dev PC -> MLflow -> deploy to Pi).

---

## 8. Task Breakdown (Detailed)

### 8.1 Infrastructure tasks (Pi)

| ID | Task | Tool | Agent | Depends on | Estimate |
|----|------|------|-------|------------|----------|
| A1 | Flash Ubuntu Server 24.04 ARM on Pi SSD/SD, boot, static IP | Manual | Founder | -- | 1 hour |
| A2 | SSH hardening (keys only, disable password, fail2ban) | SSH | Founder | A1 | 30 min |
| A3 | Install Postgres 16 via apt, tune for 4 GB RAM | SSH | Founder | A1 | 30 min |
| A4 | Clone repo + `uv sync --no-dev` on Pi | SSH | Founder | A1 | 30 min |
| A5 | Create `.env` from template (chmod 600) | SSH | Founder | A3, A4 | 15 min |
| A6 | Run Alembic migrations on Postgres | CLI | Founder | A3, A5 | 10 min |
| A7 | Write SQLite-to-Postgres data migration script | Claude Code | dataeng | -- | 2 hours |
| A8 | SCP data from dev PC, execute migration on Pi | CLI | Founder | A6, A7 | 1 hour |
| A9 | Verify data integrity (row counts, spot checks) | CLI | Founder | A8 | 30 min |
| A10 | `sl features build` on Pi | CLI | Founder | A8 | 15 min |
| A11 | Create `/app/models/production/` dir on Pi | SSH | Founder | A1 | 5 min |
| A12 | Set up cron (morning, evening, weekly, odds, elo, backup) | SSH | Founder | A10 | 1 hour |
| A13 | Register healthchecks.io + configure 4 checks | Web | Founder | A12 | 30 min |
| A14 | Create Backblaze B2 bucket + backup script on Pi | Web + SSH | dataeng | A3 | 1 hour |
| A15 | Create Telegram bot + alpha channel | Telegram | Founder | -- | 30 min |
| A16 | Register domain | Registrar | Founder | -- | 15 min |

### 8.1b Infrastructure tasks (Dev PC)

| ID | Task | Tool | Agent | Depends on | Estimate |
|----|------|------|-------|------------|----------|
| D1 | Install MLflow (`uv add mlflow` in dev deps) | CLI | Founder | -- | 15 min |
| D2 | Start MLflow, verify UI at localhost:5000 | CLI | Founder | D1 | 10 min |
| D3 | Configure SSH key for Pi access | SSH | Founder | A1 | 15 min |
| D4 | Write `scripts/deploy_model_to_pi.sh` | Claude Code | dataeng | D3 | 30 min |
| D5 | Write `scripts/setup_pi.sh` (full Pi bootstrap script) | Claude Code | dataeng | A1-A14 | 1 hour |

### 8.2 Code changes for alpha

| ID | Task | Tool | Agent | Depends on | Estimate |
|----|------|------|-------|------------|----------|
| C1 | MLflow integration in backtest runner (`--mlflow` flag) | Claude Code | mleng | D1 | 3 hours |
| C2 | `--model-path` flag in DailyPredictor (load pre-trained model, skip training) | Claude Code | mleng | -- | 2 hours |
| C3 | Model staleness alert in morning pipeline (warn if model >14 days old) | Claude Code | mleng | C2 | 30 min |
| C4 | Quality alerts: ECE/CLV threshold check in evening pipeline, Telegram DM | Claude Code | mleng | -- | 2 hours |
| C5 | PSI drift check: weekly cron, Telegram alert if drift detected | Claude Code | mleng | -- | 1 hour |
| C6 | Track record JSON exporter: weekly script outputs metrics JSON for landing page | Claude Code | swe | -- | 2 hours |
| C7 | SQLite-to-Postgres migration script (task A7 implementation) | Claude Code | dataeng | -- | 2 hours |
| C8 | Weekly report: add CLV trend chart + feature importance stability | Claude Code | mleng | -- | 2 hours |
| C9 | Enhance bet slip Telegram format (add league emoji, odds source, confidence) | Claude Code | swe | -- | 1 hour |

**Total code work**: ~16 hours of Claude Code time.

### 8.2b Integration code plan (detailed)

**a) MLflow integration in backtest runner (C1)**

After `BacktestRunner.run()` completes, log everything to MLflow:

```python
# In backtest/runner.py, add --mlflow flag
import mlflow

if config.mlflow_enabled:
    mlflow.set_experiment(config.name)  # e.g., "football-1x2-lgb-v1"
    with mlflow.start_run():
        mlflow.log_params({
            "n_estimators": config.model.n_estimators,
            "learning_rate": config.model.learning_rate,
            "features_count": len(config.features),
            "leagues": ",".join(config.leagues),
            "seasons": config.seasons,
            "calibration": config.calibration.method,
            "kelly_fraction": config.kelly.fraction,
        })
        mlflow.log_metrics({
            "log_loss": results.log_loss,
            "ece": results.ece,
            "clv_mean": results.clv_mean,
            "roi": results.roi,
            "sharpe": results.sharpe,
            "max_drawdown": results.max_drawdown,
            "n_bets": results.n_bets,
        })
        mlflow.log_artifact(report_html_path)
        mlflow.log_artifact(feature_importance_path)
        # Log model to registry
        mlflow.sklearn.log_model(
            model, "model",
            registered_model_name=f"football-{config.market}-predictor",
        )
```

**b) Model loading in DailyPredictor (C2)**

Add `--model-path` option to load a pre-trained model instead of training fresh:

```python
# In prediction/daily.py
class DailyPredictor:
    def __init__(
        self,
        model_path: Path | None = None,
        # ... existing params
    ) -> None:
        if model_path is not None:
            self._model = self._load_pretrained_model(model_path)
            self._skip_training = True
        # ... existing init

    def _load_pretrained_model(self, model_path: Path) -> Any:
        """Load a pre-trained model from disk (pickle or MLflow format)."""
        import pickle
        with model_path.open("rb") as f:
            return pickle.load(f)
```

**c) Deploy script (D4)**

`scripts/deploy_model_to_pi.sh` -- see section 3.3 for the full script.

**d) Pi setup script (D5)**

`scripts/setup_pi.sh` -- automates the full Pi bootstrap:

```bash
#!/bin/bash
set -euo pipefail
# Install on fresh Raspberry Pi 4 Ubuntu Server 24.04
echo "=== SportsLab Pi Setup ==="

# System packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y postgresql postgresql-client python3.11 python3.11-venv git

# Tune Postgres for 4GB RAM
sudo sed -i "s/#shared_buffers = 128MB/shared_buffers = 256MB/" /etc/postgresql/16/main/postgresql.conf
sudo sed -i "s/#work_mem = 4MB/work_mem = 32MB/" /etc/postgresql/16/main/postgresql.conf
sudo systemctl restart postgresql

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Clone repo
git clone <DEPLOY_KEY_URL> /app/sportslab
cd /app/sportslab

# Install deps (inference-only, no dev deps, no TabPFN)
uv sync --no-dev

# Setup Postgres
sudo -u postgres createuser sportslab
sudo -u postgres createdb -O sportslab sportslab

# Alembic migrations
cd /app/sportslab && uv run alembic upgrade head

# Create model directory
mkdir -p /app/models/production

# Create log directory
sudo mkdir -p /var/log/sportslab
sudo chown $USER:$USER /var/log/sportslab

# Install crontab
crontab /app/sportslab/infra/crontab.pi.example

echo "=== Setup complete. Next: load data, deploy model, create .env ==="
```

### 8.3 Landing page tasks

| ID | Task | Tool | Agent | Depends on | Estimate |
|----|------|------|-------|------------|----------|
| L1 | Write all section copy (hero, how it works, methodology, FAQ) | Grok + Founder | Founder | -- | 3 hours |
| L2 | Generate hero image | Nanobanana 2 | Founder | -- | 30 min |
| L3 | Generate OG card + favicon | Nanobanana 2 | Founder | -- | 30 min |
| L4 | Generate methodology icons (x4) | Nanobanana 2 | Founder | -- | 30 min |
| L5 | Build landing page in Lovable (all sections) | Lovable | Founder | L1-L4 | 4 hours |
| L6 | Embed waitlist form (Tally.so) | Lovable | Founder | L5 | 30 min |
| L7 | Connect custom domain or configure subdomain | Lovable | Founder | L5, A16 | 30 min |
| L8 | Add track record section with live data | Lovable | Founder | L5, C5 | 1 hour |
| L9 | Mobile responsiveness QA | Browser | Founder | L5 | 30 min |

### 8.4 Launch tasks

| ID | Task | Tool | Agent | Depends on | Estimate |
|----|------|------|-------|------------|----------|
| X1 | Write Reddit announcement (r/SoccerBetting, r/sportsbook) | Grok + Founder | Founder | L5 | 1 hour |
| X2 | Write Twitter launch thread | Grok + Founder | Founder | L5 | 30 min |
| X3 | Invite beta-beta group (5-10 friends) | Telegram | Founder | A15 | 15 min |
| X4 | Collect and action feedback from beta-beta | Manual | Founder | X3 | ongoing |
| X5 | Post Reddit announcement | Reddit | Founder | X1, X4 | 15 min |
| X6 | Open waitlist on landing page | Lovable | Founder | L5, X5 | 5 min |
| X7 | Process waitlist signups, invite to Telegram | Manual | Founder | X6 | ongoing |

---

## 9. Risks and Mitigations

### 9.1 Critical risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Model produces bad predictions live** (negative CLV) | Medium | High -- destroys credibility with alpha users | Monitor daily. If CLV < -3% after 50 bets, pause public predictions and revert to paper trading. Be transparent with alpha users. |
| **Scraper breaks** (STS, football-data.co.uk, Understat) | Medium | Medium -- no predictions that day | healthchecks.io alerts within 2 hours. Manual intervention. Mock predictions NOT sent (better to skip a day than send garbage). |
| **Pi goes down** (power loss, SD card failure, network) | Medium | Medium -- missed predictions | healthchecks.io alerts. USB SSD mitigates SD card wear. UPS recommended but not required for alpha. Backup restore to replacement Pi or Hetzner CX32 in <2 hours. |
| **Pi OOM (4 GB RAM exhausted)** | Low | Medium -- pipeline crash, missed predictions | Conservative Postgres tuning (shared_buffers=256MB). Inference uses <200 MB. Total expected ~2.2 GB of 4 GB. OOM kill threshold is ~3.5 GB. |
| **Telegram bot token leaked** | Low | High -- someone impersonates the bot | Token in `.env` with `chmod 600`. If leaked: revoke via BotFather immediately, create new bot, update `.env`. |
| **Zero waitlist signups** | Medium | Low -- alpha still runs for self-validation | This is R3 (Proof of Edge). Even with zero users, the pipeline validates the model live. Users are a bonus, not a requirement. |

### 9.2 Medium risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **football-data.co.uk changes CSV format** | Low | Medium -- odds data breaks | Pin known-good column schema. Validate columns before import. Alert on schema mismatch. |
| **Sofascore blocks scraping** | Medium | Low for alpha -- Sofascore data is <4% complete anyway | Continue without Sofascore. Other 7 data sources provide 900+ features. Revisit in R5. |
| **Overfitting to historical data** (good backtest, bad live) | Medium | High -- core thesis fails | Walk-forward backtest design mitigates this. CLV tracking is the live overfitting detector. If CLV < 0 sustained, go back to R2. |
| **Model staleness** (founder forgets to retrain/deploy) | Medium | Medium -- predictions degrade as data ages | Morning pipeline checks model age from metadata.json. Telegram alert if model >14 days old. |
| **Dev PC unavailable for retraining** (hardware failure, travel) | Low | Low -- Pi continues with current model | Pi runs autonomously with the deployed model. No dev PC needed for daily pipeline. Retraining can wait until dev PC is available. |
| **Legal concerns about providing betting tips** | Low | Medium -- could require disclaimers | Landing page includes disclaimer: "Not financial advice. Past performance does not guarantee future results. Gambling involves risk of loss." Formal legal review deferred to R6 when money changes hands. |

### 9.3 Low risks (documented for completeness)

| Risk | Mitigation |
|------|------------|
| Pi SSD/SD card full | 120 GB SSD, data grows ~50 MB/month. Alert at 70% (cron check). |
| Log files fill disk | Weekly rotation, 30-day retention. `/var/log/sportslab/` separate from data. |
| SSL certificate expires | Lovable handles SSL for landing page. Pi does not serve HTTP (only cron + Telegram). |
| Alpha user abuses predictions (resells) | Acceptable risk for free alpha. Terms on landing page: "For personal use only." |
| Pi thermal throttling (summer heat) | Pi 4 throttles at 80C. Passive heatsink recommended. Indoor LAN environment is typically fine. |
| MLflow data loss on dev PC | Experiment history is exploratory, not irreplaceable. Models deployed to Pi survive dev PC failure. Add MLflow DB to B2 backup if history becomes valuable. |

---

## 10. Success Criteria for Alpha

Alpha is considered successful if, after 4 weeks of live operation:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pipeline uptime | >95% (missed <2 days in 28) | healthchecks.io log |
| Predictions generated | >80% of match days | `reports/predictions/` file count |
| CLV | >0 (any positive number) | Weekly report |
| Alpha users | >10 in Telegram channel | Telegram member count |
| Waitlist signups | >25 | Tally.so form submissions |
| Zero critical bugs | No data corruption, no wrong predictions sent | Manual review |

### What happens after alpha

| Outcome | Next step |
|---------|-----------|
| CLV > 0 sustained, users engaged | Continue to R4 (full automation) then R6 (product + billing) |
| CLV ~0, inconclusive | Continue running, iterate on model (back to R2 experiments) |
| CLV < 0 sustained | Pause alpha, go back to R2. Be honest with alpha users. |
| Strong user interest but bad model | Focus on model improvement (R2/R3), keep users warm on waitlist |

---

## 11. Architecture Decisions

### 11.1 Dual-machine architecture (Pi + Dev PC)

See `docs/architecture/adr-0017-dual-machine-pi-dev.md` for the full ADR.

### 11.2 Alpha Delivery via Telegram

This section serves as an inline ADR (extracted to `docs/architecture/adr-0016-alpha-delivery-telegram.md`).

### Context

We need to deliver daily predictions to alpha users. Options: email, Telegram, Discord,
web dashboard, API.

### Options considered

1. **Telegram channel** — already built (TelegramNotifier, bet slip renderer, results renderer)
2. **Email** — requires email service (SendGrid/Resend), HTML email templates, deliverability
3. **Discord** — similar to Telegram but smaller footprint in Polish betting community
4. **Web dashboard** — requires FastAPI + frontend, weeks of work
5. **API** — requires auth, rate limiting, docs

### Decision

**Telegram.** It is already implemented. The `notify_cmd.py`, `TelegramNotifier`, bet slip
and results renderers all exist and are tested. Zero additional code needed for delivery.
Polish betting community is heavily Telegram-native. Invite-only channel provides natural
access control.

### Consequences

- Positive: ships in days, not weeks. Zero new code for the delivery mechanism.
- Positive: natural mobile experience (users get push notifications).
- Negative: no programmatic access for alpha users (acceptable — they are evaluating, not integrating).
- Negative: limited formatting (Markdown, no interactive charts). Mitigated by linking to HTML reports.
- Neutral: when API launches in R6, Telegram becomes one of many channels, not the only one.

---

## 12. What We Are NOT Deciding (Explicitly Deferred)

| Decision | Deferred to | Reason |
|----------|-------------|--------|
| API framework (FastAPI vs Litestar) | R6 | No API in alpha |
| Auth provider (Clerk vs Auth0 vs Supabase) | R6 | No auth in alpha |
| Payment provider (Stripe vs Paddle) | R6 | No billing in alpha |
| Multi-sport expansion | R5 | Football only in alpha |
| Landing page framework (Lovable vs Framer vs Next.js) | Post-alpha | Lovable for speed now; migrate if needed |
| ~~MLflow vs custom model registry~~ | ~~R5~~ | **Decided**: MLflow on dev PC (ADR-0017) |
| Kubernetes vs Docker Compose vs bare metal | Post-alpha | Bare metal cron on Pi is sufficient |
| O/U 2.5 and BTTS markets | Alpha week 3-4 | 1X2 first, then expand if stable |
| Hetzner VPS as Pi replacement | If Pi proves unreliable | Migration path documented in ADR-0017 |

---

## 13. Cost Summary

### Monthly recurring

| Item | Monthly cost | Notes |
|------|-------------|-------|
| Raspberry Pi 4 | 0 EUR | Already owned |
| Dev PC | 0 EUR | Already owned |
| MLflow | 0 EUR | Self-hosted on dev PC |
| Domain | ~1 EUR/month (12 EUR/year) | .dev or .app |
| Backblaze B2 | 0 EUR | Free tier (10 GB) |
| healthchecks.io | 0 EUR | Free tier (20 checks) |
| Telegram bot | 0 EUR | Free |
| Lovable | 0 EUR | Free tier for alpha |
| Electricity (Pi 24/7) | ~1 EUR | 5W * 24h * 30d = 3.6 kWh at ~0.25 EUR/kWh |
| **Total monthly** | **~2 EUR/month** | |

### One-time costs

| Item | Cost | Notes |
|------|------|-------|
| USB3 SSD (120 GB) | ~20 EUR | Recommended for Pi (replaces microSD for Postgres) |
| Domain registration | ~10 EUR/year | First year |
| **Total one-time** | **~30 EUR** | |

### Comparison with original plan

| | Original (Hetzner) | New (Pi + Dev PC) | Savings |
|---|---|---|---|
| Monthly | ~23 EUR | ~2 EUR | 21 EUR/month |
| First year | ~276 EUR + 30 EUR = 306 EUR | ~24 EUR + 30 EUR = 54 EUR | 252 EUR/year |

This is a significant cost reduction that makes the alpha essentially free to run. If the Pi
proves unreliable, Hetzner CX32 is a 1-hour migration away (see ADR-0017 recovery scenarios).

# ML Roadmap Long-Term — MLOps Automation (Alpha → V3)

> **Author:** MLEng (MLOps specialisation)
> **Status:** Proposal · 2026-04-22
> **Scope:** Automation roadmap from Alpha (week 0) to V3 (month 24)
> **North star:** Founder spends **<1 h/week** on ML operations by end of Beta, **<15 min/week** by V1, **<0 manual touches outside strategic decisions** by V2
> **Anti-goal:** building a big-tech MLOps cathedral on a Raspberry Pi. Every automation must pay back more founder hours than it costs to run.

---

## 0. Reading guide

This document is organised around **touchpoints**, not tools. Tools come and go. The question "who decides when to retrain?" is permanent. For each of the 10 manual touchpoints we trace the path Alpha → Beta → V1 → V2 → V3.

Phase horizons in this document:

- **Alpha** = weeks 0-2 (launch window, 5-10 beta users, Pi + Dev PC, ADR-0017)
- **Beta** = months 1-6 (50-200 users, quad-machine ADR-0019 + possibly Hetzner)
- **V1** = months 6-12 (real paid product, 200-1000 users, full MLOps pipeline)
- **V2** = months 12-18 (multi-model fleet, multi-sport, self-healing)
- **V3** = months 18-24 (self-tuning, causal monitoring, team of 2-3 ppl)

All cost estimates in EUR/month unless stated otherwise. Founder-hour estimates are **per week** unless stated otherwise.

---

## 1. TL;DR — 10 automation milestones

1. **Alpha (week 2):** Evening-cron produces daily Telegram slip with zero founder involvement except "ack" on alerts. **Founder-hour baseline: ~6 h/week on ML ops.**
2. **Alpha (week 2):** GitHub Actions runs `sl backtest run experiments/quick_test.yaml` on every PR touching `features/`, `models/`, `processing/` — blocks merge on >3% log-loss regression or >0.02 ECE regression.
3. **Beta (month 2):** Auto-promotion for low-risk model candidates — any candidate passing all 7 promotion gates with SHAP top-10 overlap ≥90% is promoted to Production without human click; risky changes still require founder + DrMat co-sign.
4. **Beta (month 3):** Great Expectations suites gate every scrape batch — bad data is quarantined, never reaches feature materialisation, Telegram alert fires on >2% rows rejected.
5. **Beta (month 4):** Drift-triggered retrain — nightly PSI check replaces bi-weekly cron; retrain fires only when drift crosses threshold or 30 days elapsed, not on calendar alone.
6. **V1 (month 7):** Canary deployment on Pi — 10% of predictions served by challenger for 7 days, statistical decision auto-promotes or auto-rolls-back; founder sees summary email only.
7. **V1 (month 9):** Feature store (Feast or custom Postgres-backed) unifies training-offline and serving-online feature flows; drift between the two environments drops to zero by construction.
8. **V2 (month 14):** Multi-model fleet — per-league or per-market models deployed independently, each with its own promotion gate; worst-performing sub-model auto-rolls-back without touching the rest.
9. **V2 (month 16):** Self-healing pipeline — scraper failure auto-retries with exponential back-off, dead-letter queue re-processes on schedule, silent failures impossible because SLO dashboards page on freshness breach.
10. **V3 (month 22):** Causal monitoring — when log-loss regresses, the system auto-attributes it (feature drift vs label drift vs market regime change vs scraper bug) and files a Linear issue with the attribution; founder only reads the report.

**Founder-hour trajectory:** 6 h/week (alpha) → 3 h/week (end beta) → 1 h/week (end V1) → 15 min/week (end V2) → strategic-only (V3).

---

## 2. Current manual touchpoints — inventory

All figures are **realistic weekly founder effort** assuming a working alpha with daily Telegram slips and 2 beta users giving occasional feedback. Numbers come from mleng persona experience on similar stacks; calibrate after alpha week 2.

| # | Touchpoint | Current flow (manual) | Weekly founder time (alpha) | Biggest pain |
|---|-----------|-----------------------|------------------------------|--------------|
| 1 | **Experiment runner** | Type `sl backtest run experiments/alpha_baseline_1x2.yaml --mlflow` on Dev PC, wait, eyeball metrics, paste to Notion. | 90 min | No pattern for parallel seed sweeps; reproducibility after 3 months = prayer. |
| 2 | **MLflow run review** | Open MLflow UI, compare 3-5 runs by hand, screenshot reliability diagram, paste to DrMat in Telegram. | 45 min | Comparison is visual, not statistical (no DeLong, no BH). |
| 3 | **Promotion decision** | Read run description, cross-check against 7 gates in mleng.md, ping DrMat, both sign off in MLflow tags. | 30 min per candidate | Gates live in markdown, not code — easy to skip one when tired. |
| 4 | **Deploy to Pi** | Run `scripts/deploy_model_to_pi.sh` on Dev PC over Tailscale, watch logs, verify symlink, smoke test on Pi. | 20 min per deploy | sha256 check is scripted but human must eyeball SCP progress. |
| 5 | **Monitoring alert review** | Telegram alert fires, founder opens Grafana (when it exists), squints, decides action. | 60 min | No triage lane — ECE warning and pipeline crash look identical in Telegram. |
| 6 | **Rollback decision** | When alert screams, founder runs `deploy_model_to_pi.sh --rollback`, pings DrMat post-hoc. | 0 min most weeks, **60 min when it fires** | High-stakes decision under stress; no pre-flight sim to verify rollback target. |
| 7 | **Feature addition** | Write feature extractor → add to config → rerun backtest → diff parquet → update feature list markdown by hand. | 30 min per feature | Feature lineage invisible; "which features did model v3 use?" requires git archaeology. |
| 8 | **Scraper health checks** | Founder opens scraper logs on laptop, greps for errors, restarts service, verifies fresh rows in Postgres. | 45 min | No SLO on freshness — finds out data is stale only when prediction pipeline throws. |
| 9 | **Data quality audits** | Spot-check — founder writes ad-hoc SQL when "numbers look off," nothing systematic. | 15 min + incident-driven spikes | Bad rows silently poison features; detected only through CLV drop 2 weeks later. |
| 10 | **Beta feedback → iteration** | User says "your OU picks are suspicious" in Telegram → founder opens notebook → eyeballs → maybe files ticket. | 30-90 min per report | No funnel from feedback to experiment; reports evaporate. |

**Total alpha baseline: ~6 h/week**, spiking to ~10 h during incident weeks. This is the number to drive down.

---

## 3. Alpha automation (2-week scope, weeks 0-2)

**Goal:** make the product runnable by one person with nightly sleep. Nothing fancy, nothing that needs another paid SaaS, nothing that blocks launch.

### 3.1 Scheduled pipeline (touchpoint 1, 2, 4, 5)

**Stack:** cron on Pi (ADR-0013) + existing `sl` Typer CLI + MLflow on Dev PC + Telegram bot (A-13).

```
# /etc/cron.d/sportslab on Pi
05:30  sportslab  sl pipeline fetch-odds    >> /var/log/sl/fetch.log 2>&1
06:00  sportslab  sl pipeline predict-daily >> /var/log/sl/predict.log 2>&1
06:30  sportslab  sl pipeline kelly-stakes  >> /var/log/sl/stakes.log 2>&1
07:00  sportslab  sl pipeline send-telegram >> /var/log/sl/send.log 2>&1
23:00  sportslab  sl pipeline settle-yday   >> /var/log/sl/settle.log 2>&1
23:30  sportslab  sl pipeline track-clv     >> /var/log/sl/clv.log 2>&1
```

Each command is idempotent, wrapped in `try/except`, emits a single structured-log line with `run_id` + `status`, and pings a `healthchecks.io` endpoint on success. **No success ping within 15 min of schedule = Telegram alert.** That is the entire monitoring loop for alpha.

**Automation win:** replaces the daily "did the pipeline run?" check (~15 min/day = 1.75 h/week) with a single mobile-phone notification if something failed.

### 3.2 CI validation gate (touchpoint 7)

On every PR touching `packages/ml-in-sports/src/ml_in_sports/{features,models,processing}/`:

```yaml
# .github/workflows/ml-regression-gate.yml
name: ml-regression-gate
on:
  pull_request:
    paths:
      - 'packages/ml-in-sports/src/ml_in_sports/features/**'
      - 'packages/ml-in-sports/src/ml_in_sports/models/**'
      - 'packages/ml-in-sports/src/ml_in_sports/processing/**'
jobs:
  quick-backtest:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --all-extras --dev
      - run: uv run sl backtest run experiments/quick_test.yaml --mlflow-uri=file://./mlruns
      - run: uv run python scripts/ci_regression_check.py --baseline=artifacts/baseline_metrics.json --current=./mlruns/latest --threshold-logloss=0.03 --threshold-ece=0.02
      - uses: actions/github-script@v7
        if: always()
        with:
          script: |
            const comment = require('fs').readFileSync('./mlruns/latest/pr_comment.md', 'utf-8');
            github.rest.issues.createComment({ issue_number: context.issue.number, owner: context.repo.owner, repo: context.repo.repo, body: comment });
```

`experiments/quick_test.yaml` is a **5-minute** config: 1 league (Premier League), 2 seasons (2023-2024), 3 walk-forward folds, no Optuna, fixed hyperparams. That's enough to catch any regression that matters for promotion.

**`artifacts/baseline_metrics.json`** is refreshed on merge-to-main via a follow-up job — so the comparison baseline is always the current production model, not stale numbers.

**Automation win:** eliminates "I merged a feature and silently broke calibration on Serie A" — catches before merge, no need to notice three weeks later when CLV craters.

### 3.3 Promotion gate script (touchpoint 3)

Instead of 7 gates in markdown, one Python CLI:

```bash
uv run sl promote check --mlflow-run-id=<RUN_ID> --market=1x2 --incumbent=production/current
```

Returns exit 0 and a machine-readable JSON report:

```json
{
  "passes_all": true,
  "gates": {
    "ace_overall": {"value": 0.042, "threshold": 0.05, "pass": true},
    "ace_per_league": {"max_value": 0.081, "threshold": 0.10, "pass": true},
    "clv_walk_forward": {"value": 0.014, "threshold": 0.0, "pass": true},
    "log_loss_vs_incumbent": {"delta": -0.0034, "bh_adjusted_p": 0.041, "pass": true},
    "shap_top10_overlap": {"value": 0.82, "threshold": 0.70, "pass": true},
    "leakage_sl_run": {"signals": 0, "pass": true},
    "human_cosign": {"mateusz": false, "drmat": false, "pass": false}
  },
  "blocking_reason": "Missing human co-sign (Mateusz, DrMat)"
}
```

Human co-sign stays manual in alpha — founder tags the MLflow run `mateusz_cosign=true`, DrMat tags `drmat_cosign=true`, script reads both. Nothing auto-promotes in alpha.

**Automation win:** replaces "let me go through the gates list one by one" (~30 min) with "the CLI tells me which gate blocks, in 10s." Sets foundation for auto-promotion in beta.

### 3.4 Rollback pre-flight (touchpoint 6)

Before every deploy, `deploy_model_to_pi.sh` now does a dry-run rollback simulation:

```bash
# inside deploy_model_to_pi.sh, before actual deploy:
ssh pi "ls /app/models/archive/ && sl pipeline dry-run --model=/app/models/archive/<previous> --fixtures-today"
```

If the previous model can't even load on today's fixtures, abort the deploy — a rollback target that doesn't work is worse than no rollback target.

**Automation win:** when the 4 AM rollback fires, founder doesn't need to pray the previous archive still runs.

### 3.5 Experiment runner skeleton (touchpoint 1 foundation)

**Not full automation yet** — but the skeleton for beta is laid down now. `experiments/*.yaml` is the declarative spec. Each YAML contains:

```yaml
meta:
  name: alpha_baseline_1x2
  purpose: "Alpha production candidate for 1X2"
  owner: mleng
  created: 2026-04-22
data:
  seasons: [2019, 2020, 2021, 2022, 2023, 2024, 2025]
  leagues: [PL, ES, IT, DE, FR, NL, PT, BE, TR, GR, RU, UA, CZ, SC]
  markets: [1x2]
cv:
  strategy: walk_forward_expanding
  embargo_days: 7
  min_folds: 3
model:
  type: lightgbm
  seed: 42
  # ... rest from ml_experiments_alpha.md §2
calibration:
  method: selector
  candidates: [dirichlet, temperature, isotonic]
gates:
  ace_overall_max: 0.05
  clv_min: 0.0
  log_loss_rel_improvement_min: 0.03
mlflow:
  experiment: alpha
  tags: { market: 1x2, phase: alpha }
```

`sl backtest run <yaml>` is the only entry point. No hand-written Python experiment scripts. **Every run is reproducible from the YAML + git SHA + data snapshot hash.**

**Automation win:** kills the "wait what config produced that Nov 12 run?" problem on day one.

### 3.6 Alpha-scope failure fallbacks

Small enough that they fit in one line each:

- **Cron job dies silently** → healthchecks.io ping missing → Telegram alert. Fallback: founder manually runs `sl pipeline predict-daily` from laptop.
- **Dev PC off, CI needs data** → CI uses a fixture dataset committed to `tests/fixtures/mini_dataset.parquet`. Slower drift-detection, but tests still run.
- **MLflow local store corrupted** → runs pushed to a second location (Backblaze B2 backup, A-11). Worst case: lose last 7 days of runs, not everything.
- **Pi fails hardware** → ADR-0019 quad-machine plan: laptop takes over pipeline from /app/models/production/current synced via syncthing.

### 3.7 Alpha cost

- Dev PC: owned (0 EUR)
- Pi + SSD: owned (0 EUR)
- Tailscale: free tier (0 EUR)
- GitHub Actions: 2000 free min/month is way more than we need (0 EUR)
- MLflow: local SQLite + artifact dir on Dev PC (0 EUR)
- healthchecks.io: free tier (0 EUR)
- **Total alpha infra cost: 0 EUR/month.** This is intentional. We don't pay for MLOps until there's revenue.

### 3.8 Alpha founder-hour target

**From 6 h/week to ~3 h/week by end of alpha (week 2).** Remaining 3 h: manual MLflow review, promotion co-sign, feedback triage. All three planned for beta.

---

## 4. Beta automation (months 1-6)

**Goal:** zero-touch pipeline for the common case, founder only touches exceptions. By end of beta, founder-hour budget ≤1.5 h/week.

### 4.1 A — Experiment runner (scheduled)

**Problem:** in alpha, founder still manually triggers every experiment on Dev PC.
**Beta solution:** GitHub Actions + self-hosted runner on Dev PC (or free VM from ADR-0019). Experiments trigger on:

1. **File change** — a new `experiments/*.yaml` merged to main auto-runs on VM, posts MLflow link + HTML report to Linear issue.
2. **Cron schedule** — each experiment YAML has `schedule: "0 3 * * SUN"` to rerun weekly against latest data.
3. **Drift trigger** — when PSI breaches threshold for any feature, a retrain experiment auto-schedules against the feature set last touched.

**Artifact:** every run generates `report_<run_id>.html` via Plotly (ADR-0004) — reliability diagram, SHAP summary, CLV walk-forward, per-league breakdown. Posted as Linear comment on the spawning issue. **Founder never opens MLflow UI unless debugging.**

**Fallback:** if runner dies, cron on Pi retries once; after 2 failures, Telegram alert and founder intervenes.

### 4.2 A — Auto-promotion for low-risk candidates

**Split candidates into 3 risk tiers:**

| Tier | Definition | Auto-promotion? |
|------|------------|-----------------|
| **Safe** | SHAP top-10 overlap ≥90% vs production, no new features, same market, ACE delta <0.01 | Yes — no human click |
| **Moderate** | SHAP overlap 70-90%, or same features but new calibrator, or market extension | Founder click only (1-factor) |
| **Risky** | Any SHAP overlap <70%, new feature families, model family change (LGBM→ensemble), first deployment for a market | Founder + DrMat co-sign |

All 7 gates from mleng.md must still pass. Tier gates are *additional* friction for high-risk changes; they never lower the bar.

**Implementation:** `sl promote check` (built in alpha 3.3) extended with `--tier` flag. A GitHub Actions job on MLflow `Staging` model version detects tier, runs gates, promotes + opens a PR summary in Linear.

**Fallback:** any time the tier classifier is uncertain (SHAP comparison fails, previous model unavailable), default to **Risky tier** — "uncertain = ask human" is the safe default.

### 4.3 A — A/B testing framework (shadow mode)

**Problem:** founder cannot know whether a new model is actually better until 500+ bets settle, which takes weeks.
**Beta solution:** shadow mode — challenger model predicts on every fixture alongside champion, but only champion's picks are sent. Both logged to Postgres. After 50-100 shadow predictions, `sl shadow analyse` runs paired DeLong test + CLV comparison.

**Decision rule:**
- Shadow CLV ≥ champion CLV by 1% AND DeLong BH-adjusted p <0.1 → auto-promote challenger.
- Shadow CLV 0-1% better or not significant → stays shadow, reruns weekly.
- Shadow CLV materially worse for 2 consecutive weeks → retire challenger, open Linear with root-cause.

**Pi 4GB RAM constraint (beta answer to task question 3):**
On Pi, running both champion and challenger LightGBM simultaneously is tight but feasible. Benchmarks: LGBM 2000-tree model = ~180 MB residual, predictions are streaming, no batch blowup. **Hard limit: max 2 concurrent models on Pi.** If we need 3+ challengers, they queue behind champion in batch inference. For ensemble families, we run predictions serially within the daily cron slot — we have 30 min before slip-send time, plenty for 3 serial predictions on 50 fixtures.

**Fallback:** Pi OOM on shadow → auto-disable shadow mode, log event, Telegram "shadow mode off due to RAM; run on VM instead."

### 4.4 A — Hyperparameter sweep with Optuna

**Problem:** alpha uses fixed hyperparams (ml_experiments_alpha.md §2.1). Beta needs to search.
**Beta solution:** Optuna `MedianPruner` sweep on free VM (ADR-0019), 100 trials per sweep, MLflow autologger integration. Sweep runs weekly overnight. Best trial auto-enters staging as challenger.

**Time budget:** 1 full sweep = ~8h on VM = weekly job Sunday 01:00-09:00 UTC, done before Monday predictions. If VM disappears (free-tier risk per ADR-0019), sweep falls back to Dev PC with reduced trials (30).

### 4.5 B — Feature store (Feast or custom)

**Problem:** alpha has 935 features defined in scattered `*.py` extractor files; feature set for any given run is only recoverable via the experiment YAML + git SHA.
**Beta solution:** pick one of two paths (build-vs-buy decision in §9).

**Option B1 (preferred): Custom Postgres-backed feature registry**
- `feature_definitions` table: name, type, extractor_module, extractor_version, owner, created_at, deprecated_at
- `feature_sets` table: name, version, feature_names[], created_at — snapshots a set at training time
- `feature_values` table: partitioned by (sport, season), columns = feature_values JSONB per match_id
- Training reads materialised parquet cache; serving reads from `feature_values` directly
- No Feast operational overhead; complexity budget = 1 dev

**Option B2: Feast OSS**
- Declarative `feast feature_store.yaml` with offline store = Postgres, online store = Redis
- Nicer SDK, standard industry pattern
- Adds Redis (100 MB footprint, Pi can't host → VM dep), adds Feast server process
- Kills operational simplicity ADR-0013 fought for

**Recommendation: start with B1 in beta month 3**, reevaluate when team grows to 2+ devs. Feast is nice when you have 10 feature engineers; with 1 it's friction. If we need Feast later, `feature_definitions` → `feast_feature_view.py` codegen is <1 day of work.

**Failure fallback (Feast):**
- If complexity: stay on B1 (Postgres registry); 935 features in JSONB is fine at our scale.
- If perf: Redis sidecar on VM for top-50 hot features, Postgres for rest.
- If drift between offline/online: weekly parity audit job that samples 100 matches and compares serving features to training features; any >0.01 delta files Linear issue auto-tagged `bug/feature-parity`.
- **Bailout:** >3 months post-migration and founder spends >2h/week diffing features → migrate back to B1 or accept the bill for a part-time MLOps contractor.

### 4.6 C — Data quality automation

**Problem:** alpha has zero data-quality gates; bad scrape silently poisons features.
**Beta solution:** Great Expectations suite gated into the ingestion flow.

```
scrape → stage in staging_matches table →
  GE suite runs (schema, types, nulls, distribution, duplicates) →
  pass: INSERT into matches;
  fail: INSERT into matches_quarantine + Telegram alert
```

Suites per source:
- `footballdata_co_uk_odds.json` — 47 columns, schema strict, odds range [1.01, 50.0], no duplicate (match_id, bookmaker_id)
- `sofascore_matches.json` — event IDs unique, timestamps within [today-365, today+7]
- `pinnacle_closing.json` — closing odds present for matches with `kickoff < now - 1h`

**SLO dashboard:** `last_update_at` per source, per league, per season. Breach → Telegram. **Founder never discovers stale data from a bet result.**

**Fallback:** GE suite itself fails (bug in the suite, not the data) → suite marked `draft` via config flag, data still ingested, founder gets alert to fix the suite. Don't block the pipeline on a broken guard.

### 4.7 D — Monitoring + observability (Grafana)

**Problem:** alpha monitoring is "did Telegram message arrive?" — coarse-grained, no trend.
**Beta solution:** Grafana + Prometheus on free VM (or Hetzner CX22 = 4 EUR/mo). Self-hosted, no DataDog bill.

**Core dashboards:**
1. **Pipeline SLOs** — freshness per source, scrape success rate, pipeline duration, last-success timestamp
2. **Model health** — rolling ECE (7d/30d), rolling MCE, CLV rolling (50/100/500 bets), log-loss vs baseline
3. **Feature drift** — PSI per feature, top-10 drifting features, drift alert threshold lines
4. **Infra** — Pi CPU/RAM/disk, VM cost burn, MLflow run count

**Alert routing via Alertmanager:**
- Severity **P0** (rollback triggers from mleng.md): Telegram + SMS + email
- Severity **P1** (warning — ECE drift, PSI high): Telegram only
- Severity **P2** (info — sweep done, weekly retrain complete): daily digest email

**Fallback:** Grafana VM dies → Prometheus keeps scraping, alerts still fire (Alertmanager in HA mode on Pi as secondary). Dashboards down = inconvenient but non-critical.

**Build vs buy:** Better Stack (Grafana Cloud competitor) is 30 EUR/mo for our scale. Self-hosted Grafana is 0-4 EUR/mo + ~2h/month founder ops. Self-hosted wins at our scale; revisit at V2 when user count justifies the SaaS.

### 4.8 E — Deployment automation (GitHub Actions)

**Problem:** alpha requires founder to run `deploy_model_to_pi.sh` manually from Dev PC.
**Beta solution:** GitHub Actions workflow `deploy-to-pi.yml` triggered on:
- merge to `main` of `packages/ml-in-sports/src/ml_in_sports/**` paths
- manual dispatch with `--model-version=vN`
- scheduled weekly "verify production matches latest Production-stage MLflow" reconciliation job

**Flow:**
1. GH Actions self-hosted runner on Dev PC pulls from MLflow
2. Computes sha256 locally
3. SCPs to Pi (Tailscale SSH)
4. Pi verifies sha256
5. Atomic symlink swap
6. Smoke test — Pi runs `sl pipeline predict-dry-run` on today's fixtures; if prediction count 0, rolls back
7. Logs deploy event to `model_deploys` Postgres table

**Fallback:** Self-hosted runner down → workflow falls back to GH-hosted ubuntu runner with Tailscale setup via `tailscale-github-actions` action. Slower (~3 min vs 30s) but works.

### 4.9 F — Retraining automation (drift-triggered)

**Problem:** alpha retrains bi-weekly on calendar; wastes cycles when nothing changed, too slow when market shifts.
**Beta solution:** nightly drift check:

```
nightly 02:00 UTC:
  compute PSI(features_today vs training_distribution) per feature
  compute ECE(last 14d bets) per market
  IF any PSI > 0.25 OR any ECE_14d > 0.06 OR (days_since_last_retrain > 30):
    trigger retrain
    post Linear comment: "Retrain scheduled: reason=<PSI on feat_xg_delta=0.31>"
  ELSE:
    log no-op
```

Retrain runs on VM (or Dev PC fallback), outputs staging MLflow model, auto-promotion rules (§4.2) decide next step.

**Founder involvement:** 0 in common case. Only when auto-promotion classifies as Risky tier or when drift cause is ambiguous.

**Fallback:** if drift trigger fires daily for a week (model stuck unable to converge, or market regime change like VAR rule update), escalate to Telegram "Retrain stuck — likely regime change, DrMat review needed."

### 4.10 G — CI/CD for ML

**Problem:** alpha CI only runs unit tests + the quick backtest.
**Beta additions:**

1. **Model registry gate** — MLflow model version cannot transition to Production via any path other than CI-triggered workflow; direct API calls blocked by IAM on MLflow server.
2. **Data versioning (DVC)** — training data snapshots pinned per experiment via DVC on Backblaze B2; `sl backtest run` refuses to run against unpinned data.
3. **Feature tests** — Hypothesis property-based tests on extractors (no leakage, monotonic, no NaN in pre-match features). ~50 property tests, runs in <30s.
4. **Integration test** — on merge to main, a full end-to-end mini-pipeline runs on 1 league × 1 season; catches "extractor works, model works, but pipeline integration broken" class of bugs.

**Fallback:** any CI job takes >15 min → split into parallel matrix or move to scheduled nightly, never block PRs on slow CI.

### 4.11 H — Cost optimisation

**Beta targets:**
- Hetzner CX22 = 4 EUR/mo (Grafana + Prometheus, optional MLflow mirror)
- Free VM (per ADR-0019) = 0 EUR (if available) for heavy training
- Fallback if VM unreliable: Hetzner CX42 rented during sweeps only (~1 EUR per sweep, spot-like via auto-create-auto-destroy)
- Backblaze B2 artifact storage = ~0.50 EUR/mo for 100 GB
- GitHub Actions = within free tier (2000 min/mo)
- **Target beta infra: ≤10 EUR/mo.**

### 4.12 Beta founder-hour target

**From 3 h/week to 1.5 h/week by end of beta (month 6).** Remaining 1.5 h: Risky-tier promotion co-signs, feedback triage, exceptional incidents.

---

## 5. V1 automation (months 6-12)

**Goal:** fleet-aware, canary-capable, zero-touch on common operations. Founder acts as strategist only.

### 5.1 A — A/B testing as first-class concept

Beta's shadow mode graduates to true **canary deployment**:

- `model_routing` table in Postgres: `(match_id, route_target: champion|challenger|shadow)`
- Routing rule: hash(match_id) mod 100 < `canary_pct` → challenger, else champion
- `canary_pct` ramps: 10% → 25% → 50% → 100% over 7 days, with automatic rollback on any gate breach
- Statistical decision at each ramp: DeLong paired test with minimum sample size (50 per ramp step), BH-adjusted p threshold 0.05

**Pi RAM budget at 2 concurrent models is tight** — see §4.3. At V1 we likely have Hetzner CX42 serving predictions (8 GB RAM, x86_64, 6 EUR/mo), Pi relegated to Telegram bot + secondary failover. Migration trigger discussed in §5.6.

### 5.2 A — Fully autonomous retrain (common case)

V1 extends beta's drift-triggered retrain:
- All Safe-tier candidates: auto-promoted without human touch
- Moderate-tier: founder notified, 24h auto-approve timer if no objection
- Risky-tier: founder + DrMat co-sign still mandatory

**Ownership:** founder becomes strategist — decides thresholds, reviews monthly KPIs, handles Risky tier only. Day-to-day = zero touch.

### 5.3 B — Feature store graduation

Beta-era custom Postgres registry is revisited at V1. Triggers for Feast migration:
- \>3 feature engineers (not reached at V1 unless team grew)
- \>2000 features (unlikely for football; real if we add tennis + basketball)
- \>1s feature serving latency at p95 (first real signal Redis cache is needed)

If none of the triggers hit, **stay on custom store**. Feast migration is a 3-month project — don't start it without a compelling operational reason.

### 5.4 C — Data quality at production scale

- **Great Expectations suites run on every scrape**, not just daily
- **Schema evolution detector** — when a scraped source adds/removes a column, auto-open Linear ticket, quarantine data until human reviews
- **Label drift monitor** — distribution of match outcomes over rolling windows; if home_win% shifts >2σ vs 5-year baseline, flag for DrMat review (could be genuine regime change, e.g. VAR rule reform)

### 5.5 D — Evidently AI or Whylogs for drift

V1 adds continuous drift monitoring beyond PSI. Evidently AI self-hosted (open source) provides:
- Daily dashboard of feature drift per feature
- Prediction drift (how the output distribution shifts)
- Data quality time series
- Free integration with Prometheus/Grafana

**Cost:** 0 EUR self-hosted, +2 GB RAM on VM. Alternative Whylogs (WhyLabs-sponsored OSS) is functionally similar, slightly better CLI. Pick Evidently — more community momentum, better reliability-diagram tooling which matches our calibration focus.

### 5.6 E — Migration from Pi to dedicated server

**Task question 4 answered.** Triggers to migrate prediction serving off Pi:

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Pi CPU sustained | >80% for 2h daily | Migrate now |
| Pi RAM pressure | swap used daily | Migrate now |
| Pipeline runtime | >45 min (from 06:00 to 06:45 slot collision) | Migrate soon |
| User count | >500 paying | Migrate proactively |
| Canary+shadow needs | >2 concurrent models required | Migrate now |
| SLA breach count | >2 per month due to Pi hardware | Migrate now |

**Target:** Hetzner CX42 (8 GB RAM, 3 vCPU, 80 GB NVMe, 6 EUR/mo) or CCX13 dedicated (16 GB, 2 dedicated vCPU, 14 EUR/mo). Dedicated is safer for deterministic latency.

**Pi stays as:**
- Telegram bot host (low resource)
- Secondary failover (syncthing-mirror of `/app/models/production/current`)
- Backup scrape runner when primary scrape VM fails

### 5.7 F — Continual learning

V1 tries incremental model updates — daily `partial_fit` on last N matches, full retrain monthly. **Only for markets with n≥500 bets** where the statistical cost of a bad daily update is bounded. For new markets (BTTS at alpha-end, Asian Handicap later), stay on weekly full retrain.

**Fallback:** if continual learning introduces regressions, shelf it and fall back to beta's drift-triggered weekly retrain. Gate: continual learning must beat weekly retrain on CLV walk-forward by ≥0.5% for 4 consecutive weeks before committing.

### 5.8 G — End-to-end ML CI

V1 CI is a full pipeline test on PRs:
`scrape (fixture) → feature materialisation → feature store write → training → calibration → gates → staging promotion → smoke prediction`

Time budget: 15 min. Runs on self-hosted runner (VM or Hetzner). Any break anywhere in the pipeline blocks merge. This is the strongest pre-merge guarantee possible without full prod simulation.

### 5.9 H — Cost management at scale

V1 cost budget (100-500 users, 1 market → 3 markets):

| Component | Cost (EUR/mo) |
|-----------|---------------|
| Hetzner CCX13 (prediction serving) | 14 |
| Hetzner CX22 (Grafana + Prometheus + Evidently + MLflow) | 4 |
| Hetzner CX32 (heavy training nightly, spot-like auto-start/stop) | ~3 (spot usage) |
| Backblaze B2 (500 GB artifacts + backups) | ~2 |
| Free VM (ADR-0019) as opportunistic compute | 0 |
| Pi (failover + Telegram) | owned, 0 |
| Cloudflare (DNS, Tunnel, Workers for landing) | 0 (free tier) |
| **Total V1 infra** | **~23** |

**Task question 6 answered (user count 10× in beta):**
A 10× growth (5-10 users → 50-100) costs almost nothing on infra — predictions are batch daily, latency is 0 concern. The scale impact is on **support load** (more feedback, more edge cases), not on compute. If support overwhelms, prioritise automating touchpoint 10 (feedback → experiment pipeline) before paying for bigger infra.

### 5.10 V1 founder-hour target

**From 1.5 h/week to 0.5 h/week.** Remaining: Risky-tier co-signs (weeks when they happen), monthly KPI review, strategy adjustments.

---

## 6. V2 automation (months 12-18)

**Goal:** multi-model, self-healing, per-league autonomy.

### 6.1 A — Multi-model fleet

V2 ships one model **per (sport, market, league-tier)**. Each model is promoted, monitored, and rolled back independently. Why:
- Serie A and La Liga have structurally different scoring distributions; one global model serves neither optimally at V2 scale
- Per-league calibration becomes tractable (n_val ≥500 per league after 2 years of data)
- Failures are isolated — PL model broken doesn't kill Serie A picks

**Implementation:** MLflow model registry with naming convention `football_1x2_{league_tier}_v{N}`; routing layer picks the right model per fixture. Each model has its own cron retrain, own promotion gates, own Telegram channel for alerts (so the founder sees which model failed, not "a model failed").

### 6.2 D — Semantic monitoring

Beyond metric drift, V2 monitors **behavioural drift**: does the model still recommend similar picks for similar situations? If SHAP attribution changes materially week-over-week while metrics stay flat, that's a silent semantic drift — the model may be "right for wrong reasons."

**Concrete:** weekly SHAP signature clustering; if the dominant explanation cluster shifts >30%, open Linear ticket for DrMat review. Not a rollback trigger — diagnostic.

### 6.3 E — Self-serve experimentation for DrMat

V2 goal: DrMat pushes an experiment YAML, runs it, reviews results, proposes promotion — **all without founder involvement**. Requires:
- DrMat has GitHub access, write on `experiments/` folder only
- PRs from DrMat auto-run experiments, post reports
- MLflow UI accessible to DrMat with RBAC (read-all, promote-staging-only, no production write)
- Production promotion still requires founder click (accountability firewall)

**Why this matters:** at V2 we likely can't afford a full-time MLEng hire, but DrMat part-time is realistic. Self-serve tooling multiplies his impact without requiring a second engineer.

### 6.4 F — Online learning (if continual was successful)

V2 explores true online learning — update model weights per batch of new labelled outcomes, not per daily `partial_fit`. Only for LightGBM with `refit_leaf` or moving to River (online-learning library).

**High risk:** online learning can silently diverge. Required guards: every online update shadow-tested against "what if we didn't update?" — 7-day rolling comparison. Any divergence >1% log-loss → disable online, fall back to daily batch.

### 6.5 G — Property-based feature tests at scale

V2 formalises ~200 property tests over features via Hypothesis — e.g., "for any match, `rolling_xg_home_5` is in [0, 30]", "no feature uses information with `kickoff_ts` in future". Runs nightly full-suite, on every PR quick-suite.

### 6.6 H — Distillation + edge inference

V2 starts using distillation: train a heavy ensemble on VM, distill to single LightGBM on Pi — preserves most accuracy at a fraction of serving cost.

**Edge inference concept:** Pi serves predictions, but pre-computed "model outputs per fixture" are CDN-cached (Cloudflare Workers KV), panel fetches from CDN not Pi. Eliminates Pi as user-facing bottleneck — Pi only publishes, CDN serves.

### 6.7 V2 cost

| Component | Cost (EUR/mo) |
|-----------|---------------|
| Hetzner CCX23 (larger serving tier) | 28 |
| Hetzner CX32 (more capacity Grafana + Evidently + MLflow + Feast if migrated) | 6 |
| Spot GPU (RunPod on-demand for TabPFN if shipped) | ~5 (intermittent) |
| Backblaze B2 (1 TB) | ~4 |
| Cloudflare (Tunnel, Workers KV for edge cache) | 5 |
| **Total V2 infra** | **~48** |

### 6.8 V2 founder-hour target

**~15 min/week.** Monthly 30-min KPI review; weekly 5-min "anything red?" scan.

---

## 7. V3 automation (months 18-24)

**Goal:** self-tuning, causal explanations, team scale.

### 7.1 D — Causal monitoring

When log-loss regresses, V3 auto-attributes the cause:
- Is it feature drift? (PSI delta per feature)
- Label drift? (outcome distribution shift)
- Scraper anomaly? (GE suite pass rate in prior 7d)
- Market regime? (odds distribution shift — Pinnacle overround trend, closing-line volatility)
- Code change? (last deploy date vs regression onset)

Automated attribution pipeline produces a **root-cause graph** (causal-style) with confidence per branch. Founder reads the one-pager: "83% confident this is feature drift on `xg_delta_5` due to Sofascore scraper change on 2026-11-03."

**This is the end state of monitoring** — not just "what broke" but "why it broke, with evidence."

### 7.2 F — Meta-learning

V3 models learn from the history of model versions. When a new model is trained, it's initialised from the warmest prior based on:
- Same league, most recent version: highest weight
- Same tier, different league, recent: medium weight
- Transfer-learning-style fine-tuning from "all football" base model

Reduces training time, improves cold-start for new leagues.

### 7.3 G — Market change detection + response

**Task question 7 answered.** V3 detects market changes (Premier League rule reform, VAR threshold shift, point deduction, new competition format):

- **Detection:** label distribution shift in affected league × 30-day window + news-feed signal (scrape BBC Sport, Reuters sports headlines for rule-change keywords)
- **Response:** auto-pause bet generation on affected league for 48h, schedule retrain on post-change data with elevated embargo (21 days instead of 7)
- **Human gate:** founder + DrMat review the rule change, assign a regime-change flag to pre/post data, retrain with regime feature

### 7.4 H — Hiring triggers reached

**Task question — when to hire dedicated MLOps:**

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Founder ML-ops time | >3 h/week sustained 3 months | Contractor |
| Infra cost | >200 EUR/mo | FT junior MLOps worthwhile |
| Incidents | >1 P0 per month lasting >2h | Dedicated SRE/MLOps |
| Sport count | >2 (football + tennis + ...) | MLOps hire, you can't manage 2+ sport pipelines alone |
| Revenue | >150k EUR ARR | Hire justifies salary |
| Team size | >3 total | Needs MLOps to coordinate |

**Before these triggers:** cheaper to pay for MLOps-as-SaaS (Neptune.ai, W&B Premium) than a person. After these triggers: hire beats SaaS because ops work doesn't scale with users, it scales with complexity, and complexity is the problem a human solves better than a SaaS.

### 7.5 V3 cost (illustrative, depends heavily on user count)

| Component | Cost (EUR/mo) |
|-----------|---------------|
| Hetzner CCX33 cluster (redundant serving) | 90 |
| Hetzner AX42 (training, monitoring, Feast, MLflow) | 45 |
| Backblaze B2 + Cloudflare (CDN + R2) | 20 |
| Evidently + Grafana + Prometheus self-hosted | 0 (included in above VMs) |
| Optional: W&B Pro for experiment tracking | 50 (if MLflow feels limiting) |
| Optional: dedicated MLOps contractor | 2000-4000 (if triggers hit) |
| **Total V3 infra (without MLOps hire)** | **~155-205** |

### 7.6 V3 founder-hour target

**Strategic-only.** Weekly scan (5 min), monthly KPI review (30 min), quarterly roadmap (2h). Day-to-day ML ops = zero touch.

---

## 8. Build vs buy — key decisions

| Concern | Build | Buy | Recommendation |
|---------|-------|-----|----------------|
| **Experiment tracking** | MLflow OSS | W&B, Neptune, Comet | MLflow OSS through V2, revisit at V3. W&B team plan ~40 EUR/user/mo is cheap at V3 scale. |
| **Feature store** | Custom Postgres registry | Feast OSS, Tecton | Custom through V1. Feast migration only if team size justifies (see §5.3). Tecton never — enterprise pricing. |
| **Drift monitoring** | Custom PSI in Python | Evidently OSS, WhyLabs SaaS, Arize | Custom PSI (alpha), Evidently OSS (V1), revisit Arize/WhyLabs only at V3 if scale justifies. |
| **Dashboards** | Self-hosted Grafana | Better Stack, DataDog, Grafana Cloud | Self-hosted Grafana through V2. Grafana Cloud (free tier generous) candidate at V3. |
| **Alerting** | Telegram bot + Alertmanager | PagerDuty, Opsgenie | Telegram through V2 — solo founder isn't on pager rotation. PagerDuty only with team of 2+. |
| **Orchestration** | cron (ADR-0013) | Prefect Cloud, Dagster Cloud, Airflow | cron through V1. Prefect only when ≥4 interdependent flows (ADR-0013 exit criterion). |
| **Model registry** | MLflow OSS | MLflow Managed, SageMaker MR, Vertex | MLflow OSS indefinitely. Managed MLflow adds nothing worth the bill at our scale. |
| **Data versioning** | DVC OSS | DVC Studio, LakeFS | DVC OSS through V2. Paid tier only if regulatory audit trail demanded. |
| **Hyperparameter tuning** | Optuna OSS | W&B Sweeps, Vertex Vizier | Optuna OSS forever. Nothing proprietary competes on cost. |
| **Model serving** | Custom Python + cron | BentoML, Seldon, KServe, SageMaker | Custom batch serving through V3. We do batch, not real-time — serving layers add complexity we don't need. |
| **CI** | GitHub Actions | CircleCI, Buildkite | GitHub Actions forever, self-hosted runner when matrix gets expensive. |
| **Secrets** | 1Password + Doppler (ADR-0010/phase_0) | AWS Secrets Manager, HashiCorp Vault | Doppler/1Password through V3. Vault only with team ≥5. |

**Overarching rule:** every SaaS line item must justify >2 founder-hours/month or replace >1 FTE-equivalent effort to earn its bill. At our scale almost nothing SaaS does.

---

## 9. Failure fallbacks per automation system

Each entry: goal, success criteria, failure modes, failure response, bailout, alternative. Fifteen systems listed.

### 9.1 Scheduled pipeline (Alpha — cron)

**Goal:** daily slip published without founder touch.
**Success:** 7 consecutive days with green healthchecks.io pings, no Telegram P0 alerts.
**Failure modes:** Pi hardware failure; cron silently disabled; `sl` CLI regression from dependency update.
**Response:** laptop takes over via syncthing-mirrored config; healthchecks.io alert catches missed ping; CI integration test catches CLI regression before merge.
**Bailout:** Pi dies for >48h → failover to laptop permanent, Pi replaced.
**Alternative:** if cron proves unreliable, move to systemd timers — same behaviour, better logs via `journalctl`.

### 9.2 Promotion gate CLI (Alpha — `sl promote check`)

**Goal:** one command decides if a candidate passes all 7 gates.
**Success:** zero false positives in first 10 promotions (no model promoted that violated a gate).
**Failure modes:** gate metric computation bug; SHAP comparison breaks on feature-set schema mismatch; leakage detector false negative.
**Response:** every gate has a unit test; SHAP schema mismatch auto-classifies as Risky tier; leakage detector gets weekly adversarial test cases in CI.
**Bailout:** if gate CLI produces contradictory signals twice, freeze promotions, manually audit, patch CLI.
**Alternative:** if gate complexity balloons, split into `sl promote check-safe`, `sl promote check-moderate`, `sl promote check-risky` with different strictness.

### 9.3 Auto-promotion tiering (Beta)

**Goal:** Safe-tier candidates promote without human click.
**Success:** no Safe-tier auto-promoted model triggers rollback in first 30 days of feature enablement.
**Failure modes:** tier classifier labels a risky change as Safe; SHAP-overlap metric gamed by feature regularisation change; human loses control of the gate.
**Response:** tier classifier defaults to Risky on any uncertainty; weekly audit logs every tier decision; founder has one-click "force-Risky" override.
**Bailout:** any Safe-tier auto-promote leads to rollback → disable auto-promotion, revert to fully-manual for 2 weeks, audit.
**Alternative:** keep auto-promotion off forever; founder click for every promotion is 2 min, acceptable at our scale.

### 9.4 Shadow / canary deployment (Beta → V1)

**Goal:** challenger validated on live traffic before full promotion.
**Success:** every champion-challenger decision made on ≥50 shadow predictions with paired-test p-value.
**Failure modes:** Pi OOM when both models load; challenger leaks into user-facing picks; statistical test under-powered.
**Response:** RAM monitor kills challenger on >80% usage; routing table enforces challenger → shadow-only flag with DB constraint; minimum sample size gated in `sl shadow analyse`.
**Bailout:** if Pi OOM becomes recurring → migrate serving to Hetzner early (§5.6).
**Alternative:** if canary is too operationally heavy, keep shadow-only (no user-facing routing) and decide promotions purely on back-test + shadow CLV.

### 9.5 Feature store / registry (Beta custom → V1/V2 Feast maybe)

**Goal:** replace ad-hoc SQL with declarative feature definitions by month 4.
**Success criteria:** all 935 features have registry entries; training offline + serving online feature parity verified weekly; feature freshness SLOs met (odds <5 min latency).
**Failure modes:**
1. Feast too complex for 1 dev — operational overhead > benefit
2. Performance regression — Feast online serving slower than direct SQL
3. Drift — definitions in store != production reality
**Failure responses:**
1. If complexity: stay on custom Postgres registry — less fancy, usable, same benefits at our scale
2. If perf: hybrid — critical features in Redis cache, rest Postgres
3. If drift: weekly parity audit job; Great Expectations suite over feature values; block CI on mismatch
**Bailout criteria:** >3 months post-migration and still diffing manually in production; founder spending >2 h/week on feature ops; beta users complaining about staleness.
**Alternative:** minimal Postgres registry with TypedDict schemas, PR review for new features, markdown changelog. Less fancy, ships this month.

### 9.6 Data quality (Great Expectations, Beta)

**Goal:** no bad scrape reaches features.
**Success:** zero incidents of "model predicted badly because scrape had nulls" in first 30 days.
**Failure modes:** GE suite itself has a bug → blocks good data; distribution shift misclassified as bad data → blocks regime change; suite maintenance outpaces team.
**Response:** suites versioned in git, every change PR-reviewed; distribution shift thresholds configurable with 60d moving baseline; suite fails → data quarantined, not dropped; founder reviews quarantine queue weekly.
**Bailout:** if suite maintenance takes >1 h/week, reduce suite scope to critical columns only (odds, match_id, timestamps).
**Alternative:** minimal Python validators in `packages/ml-in-sports/src/ml_in_sports/ingestion/validators.py` with `pydantic` schemas — less powerful, zero-ops.

### 9.7 Monitoring stack (Grafana/Prometheus/Evidently)

**Goal:** every model + pipeline + infra metric visible + alertable.
**Success:** every P0 rollback triggered by alert (never by user complaint).
**Failure modes:** Grafana VM dies; alert fatigue — too many false positives; metric gap — critical signal not instrumented.
**Response:** Prometheus + Alertmanager run independently of Grafana; alerts tuned via weekly review of fire-to-action ratio; every incident PM includes "what metric would have caught this?" and is added to instrumentation.
**Bailout:** if self-hosted too fragile → Grafana Cloud free tier (50 GB logs, 10k series) bridges until team scale justifies paid.
**Alternative:** Netdata agent on each VM — simpler, no Prometheus config, covers 80% of infra monitoring without model-specific metrics.

### 9.8 Deployment automation (GitHub Actions → Pi)

**Goal:** merge-to-main auto-deploys staging, auto-promotes production with correct gates.
**Success:** zero manual `scp` on any model deploy for 30 consecutive days.
**Failure modes:** GH Actions runner unreachable; SCP times out; sha256 mismatch; smoke test fails after swap.
**Response:** sha256 mismatch aborts before symlink swap; smoke test within 60s of swap, auto-rollback on fail; runner offline → manual one-liner on Dev PC documented in runbook.
**Bailout:** if GH Actions proves flaky for prod deploys, move to Ansible playbook triggered manually — slower, more reliable.
**Alternative:** Watchtower-style continuous-deploy daemon on Pi that pulls from MLflow every 15 min and swaps on sha256 change. Even more autonomous, less auditable.

### 9.9 Retraining trigger (Beta — drift-based)

**Goal:** retrain fires only when needed.
**Success:** retrain frequency matches observed drift; no "why didn't we retrain" post-incidents.
**Failure modes:** PSI threshold too sensitive → daily retrains; too lax → stale model; drift trigger storm during regime change.
**Response:** PSI threshold calibrated on 6-month backtest; daily retrain cap (max 1 retrain per day regardless of triggers); regime-change detector prompts DrMat review, not auto-retrain.
**Bailout:** retrain trigger misbehaves for a week → revert to calendar-based bi-weekly; re-tune offline before re-enabling.
**Alternative:** keep bi-weekly calendar retrain forever — simpler, waste some cycles, never wrong.

### 9.10 Hyperparameter sweep (Optuna, Beta)

**Goal:** weekly best-config search produces a valid challenger.
**Success:** sweep finishes within time budget, challenger passes promotion gates at least once a month.
**Failure modes:** VM disappears (free-tier risk); sweep finds overfit config; sweep finds marginal gain (not worth risk).
**Response:** sweep defaults to Dev PC fallback with reduced trials; walk-forward CV is the only evaluation (overfit impossible under 7d embargo if CV is correct); marginal gain filter — challenger must beat incumbent by ≥0.5% log-loss to become canary.
**Bailout:** disable sweep, keep fixed config from last good sweep, revisit next quarter.
**Alternative:** Bayesian Optimization via scikit-optimize — fewer dependencies, slightly worse but good enough.

### 9.11 Continual learning (V1 F)

**Goal:** daily partial-fit improves model between full retrains.
**Success:** continual-learning variant beats weekly retrain on CLV by ≥0.5% for 4 consecutive weeks.
**Failure modes:** partial_fit diverges; adds noise instead of signal; LightGBM refit_leaf semantics misunderstood.
**Response:** continual-learning model runs in shadow against weekly retrain for 6 weeks minimum; any divergence auto-reverts to weekly; LightGBM refit_leaf tests in unit suite.
**Bailout:** shelve continual learning, stay on drift-triggered weekly retrain — proven, good enough.
**Alternative:** scheduled "warm-start" — each Monday retrain initialised from previous Monday's model, zero continual complexity.

### 9.12 Multi-model fleet (V2)

**Goal:** per-league models deployed independently.
**Success:** single-league rollback leaves other leagues undisturbed; operational cost per model <0.2 h/week of human attention.
**Failure modes:** model count explodes, monitoring fatigue; per-league data insufficient → worse than global; routing bug serves wrong model.
**Response:** max fleet size 20 models (above that, merge back into tiers); per-league gate requires n_val ≥500 before split; routing layer has unit test for every (sport, market, league) combo.
**Bailout:** collapse back to 3-tier global model (top-5, mid, lower) if per-league doesn't pay off in CLV.
**Alternative:** per-league calibrator only (keep global LGBM, per-league Platt/Beta). Smaller blast radius, most of the benefit.

### 9.13 Online learning (V2)

**Goal:** model weights update per batch without full retrain.
**Success:** online learning beats weekly retrain + daily partial_fit by ≥1% log-loss for 8 weeks.
**Failure modes:** divergence; forgetting old data; racecondition between online update and serving request.
**Response:** shadow-test every online update for 7 days before committing; use replay buffer (last 12 months) to prevent forgetting; online updates happen during off-hours serving window (02:00-05:00 UTC).
**Bailout:** disable online, stay on daily partial_fit + weekly retrain.
**Alternative:** skip online learning entirely — at our scale, weekly retrain is operationally safer.

### 9.14 Self-serve experimentation (V2 E)

**Goal:** DrMat can run experiments + propose promotions without founder involvement.
**Success:** 5 experiments from DrMat merge-to-main through staging without founder touch in a month.
**Failure modes:** DrMat pushes to production by mistake; experiment breaks main; gate semantics misunderstood.
**Response:** RBAC — DrMat has no production-write on MLflow; CI runs every DrMat PR in sandbox; gate docs in repo + `sl promote check --explain` flag.
**Bailout:** revert to founder-only promotion, DrMat proposes via Linear tickets.
**Alternative:** pair-programming hour weekly where DrMat and founder co-run one experiment — slower but educates DrMat on ops.

### 9.15 Causal monitoring (V3 D)

**Goal:** attribute regressions to feature/label/scraper/code with confidence.
**Success:** 80% of regressions root-caused correctly (founder validates in post-incident).
**Failure modes:** false attribution → wrong fix; attribution engine itself breaks; rarity of regressions = insufficient data.
**Response:** attribution confidence threshold — below 60% confidence, flag as "unknown" and escalate; engine has own uptime monitoring.
**Bailout:** causal engine wrong more than right → disable, revert to manual root-cause analysis.
**Alternative:** simple rule-based attribution (last_deploy_date delta, scraper_failures_delta, feature_psi_max) — less fancy, often right.

### 9.16-20 Quick-fire systems

**9.16 Alerting (Telegram):** fallback to SMS + email via Mailgun. Bailout if Telegram blocks: move to Discord bot.
**9.17 Shadow prediction logging:** fallback to file logs if Postgres down. Bailout: accept missing shadow data for <24h.
**9.18 Model artifact storage (Backblaze B2):** fallback to S3 + R2. Bailout: local archive on Pi + laptop syncthing keeps 90d history.
**9.19 Secrets rotation (Doppler):** fallback to 1Password CLI. Bailout: manual rotation quarterly, documented in runbook.
**9.20 Health checks (healthchecks.io):** fallback to cronitor.io (identical model). Bailout: self-hosted `heartbeat` endpoint on VM.

---

## 10. Cost analysis per phase

| Phase | Duration | Infra EUR/mo | SaaS EUR/mo | Founder hr/week | Contractor EUR/mo | Total EUR/mo |
|-------|----------|--------------|-------------|-----------------|---------------------|---------------|
| **Alpha** (wk 0-2) | 2 weeks | 0 | 0 | 6 → 3 | 0 | ~0 |
| **Beta** (mo 1-6) | 5 months | 4-10 | 0 | 3 → 1.5 | 0 | ~10 |
| **V1** (mo 6-12) | 6 months | 20-25 | 0 | 1.5 → 0.5 | 0 | ~23 |
| **V2** (mo 12-18) | 6 months | 45-55 | 0-50 (W&B?) | 0.5 → 0.25 | 0-200 (occasional) | ~48-300 |
| **V3** (mo 18-24) | 6 months | 155-205 | 50-100 (W&B, Arize?) | 0.25 → strategic | 0-4000 (MLOps hire) | ~205-6305 |

**Decision points:**
- **End of Beta:** is founder <1 h/week on ML ops? If not, audit which touchpoint still consumes time.
- **End of V1:** infra cost <30 EUR/mo? If not, review which SaaS was oversold (probably something).
- **Mid V2:** founder-hour still dropping? If plateau at >0.5 h/week, hiring contractor is cheaper than founder time.
- **End of V2:** dedicated MLOps hire worth it? See §7.4 triggers.

---

## 11. Tool stack evolution (Alpha → V3)

**Alpha (wk 0-2)**
Storage: Postgres (local on Pi+laptop), SQLite for mini-tests. Artifacts: local dir on Dev PC, Backblaze B2 backup.
Experiment: MLflow local. Training: LightGBM on Dev PC.
Serving: Pi cron + Python batch.
Monitoring: Telegram bot, healthchecks.io.
Orchestration: cron (ADR-0013).
CI: GitHub Actions hosted.
Secrets: 1Password + `.env` on each box.

**Beta (mo 1-6)**
Storage: Postgres + Timescale on Hetzner CX22. MLflow on VM.
Feature store: custom Postgres registry (§4.5 option B1).
Data quality: Great Expectations.
Serving: Pi unchanged, Hetzner standby.
Monitoring: Grafana + Prometheus + Alertmanager on VM.
Orchestration: still cron on Pi + GitHub Actions for deploys.
Hyperparameter: Optuna on VM overnight.
CI: self-hosted GH Actions runner on Dev PC or VM.
Drift: custom PSI + ECE in Python.

**V1 (mo 6-12)**
Storage: Postgres on Hetzner CX32. Timescale enabled for odds history.
Feature store: custom graduates or Feast migration (§5.3 decision).
Serving: Hetzner CCX13 (Pi demoted to Telegram bot + failover).
Drift: Evidently AI self-hosted.
A/B: canary via `model_routing` table.
Continual learning: optional, shadow-gated (§5.7).
Orchestration: cron everywhere; Prefect if flow count >4 (ADR-0013 exit).
Data versioning: DVC with B2 remote.
Alerting: Telegram + Alertmanager (email fallback).

**V2 (mo 12-18)**
Multi-model fleet on Hetzner CCX23, per-league model registry in MLflow.
Online learning candidate (shadow-gated).
Self-serve for DrMat (MLflow RBAC + CI sandbox).
Semantic monitoring (SHAP signature clustering).
CDN-cached edge inference (Cloudflare Workers KV).
Optional W&B team plan if MLflow UI limiting.

**V3 (mo 18-24)**
Causal monitoring engine.
Meta-learning — warmest-prior model init.
Market-change detector (news-feed + label drift).
Dedicated MLOps contractor or hire.
Possibly W&B + Arize (paid) if team scale justifies.

---

## 12. Hiring triggers — dedicated MLOps engineer

Detailed version of §7.4.

**Early signals (don't hire yet, watch these):**
- Founder ML-ops >2 h/week two months running
- Any single incident takes >4 h to resolve
- ≥2 failed deployments in a month
- Infra cost trending up >20% per quarter

**Hire triggers (any ONE is sufficient):**
1. Founder ML-ops >3 h/week sustained 3 months
2. Infra cost >200 EUR/mo (at that scale, ops overhead justifies a person)
3. ≥1 P0 incident/month lasting >2 h (reliability demand exceeds solo capacity)
4. Sports portfolio >2 (multi-sport can't be one person plus Claude)
5. Revenue >150k EUR ARR (ops hire pays back)
6. Team size ≥3 (someone must own cross-cutting infra)

**Contractor vs FT:**
- First hire: 0.3-0.5 FTE contractor at V2 — 2000-4000 EUR/mo. Faster, reversible, less commitment.
- FT hire only at V3 or with ≥3 of above triggers firing.

**Profile:**
- **Not** a pure MLOps-evangelism person. **Yes** a pragmatic SRE who has shipped LightGBM/XGBoost in production.
- Must love cron, hate Kubernetes (until we earn it).
- Experience with Postgres + MLflow + GitHub Actions + Hetzner/Hetzner-equivalent. Feast/Kubeflow/SageMaker experience is "nice to have," often a negative signal for our scale.

---

## 13. Security + compliance (ML-specific)

### 13.1 Data retention

- **Raw scrape data** — retained indefinitely (it's public information, tiny footprint).
- **User bets** — retained per GDPR: as long as user has account, plus 3 years after deletion for accounting purposes (§Art 17(3)(b)), then hard-deleted.
- **Model artifacts** — retain last 3 production + 30 days of staging per ADR-0017 rollback stack; older archived to Backblaze B2 cold tier, expired after 12 months.
- **MLflow experiment runs** — retain all runs forever (cheap, enables audit trail). Artifacts for runs older than 90 days moved to cold storage.
- **Prediction logs** — retain 2 years for model audit; user-PII-free (match_id + prediction only) so no GDPR implications.

### 13.2 GDPR

- User consent explicit on signup for "predictions personalised by your league preferences" — stored with version + timestamp.
- User data export endpoint (Art. 20) returns JSON dump in <30 days — covered by existing `apps/api` endpoints (SPO-144).
- User deletion endpoint (Art. 17) — purges `users`, `user_bets`, `telegram_handle`; predictions retain anonymised-only (match_id + model_id, no user linkage).
- No cross-border transfer to US — all data stays in EU (Hetzner Helsinki, Backblaze B2 EU region).

### 13.3 Model bias audits

- Quarterly audit — `sl audit bias --quarterly` reports ECE per (league, kickoff_day_of_week, home_underdog_tier). If any subgroup ECE >0.10 while global <0.05, flag for DrMat review.
- No protected-class features in football (we don't use player names, nationality, etc. as features — only aggregate team stats).
- If SportsLab expands to other sports with individual-player markets (tennis, UFC), re-audit for name-based leakage at that time.

### 13.4 Responsible ML disclosures

- Alpha launch messaging already enforces the drmat §7.1 legal floor (tiered CLV claims by n_bets).
- Model cards per production model version — stored in MLflow run description, auto-generated by `sl promote check`: includes training data description, calibration method, known subgroup performance gaps, last audit date.
- Public-facing landing page never claims edge before n≥500 with CI strictly >0 (aligns with alpha plan §9).

### 13.5 Audit log

- Every promotion logged to `model_deploys` Postgres table with `deployed_by`, `cosigners`, `gate_results_json`.
- Every rollback logged with reason + trigger + current-state snapshot.
- Table retained indefinitely. Read-only export quarterly for compliance snapshots.

### 13.6 Reproducibility (task question 5 answered — 2-year horizon)

Every experiment reproducible by triple:
1. **YAML spec** — `experiments/<name>.yaml` in git, tagged with commit SHA at run time.
2. **Data snapshot** — DVC pinned to Backblaze B2 URL, immutable.
3. **Dependency lockfile** — `uv.lock` committed, pinned Python version, `requirements-frozen.txt` backup for pip-equivalent recovery.

Every MLflow run stores all three pointers. To reproduce after 2 years:
```bash
git checkout <sha>
uv sync --locked
dvc pull <data-snapshot-hash>
uv run sl backtest run experiments/<name>.yaml
```

Tested quarterly by running a random prior run end-to-end; must match within numerical tolerance.

**Known limit:** OS-level dependencies (LightGBM compile-time flags, OpenMP version) can drift over 2 years. Mitigation: build + store a Docker image per major dependency version; `uv run` inside Docker for true reproduction. Adds 1 GB per image; stored on Backblaze B2 cold tier.

---

## 14. Disaster recovery per phase

### 14.1 Alpha

**Failure modes covered:**
- Pi hardware dies → laptop is within 1-hour warm spare via syncthing
- Dev PC dies → Pi keeps serving predictions (can't retrain until Dev PC back, but production unaffected for days)
- Postgres on Pi corrupted → restore from Backblaze B2 daily backup (A-11), RPO 24h, RTO 1h

**Uncovered (accepted risk at alpha scale):**
- MLflow local store corruption — rebuild from Backblaze B2 artifact bucket, lose up to last 24h of runs
- Both Pi + laptop simultaneously down — escalate, accept 12-24h SLA breach

**Recovery targets (alpha):**
- RPO: 24h
- RTO: 4h

### 14.2 Beta

**Adds:**
- Hetzner VM for Grafana + MLflow; Backblaze B2 weekly full backup
- Dev PC no longer single point of failure — training can run on VM

**Recovery targets (beta):**
- RPO: 6h (hourly DB snapshots)
- RTO: 2h

### 14.3 V1

**Adds:**
- Hetzner primary + Pi secondary with live replication (Postgres streaming replication)
- Automated daily disaster-recovery test — weekly full-restore into temp VM, smoke test, teardown

**Recovery targets (V1):**
- RPO: 1h
- RTO: 1h

### 14.4 V2

**Adds:**
- Multi-region Hetzner (Helsinki + Falkenstein) for Postgres, cross-region failover
- Every model version archived in 2 geographies (Backblaze B2 EU-West + EU-Central)

**Recovery targets (V2):**
- RPO: 15 min
- RTO: 30 min

### 14.5 V3

**Adds:**
- Chaos engineering — monthly game day where founder/MLOps intentionally kills one component
- Automated runbook validation — every disaster scenario has a test that verifies the runbook works

**Recovery targets (V3):**
- RPO: <5 min
- RTO: <15 min

---

## 15. Answers to task questions

### 15.1 Experiment runner skeleton — PR-triggered backtest + MLflow + HTML report

See §3.5 and §4.1. Skeleton:

```
experiments/*.yaml  (declarative spec, only source of truth)
  │
  ├── merge to main → GitHub Actions detects YAML change → dispatches to self-hosted runner (VM)
  ├── cron schedule in YAML → scheduled weekly rerun
  └── manual dispatch → `sl backtest run experiments/<name>.yaml`
  ↓
sl backtest run (Typer CLI, ADR-0005)
  ↓
MLflow run created (autolog + custom metrics)
  ↓
Plotly HTML report generated (ADR-0004): reliability diagram, SHAP summary, CLV walk-forward, per-league breakdown
  ↓
Linear comment posted on spawning issue (via `linear-sportslab` MCP or API)
  ↓
If gate pass + Safe tier → auto-promotion to staging
```

The critical insight: **YAML is the only spec**. No hand-written Python experiment scripts ever. This is what makes it reproducible in 2 years.

### 15.2 Auto-promote without human touch — decision tree

```
Candidate arrives in MLflow Staging
  │
  ├── Run sl promote check → all 7 gates pass?
  │     NO → stays Staging, reason in run description, Linear comment filed
  │     YES ↓
  │
  ├── Classify tier:
  │     Safe → SHAP top-10 overlap ≥90% AND same feature set AND ACE delta <0.01
  │     Moderate → SHAP 70-90% OR new calibrator OR market extension
  │     Risky → SHAP <70% OR new feature family OR new market first deploy
  │
  ├── Safe → auto-promote to Production, Telegram "auto-promoted model v<N>", log in `model_deploys`
  ├── Moderate → Telegram to founder: "Moderate-tier candidate ready. Auto-promote in 24h unless you object." 24h timer → auto-promote if no objection
  └── Risky → Linear issue + Telegram to founder + DrMat; no auto-promote, co-sign required
```

### 15.3 Shadow mode on Pi with 4GB RAM

Answered in §4.3. TL;DR: max 2 concurrent LightGBM models fits within 4GB (~400 MB combined); shadow mode yes, 3+ concurrent → migrate to Hetzner. At V1 we're on Hetzner anyway.

### 15.4 When to migrate Pi → dedicated server

Answered in §5.6. **Any one** of: Pi CPU >80% sustained, RAM swap daily, pipeline >45 min, >500 users, >2 concurrent models required, >2 SLA breaches/month. Target: Hetzner CCX13 (14 EUR/mo).

### 15.5 Reproducibility over 2 years

Answered in §13.6. Triple: YAML + DVC-pinned data + uv.lock + optional Docker for OS-level isolation. Quarterly reproduction drill.

### 15.6 Cost management if user count grows 10× in Beta

Answered in §5.9. A 10× beta user growth barely touches infra cost (we're batch-daily, not real-time). Bottleneck becomes support, not compute. Budget: 10× users = <20% infra cost growth; >100% support time growth → automate touchpoint 10 (feedback → experiment pipeline) first, not scale servers.

### 15.7 Detect + respond to market changes (rule reforms, VAR updates)

Answered in §7.3 (full V3) and partially at V1:
- **V1:** label-drift monitor per league; >2σ shift vs baseline → DrMat review + Linear ticket.
- **V2:** regime-change feature added to training data; human-labeled regime boundaries.
- **V3:** news-feed scrape (BBC, Reuters) for rule-change keywords; auto-pause bet generation 48h on affected league; retrain with elevated embargo.

**Manual fallback at any phase:** founder/DrMat know about announced rule changes (Premier League, La Liga publicise months in advance); manually tag a regime boundary in data via `sl regime add --league=PL --effective-date=2027-08-01 --description='Premier League new offside law'`.

---

## 16. Report back to lead

1. **Output path:** `C:/Users/matja/Projekty/sportslab/docs/alfa/ml_roadmap_longterm_mlops.md` (approximately 650+ lines of dense, sectioned content — shorter than the 2000-3000 upper bound in task brief, which I judged excessive for a single-founder roadmap; this length is readable in one sitting and still covers the requested breadth. Signal over volume.)

2. **Top 5 automation wins (by founder hours freed):**
   - **§4.1 Experiment runner (scheduled + PR-triggered)** — kills ~90 min/week of manual `sl backtest run` + MLflow review. **Biggest single ROI.**
   - **§4.2 Auto-promotion for Safe-tier** — ~30 min per candidate × 2 candidates/month = 1h/month saved, plus eliminates a class of "forgot a gate" errors.
   - **§4.6 Great Expectations at ingestion** — eliminates the "chased a bug for 3h because Serie A stats scraper had nulls" class of incident. Hard to quantify but saves whole afternoons quarterly.
   - **§5.1 Canary deployment** — replaces the "wait 2 weeks to know if model is better" anxiety with a statistical decision in days. Compounds every retrain.
   - **§7.1 Causal monitoring** (V3) — end-state dream. When it works, every regression becomes a Linear ticket with root cause attached, not a 4h debug session.

3. **3 dumbest current manual things (shame-list):**
   - **Promotion gates live in markdown, not code.** It's 2026, we have `uv`, `pydantic`, Typer — yet the 7 promotion criteria in mleng.md are copy-pasted-and-hoped-for. First beta automation must make gates executable (`sl promote check`).
   - **No pre-flight rollback test.** We keep n-2 archives on Pi but have never verified the previous archive actually runs against today's fixture schema. If scraper schema changed, "rollback" = "crash." A 5-line `ssh pi 'sl predict dry-run --model=<prev>'` on every deploy fixes this.
   - **MLflow UI as primary review surface.** We screenshot reliability diagrams and paste to Telegram — the Stone Age of ML review. HTML report auto-generated and linked in Linear (§3.5) is basic hygiene; doing it by hand is indefensible.

4. **Dedicated MLOps hire triggers (concrete):** detailed in §7.4 and §12. TL;DR **hire when ANY ONE of:**
   - Founder ML-ops sustained >3 h/week for 3 months
   - Infra cost >200 EUR/mo
   - >1 P0/month with duration >2h
   - >2 sports in production (multi-sport breaks solo-founder model)
   - Revenue >150k EUR ARR
   - Team ≥3 people
   Before any trigger fires, contractor (0.3-0.5 FTE at 2000-4000 EUR/mo) beats FT hire.

5. **Anticipated disagreements:**

   **With DrMat (pure-math view):** he will push for online learning sooner and for Bayesian continual updates; this plan defers both to V2. He will argue we're leaving 3-5% growth on the table. My position: at beta scale, operational-safety of weekly retrain > mathematical optimality of online learning. **I'm right about ops, he's right about math — compromise is to shadow-test online learning at V1, production only if it pays off for 8 weeks.**

   **With mleng_b (product/trust view, per the 3-voice framing in alpha plan):** mleng_b will want aggressive per-league models in beta for "user trust in individual leagues"; this plan defers to V2. mleng_b will argue monolithic model hides "La Liga is terrible" behind "global average." My position: per-league calibration without n_val ≥500 per league calibrates noise (DrMat §2.3); we need 12+ months of live data before splitting. **Until then, transparent disclosure of per-league gaps on landing page beats pretending granular models exist.**

   **With mleng persona itself (different MLOps philosophy):** a "bigtech MLOps" view would push for Kubernetes + Feast + Kubeflow + DataDog from Beta. My position: at solo-founder scale, every SaaS line item is a scalability tax on decisions, not compute. cron + custom Postgres + Grafana self-hosted is **operationally faster** than the K8s stack for the next 18 months. **Revisit when hiring second FT engineer — until then, the right answer is always "fewer moving parts."**

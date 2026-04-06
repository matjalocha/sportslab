# Machine Architecture

**Cel:** Dokument źródłowy dla architektury całodobowej maszynki. Opisuje komponenty, data flow, timing, zależności.

## High-level diagram (3 warstwy)

```
┌─────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                         │
│                                                              │
│   ┌────────────┐    ┌────────────┐    ┌──────────────┐      │
│   │  Next.js   │    │  FastAPI   │    │  Telegram    │      │
│   │    Web     │    │   Public   │    │   Bot Pro    │      │
│   │    App     │◄───┤    API     │───►│  (P6 sec.)   │      │
│   └────────────┘    └─────┬──────┘    └──────────────┘      │
│                           │                                  │
└───────────────────────────┼─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   APPLICATION LAYER                          │
│                                                              │
│   ┌────────────────────────────────────────────────┐        │
│   │               Prefect Server                    │        │
│   │          (orchestration + scheduling)           │        │
│   └────────────┬────────────────────────┬──────────┘        │
│                │                        │                    │
│                ▼                        ▼                    │
│   ┌─────────────────┐        ┌──────────────────┐            │
│   │  Scraping Flows │        │  Training Flows  │            │
│   │  (DataEng)      │        │  (MLEng)         │            │
│   └────────┬────────┘        └────────┬─────────┘            │
│            │                          │                      │
│            ▼                          ▼                      │
│   ┌─────────────────┐        ┌──────────────────┐            │
│   │ Features Flows  │        │ Prediction Flows │            │
│   │  (DataEng +     │        │  (MLEng +        │            │
│   │   MLEng)        │        │   DrMat)         │            │
│   └────────┬────────┘        └────────┬─────────┘            │
│            │                          │                      │
│            └──────────┬───────────────┘                      │
│                       ▼                                      │
│            ┌────────────────────┐                            │
│            │  Reporting Flows   │                            │
│            │  (SWE + MLEng)     │                            │
│            └────────────────────┘                            │
│                                                              │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                      DATA LAYER                              │
│                                                              │
│  ┌───────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │  Postgres 16  │   │   MLflow     │   │  Backblaze   │    │
│  │  + Timescale  │   │ (model reg)  │   │  B2 (backup) │    │
│  └───────────────┘   └──────────────┘   └──────────────┘    │
│                                                              │
│  ┌───────────────┐   ┌──────────────┐                        │
│  │  Parquet      │   │  Redis cache │                        │
│  │  (features)   │   │  (API)       │                        │
│  └───────────────┘   └──────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                 MONITORING & OBSERVABILITY                    │
│                                                               │
│  ┌────────────┐   ┌────────────┐   ┌──────────────────┐      │
│  │ Grafana /  │   │  Prefect   │   │   Telegram /     │      │
│  │BetterStack │   │   Logs     │   │   Slack alerts   │      │
│  └────────────┘   └────────────┘   └──────────────────┘      │
└───────────────────────────────────────────────────────────────┘
```

## Data flow (per-day)

### Timeline

```
00:00 ────────────────────────────────────────────────────────► 24:00
  │                                                               │
  ▼                                                               │
[Scraping Window]                                                 │
  00:00 — Football results (ended matches 22:00 previous day)     │
  00:30 — Tennis results (multi-timezone)                         │
  01:00 — NBA results (ended matches last night Europe time)      │
  01:30 — NHL results                                             │
  02:00 — Odds movement (overnight)                               │
  02:30 — Pinnacle closing (już zamknięte mecze)                  │

[Data Quality]
  03:00 — Great Expectations checks
  03:30 — Team name normalization verification
  04:00 — Scrape log audit

[Features]
  04:30 — Materialize features (football)
  05:00 — Materialize features (tennis, basketball, hockey)
  05:30 — CLV tracking compute

[ML Pipeline]
  06:00 — Drift detection (PSI, label drift, odds drift)
  06:30 — If drift OR weekly Sunday → Retrain models
  07:00 — Predictions dla upcoming matches (next 7 days)
  07:30 — Calibration check (ECE per liga, per sport)

[Value Bets Generation]
  08:00 — Hybrid Calibrated Portfolio Kelly — strategy execution
  08:30 — Per-strategy backtests update (rolling)

[Reporting]
  09:00 — Generate MD reports
  09:30 — Generate JSON API cache
  10:00 — Generate PDF reports (for paid customers)
  10:30 — Push to API + notify clients (webhooks, emails)

[Operations]
  11:00 — Backup Postgres → B2
  11:30 — Backup MLflow → B2
  12:00 — Health check rollup

[Live Operations - throughout day]
  Every 2h before match: lineup scraping (Sofascore)
  Every 30m: odds monitoring (value changes)
  Every 1h: in-play research data (not production in P5)
  2h after match end: result scraping + validation

[End of day]
  23:00 — Daily report to Lead (Telegram)
  23:30 — Cost attribution calculation
```

## Component responsibilities

### Scraping Flows (DataEng)

- **`scrape_football_results`** — daily, all 10 leagues
- **`scrape_football_odds`** — 4x per day (morning, midday, evening, pre-match)
- **`scrape_tennis_results`** — daily, continuous throughout day for live
- **`scrape_basketball_results`** — daily (NBA + EuroLeague)
- **`scrape_hockey_results`** — daily during season
- **`scrape_pinnacle_closing`** — daily, previous day's closed matches
- **`scrape_lineups`** — 2h before each match, multi-source

### Training Flows (MLEng + DrMat)

- **`retrain_football_ensemble`** — drift-triggered + weekly Sunday safety net
- **`retrain_tennis_model`** — same trigger
- **`retrain_basketball_model`** — same trigger
- **`retrain_hockey_model`** — same trigger
- **`calibrate_models`** — after each retrain
- **`validate_models`** — walk-forward on held-out, gate promotion to production

### Prediction Flows (MLEng)

- **`predict_upcoming`** — daily, predicts next 7 days all sports
- **`generate_value_bets`** — daily, using production model
- **`apply_portfolio_kelly`** — daily, portfolio optimization
- **`clv_tracking`** — daily, vs Pinnacle closing

### Reporting Flows (SWE + MLEng)

- **`generate_md_reports`** — daily + on-demand
- **`generate_json_api`** — daily, pushes to API cache
- **`generate_pdf_reports`** — daily for paid customers (P6)
- **`publish_to_clients`** — webhooks, emails, Telegram Pro bot

### Operations Flows (DataEng + SWE)

- **`backup_database`** — daily
- **`backup_mlflow`** — daily
- **`data_quality_checks`** — daily
- **`health_check_rollup`** — continuous
- **`cost_attribution`** — daily

## Infrastructure topology

```
                    Internet (Cloudflare)
                           │
                           ▼
        ┌──────────────────────────────────┐
        │    Production VPS (Hetzner CX42) │
        │    (16 GB RAM, 8 vCPU)           │
        │                                   │
        │  ┌────────────────────────────┐  │
        │  │       Docker Compose        │  │
        │  │                             │  │
        │  │  • nginx (reverse proxy)    │  │
        │  │  • api (FastAPI)            │  │
        │  │  • web (Next.js)            │  │
        │  │  • prefect server           │  │
        │  │  • prefect worker(s)        │  │
        │  │  • postgres 16 + timescale  │  │
        │  │  • mlflow                   │  │
        │  │  • redis                    │  │
        │  │                             │  │
        │  └────────────────────────────┘  │
        │                                   │
        └──────────────┬───────────────────┘
                       │
                       │ (SSH, rsync, HTTPS)
                       │
                       ▼
        ┌──────────────────────────────────┐
        │   Staging VPS (Hetzner CX32)     │
        │   (8 GB RAM, 4 vCPU)             │
        │   Same stack for testing          │
        └──────────────────────────────────┘
                       │
                       │
        ┌──────────────┼──────────────────┐
        │              │                  │
        ▼              ▼                  ▼
   ┌─────────┐   ┌──────────┐     ┌──────────────┐
   │ GPU Pod │   │ Backblaze│     │ Cloudflare   │
   │(RunPod) │   │    B2    │     │   (DNS/CDN)  │
   │(ephemer)│   │ (backup) │     │              │
   └─────────┘   └──────────┘     └──────────────┘
```

## Security considerations

- **SSH** tylko z whitelisted IPs (VPN + static IPs zespołu)
- **Firewall** — open porty: 22 (SSH), 80, 443 (HTTP/HTTPS), 5432 (Postgres — tylko internal), 4200 (Prefect UI — VPN only)
- **Secrets** — wszystkie w Doppler, zero hardcoded
- **Database users** — read-only dla app, write-only dla pipelines, admin tylko dla DataEng
- **Rate limiting** — nginx rate limits dla public API
- **WAF** — Cloudflare WAF basic rules

## Scaling considerations (Future)

### P5 → P6
- Dodanie load balancer jeśli >1 API server
- Separate DB server (managed Postgres zamiast Docker)
- Redis cluster dla API cache

### P6 → P6+
- Kubernetes jeśli >5 servers
- Multi-region (EU + US) dla latency
- CDN dla static assets (Cloudflare Pages)
- Separate ML inference servers (dedicated GPU)

## Disaster Recovery (DR)

### Scenarios

1. **Production VPS dies** → Odtwórz z Terraform + ostatniego backupu Postgres. RTO: 4h. RPO: 24h.
2. **Database corruption** → Restore z B2 backup. RTO: 2h. RPO: 24h.
3. **Model poisoning / bad deployment** → Rollback do poprzedniego modelu w MLflow. RTO: 15 min. RPO: 0.
4. **Scraping bany wszystkich bukmacherów jednocześnie** → Fallback na Pinnacle + Betfair only. RTO: 1h. RPO: 1h.
5. **Prefect server crashes** → Restart z Docker, flows wznowią po scheduling. RTO: 30 min. RPO: 0 (flows są idempotentne).

### Recovery runbook
Szczegóły w `docs/runbook/dr_plan.md` (do utworzenia w P5.44).

### Monthly DR drill
- Raz w miesiącu symulacja: jedna osoba odtwarza system z backupów na czystym VPS
- Mierzymy czas + dokumentujemy problemy
- Update runbook gdy coś nie działa

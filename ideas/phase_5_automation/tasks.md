# Phase 5 — Tasks

## Task table

### Infrastructure setup

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P5.1 | Hetzner Cloud account + staging VPS (CX32, Ubuntu 22) | SWE | — | — | Staging VPS działa, SSH access z team keys, Docker zainstalowany |
| P5.2 | Terraform / Ansible setup dla VPS configuration | SWE | DataEng | P5.1 | Odtworzenie VPS z IaC działa, dokumentowane |
| P5.3 | Production VPS (CX42) | SWE | — | P5.2 | Production VPS zkonfigurowany, firewall, fail2ban, monitoring user |
| P5.4 | Cloudflare DNS + SSL dla wszystkich subdomain (api., app., grafana., prefect.) | SWE | Lead | P5.3 | DNS records, SSL active, HTTPS redirect |
| P5.5 | Backblaze B2 bucket + credentials | DataEng | SWE | — | Bucket utworzony, access key w Doppler |
| P5.6 | Doppler project (staging, prod) + secrets sync | SWE | DataEng | — | Secrets dostępne na serwerach, rotacja udokumentowana |
| P5.7 | Docker images dla wszystkich services (api, scheduler, ml, scraper) | SWE | DataEng, MLEng | P1 done | Images buildowane na CI, push do GHCR |

### Database migration

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P5.8 | Postgres 16 + Timescale extension na production VPS | DataEng | SWE | P5.3 | Postgres działa, Timescale zainstalowane, backup user |
| P5.9 | Alembic migration — nowy baseline dla Postgres (z SQLite jako source) | DataEng | MLEng | P5.8 | Migration scripts uruchamialne, schema identical na PG |
| P5.10 | Bulk data migration — SQLite → Postgres | DataEng | — | P5.9 | Wszystkie tabele przeniesione, row counts match, testy passing na PG |
| P5.11 | Partitioning — matches/odds tabele per (sport, season) | DataEng | — | P5.10 | Partitioning w Alembic, testy performance |
| P5.12 | Read-only user + application user dla aplikacji | DataEng | SWE | P5.11 | Role + permissions działają |
| P5.13 | Backup strategy — daily snapshot → B2, weekly full, monthly test restore | DataEng | SWE | P5.8, P5.5 | Automatic backup job, test restore successful |
| P5.14 | DB monitoring — slow queries, connection pool, disk usage | DataEng | SWE | P5.8 | Grafana/Better Stack pokazuje metrics |

### Orchestration — Prefect flows

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P5.15 | Prefect Server self-hosted (Docker) lub Cloud (free tier) | DataEng | SWE | P5.3 | Prefect UI dostępne, worker uruchomiony |
| P5.16 | Flow: scraping — parametryzowane per (sport, league, source) | DataEng | — | P5.15 | Flow działa dla football top-5, deployable |
| P5.17 | Flow: features materialization — parametryzowane per sport | DataEng | MLEng | P5.16 | Flow generates parquet, cached inteligentnie |
| P5.18 | Flow: training — drift-triggered + weekly safety net | MLEng | DataEng | P5.17 | Flow trenuje model, zapisuje do MLflow, publishes prediction model |
| P5.19 | Flow: predictions — per sport, per upcoming window | MLEng | DataEng | P5.18 | Flow generates predictions, zapisuje do DB + cache |
| P5.20 | Flow: bets generation (portfolio Kelly) — per strategy | MLEng | DrMat | P5.19 | Flow generates `bets_r{N}.md`, JSON, DB entries |
| P5.21 | Flow: reporting — MD, JSON, PDF (PDF dla P6 klientów) | SWE | MLEng | P5.20 | Reports zapisywane, dostępne via API |
| P5.22 | Flow: CLV tracking — daily Pinnacle closing pull + CLV compute | DataEng | MLEng | P5.19 | CLV tabela aktualizowana daily |
| P5.23 | Flow: drift detection — daily PSI compute | MLEng | DrMat | P5.17 | Drift raport generowany, trigger retraining gdy PSI > 0.25 |
| P5.24 | Flow: data quality checks — Great Expectations suites | DataEng | MLEng | P5.10 | GE suites running, alerts gdy fail |
| P5.25 | Flow: backup — daily Postgres snapshot → B2 | DataEng | SWE | P5.13 | Daily backup job w Prefect |
| P5.26 | Flow orchestrator — master flow z dependencies między flows | DataEng | MLEng | P5.15-25 | Master flow uruchamia cały pipeline na 1 click + scheduled |
| P5.27 | Flow scheduling — cron-like schedule w Prefect | DataEng | — | P5.26 | Daily schedule aktywny, monitoring |

### GPU inference

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P5.28 | RunPod / Lambda account + API integration | MLEng | SWE | — | Credits dodane, API key w Doppler |
| P5.29 | On-demand GPU pod provisioning — ephemeral dla TabPFN inference | MLEng | SWE | P5.28 | Prefect flow uruchamia GPU pod, robi inference, terminuje |
| P5.30 | Fallback CPU TabPFN — gdy GPU niedostępne | MLEng | — | P5.29 | Pipeline nie pada gdy GPU nie działa, logs warning |
| P5.31 | Cost monitoring dla GPU | MLEng | SWE | P5.29 | Dashboard $ per dzień, alert > €10/dzień |

### Monitoring + alerting

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P5.32 | Decision: Better Stack vs self-hosted Grafana/Loki | SWE | Lead | — | Decyzja udokumentowana, wybrany stack |
| P5.33 | Monitoring stack deployment | SWE | DataEng | P5.32 | Dashboards dostępne, logs collecting |
| P5.34 | Dashboards: system metrics (CPU, RAM, disk, network) | SWE | — | P5.33 | 1 dashboard per VPS |
| P5.35 | Dashboards: pipeline metrics (scrape success rate, records processed, latency) | DataEng | SWE | P5.33 | 1 dashboard per major flow |
| P5.36 | Dashboards: model metrics (ECE, CLV, ROI rolling, drift) | MLEng | DrMat | P5.33 | 1 dashboard per sport |
| P5.37 | Dashboards: business metrics (predictions count, bets generated, total stakes) | Lead | MLEng | P5.33 | Business dashboard dla Lead |
| P5.38 | Alerting rules — krytyczne (pipeline down, DB unreachable) | SWE | DataEng | P5.33 | Alerts wysyłane do Telegram |
| P5.39 | Alerting rules — warning (slow query, high drift, low CLV) | MLEng | DrMat | P5.33 | Warnings wysyłane do Slack |
| P5.40 | On-call rotation + runbook dla typowych alertów | Lead | SWE, DataEng | P5.38 | Runbook w `docs/runbook/`, rotacja ustalona |

### Reliability + DR

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P5.41 | Health checks — każdy flow ma health endpoint | DataEng | SWE | P5.26 | Health endpoints zwracają 200 gdy OK |
| P5.42 | Auto-retry — transient failures (network, rate limit) | DataEng | — | P5.16 | Retries z exponential backoff, max 3 |
| P5.43 | Rollback mechanism — poprzedni model dostępny, DB backup z 7 dni | MLEng | DataEng | P5.13 | `sl rollback --model v2025-11-01` działa |
| P5.44 | DR plan — pisemny, testowany | SWE | DataEng | P5.13 | `docs/runbook/dr_plan.md`, monthly drill |
| P5.45 | Chaos testing — randomly kill VPS, check restore | SWE | DataEng | P5.44 | System restoruje < 4h |
| P5.46 | Production deployment pipeline — GitHub Actions → Docker → Hetzner | SWE | DataEng | P5.7, P5.3 | `git push` na main = auto deploy na staging, manual gate na prod |
| P5.47 | 30-day stability test — system działa bez manual intervention | cały zespół | Lead | wszystko | 30 dni log bez manual interventions |

### Cost management

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P5.48 | Cost dashboard — aggregacja z Hetzner, B2, Doppler, Prefect, RunPod | SWE | Lead | — | Monthly cost report, auto-generated |
| P5.49 | Cost optimization review | Lead | SWE, DataEng, MLEng | P5.48 | 3 action items dla cost reduction |

## Równoległa praca w P5

- **DrMat**: Advanced research (P2 research backlog items P3+)
- **Designer**: Aplikacja Next.js design + handoff dla P6
- **Lead**: Fundraising research (jeśli potrzeba), customer discovery intensywny

## Kluczowe decyzje w P5

1. **Prefect vs Dagster** — rekomendacja Prefect 2.x
2. **Better Stack vs self-hosted Grafana** — rekomendacja Better Stack w P5 (szybciej), self-hosted w P6 (taniej na scale)
3. **Postgres self-hosted vs managed (Supabase/Neon)** — **rekomendacja: managed (Supabase)** dla szybszego P5, self-hosted opcjonalnie w P6 dla kontroli
4. **On-call rotation** — wszyscy czy tylko SWE + DataEng? **Rekomendacja:** tylko engineering rotuje on-call
5. **Cost budget** — max €500/m-c w P5. Jeśli więcej, review w P5.49

## DoD fazy P5

- [ ] Wszystkie flows zautomatyzowane w Prefect
- [ ] Monitoring + alerting działa, alerts są actionable (nie noise)
- [ ] DB migracja SQLite → Postgres skończona
- [ ] Backup daily + test restore pozytywny
- [ ] DR plan przetestowany
- [ ] **30 dni bez manual intervention** (= DoD)
- [ ] Cost report pokazuje < €500/m-c
- [ ] Documentation kompletna (runbook, architecture, DR)

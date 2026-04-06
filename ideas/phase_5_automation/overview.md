# Phase 5 — Automation

**Widełki:** 6-10 tygodni (może iść równolegle z końcówką P4)
**Cel:** Przejście z **ręcznie uruchamianych skryptów** do **całodobowej maszynki**, która działa bez manual intervention.
**Przejście do P6:** Patrz [phase_transitions.md](../phase_transitions.md#p5--p6--automation--product--app)

## Kontekst

Po P1-P4 mamy:
- Czysty kod, CI/CD, testy
- Calibrowane modele z IP
- 10 lig + 3 sporty
- Wszystko **nadal uruchamiane ręcznie** (user wpisuje `sl run-pipeline` codziennie)

P5 = **zero manual intervention przez 30 dni**.

## Co to znaczy "zero manual intervention"

Zespół nie loguje się na serwer codziennie żeby odpalić skrypt. Zamiast tego:
- **Orkiestrator (Prefect/Dagster)** wie co ma uruchomić, kiedy i w jakiej kolejności
- **Monitoring** wykrywa problemy zanim my zauważymy
- **Alerty** przychodzą tylko gdy coś wymaga ludzkiej decyzji (nie na każdy warning)
- **Retry** obsługuje przejściowe błędy automatycznie
- **Rollback** działa gdy nowy deployment się psuje
- **Backup** jest automatic i testowany

Cel: przez 30 dni zespół może wyjechać na urlop, a system działa.

## Architektura maszynki (high-level)

```
┌─────────────────────────────────────────────────┐
│             Prefect / Dagster                    │
│         (orkiestracja flows)                     │
└──────────────┬──────────────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌──────────┐
│ Scraping│         │  Trening │
│  Flows  │         │  Flows   │
└────┬────┘         └────┬─────┘
     │                   │
     ▼                   ▼
┌──────────┐        ┌──────────┐
│ Postgres │        │  MLflow  │
│  (data)  │        │ (models) │
└──────────┘        └──────────┘
     │
     ▼
┌──────────────┐
│   Features   │
│   Materialize│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Prediction  │
│  + Bets Gen  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Reports +  │
│   API Cache  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Monitoring  │
│  + Alerting  │
└──────────────┘
```

## Daily schedule (przykładowy)

```
00:00  Scrape yesterday's results (all sports, leagues)
01:00  Update odds (overnight movement from bookmakers)
02:00  Pinnacle closing odds dla zamkniętych meczów → CLV tracking
03:00  Data quality checks (Great Expectations)
04:00  Materialize features (parquet refresh)
05:00  Drift detection — jeśli drift, trigger retraining
06:00  Retrain models (jeśli drift lub weekly cadence)
07:00  Predict upcoming matches (next 7 days)
08:00  Generate value bets + portfolio Kelly stakes
09:00  Generate reports (MD + JSON + PDF dla klientów P6)
10:00  Push to API cache + notify clients
11:00  Health check + rollup metrics
12:00  Daily backup do Backblaze B2

... przez dzień live:
- Sofascore lineup scraping 2h przed każdym meczem
- Live odds monitoring co 15 minut
- Post-match result scraping 2h po każdym meczu
```

## Kluczowe komponenty

### 1. Orkiestracja
**Wybór:** Prefect 2.x (rekomendacja) lub Dagster
- Prefect — prostszy setup, lepsza Python-native API
- Dagster — bardziej opinionated, lepszy dla data quality

### 2. Infrastructure
- **Staging VPS:** Hetzner CX32 (~€20/m-c) — testowanie przed production
- **Production VPS:** Hetzner CX42 (~€35/m-c) — 8 vCPU, 16GB RAM
- **GPU on-demand:** RunPod / Lambda Labs dla TabPFN inference (spot instances)
- **Storage:** Backblaze B2 dla backupów (~€5/m-c dla 1TB)
- **CDN:** Cloudflare free tier

### 3. Database
**Migracja SQLite → Postgres 16** (w P5.X):
- Timescale extension dla time-series odds
- Partitioning per sport + per liga
- Read replicas jeśli potrzebne (prawdopodobnie nie w P5)

### 4. Monitoring
**Stack (do wyboru):**
- **Grafana + Loki + Prometheus** (self-hosted, pełna kontrola)
- **Better Stack** (hosted, szybszy setup, €22/m-c Pro)
- **Rekomendacja:** Better Stack w P5, migracja na self-hosted w P6 gdy skalujemy

### 5. Secrets
**Doppler** lub **1Password Connect** — secrets sync do production bez hardcodingu.

### 6. Alerting
- **Telegram bot** dla Lead + engineering team
- **Slack webhook** dla reszty zespołu
- **Email** dla krytycznych failures
- **PagerDuty** — tylko jeśli P6 wymaga (klienci płacący za uptime SLA)

## Główne outputy

- Prefect flows dla wszystkich pipeline'ów (scraping, training, prediction, reporting)
- Postgres production DB z partitioningiem
- Monitoring stack (Grafana/Loki lub Better Stack) z dashboardami
- Alerting — krytyczne vs informative alerts
- Backup strategy — daily → B2, monthly → offsite, test restore monthly
- DR plan — odtworzenie systemu < 4h
- Cost report — infra $ per miesiąc, per sport, per liga
- SLA internal — system uptime target 99% w P5 (higher w P6)

## Zadania

Szczegóły → [tasks.md](tasks.md)

## Wspierające dokumenty

- [machine_architecture.md](machine_architecture.md) — szczegółowy diagram architektury + data flow

## Ryzyka w P5

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|---|---|---|---|
| Prefect Cloud limit darmowy przekroczony | Średnie | Niski | Self-hosted Prefect server lub upgrade plan |
| Migracja SQLite → Postgres zepsuje dane | Średnie | Wysoki | Dual-write period, test na kopii, stopniowa migracja |
| Scraping bans podczas daily automation (STS, LVBet widzą intense traffic) | Wysokie | Wysoki | Rotation proxy, variable delays, distributed scraping |
| GPU bursts przekraczają budget | Średnie | Średni | Budget alerts, fallback na CPU TabPFN, preemptible spot |
| Backup restore nie działa gdy potrzebny (untested) | Średnie | **Krytyczny** | Monthly restore drill, test automatyczny |
| Monitoring alert fatigue (za dużo noise) | Wysokie | Średni | Stopniowy tuning alertów, severity levels |
| Pipeline się psuje w weekend gdy zespół offline | Średnie | Wysoki | On-call rotation, auto-rollback, health checks |
| Cost rośnie niekontrolowanie | Średnie | Średni | Monthly cost review, budget alerts, cost attribution |

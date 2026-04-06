# Data Strategy — Evolution per faza

**Owner:** DataEng (primary), MLEng (consumer)
**Cel:** Ewolucja warstwy danych od obecnego SQLite do production-ready architecture per faza.

## Aktualny stan

- **DB:** SQLite `src/db/football.db` (351MB, 11 tabel)
- **Features:** `data/features/all_features.parquet` (21,709 rows × 825 cols, Mar 2026)
- **Cache:** soccerdata cache w system temp
- **Backup:** ręczny, niesystematyczny
- **Query pattern:** Python/SQLAlchemy z obecnego `src/utils/database.py`

## Ewolucja

### P0 — baseline dokumentacji
- Schema udokumentowana w `docs/schema.md` ✅
- Baseline backup raz (P1.1 task)

### P1 — Alembic migrations + refactor
- **Alembic migrations** dla SQLite — reverse engineer obecny schema
- Rozbicie `src/utils/database.py` na `src/ml_in_sports/db/` per tabela
- Testy na każdym endpoint CRUD
- Connection pooling via SQLAlchemy

### P2 — rozszerzenia schema (nowe features z IP)
- Nowe tabele: `calibration_metrics`, `clv_tracking`, `drift_metrics`, `portfolio_allocations`
- Alembic migration per change
- Indexy dla performance (query patterns z CLV tracking)

### P3 — skalowanie dla 10 lig
- **Performance review** — czy SQLite wystarcza dla 10 lig?
- **Partycjonowanie logiczne** per liga (partitioned views w SQLite)
- **Parquet jako analytical layer** — DuckDB/pyarrow dla large queries
- Materialized views dla częstych zapytań

### P4 — multi-sport schema
- Sport-agnostic base + sport-specific extensions
- **Schema design:**
  ```sql
  CREATE TABLE matches (
    match_id TEXT PRIMARY KEY,
    sport_id TEXT NOT NULL,     -- 'football', 'tennis', 'basketball', 'hockey'
    league_id TEXT NOT NULL,
    date TIMESTAMP,
    home_entity_id TEXT,         -- team dla football/basketball/hockey, player dla tennis
    away_entity_id TEXT,
    ...
  );

  CREATE TABLE match_football_details (
    match_id TEXT PRIMARY KEY REFERENCES matches(match_id),
    home_goals INT,
    away_goals INT,
    home_xg FLOAT,
    ...
  );

  CREATE TABLE match_tennis_details (
    match_id TEXT PRIMARY KEY REFERENCES matches(match_id),
    surface TEXT,
    best_of INT,
    sets JSONB,
    ...
  );
  ```
- **Polymorphic queries** via view `matches_with_details`

### P5 — migracja SQLite → Postgres 16 + Timescale
- **Postgres 16** jako production DB
- **Timescale extension** dla time-series (odds movement, CLV tracking over time)
- **Partitioning fizyczne** per (sport_id, season)
- **Read replicas** opcjonalnie (gdy SELECT load > WRITE load)
- **Connection pooling** via PgBouncer

**Migration plan:**
1. **Dual-write period** — SQLite + Postgres równolegle przez 2 tygodnie
2. **Validation** — row counts, checksums, integrity checks match
3. **Switchover** — production używa Postgres, SQLite jako backup read-only
4. **Decommission** — po 1 miesiącu stabilnej pracy, SQLite jest archiwizowane

**Narzędzia migracji:**
- `pgloader` dla bulk transfer
- Custom Python script dla dual-write
- Alembic dla ongoing schema changes

### P6 — analytical layer + caching
- **Redis** dla API cache (częste queries z value feed, predictions)
- **DuckDB / Parquet** jako analytical layer (raporty, dashboardy)
- **Materialized views** w Postgres dla cross-aggregations
- **Supabase** alternatywa dla managed Postgres

### P6+ — skalowanie horyzontalne (gdy >100 klientów)
- **Sharding** per sport lub per klient
- **Separate OLTP (Postgres) + OLAP (ClickHouse/DuckDB)**
- **CDC** (Change Data Capture) dla real-time analytics
- **Data lake** na S3/B2 dla historical long-term storage

## Data layers (docelowa architektura P5+)

```
┌─────────────────────────────────────────────────────┐
│                   CONSUMER LAYER                     │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │   API    │  │Dashboards│  │ ML Training Jobs │   │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │             │                 │              │
└───────┼─────────────┼─────────────────┼──────────────┘
        │             │                 │
        ▼             ▼                 ▼
┌─────────────────────────────────────────────────────┐
│                    CACHE LAYER                       │
│                                                      │
│  ┌──────────┐                    ┌───────────┐      │
│  │  Redis   │                    │ Parquet + │      │
│  │ (hot)    │                    │  DuckDB   │      │
│  └─────┬────┘                    │(analytic) │      │
│        │                         └─────┬─────┘      │
└────────┼───────────────────────────────┼────────────┘
         │                               │
         ▼                               ▼
┌─────────────────────────────────────────────────────┐
│                 TRANSACTIONAL LAYER                  │
│                                                      │
│        ┌─────────────────────────────────┐          │
│        │  Postgres 16 + Timescale        │          │
│        │  (partitioned per sport/season) │          │
│        └──────────────┬──────────────────┘          │
│                       │                              │
└───────────────────────┼─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                  ARCHIVAL LAYER                      │
│                                                      │
│        ┌─────────────────────┐                      │
│        │  Backblaze B2       │                      │
│        │  (daily snapshots + │                      │
│        │   historical archiv)│                      │
│        └─────────────────────┘                      │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Data quality

### Checks (automatyczne w P5 flows)

**Using Great Expectations:**

1. **Completeness**
   - Każdy match ma home_team, away_team, date, league, sport
   - Odds coverage > 80% per liga per rok
   - Features coverage > 90% per match

2. **Consistency**
   - Team names w `matches` istnieją w `teams`
   - Odds values są w range (1.01, 100)
   - Dates są w przeszłości dla completed matches
   - Home + away goals ≥ 0

3. **Uniqueness**
   - Match id jest unique per (sport, league, date, home, away)
   - Brak duplikatów w odds per bookmaker per match

4. **Referential integrity**
   - Foreign keys walidowane (Postgres robi to natywnie)

5. **Distribution**
   - Home/Draw/Away distribution per liga ~50/25/25 ±5pp
   - Goals per match ~2.5 ±0.5
   - Alerty gdy distribution się dramatycznie zmienia

### Quality gates

- **P1**: Tests pokrywają CRUD operations
- **P5**: Great Expectations suites running daily, alerts gdy fail

## Backup strategy

### P0-P2 (baseline)
- **Ręczny dump** raz na tydzień, upload do B2 manually
- **Retention:** 4 tygodnie

### P5+ (automated)
- **Daily snapshot** → B2 (retention 30 dni)
- **Weekly full** → B2 (retention 12 tygodni)
- **Monthly archive** → B2 cold tier (retention 12 miesięcy)
- **Yearly archive** → infinite retention
- **Monthly test restore** — weryfikacja że backup działa

### Recovery metrics target
- **RPO** (Recovery Point Objective): **24h** (maksymalnie stracamy 1 dzień danych)
- **RTO** (Recovery Time Objective): **4h** (odtworzenie systemu z backupu)

## Data retention policy

### Raw data
- **Historical matches/odds:** forever (unique value)
- **Scraping logs:** 90 dni (dla debugging)
- **API access logs:** 365 dni (dla audit)

### Derived data
- **Features parquet:** regenerated daily z DB, keep last 30 dni
- **Model predictions:** forever (dla CLV tracking + backtest)
- **Model artifacts:** keep last 12 wersji per model

### User data (P6+)
- **Usage logs:** 365 dni (GDPR compliance)
- **Billing records:** 7 lat (regulacje podatkowe)
- **User accounts:** until deletion request + 30 dni
- **User tokens:** until rotation + 90 dni log

## GDPR considerations

- **Player data:** Tylko dane sportowe (publicznie dostępne stats), zero PII players
- **Customer data:** Imię/nazwisko, email, company, billing info — wszystko behind auth
- **Right to be forgotten:** Implementować endpoint `DELETE /v1/users/me` (P6)
- **Data export:** `GET /v1/users/me/export` (GDPR right to portability)
- **Data processing basis:** Legitimate interest (B2B) + explicit consent (B2C)

## Cost implications per faza

| Faza | Storage | Compute | Backup | Monthly |
|---|---|---|---|---|
| P0-P2 | SQLite 1GB | Local | Manual | ~€5 |
| P3 | SQLite 5GB | Local | B2 €1 | ~€6 |
| P4 | SQLite 10GB | Local | B2 €2 | ~€10 |
| P5 | Postgres Hetzner (z VPS) | Hetzner | B2 €5 | ~€30 |
| P6 | Supabase Pro lub self-hosted | Dedicated | B2 €10 | ~€50-100 |
| P6+ | Scale tier | Dedicated + read replicas | B2 €30 | ~€200+ |

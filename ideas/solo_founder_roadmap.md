# Solo Founder Roadmap — SportsLab

> **Kontekst:** Plan w `ideas/` był napisany dla 6-osobowego zespołu seniorów.
> Ten dokument to **oficjalna adaptacja** dla realiów: 1 osoba (Mateusz) + Claude Code.
> Firma zostanie założona dopiero po udowodnieniu profitable modelu.
>
> **Data utworzenia:** 2026-04-06
> **Zastępuje:** oryginalne fazy P0–P6 w zakresie priorytetyzacji i timeline'u

---

## Zasada nadrzędna

Jedno pytanie decyduje o wszystkim: **"Czy model bije rynek?"**

Wszystko co nie przybliża do odpowiedzi na to pytanie — firma, prawnik, design system,
whitepaper na arXiv, Slack, weekly standupy — jest odroczone do momentu gdy odpowiedź
brzmi TAK i są na to dane (CLV > 0 przez 3+ miesiące).

---

## Fazy (zredukowane z 7 do 6)

### R0: Foundations (1 tydzień) — DONE ✅

Zrobione:
- [x] Linear workspace (SPO-5 → SPO-29)
- [x] GitHub monorepo zainicjalizowane
- [x] Tech debt audit (`docs/tech_debt_audit.md`)
- [x] Math audit (`docs/math_audit.md`)
- [x] Pricing research (`ideas/phase_6_product_app/product_offerings.md`)
- [x] Subagenci Claude Code skonfigurowani (10 agentów)

Pominięte (vs oryginalny P0):
- P0.1–P0.3 (firma) → po profitable model
- P0.4–P0.9 (konta firmowe bukmacherów) → konta osobiste wystarczą
- P0.10 (umowy z zespołem) → nie ma zespołu
- P0.15–P0.18 (1Password Teams, Slack, weekly rhythm) → solo
- P0.22–P0.24 (budżet formalny, Doppler, domena) → przedwczesne

### R1: Clean Code (4–6 tygodni) — IN PROGRESS

**P1.4 migracja kodu: DONE ✅** (22/22 moduły, 703 testy, mypy clean)

Pozostało z oryginalnego P1:

| # | Task | Status | Priorytet |
|---|------|--------|-----------|
| P1.5 | CLI entry points (Typer) | TODO | Wysoki — potrzebne do P5 automation |
| P1.8 | GitHub Actions CI | TODO | Wysoki — bezpieczeństwo kodu |
| P1.9 | pre-commit hooks | TODO | Wysoki — łapie błędy przed commitem |
| P1.12 | structlog (zastąp print) | TODO | Średni — potrzebne przed P5 |
| P1.13 | pydantic-settings | TODO | Średni — potrzebne przed P5 |
| P1.14 | Alembic migrations | TODO | Średni — potrzebne przed Postgres |
| P1.15 | Coverage ≥ 80% | TODO | Średni |
| P1.17 | CONTRIBUTING.md | TODO | Niski — solo |

Pominięte z P1 (YAGNI dla solo):
- P1.1 (backup do B2 + archive branch) → git history wystarczy
- P1.6 (notebooks → research/) → nie blokuje nic
- P1.16 (split dużych modułów < 300 LOC) → refaktor w P2 gdy będzie potrzeba
- P1.20 (benchmarks) → premature
- P1.21 (Justfile) → nice-to-have, nie krytyczne
- P1.22–P1.23 (split pipeline.py + database.py) → odroczone, działa jak jest
- P1.25 (CI caching) → optymalizacja, nie teraz
- P1.26 (Docker) → potrzebne dopiero w P5
- P1.27 (design system tokens) → P6
- P1.28 (whitepaper draft) → po profitable model

### R2: Better Models (8–10 tygodni)

Kluczowa faza — tu powstaje (lub nie) edge nad rynkiem. Centralny deliverable:
**`sl backtest --config experiments/X.yaml` → ładny HTML raport + terminal summary.**

Specyfikacja raportu: `docs/design/backtest_report_spec.md`

**Priorytet 0 — Backtest Framework (tydzień 1–2):**
- YAML config (Pydantic model): modele, kalibracja, Kelly, ligi, sezony, rynki
- Walk-forward runner (train on N seasons, test on next)
- Metrics module (log_loss, ECE, Brier, CLV, ROI, Sharpe, drawdown, hit rate)
- Raport HTML (Plotly interactive) — faza 1: sekcje B+D+E (werdykt, CLV, P&L)
- Raport terminal (Rich) — kompaktowe podsumowanie
- CLI `sl backtest --config`

**Priorytet 1 — Kalibracja (tydzień 2–4):**
- P2.2 Temperature Scaling dla TabPFN
- P2.3 Platt scaling per liga per sezon
- P2.4 Isotonic regression
- P2.6 Calibration pipeline — auto-wybór best scaler (walk-forward)
- P2.7 ECE monitoring per liga per rynek (sekcja C raportu)

**Priorytet 2 — Portfolio Kelly (tydzień 4–6):**
- P2.11 Portfolio Kelly z per-match/per-round/per-league limits
- P2.12 Shrinkage Kelly (w kierunku rynku dla outlierów)

**Priorytet 3 — CLV + Drift (tydzień 6–8):**
- P2.15 Pinnacle closing odds (via football-data.co.uk + The Odds API free tier)
- P2.16 CLV tracking rolling 30/90d (sekcja D raportu)
- P2.18 Drift detection (PSI) na key features

**Priorytet 4 — Ensemble + Backtest (tydzień 8–10):**
- P2.23 Hybrid ensemble (LGB + XGB + TabPFN + LogReg meta)
- P2.24 Backtest: `sl backtest --config experiments/hybrid_v1.yaml`
  → pełny raport HTML z porównaniem Hybrid vs LGB vs XGB vs TabPFN
- Raport HTML faza 2: sekcje C+F+H (kalibracja, stakes, model comparison)

Pominięte z P2 (odroczone):
- P2.1, P2.30 (whitepaper, arXiv) → po profitable model
- P2.5 (Beta calibration per market) → nice-to-have, nie krytyczne
- P2.8–P2.10 (Dixon-Coles, goals model) → po podstawowym edge
- P2.9 (Bayesian Dixon-Coles PyMC) → wymaga deep stat knowledge, skip
- P2.13 (korelacje akumulatorów) → optymalizacja, nie core
- P2.17 (CLV alerting Telegram) → prosty if/print wystarczy
- P2.19–P2.22 (label drift, odds drift, auto-retraining, SHAP stability) → overkill na start
- P2.25 (in-play feasibility) → po profitable pre-match
- P2.31–P2.33 (docs, wireframes, customer discovery) → po profitable model

### R3: Proof of Edge (8–16 tygodni) — NOWA FAZA

**Brakuje w oryginalnym planie.** Bez tego nie wiadomo czy model działa live.

**Tydzień 1–4: Paper trading**
- Codzienne predictions na nadchodzące mecze
- Porównanie z closing odds (CLV tracking)
- Logging: prediction → actual result → CLV
- Target: CLV > 0 na 100+ betów

**Tydzień 5–16: Real money (mały stake)**
- Bankroll: €1000–2000 osobistych pieniędzy
- Stake: 1–3% per bet (Kelly/4 lub Kelly/5 — konserwatywnie)
- 2–3 bukmacherów (STS + LVBet/Fortuna)
- Tracking ROI, drawdown, max losing streak
- Target: ROI > 0% po 200+ betów, CLV > 0 sustained

**Decyzja po R3:**
- ✅ CLV > 0 sustained 3+ miesiące → kontynuuj do R4
- ❌ CLV < 0 → wróć do R2, iterate

### R4: Automation (2–3 tygodnie)

Uproszczone vs oryginalny P5 (49 tasków → ~10):

- Hetzner VPS (CX32, €20/mies.)
- Postgres migracja (Alembic)
- cron + Python script (daily: scrape → features → predict → report)
- Telegram bot (alerty + daily bet slip)
- Prosty monitoring (Better Stack free tier lub healthchecks.io)
- B2 backup (SQLite/Postgres dump daily)

Pominięte (overkill dla solo):
- Prefect/Dagster → cron wystarczy
- Grafana/Loki → Better Stack
- Great Expectations → prosty assert w Python
- MLflow model registry → pickle + JSON
- DR plan, chaos testing → backup + testowy restore
- GPU bursts → nie potrzebne na daily inference
- On-call rotation → jesteś jedyną osobą

### R5: Expansion (12–20 tygodni)

Dopiero gdy R4 działa stabilnie przez 30 dni.

**R5a — More Leagues (6–10 tyg.):**
- 5 nowych lig (Top-10 total) — Championship, Eredivisie, Ekstraklasa, Bundesliga 2, Serie B
  (lub inny mix wg dostępności danych i strategicznej wartości)
- Team name normalization per liga
- Feature parity per liga (wszystkie features obecne)
- Backtest per liga (CLV > 0 na 100+ betów)
- Scrapery uruchomione i zweryfikowane

**R5b — More Sports (6–10 tyg., sekwencyjnie po R5a lub częściowo równolegle):**
- Tenis (Jeff Sackmann data, Bradley-Terry/ELO per nawierzchnia, forma, zmęczenie, H2H)
- Koszykówka (NBA Stats API, pace-adjusted metrics, player availability)
- Hokej (NHL API, Natural Stat Trick)
- Abstract sport framework gdy masz 2+ sporty
- Backtest per sport (CLV > 0)

Uwaga: przy solo founder + Claude Code sporty robione sekwencyjnie (nie 3 naraz).
Tenis jako pierwszy (najprostszy model 1v1, najlepsze darmowe dane).

### R6: Product & Revenue (8–12 tygodni)

Dopiero gdy masz 3–6 miesięcy profitable track record.

**Krok 1 — Firma (1–2 tyg.):**
- sp. z o.o. (lub JDG — decyzja wg sytuacji)
- Konto firmowe
- Konta bukmacherskie firmowe
- Prawnik (1–2h konsulting: regulacje hazardowe, ToS)
- Księgowy (biuro rachunkowe)

**Krok 2 — MVP produkt (4–6 tyg.):**
- FastAPI backend z 1 SKU: **Value Feed API** (probabilities per match, CLV, Kelly stakes)
- Clerk auth + Stripe subscription
- Prosta docs page (MkDocs lub Mintlify)
- Landing page (Framer, $30/mies. — szybciej niż Next.js)

**Krok 3 — Pierwszy klient (2–4 tyg.):**
- 3–5 rozmów z potencjalnymi klientami (tipsterzy, mali bukmacherzy, ML teams)
- Track record jako dowód (CLV charts, ROI, Sharpe)
- Target: 1 płacący klient, MRR > koszty infra (~€50)

Pominięte (vs oryginalny P6):
- 9 SKU → 1 SKU na start
- Next.js dashboard → API-first, dashboard później
- Design system → shadcn/ui out of the box
- 42 klientów / €55k MRR → 5 klientów / €2–5k MRR realistic year 1
- Customer success manager → Ty
- Growth/marketing team → Ty + content

---

## Koszty realne (solo founder)

| Faza | Miesięczny koszt |
|------|-----------------|
| R0–R2 | ~€5 (GitHub Pro, reszta free) |
| R3 | ~€5 + bankroll €1000–2000 (jednorazowo) |
| R4 | ~€25 (+ Hetzner €20) |
| R5 | ~€30 (+ proxy €5 na scraping) |
| R6 | ~€100–200 (Stripe fees, Framer, prawnik jednorazowo) |

Vs oryginalny plan: €229/mies. tooling + €55–80k/mies. zespół.

---

## Timeline realistyczny

| Faza | Czas | Kumulatywnie |
|------|------|-------------|
| R0 | 1 tyg. | 1 tyg. ✅ |
| R1 | 4–6 tyg. | 5–7 tyg. (in progress) |
| R2 | 8–10 tyg. | 13–17 tyg. |
| R3 | 8–16 tyg. | 19–31 tyg. |
| R4 | 2–3 tyg. | 21–34 tyg. |
| R5a (ligi) | 6–10 tyg. | 27–44 tyg. |
| R5b (sporty) | 6–10 tyg. | 33–54 tyg. |
| R6 | 8–12 tyg. | 41–66 tyg. |

**Do decyzji "profitable czy nie": ~5–8 miesięcy.**
**Do pełnego expansion (10 lig + 3 sporty): ~8–14 miesięcy.**
**Do pierwszego klienta: ~10–16 miesięcy.**

---

## Narzędzia — co zostaje, co odpada

### Zostaje (potrzebne teraz lub wkrótce)
- Python 3.11+, uv, pandas, numpy, scikit-learn
- LightGBM, XGBoost, TabPFN
- pytest, ruff, mypy, pre-commit
- structlog, pydantic-settings
- GitHub, Linear, Claude Code
- Typer (CLI), SQLAlchemy + Alembic
- FastAPI (R6), Clerk (R6), Stripe (R6)

### Zostaje ale później
- Postgres + Timescale (R4)
- Docker (R4)
- Hetzner (R4)
- Next.js + shadcn/ui + Tremor (R6, dashboard)
- Framer (R6, landing page)
- Recharts/D3 (R6, zaawansowane wizualizacje)

### Odpada (YAGNI dla solo)
- Slack, Google Workspace (6 users), Notion
- 1Password Teams, Doppler
- MLflow, DVC, Weights & Biases, Feast
- Prefect/Dagster (cron wystarczy)
- Great Expectations (asserty w Pythonie)
- Grafana + Loki + Prometheus (Better Stack)
- Redis (nie potrzebne przy <100 req/s)
- Kafka/RabbitMQ (nigdy nie było potrzebne)
- design system tokens, Figma library
- Miro, FigJam, Calendly, Loom
- factory_boy, hypothesis (plain pytest wystarczy)
- Terraform/Ansible (1 serwer = ręcznie)

### Dodane (nie było w planie)
- **Framer** — landing page w R6 (szybciej niż Next.js)
- **Tremor** — gotowe dashboard components w R6
- **v0.dev** — generowanie UI z promptów
- **The Odds API** — Pinnacle closing odds (free tier)
- **football-data.co.uk** — historyczne closing odds
- **healthchecks.io** — monitoring cron jobs (free tier)

---

## Relacja do oryginalnych plików `ideas/`

Oryginalne pliki w `ideas/phase_*` pozostają jako **reference** — zawierają wartościowy
kontekst (DoD, dependency graphs, domain knowledge). Ten dokument **nadpisuje priorytetyzację
i timeline**, nie kasuje wiedzy.

Gdy SportsLab urośnie do zespołu, oryginalne plany P3–P6 mogą być przywrócone
w pełnym zakresie.

---

## Pinnacle access (krytyczna ścieżka)

Pinnacle nie jest dostępne legalnie z Polski. Rozwiązania:
1. **football-data.co.uk** — historyczne Pinnacle closing odds (darmowe, CSV)
2. **The Odds API** — live Pinnacle odds (free tier: 500 calls/mies.)
3. **Betfair Exchange** — alternatywny benchmark (sharp market)
4. **Oddschecker API** (jeśli dostępne) — aggregated closing

CLV tracking vs Pinnacle closing jest **gold standard** dowodu edge'u.
Bez tego nie ma "proof of profitability".

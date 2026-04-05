# Phase 3 — Tasks

## Task table

| # | Task | Owner | Collab | Depends on | DoD | Gap |
|---|------|-------|--------|------------|-----|-----|
| P3.0 | Data audit — każda z 5 proponowanych lig: dostępność w Understat/FBref/Sofascore | DataEng | MLEng, DrMat | P2 done | `data_source_matrix.md` wypełniony, decision log "go/no-go" per liga | — |
| P3.1 | Rozszerzenie `extractors/` o nowe ligi — Eredivisie | DataEng | — | P3.0 | Scraper działa, dane w DB, testy pokrywają | — |
| P3.2 | Rozszerzenie `extractors/` o Primeira Liga | DataEng | — | P3.0 | Scraper działa | — |
| P3.3 | Rozszerzenie `extractors/` o Championship | DataEng | — | P3.0 | Scraper działa | — |
| P3.4 | Rozszerzenie `extractors/` o MLS | DataEng | — | P3.0 | Scraper działa | — |
| P3.5 | Rozszerzenie `extractors/` o Brasileirão | DataEng | — | P3.0 | Scraper działa | — |
| P3.6 | Team name normalization — Eredivisie aliases | DataEng | — | P3.1 | `teamname_replacements.json` aktualne, testy per team | — |
| P3.7 | Team name normalization — Primeira Liga | DataEng | — | P3.2 | Aktualne + testy | — |
| P3.8 | Team name normalization — Championship | DataEng | — | P3.3 | Aktualne + testy | — |
| P3.9 | Team name normalization — MLS | DataEng | — | P3.4 | Aktualne + testy | — |
| P3.10 | Team name normalization — Brasileirão | DataEng | — | P3.5 | Aktualne + testy | — |
| P3.11 | Feature engineering check per new league — czy wszystkie features mają non-NaN values | MLEng | DataEng | P3.1-3.5 | `sl features check --league eredivisie` raportuje coverage > 80% | — |
| P3.12 | Season codes + `seasons.py` rozszerzone — MLS ma inny kalendarz (Marzec-Listopad), Brasileirão też | DataEng | MLEng | P3.4, P3.5 | Funkcja `get_season_code(date, league)` działa per liga | — |
| P3.13 | Odds scraping — nowe ligi u STS/Fortuna/Betclic/LVBet/Superbet | DataEng | SWE | P3.1-3.5 | Odds dostępne, zapisywane do `match_odds` | — |
| P3.14 | Trening modelu — każda nowa liga ma własny + cross-league baseline | MLEng | DrMat | P3.11 | Modele w registry, metrics zapisane | — |
| P3.15 | Backtest walk-forward — Eredivisie | MLEng | DrMat | P3.14 | Raport w `docs/leagues/eredivisie.md` — ROI, ECE, CLV, decision | — |
| P3.16 | Backtest walk-forward — Primeira Liga | MLEng | DrMat | P3.14 | Raport w `docs/leagues/primeira_liga.md` | — |
| P3.17 | Backtest walk-forward — Championship | MLEng | DrMat | P3.14 | Raport w `docs/leagues/championship.md` | — |
| P3.18 | Backtest walk-forward — MLS | MLEng | DrMat | P3.14 | Raport w `docs/leagues/mls.md` | — |
| P3.19 | Backtest walk-forward — Brasileirão | MLEng | DrMat | P3.14 | Raport w `docs/leagues/brasileirao.md` | — |
| P3.20 | Cross-league model — czy joint training bije per-league? (NB18 rozszerzone) | DrMat | MLEng | P3.15-19 | Raport, decyzja: per-league czy cross | — |
| P3.21 | Per-liga calibration tuning (temperature, Platt, beta) | MLEng | DrMat | P3.14 | ECE < 2% per liga | — |
| P3.22 | Cost analysis per liga — ile scraping, ile infra, ile czasu | DataEng | Lead | P3.13 | Tabela w `infrastructure/cost_model.md` | — |
| P3.23 | Decision log — które ligi zatrzymujemy (ROI > 5%), które porzucamy | Lead | MLEng, DrMat | P3.15-19 | Dokument decyzyjny `docs/leagues/decision_log.md` | — |
| P3.24 | Materialize features dla wszystkich 10 lig jednocześnie (scaling test) | DataEng | MLEng | P3.11 | `all_features.parquet` zawiera 10 lig, czas materializacji zmierzony | — |
| P3.25 | Test performance regresji — czy 10 lig w DB spowolni pipeline? | MLEng | DataEng | P3.24 | Benchmark vs P1 baseline, decyzje o optymalizacji (indeksy DB, partitioning) | — |
| P3.26 | DB schema — partitioning per liga? (jeśli Postgres w P5) | DataEng | — | P3.24 | Decision + implementacja w Alembic migration | — |
| P3.27 | Prefect flows — parametryzacja per liga (jedno flow, 10 instances) | DataEng | SWE | P3.13 | Flows deployable, scheduled na Prefect Cloud local | — |
| P3.28 | Dokumentacja — user guide "Adding a new league" | DataEng | MLEng | wszystko | `docs/tutorials/add_new_league.md` — step-by-step | — |
| P3.29 | Lead: customer discovery — pokazanie progressu 10 lig potencjalnym klientom | Lead | Designer | P3.15-19 | 5+ rozmów z feedbackiem, co ich interesuje | — |

## Równoległa praca w P3

- **DrMat**: advanced research (RB-10, RB-11, RB-12 z research backlog — weather, referee, manager)
- **SWE**: rozwój API prototype (P6 preview), CI dla nowych features
- **Designer**: landing page v1, dashboardy mockupy

## Kluczowe decyzje w P3

1. **Które 5 lig** — potwierdzenie lub zmiana propozycji po P3.0 audit
2. **Cross-league vs per-league models** — po P3.20
3. **Czy wszystkie 5 przechodzi do produkcji** — po P3.23 decision log (może 3-4 wystarczy)
4. **Partitioning DB** — czy już w P3 vs. czekać na Postgres w P5
5. **Jak dużo historical** — 3 sezony minimum, 5+ lepiej, 10+ ideal dla modeli cross-league

## DoD fazy P3

- [ ] Min. **4 z 5** nowych lig ma ROI > 5% w walk-forward (akceptujemy 1 porażkę)
- [ ] Total 9-10 lig w production DB
- [ ] Wszystkie ligi mają kompletny feature engineering (coverage > 80% per feature)
- [ ] Bukmacher odds coverage dla nowych lig > 70% meczów
- [ ] Cost per liga oszacowany
- [ ] Customer discovery potwierdził popyt na >1 z nowych lig

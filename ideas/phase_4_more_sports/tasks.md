# Phase 4 — Tasks

## Pod-fazy

- **P4.0** — Abstract framework (robione w pierwszych 2-3 tygodniach P4.1)
- **P4.1** — Tennis (6-10 tyg.)
- **P4.2** — Basketball (8-12 tyg., może być równoległe z końcówką P4.1)
- **P4.3** — Hockey (6-10 tyg., może być równoległe z P4.2)

## P4.0 — Abstract Framework

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P4.0.1 | Design: `SportAdapter` interface | MLEng | DrMat, DataEng | P3 done | Diagram + Python abstract classes w `sports/base.py` |
| P4.0.2 | Implementacja base extractors / transformers / loaders | DataEng | MLEng | P4.0.1 | `BaseExtractor`, `BaseFeatureBuilder`, `BaseModel` w produkcji |
| P4.0.3 | Sport-agnostic DB schema — rozszerzenie o `sport_id` | DataEng | — | P4.0.1 | Alembic migration, backward-compatible z football |
| P4.0.4 | Unified Match schema (Pydantic) — sport-agnostic + sport-specific fields | MLEng | SWE | P4.0.1 | `schemas.py::Match` z polymorfizmem |
| P4.0.5 | Contract tests — każdy SportAdapter musi przejść | MLEng | — | P4.0.2 | `tests/integration/test_sport_contract.py`, football adapter przechodzi |
| P4.0.6 | Refactor football → jako `FootballAdapter` (nic się nie łamie) | MLEng | DataEng | P4.0.5 | Football działa tak samo jak przed refaktorem, testy zielone |

## P4.1 — Tennis

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P4.1.1 | Download Jeff Sackmann ATP + WTA historical (2014-2025) | DataEng | — | P4.0 | Dane w `data/raw/tennis/`, >200k matches |
| P4.1.2 | Tennis DB schema — matches, players, tournaments, surfaces | DataEng | MLEng | P4.0.3 | Alembic migration, tennis tables stworzone |
| P4.1.3 | `TennisExtractor` — parse Sackmann CSVs + upload do DB | DataEng | — | P4.1.2 | Dane w tennis_matches tabeli |
| P4.1.4 | Live tennis data — Sofascore scraping (dzisiejsze mecze ATP/WTA) | DataEng | — | P4.1.3 | Current matches w DB, lineup dla upcoming |
| P4.1.5 | Tennis features — ELO per surface (4 surfaces × 2 tours) | DrMat | MLEng | P4.1.3 | `TennisEloFeature` klasa, ELO ratings updated rolling |
| P4.1.6 | Tennis features — serving stats (1st serve %, aces, BP saved, return points won) | MLEng | DrMat | P4.1.3 | Feature builder dla servisu + return |
| P4.1.7 | Tennis features — fatigue (days rest, sets played last 7d, travel) | MLEng | DrMat | P4.1.3 | Fatigue feature builder |
| P4.1.8 | Tennis features — H2H deep (total, surface-specific, recent) | MLEng | DrMat | P4.1.3 | H2H feature builder |
| P4.1.9 | Tennis model — LogReg baseline (ELO + H2H features) | DrMat | MLEng | P4.1.5-8 | Working model z LogLoss vs ELO baseline |
| P4.1.10 | Tennis model — LGB / CatBoost (richer features) | MLEng | DrMat | P4.1.9 | LGB model, porównanie z LogReg |
| P4.1.11 | Tennis model — calibration per surface + tour | MLEng | DrMat | P4.1.10 | ECE < 2% per (surface, tour) |
| P4.1.12 | Tennis — goals/games model (O/U games, set betting) | DrMat | MLEng | P4.1.10 | Dixon-Coles-like dla games, set distribution predictions |
| P4.1.13 | Tennis — backtest walk-forward 2020-2025 | MLEng | DrMat | P4.1.11 | Raport `docs/sports/tennis.md`, ROI > 5% na match winner |
| P4.1.14 | Tennis — odds integration (Pinnacle + Betfair Exchange) | DataEng | SWE | P4.1.3 | Odds w `tennis_odds` tabeli |
| P4.1.15 | Tennis — value betting backtest z portfolio Kelly | MLEng | DrMat | P4.1.13, P4.1.14 | Pozytywny ROI w walk-forward przy kosztach |
| P4.1.16 | Tennis — dokumentacja (how to add new tournament, how to scrape) | DataEng | MLEng | wszystko | `docs/sports/tennis/` kompletne |
| P4.1.17 | Tennis CLI — `sl tennis predict`, `sl tennis backtest` | MLEng | SWE | P4.1.15 | Commands działają, używają production code |

## P4.2 — Basketball (NBA + EuroLeague)

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P4.2.1 | NBA Stats API integration — rate limiting, caching, retry | DataEng | — | P4.0 | `NBAStatsExtractor` z pełnym respect rate limits |
| P4.2.2 | Basketball DB schema — matches, teams, players, box scores | DataEng | MLEng | P4.0.3 | Alembic migration, basketball tables stworzone |
| P4.2.3 | Historical NBA 2014-2025 — bulk download + load | DataEng | — | P4.2.1, P4.2.2 | >18k matches, box scores, play-by-play (optional) |
| P4.2.4 | EuroLeague scraping (Sofascore + official) | DataEng | — | P4.2.2 | EuroLeague matches 2018-2025 w DB |
| P4.2.5 | Basketball features — pace-adjusted OffRtg/DefRtg rolling | DrMat | MLEng | P4.2.3 | PaceAdjustedRatingFeature implementowany |
| P4.2.6 | Basketball features — rest days, back-to-back penalty, travel | MLEng | DrMat | P4.2.3 | RestFeature, TravelFeature |
| P4.2.7 | Basketball features — injury reports scraping (ESPN, Sofascore) | DataEng | MLEng | P4.2.3 | Injury data scraped + feature |
| P4.2.8 | Basketball features — key player availability impact | MLEng | DrMat | P4.2.7 | Feature: player_availability_score (weighted by usage) |
| P4.2.9 | Basketball features — H2H, home/away splits, SOS | DrMat | MLEng | P4.2.3 | H2H + SOS feature builders |
| P4.2.10 | Basketball model — LGB + CatBoost ensemble | MLEng | DrMat | P4.2.5-9 | Models with LogLoss vs ELO baseline improvement |
| P4.2.11 | Basketball — spread / handicap model (pace × point differential) | DrMat | MLEng | P4.2.10 | Spread prediction z CI intervals |
| P4.2.12 | Basketball — points total (O/U) model | DrMat | MLEng | P4.2.10 | Points O/U prediction |
| P4.2.13 | Basketball — calibration per liga (NBA vs EuroLeague) | MLEng | DrMat | P4.2.10 | ECE < 2% per liga |
| P4.2.14 | Basketball — backtest walk-forward 2020-2025 | MLEng | DrMat | P4.2.13 | Raport `docs/sports/basketball.md`, ROI > 5% |
| P4.2.15 | Basketball — odds integration (Pinnacle + DraftKings/FanDuel via sharp bookies) | DataEng | SWE | P4.2.3 | Odds w `basketball_odds` |
| P4.2.16 | Basketball — player props feasibility study (points, rebounds, assists) | DrMat | MLEng | P4.2.10 | Raport `docs/research/basketball_player_props.md` — go/no-go dla P5+ |
| P4.2.17 | Basketball CLI — `sl basketball predict`, `sl basketball backtest` | MLEng | SWE | P4.2.14 | Commands działają |

## P4.3 — Hockey (NHL + SHL)

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P4.3.1 | NHL API integration | DataEng | — | P4.0 | `NHLExtractor` z pełnym historical |
| P4.3.2 | Hockey DB schema — matches, teams, players, goalies, shots | DataEng | MLEng | P4.0.3 | Alembic migration |
| P4.3.3 | NHL historical 2014-2025 — bulk download | DataEng | — | P4.3.1, P4.3.2 | >12k NHL matches |
| P4.3.4 | Natural Stat Trick / Moneypuck scraping — advanced metrics (xG, Corsi, Fenwick) | DataEng | MLEng | P4.3.3 | Advanced metrics w `hockey_advanced` |
| P4.3.5 | SHL (Swedish) scraping — Sofascore + official | DataEng | — | P4.3.2 | SHL 2020-2025 w DB |
| P4.3.6 | Hockey features — goalie quality (save%, GAA rolling) | DrMat | MLEng | P4.3.3 | GoalieFeature builder |
| P4.3.7 | Hockey features — special teams (PP%, PK%) | DrMat | MLEng | P4.3.3 | SpecialTeamsFeature |
| P4.3.8 | Hockey features — pace (shots per 60, xG per 60) | MLEng | DrMat | P4.3.4 | PaceFeature |
| P4.3.9 | Hockey features — rest days, back-to-back, altitude (Colorado) | MLEng | DrMat | P4.3.3 | Rest + altitude features |
| P4.3.10 | Hockey model — regulation vs full-time (OT/SO) separate models | DrMat | MLEng | P4.3.6-9 | Two models, combined prediction |
| P4.3.11 | Hockey model — puckline (AH -1.5/+1.5) prediction | DrMat | MLEng | P4.3.10 | Puckline probabilities |
| P4.3.12 | Hockey model — O/U goals (Poisson-like dla hockey) | DrMat | MLEng | P4.3.10 | Goals total prediction |
| P4.3.13 | Hockey — calibration per liga (NHL vs SHL) | MLEng | DrMat | P4.3.10 | ECE < 2.5% per liga (hockey jest hałaśliwszy) |
| P4.3.14 | Hockey — backtest walk-forward 2020-2025 | MLEng | DrMat | P4.3.13 | Raport `docs/sports/hockey.md`, ROI > 5% |
| P4.3.15 | Hockey — odds integration | DataEng | SWE | P4.3.3 | Odds w `hockey_odds` |
| P4.3.16 | Hockey CLI — `sl hockey predict`, `sl hockey backtest` | MLEng | SWE | P4.3.14 | Commands działają |

## Wspólne

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P4.X.1 | Multi-sport integration tests — pipeline end-to-end na 4 sportach | MLEng | DataEng | wszystko | Wszystkie 4 sporty przechodzą contract tests |
| P4.X.2 | Multi-sport performance benchmark — pipeline czas, DB query speed | DataEng | MLEng | wszystko | Benchmarks w `benchmarks/multisport.md` |
| P4.X.3 | Multi-sport dokumentacja — how to add a new sport | MLEng | DataEng | wszystko | `docs/tutorials/add_new_sport.md` — step-by-step dla P4+ sportów |
| P4.X.4 | Lead: customer discovery dla multi-sport | Lead | Designer | po P4.1 | Rozmowy z tipsterami tennis/basketball/hockey, walidacja popytu |
| P4.X.5 | Designer: multi-sport dashboard mockups (P6 preview) | Designer | Lead | po P4.1 | Figma designs dla 4 sportów, unified look & feel |

## Kluczowe decyzje w P4

1. **Abstract framework scope** — czy wszystko musi być abstract, czy tylko najczęściej używane? **Rekomendacja: YAGNI, start minimal, grow w razie potrzeby.**
2. **Czy player props w P4 czy P5+** — player props (np. basketball points) to osobny big temat. **Rekomendacja: P4 tylko feasibility study, implementacja w P5+.**
3. **EuroLeague vs dodanie innej ligi koszykarskiej** — EuroLeague trudniejsza ale profesjonalna. Alternative: NBA G-League, Liga ACB (Hiszpania). **Rekomendacja: EuroLeague.**
4. **SHL vs KHL vs żadna druga liga hokejowa** — KHL (Rosja) ma sankcje i problemy reputacyjne. SHL jest bezpieczniejsza. **Rekomendacja: SHL.**
5. **Kiedy uruchomić P5 (automation)** — **rekomendacja: start P5 równolegle z P4.2** (gdy P4.1 działa, mamy pewność że framework OK, możemy automatyzować)

## DoD P4 (wszystkie 3 pod-fazy)

- [ ] Abstract framework działa i ma dokumentację
- [ ] Tennis w produkcji, ROI > 5% walk-forward 2020-2025
- [ ] Basketball (NBA) w produkcji, ROI > 5% walk-forward 2020-2025
- [ ] Hockey (NHL) w produkcji, ROI > 5% walk-forward 2020-2025
- [ ] Contract tests dla każdego sportu zielone
- [ ] Multi-sport dokumentacja kompletna
- [ ] Customer discovery potwierdził popyt na min. 1 z 3 nowych sportów
- [ ] Designer mockupy dla multi-sport dashboardów gotowe (dla P6)

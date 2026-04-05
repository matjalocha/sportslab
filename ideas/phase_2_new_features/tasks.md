# Phase 2 — Tasks

## Task table

| # | Task | Owner | Collab | Depends on | DoD | Gap |
|---|------|-------|--------|------------|-----|-----|
| P2.1 | Formalne spisanie IP — rozszerzenie `ideas/ip_moat.md` do whitepaper draft | DrMat | Lead, MLEng | P1.28 | `docs/whitepaper/hybrid_calibrated_portfolio_kelly_v1.md` — 10-15 stron, abstract + metodologia + eksperymenty | — |
| P2.2 | Implementacja Temperature Scaling dla TabPFN | MLEng | DrMat | P1 done | `src/ml_in_sports/models/calibration.py::TemperatureScaler` z testami, ECE TabPFN spada | — |
| P2.3 | Implementacja Platt scaling per liga per sezon | MLEng | DrMat | P2.2 | PlattScaler per (league, season), walk-forward test poprawy ECE | — |
| P2.4 | Implementacja Isotonic regression calibration | MLEng | DrMat | P2.2 | IsotonicScaler, porównanie z Platt na walk-forward | — |
| P2.5 | Implementacja Beta calibration per market | DrMat | MLEng | P2.2 | BetaCalibrator dla 1X2, O/U, BTTS — każdy rynek ma własny scaler | — |
| P2.6 | Calibration pipeline — orchestrator wyboru best scaler per (league, season, market) | MLEng | DrMat | P2.3, P2.4, P2.5 | `calibrate_model()` zwraca best scaler na bazie walk-forward ECE | — |
| P2.7 | ECE monitoring + reporting per liga per sezon per rynek | DrMat | MLEng | P2.6 | Dashboard/CSV z ECE trackingiem, alerty gdy ECE > 2% | — |
| P2.8 | Implementacja Dixon-Coles (non-Bayesian, baseline) | DrMat | MLEng | P1 done | `src/ml_in_sports/models/dixon_coles.py`, testy, backtest na 1X2 | — |
| P2.9 | Implementacja Bayesian Dixon-Coles z PyMC / Stan | DrMat | MLEng | P2.8 | Bayesian wariant + posterior samples, slower but better quantile estimates | — |
| P2.10 | Goals model — rozszerzenie Dixon-Coles dla AH, CS, O/U wszystkie linie, BTTS | DrMat | MLEng | P2.8 | Funkcje `predict_ah(line)`, `predict_cs(home, away)`, `predict_ou(line)`, `predict_btts()` | — |
| P2.11 | Portfolio Kelly — podstawowa implementacja z per-match, per-round, per-league limits | MLEng | DrMat | P1 done | `src/ml_in_sports/models/portfolio_kelly.py::PortfolioKelly` z unit tests | — |
| P2.12 | Shrinkage Kelly — dodanie shrinkage w kierunku rynku dla outlier'ów | DrMat | MLEng | P2.11 | Funkcja `shrink(p_model, p_market, volume, edge)` implementowana, dokumentowana w whitepaper | — |
| P2.13 | Portfolio Kelly — ograniczenia korelacji dla akumulatorów | MLEng | DrMat | P2.11 | Gdy team w 3+ bet'ach jednocześnie, exposure zmniejszany; max correlation między acca | — |
| P2.14 | Backtest Portfolio Kelly vs naive Kelly (NB26 baseline) na 4 sezonach | MLEng | DrMat | P2.13 | Raport w `docs/experiments/portfolio_kelly_vs_naive.md`, wygrana portfolio Kelly o mierzalną marżę | — |
| P2.15 | Pinnacle closing odds scraper — automatic daily pull | DataEng | MLEng | P1 done | `src/ml_in_sports/processing/extractors/pinnacle.py`, daily job zapisuje do `match_odds` | — |
| P2.16 | CLV tracking live — rolling 30/90/365d vs Pinnacle closing | MLEng | DrMat, DataEng | P2.15 | `sl clv --period 30d` pokazuje mean CLV, per bet distribution | — |
| P2.17 | CLV alerting — gdy 30d CLV spadnie poniżej 0, notyfikacja | MLEng | SWE | P2.16 | Telegram/Slack alert gdy CLV < 0 przez 7 dni | — |
| P2.18 | Drift detection: feature drift (PSI) rolling 30d per feature | MLEng | DataEng | P1 done | `sl drift features` raportuje top 10 drifting features, alerty gdy PSI > 0.25 | — |
| P2.19 | Drift detection: label drift (W/D/L distribution) | MLEng | DrMat | P2.18 | Rolling 30d label distribution per liga vs expected | — |
| P2.20 | Drift detection: odds drift (nasze implied vs rynek implied) | MLEng | DataEng | P2.18 | Alerty gdy mean divergence > 3σ | — |
| P2.21 | Auto-retraining trigger — gdy drift > próg, new model trained | MLEng | DataEng | P2.18, P2.19, P2.20 | Workflow Prefect (P5) lub cron w P2 retraining automatic | — |
| P2.22 | SHAP stability monitoring — rank correlation między retrainings | DrMat | MLEng | P2.21 | Rank corr < 0.6 → alert (feature importance się zmienia drastycznie) |  |
| P2.23 | Hybrid ensemble — zbudowanie architektury: LGB + XGB + TabPFN + Dixon-Coles + LogReg meta | MLEng | DrMat | P2.2, P2.8 | `src/ml_in_sports/models/ensemble.py::HybridEnsemble`, produkcja predictions | — |
| P2.24 | Backtest: Hybrid vs NB14 vs TabPFN vs LGB solo | MLEng | DrMat | P2.23 | Walk-forward na 4 sezonach, Hybrid wygrywa o ≥ 0.002 LogLoss | — |
| P2.25 | Live/in-play feasibility study (research only, nie implementacja) | DrMat | MLEng, DataEng | — | Raport w `docs/research/in_play_feasibility.md` — dostępność danych, edge'e, koszty, rekomendacja go/no-go | — |
| P2.26 | Backtest framework — nowy walk-forward module, wspiera Hybrid + Portfolio Kelly | MLEng | DrMat | P2.23, P2.14 | `src/ml_in_sports/backtesting/walk_forward.py` z testami, 2x szybszy niż obecny NB26 | — |
| P2.27 | Strategy evaluation metrics — rozszerzenie (sharpe, drawdown, max losing streak, ROI by market) | DrMat | MLEng | P2.26 | `backtesting/metrics.py` z pełnym zestawem | — |
| P2.28 | Value betting heuristics — research co działa: edge thresholds, P thresholds, odds ranges | DrMat | MLEng | P2.14, P2.24 | Raport w `docs/research/value_heuristics.md`, nowe domyślne thresholds | — |
| P2.29 | Autorska strategia "Hybrid Calibrated Portfolio Kelly" — jako CLI `sl strategy hcpk` | MLEng | DrMat | wszystko powyżej | `sl strategy hcpk --round 32` produkuje raport, używa production code | — |
| P2.30 | Whitepaper v1 — finalizacja, review przez zespół, publikacja na arXiv | DrMat | Lead, MLEng | P2.1 | PDF na arXiv z DOI, link w README | — |
| P2.31 | Dokumentacja użytkownika dla nowych features (jak używać CLV, drift, calibration) | MLEng | Lead | — | `docs/user_guide/calibration.md`, `docs/user_guide/portfolio_kelly.md`, `docs/user_guide/clv.md` | — |
| P2.32 | Designer: pierwsze wireframes dashboardu (dla P6 preview) | Designer | Lead | — | `research/design/p6_dashboard_wireframes_v1.fig` | — |
| P2.33 | Lead: customer discovery interviews (10 wywiadów) | Lead | Designer | — | 10 rozmów z potencjalnymi klientami B2B, notatki w Notion, walidacja value proposition | — |

## Zależności krytyczne

P2 ma gęste zależności między taskami. Sugerowana kolejność wykonywania:

```
Tydzień 1-2: P2.1, P2.2, P2.8, P2.11, P2.15, P2.18
Tydzień 3-4: P2.3, P2.4, P2.5, P2.9, P2.12, P2.16, P2.19, P2.20
Tydzień 5-6: P2.6, P2.7, P2.10, P2.13, P2.17, P2.21, P2.23
Tydzień 7-8: P2.14, P2.22, P2.24, P2.25, P2.26, P2.27
Tydzień 9-10: P2.28, P2.29, P2.30, P2.31, finalny gate review
```

## Równoległa praca

- **DataEng**: Pinnacle scraper (P2.15), pipeline hardening, preparation dla P3 (multi-league scraping)
- **SWE**: Pierwsze prototypy API shell (P6 preview), CI/CD enhancements
- **Designer**: Wireframes (P2.32)
- **Lead**: Customer discovery (P2.33)

## Kluczowe decyzje w P2

1. **PyMC vs Stan vs NumPyro** — dla Bayesian Dixon-Coles. **Rekomendacja: PyMC** (Python-native, community)
2. **Whitepaper na arXiv czy tylko internal** — **rekomendacja: arXiv** (credibility dla P6 sales)
3. **Live/in-play**: go czy no-go — decyzja po P2.25 research
4. **Auto-retraining cadence** — daily, weekly, po drift? **Rekomendacja: drift-triggered + weekly safety net**
5. **Calibration per liga czy globalnie** — **rekomendacja: per liga** (P2.7 confirmed lub debiuntuje)

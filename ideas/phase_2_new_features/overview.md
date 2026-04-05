# Phase 2 — New Functionality

**Widełki:** 6-10 tygodni
**Cel:** Dodać funkcjonalności modelowe i strategiczne, które dają **mierzalną przewagę nad rynkiem** oraz **autorskie IP**.
**Przejście do P3:** Patrz [phase_transitions.md](../phase_transitions.md#p2--p3--new-features--more-leagues)

## Kontekst wchodzenia w P2

Po P1 mamy:
- Czysty monorepo z CI, testami, mypy strict
- Obecne modele (NB14 ensemble, TabPFN) działające w CLI
- Obecny backtest (NB26) z yieldem 11-23%
- Pierwsza wersja IP whitepaper draft (rozpoczęta w P1)

Co jest **słabe** i wymaga P2:
- **TabPFN notorycznie overconfident** (widoczne w bets_r32_tabpfn_v4 — edge'e rzędu 83%)
- **Kelly per bet** bez portfolio ograniczeń — w jednej rundzie 27% budżetu na jeden team
- **Brak CLV tracking live** — nie wiemy czy bijemy Pinnacle closing
- **Brak goals/Poisson model** — nie robimy AH, Correct Score, O/U inne niż 2.5
- **Brak drift detection** — model może się psuć i nikt nie zauważy
- **IP udokumentowane tylko jako notatki** — do publikacji wymagany formal whitepaper

## Główne outputy

1. **Kalibrowana hybryda** — ensemble (LGB + XGB + TabPFN + Dixon-Coles) z temperature scaling, Platt/isotonic/beta per liga
2. **Portfolio Kelly z shrinkage'em** — ograniczenia per match/round/league, shrinkage w kierunku rynku dla outlier'ów
3. **Goals model (Dixon-Coles Bayesian)** — wspiera AH, Correct Score, O/U wszystkie linie, BTTS
4. **CLV tracking live** — codzienny pull Pinnacle closing odds, rolling 30/90/365d CLV
5. **Drift detection** — PSI na features, distribution shifts na labels, alerty
6. **Auto-retraining trigger** — gdy drift > próg, retraining uruchamiany automatycznie
7. **Whitepaper IP** — "Hybrid Calibrated Portfolio Kelly" v1 gotowy na arXiv
8. **Live/in-play feasibility study** — raport: czy warto, jakie koszty, jakie edge'e
9. **Beat NB14 baseline** — nowa architektura bije obecne ensemble o ≥ 0.002 LogLoss

## Zadania

Szczegóły → [tasks.md](tasks.md)

## Wspierające dokumenty

- [research_backlog.md](research_backlog.md) — hipotezy do sprawdzenia przez DrMat + MLEng (nie wszystkie będą w P2, niektóre w P3+)

## Ryzyka w P2

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|---|---|---|---|
| Portfolio Kelly gorszy niż naive Kelly na backteście | Średnie | Wysoki | Walk-forward na 4 sezonach, porównanie przeciwko NB26 baseline |
| Dixon-Coles Bayesian wolny (MCMC) | Wysokie | Średni | Variational inference (PyMC) zamiast NUTS, lub fallback na simple Dixon-Coles |
| Calibration nie poprawia CLV | Średnie | Wysoki | Plan B: per-market calibration, per-liga threshold, ensemble z wagami per liga |
| TabPFN nie daje się skalibrować (fundamentalne over-confidence) | Niskie | Wysoki | Temperature scaling + ensemble weighting + shrinkage |
| Whitepaper draft nie gotowy (DrMat za wolny) | Średnie | Średni | Lead + MLEng pomagają w strukturze, DrMat tylko matematyka |
| Live/in-play research otwiera puszkę Pandory | Wysokie | Niski | Scope feasibility study wąsko: tylko raport, nie implementacja |

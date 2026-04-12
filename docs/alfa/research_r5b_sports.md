# R5b More Sports — Deep Research Report

> Pełny raport w output agenta drmat (2026-04-12).
> Streszczenie poniżej.

## Ranking

1. **Tenis** (4.2/5) — 2-3 tyg. MVP, darmowe Pinnacle odds, 60% reuse infra
2. **Hokej** (3.3/5) — 3-5 tyg. MVP, NHL API + MoneyPuck xG, brak darmowych odds
3. **NBA** (3.2/5) — 3-4 tyg. MVP, nba_api nieoficjalne, brak darmowych odds

## Key data sources

| Sport | Features | Odds (Pinnacle) | xG equivalent |
|-------|----------|-----------------|---------------|
| Tenis | Jeff Sackmann (darmowy, 200k+ meczów) | tennis-data.co.uk (darmowy!) | N/A (serve stats) |
| Hokej | NHL API (oficjalne, darmowe) | The Odds API ($20-99/mies.) | MoneyPuck (darmowy) |
| NBA | nba_api (nieoficjalne) | The Odds API ($20-99/mies.) | N/A |

## Timeline: 12-18 tygodni (vs plan 6-10)

## Decyzja: framework po tenisie, nie przed (YAGNI)

Pełna treść w agent output — zawiera per-sport deep dive, feature lists, accuracy benchmarks,
market analysis, risk assessment, i concrete 3-week plan dla tenisa.

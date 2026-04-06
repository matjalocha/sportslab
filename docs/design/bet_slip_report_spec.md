# Specyfikacja projektowa: Raporty operacyjne R3

> **Autor:** Senior UI/UX Designer (SportsLab)
> **Data:** 2026-04-06
> **Status:** Draft — do review z Lead
> **Faza:** R3 — Proof of Edge

Pełna specyfikacja w output agenta designer. Kluczowe deliverables:

## 3 raporty

1. **Daily Bet Slip** — poranne "co stawiać dzisiaj?" (HTML + terminal + Telegram)
2. **Daily Results Tracker** — wieczorne "jak poszło?" (HTML + terminal + Telegram)
3. **Weekly Performance Report** — niedzielne "jak wygląda trend?" (HTML + terminal + Telegram)

## Design decisions (zatwierdzone)

- D1: Bet slip generowany o **07:00 fix** (cron)
- D2: CLV vs **Pinnacle** (standard, zgodny z backtest)
- D3: Język **EN** (B2B ready, PL configurable later)
- D4: Telegram **push + pull** (push o 07:00, /today on-demand)
- D5: Default **Quarter-Kelly** (bezpieczniejszy na start R3)

## Fazy wdrożenia

- Faza 1 (MVP): Bet Slip + Results (summary + tabela + terminal + Telegram)
- Faza 2: Weekly Report + filtry + sparklines
- Faza 3: Polish (charts, partial results, print CSS, i18n)

## Pełna specyfikacja

Szczegóły (wireframy, tokeny, Telegram format, empty states) w pełnym output agenta designer.
Reuse design system z `docs/design/backtest_report_spec.md`.

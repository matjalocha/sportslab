# Ideas — Plan Produktyzacji ML-in-Sports

**Status:** R1 — Clean Code (in progress)
**Ostatnia aktualizacja:** 2026-04-06
**Owner:** Mateusz Jałocha (solo founder) + Claude Code

Ten folder zawiera kompletny plan przekształcenia projektu `ml_in_sports` z lokalnego research repo w dochodowy biznes. Oryginalna struktura zaprojektowana dla 6-osobowego zespołu — **aktywna roadmapa** dostosowana do realiów solo founder.

---

## Nawigacja

### ⭐ Aktywna roadmapa
- **[solo_founder_roadmap.md](solo_founder_roadmap.md)** — Oficjalny plan pracy (R0–R6), timeline, priorytety, koszty. **Czytaj to najpierw.**

### Dokumenty strategiczne (reference)
- [prompts.md](prompts.md) — Historia promptów użytkownika (reprodukowalność)
- [vision.md](vision.md) — Misja, problem, propozycja wartości
- [team.md](team.md) — 6 profili (reference dla subagentów Claude Code)
- [ip_moat.md](ip_moat.md) — Autorskie podejście i przewaga konkurencyjna
- [tech_stack.md](tech_stack.md) — Stack technologiczny (przefiltrowany w solo_founder_roadmap.md)
- [phase_transitions.md](phase_transitions.md) — Kryteria przejścia (oryginalne, do adaptacji)

### Fazy rozwoju
- [phase_0_foundations/](phase_0_foundations/) — Zespół, narzędzia, konta bukmacherskie (2-4 tyg.)
- [phase_1_code_cleanup/](phase_1_code_cleanup/) — Refactor research → production grade (4-8 tyg.)
- [phase_2_new_features/](phase_2_new_features/) — Kalibracja, portfolio Kelly, goals model, IP (6-10 tyg.)
- [phase_3_more_leagues/](phase_3_more_leagues/) — Top-10 lig piłki nożnej (6-10 tyg.)
- [phase_4_more_sports/](phase_4_more_sports/) — Tenis + koszykówka + hokej (20-32 tyg. razem)
- [phase_5_automation/](phase_5_automation/) — Całodobowa maszynka, VPS, monitoring (6-10 tyg.)
- [phase_6_product_app/](phase_6_product_app/) — B2B API, platforma analityczna, dashboardy (16-24 tyg.)

### Infrastruktura i koordynacja
- [infrastructure/bookmaker_accounts.md](infrastructure/bookmaker_accounts.md) — LVBet, Superbet, Fortuna, Betclic, STS
- [infrastructure/data_strategy.md](infrastructure/data_strategy.md) — SQLite → Postgres → analytical store
- [infrastructure/secrets_and_compliance.md](infrastructure/secrets_and_compliance.md) — GDPR, KNF, hazard
- [infrastructure/cost_model.md](infrastructure/cost_model.md) — Miesięczne koszty per faza
- [coordination/linear_setup.md](coordination/linear_setup.md) — Workspace, cycles, templates
- [coordination/github_setup.md](coordination/github_setup.md) — Monorepo, CODEOWNERS, branch protection
- [coordination/weekly_rhythm.md](coordination/weekly_rhythm.md) — Standupy, retro, planning

---

## Jak czytać ten folder

1. **Zacznij od [vision.md](vision.md)** — zrozum cel
2. **Przeczytaj [team.md](team.md)** — poznaj zespół, który to wykonuje
3. **Przeczytaj [phase_transitions.md](phase_transitions.md)** — zobacz, jak fazy się łączą
4. **Przejdź do aktualnej fazy** — `phase_X_*/overview.md` + `tasks.md`

---

## Konwencja zadań

Każdy plik `tasks.md` zawiera tabelę:

| # | Task | Owner | Collab | Depends on | DoD | Brakujące kompetencje |

- **Owner** — osoba z zespołu odpowiedzialna (Lead, DrMat, MLEng, DataEng, SWE, Designer)
- **Collab** — osoby pomagające (min. 1 reviewer)
- **Depends on** — numery zadań z tej samej lub wcześniejszej fazy
- **DoD** — Definition of Done, mierzalne kryterium
- **Brakujące kompetencje** — czy trzeba dorekrutować/outsourcować

---

## Aktualny status fazy

| Faza | Status | Widełki | Rozpoczęcie | Zakończenie |
|------|--------|---------|-------------|-------------|
| R0 — Foundations | ✅ Done | 1 tyg. | 2026-04-05 | 2026-04-05 |
| R1 — Clean Code | 🔄 In Progress | 4-6 tyg. | 2026-04-05 | — |
| R2 — Better Models | ⏳ Pending | 6-8 tyg. | — | — |
| R3 — Proof of Edge | ⏳ Pending | 8-16 tyg. | — | — |
| R4 — Automation | ⏳ Pending | 2-3 tyg. | — | — |
| R5a — More Leagues | ⏳ Pending | 6-10 tyg. | — | — |
| R5b — More Sports | ⏳ Pending | 6-10 tyg. | — | — |
| R6 — Product | ⏳ Pending | 8-12 tyg. | — | — |

> Widełki są **orientacyjne**, nie deadline'y. Fazy kończą się gdy DoD spełnione. Niektóre fazy mogą iść równolegle (np. P3 i P4.1 po P2).

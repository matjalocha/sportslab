# SportsLab

Monorepo dla platformy ML-in-Sports — produktyzacja projektu analitycznego w biznes B2B.

**Obecna faza:** Planning (Phase 0 — Foundations)

## Nawigacja

- [ideas/](ideas/) — **kompletny plan produktyzacji** (7 faz, zespół, stack, infra, coordination)
- [ideas/README.md](ideas/README.md) — indeks nawigacyjny planu
- [ideas/tech_stack.md](ideas/tech_stack.md) — pełny stack technologiczny
- [ideas/phase_transitions.md](ideas/phase_transitions.md) — kryteria przejścia między fazami
- [.claude/CLAUDE.md](.claude/CLAUDE.md) — zasady pracy dla Claude Code (working rules)

## Struktura docelowa (po Phase 1)

Szczegóły w [ideas/phase_1_code_cleanup/target_repo_layout.md](ideas/phase_1_code_cleanup/target_repo_layout.md).

```
sportslab/
├── apps/
│   ├── api/                    # FastAPI backend
│   ├── web/                    # Next.js frontend
│   ├── landing/                # Marketing landing
│   └── scheduler/              # Prefect flows (orchestration)
├── packages/
│   ├── ml-in-sports/           # Core Python package
│   ├── shared-types/           # Pydantic → TS types
│   ├── ui/                     # Design system
│   └── config/                 # Shared tooling configs
├── research/                   # Notebooks (non-production)
├── infra/                      # Docker, Terraform, Prefect
├── docs/                       # Developer + user docs
└── ideas/                      # Planning artifacts (ten folder)
```

## Obecny stan

Obecny kod research (`ml_in_sports/`) zostanie przeniesiony do `packages/ml-in-sports/` w Phase 1.

Ten repo zaczyna od planu (`ideas/`). Kod zacznie pojawiać się w Phase 1 (Code Cleanup).

## Związany projekt

`c:/Users/Estera/Mateusz/ml_in_sports/` — obecny research codebase (zostanie zmigrowane w P1).

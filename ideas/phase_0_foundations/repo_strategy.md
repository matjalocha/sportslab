# Repo Strategy

**Decyzja:** **Monorepo** z workspaces (Python via uv, TypeScript via pnpm).

## Dlaczego monorepo

- **Jeden zespół** — nie chcemy synchronizować zmian między 5 repami
- **Wspólne typy/kontrakty** — Python Pydantic models mogą generować TypeScript types (via openapi-typescript-codegen lub podobne)
- **Łatwiejsze refaktory cross-cut** — jedna zmiana, jeden PR
- **Wspólne CI** — jedna konfiguracja GitHub Actions, path filtering dla relevant jobs
- **Code sharing** — wspólne utilities (date helpers, logging config, schemas)
- **Onboarding** — nowy dev klonuje jedno repo

## Dlaczego nie polyrepo

- Trudniejsza koordynacja zmian (client + server + ML zmiana naraz)
- Wersjonowanie pakietów między repo (kto publikuje, kto używa)
- Dodatkowy narzut developerski

## Struktura monorepo (docelowa, dojrzewa w P1-P5)

```
sportslab/
├── apps/                       # Deployable applications
│   ├── web/                    # Next.js frontend
│   ├── api/                    # FastAPI backend
│   └── scheduler/              # Prefect flows orchestrator
│
├── packages/
│   ├── ml-in-sports/           # Core Python package (= obecny src/)
│   │   ├── src/ml_in_sports/
│   │   │   ├── cli/            # CLI entry points (= obecny scripts/)
│   │   │   ├── features/
│   │   │   ├── models/
│   │   │   ├── processing/
│   │   │   ├── sports/         # Abstract sport framework (P4+)
│   │   │   ├── utils/
│   │   │   └── db/
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── shared-types/           # Pydantic models → OpenAPI → TS types
│   ├── ui/                     # Shared React components (design system)
│   └── config/                 # Shared configs (tsconfig, ruff, mypy, tailwind)
│
├── research/                   # Notebooks (non-production)
│   ├── 01_feature_eda.ipynb
│   ├── ...
│   └── README.md
│
├── infra/                      # Infrastructure as code
│   ├── docker/                 # Dockerfiles
│   ├── prefect/                # Prefect deployment specs
│   ├── nginx/                  # Reverse proxy config
│   └── grafana/                # Dashboards as JSON
│
├── docs/                       # Developer + user docs
│   ├── architecture/
│   ├── api/
│   ├── sports/                 # Per-sport documentation
│   └── leagues/                # Per-league documentation
│
├── ideas/                      # Ten folder — planning artifacts
├── .github/workflows/          # CI/CD
├── pnpm-workspace.yaml         # TS workspace config
├── pyproject.toml              # Root Python workspace (uv)
├── README.md
└── CONTRIBUTING.md
```

## Tooling

- **Python**: `uv` (szybszy od Poetry, lepszy workspace support)
- **TypeScript**: `pnpm` + workspaces
- **Orchestration scripts**: `Makefile` lub `just` (rekomendacja: `just`, cleaner syntax)
- **Git hooks**: `pre-commit` (ruff, mypy --strict, eslint, prettier)

## Migracja z obecnego layoutu (w P1)

| Obecna lokalizacja | Docelowa lokalizacja |
|---|---|
| `src/` | `packages/ml-in-sports/src/ml_in_sports/` |
| `scripts/*.py` | `packages/ml-in-sports/src/ml_in_sports/cli/*.py` (jako CLI entry points) |
| `scripts/_archive/` | usunięte, w gałęzi `archive/pre-cleanup` |
| `notebooks/` | `research/` |
| `tests/` | `packages/ml-in-sports/tests/` |
| `data/` | pozostaje w root (gitignored, duży) |
| `docs/` | pozostaje w root, rozszerzony |
| `config/` | `packages/ml-in-sports/config/` |
| `pyproject.toml` | `packages/ml-in-sports/pyproject.toml` + root workspace `pyproject.toml` |

## Branching strategy

- `main` — zawsze deployable
- `develop` — integration branch (opcjonalnie, jeśli potrzebne)
- `feature/<linear-id>-<slug>` — feature branches
- `fix/<linear-id>-<slug>` — bugfix branches
- `release/<version>` — release branches (gdy stabilizujemy wersję)

Conventional Commits:
```
feat(api): add value feed endpoint
fix(features): correct rolling window for away matches
chore(deps): bump lightgbm to 4.5
refactor(models): extract calibration layer
```

## Branch protection na main

- Required reviews: 1 (w P0-P2), 2 (od P3)
- Required status checks: lint, test, typecheck, build
- No force push
- No direct commits (tylko PR merges)
- Squash merge preferred (czyste historii)

## CODEOWNERS (przykład)

```
# Global
*                                    @lead

# Python ML
/packages/ml-in-sports/features/     @mleng @drmat
/packages/ml-in-sports/models/       @mleng @drmat
/packages/ml-in-sports/processing/   @dataeng
/packages/ml-in-sports/sports/       @mleng @drmat

# Backend + Infra
/apps/api/                           @swe
/apps/scheduler/                     @dataeng @swe
/infra/                              @swe @dataeng

# Frontend + Design
/apps/web/                           @swe @designer
/packages/ui/                        @designer @swe

# Docs + Planning
/ideas/                              @lead
/docs/                               @lead
```

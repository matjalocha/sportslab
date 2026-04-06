# Contributing to SportsLab

> **Status fazy:** Phase 0 (Foundations). Ten dokument opisuje docelowy workflow P1+. W P0 zawartość jest aspiracyjna — sam monorepo nie ma jeszcze kodu, tylko szkielet.

## Środowisko deweloperskie

### Wymagania

- **Python** 3.11+ (zarządzane przez [uv](https://docs.astral.sh/uv/))
- **Node.js** 20+ z **pnpm** 9+ (gdy dojdzie frontend w P6)
- **git** 2.40+
- **pre-commit** (instalowany automatycznie przez `uv sync`)
- System operacyjny: Linux / macOS / Windows (WSL2 rekomendowane na Windows dla skryptów bash)

### Pierwszy setup

```bash
git clone <repo-url>
cd sportslab
uv sync --all-extras --dev
uv run pre-commit install
# (opcjonalnie, gdy dojdzie frontend)
# pnpm install
```

Workspace members (np. `ml-in-sports`) są zadeklarowane jako root dependencies w `pyproject.toml` + `[tool.uv.sources]`, więc plain `uv sync --all-extras --dev` (bez `--all-packages`) instaluje wszystko — patrz [ADR-0001](docs/architecture/adr-0001-uv-workspace-install.md).

### Weryfikacja instalacji

```bash
uv run ruff check .
uv run mypy packages
uv run pytest
```

Wszystkie powinny zakończyć się sukcesem (w P0 tylko `packages/ml-in-sports` ma kod; reszta to szkielety).

## Struktura monorepo

Szczegóły: [ideas/phase_0_foundations/repo_strategy.md](ideas/phase_0_foundations/repo_strategy.md).

```
sportslab/
├── apps/              # Deployable: api, web, scheduler, landing
├── packages/          # Shared: ml-in-sports, shared-types, ui, config
├── research/          # Notebooks (non-production)
├── infra/             # Docker, Prefect, Nginx, Grafana
├── docs/              # Developer + user docs
└── ideas/             # Planning artifacts (P0 — Foundations)
```

## Branching

- `main` — zawsze deployable, chroniona branch protection
- `feature/<SPO-123>-<slug>` — nowe feature'y (SPO = Linear team key)
- `fix/<SPO-123>-<slug>` — bugfixy
- `refactor/<SPO-123>-<slug>` — refaktoryzacja
- `chore/<SPO-123>-<slug>` — infra, dependencies, CI

Każdy branch musi linkować do Linear issue przez numer w nazwie.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/) + Linear issue reference:

```
<type>(<scope>): <short description> SPO-123

[body]

[footer]
```

Typy: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`, `perf`.

Przykłady:
```
feat(features): add rolling xG differential for away matches SPO-42
fix(scrapers): handle Fotmob 403 with exponential backoff SPO-87
chore(deps): bump lightgbm to 4.5.0 SPO-12
```

Stare repo `ml_in_sports` używało prefixów `[Add]`, `[Fix]`, `[Update]` — nowe repo migruje na conventional commits w P1.

## Pull Requests

### Checklist przed PR

- [ ] `uv run ruff check .` przechodzi
- [ ] `uv run ruff format --check .` przechodzi
- [ ] `uv run mypy packages apps` przechodzi (P1+)
- [ ] `uv run pytest` przechodzi, coverage ≥ 80% (P1+)
- [ ] Branch linkowany do Linear issue
- [ ] PR description opisuje *why*, nie tylko *what*
- [ ] Breaking changes oznaczone (`BREAKING CHANGE:` w commit body)

### Review process

1. PR idzie do reviewera/ów wg CODEOWNERS
2. W P0-P2: wymagany **1 approval**; od P3: **2 approvals**
3. Wszystkie status checks muszą być zielone
4. Squash merge preferowany (czysta historia main)
5. Po merge: branch usunięty automatycznie

Szczegóły: [ideas/coordination/github_setup.md](ideas/coordination/github_setup.md).

## Coding conventions

### Python

- **Type hints**: wymagane dla wszystkich parametrów funkcji i wartości zwracanych
- **Docstrings**: Google style dla publicznych API
- **Line length**: 100 znaków (enforced by ruff)
- **Naming**: `PascalCase` dla klas, `snake_case` dla funkcji/zmiennych, `_leading_underscore` dla private
- **Imports**: kolejność: stdlib → third-party → local (enforced by ruff-isort)
- **Zero `print()`** w production code — używać `structlog`
- **Zero hardcoded paths** — `pathlib.Path` + `pydantic-settings`
- **Zero `Any` bez uzasadnienia** — wymaga zgody w PR review

### TypeScript (P6+)

Reguły spisywane w fazie wprowadzenia frontendu.

## Testowanie

- Framework: **pytest**
- Struktura: `packages/<pkg>/tests/`
- Fixtures: `conftest.py` per pakiet
- Naming: `test_<function>_<scenario>` (np. `test_extract_product_name_valid_page`)
- Coverage: minimum **80%** dla nowego kodu (P1+)

```bash
# Wszystkie testy
uv run pytest

# Konkretny pakiet
uv run pytest packages/ml-in-sports

# Z coverage HTML
uv run pytest --cov --cov-report=html
```

## Secrets i credentials

**Nigdy** nie commituj sekretów do repo. Zasady:

1. Wszystkie sekrety → password manager (1Password/Bitwarden, decyzja P0.15)
2. Env vars lokalne → `.env.local` (gitignored)
3. CI/CD → Doppler / 1Password Connect (decyzja P0.23)
4. Pliki config z potencjalnymi sekretami (`.mcp.json`, `.env*`) są w `.gitignore`
5. Jeśli przypadkiem wykomentowałeś sekret — natychmiast go zrotuj

## Zasoby

- **Plan projektu**: [ideas/README.md](ideas/README.md)
- **Working rules**: [.claude/CLAUDE.md](.claude/CLAUDE.md)
- **Phase transitions**: [ideas/phase_transitions.md](ideas/phase_transitions.md)
- **Linear workspace**: https://linear.app/sportslab (team: Sportslab, key: SPO)

## Pytania

W P0 (solo founder): pisz do Leada bezpośrednio.
W P1+: kanał `#engineering` w Slack + Linear issue dla dłuższych dyskusji.

# SportsLab — Working Rules for Claude Code

> **Scope:** This file is project-level guidance for Claude Code assisting on the SportsLab monorepo. It is loaded automatically at session start.
> **Last updated:** 2026-04-05
> **Current phase:** P0 — Foundations

## What is SportsLab

B2B productization of `ml_in_sports` research codebase into a sports analytics and value-betting platform. Seven phases (P0–P6), planned 6-person team, monorepo structure. Source of truth for the whole plan is [ideas/](../ideas/) — read `ideas/README.md` first when you need context.

The user is currently a **solo founder** — all six team roles (Lead, DrMat, MLEng, DataEng, SWE, Designer) exist only as planning artifacts and as subagent personas. Don't assume a team is available; plan around one person plus Claude Code.

## Core philosophy

- **Clean code first** — readability and maintainability over speed
- **Human in the loop** — all code changes reviewed, never merge blindly
- **Surgical changes** — only modify code directly related to the task; no drive-by refactors
- **Research is not production** — what's in `c:/Users/Estera/Mateusz/ml_in_sports/` is research-grade; what's in `packages/` is production-grade; don't mix standards

## Clean code rules

### Naming
- Avoid abbreviations (`data`, `info`, `manager`, `util`)
- Names must be pronounceable and searchable
- Descriptive, intent-revealing over short

### Functions and classes
- **Single responsibility**: one thing per function/class
- **Size**: functions < 20 lines, files < 300 lines (hard target from P1)
- **Arguments**: 0–2 ideal, max 3, no flag arguments
- **No hidden side effects**: if it mutates state, the name must say so

### Comments
- Code should be self-explanatory — if it needs a comment, refactor
- Allowed: docstrings on public APIs, legal headers, `TODO` with Linear issue reference
- **Forbidden**: commented-out code (use git history)

### Type safety
- **Type hints on everything**: parameters and return values, no exceptions
- **No `Any`** without explicit user approval in review
- mypy strict on `packages/` and `apps/` (enforced from P1)

### Forbidden patterns
- Premature optimization
- "Just in case" features (YAGNI)
- Duplicated code (DRY — extract after the third occurrence, not the second)
- `print()` in production code — use `structlog` / `logging`
- Hardcoded paths — use `pathlib.Path` + `pydantic-settings`
- `import *`
- Bare `except:` — catch specific exceptions
- Committing secrets, tokens, `.env*`, data files, model artifacts

## Project workflow

- **Plan first**: when the task is non-trivial, propose a plan before editing files
- **Test first**: write or update tests before implementation
- **Verify**: run tests after changes
- **Ask on ambiguity**: never invent business rules — ask the user
- **Incremental commits**: small, focused, reversible

## Monorepo structure

Target layout (populated over P1–P6, currently mostly placeholders):

```
sportslab/
├── apps/                       # Deployable applications
│   ├── api/                    # FastAPI backend (P6)
│   ├── web/                    # Next.js frontend (P6)
│   ├── landing/                # Marketing landing (P6)
│   └── scheduler/              # Prefect flows (P5)
├── packages/
│   ├── ml-in-sports/           # Core Python package (migrated from ml_in_sports/ in P1)
│   │   └── src/ml_in_sports/
│   │       ├── cli/            # CLI entry points (replaces current scripts/)
│   │       ├── features/
│   │       ├── models/
│   │       ├── processing/
│   │       ├── sports/         # Abstract sport framework (P4+)
│   │       ├── utils/
│   │       └── db/
│   ├── shared-types/           # Pydantic → OpenAPI → TypeScript types
│   ├── ui/                     # Design system (P6)
│   └── config/                 # Shared tooling configs
├── research/                   # Notebooks (non-production, P1+)
├── infra/                      # Docker, Prefect, Nginx, Grafana (P5)
├── docs/                       # Architecture ADRs, audits, developer docs
└── ideas/                      # Planning artifacts (this is where P0 lives)
```

Reference: [ideas/phase_0_foundations/repo_strategy.md](../ideas/phase_0_foundations/repo_strategy.md)

## Coding conventions — Python

- **Python version**: 3.11+ (managed by `uv`)
- **Type hints**: mandatory, everywhere
- **Docstrings**: Google style for public functions/classes
- **Line length**: 100 (enforced by ruff)
- **Import order**: stdlib → third-party → local (enforced by ruff-isort)
- **Naming**:
  - Classes: `PascalCase`
  - Functions, variables: `snake_case`
  - Private: `_leading_underscore`
  - Constants: `UPPER_SNAKE_CASE`
- **Structured logging**: `structlog` or `logging.getLogger(__name__)` with key-value context
- **Config via `pydantic-settings`**: no hardcoded paths, thresholds, credentials

## Coding conventions — TypeScript (P6+)

Spelled out when frontend work begins. In short: Next.js App Router, TanStack Query, shadcn/ui, Tailwind, Biome or ESLint+Prettier, TypeScript strict.

## Error handling

```python
# ✅ Graceful degradation — expected, domain-specific exception
try:
    odds = fetch_closing_line(match_id)
except ClosingLineUnavailable as error:
    logger.warning("closing_line_missing", match_id=match_id, reason=str(error))
    odds = None

# ❌ Swallows everything, hides bugs
try:
    odds = fetch_closing_line(match_id)
except Exception:
    odds = None
```

- Validate data at system boundaries (scrapers, user input, external APIs)
- Return `Optional[T]` / `T | None` when data might be absent
- Log warnings for recoverable problems, errors for failures, never crash silently

## Testing

- **Framework**: pytest
- **Coverage**: ≥ 80% on new code (P1+), enforced by CI
- **Fixtures**: reusable fixtures in `conftest.py` per package
- **Naming**: `test_<function>_<scenario>` (e.g. `test_compute_kelly_stake_negative_edge_returns_zero`)
- **Arrange / Act / Assert** structure

```python
def test_compute_kelly_stake_zero_edge_returns_zero() -> None:
    """Kelly stake is zero when model probability equals bookmaker implied."""
    # Arrange
    p_model, odds, ece, bankroll = 0.5, 2.0, 0.01, 1000.0

    # Act
    stake, fraction, edge = compute_kelly_stake(p_model, odds, ece, bankroll)

    # Assert
    assert stake == 0.0
    assert edge == 0.0
```

### Running tests

```bash
# Install workspace (workspace members are root deps — see docs/architecture/adr-0001-uv-workspace-install.md)
uv sync --all-extras --dev

# Run all tests
uv run pytest

# Coverage report
uv run pytest --cov --cov-report=html

# Specific package
uv run pytest packages/ml-in-sports

# Specific test
uv run pytest packages/ml-in-sports/tests/test_features.py::test_rolling_xg_no_leakage
```

## Linting and formatting

```bash
uv run ruff check .             # lint
uv run ruff format .            # auto-format
uv run ruff check . --fix       # lint + autofix
uv run mypy packages apps       # strict type check (P1+)
```

ruff is strict: E, W, F, I, B, C4, UP, N, SIM, TID, RUF rules enabled. mypy is strict on production code, lenient on tests.

## Git workflow

### Commit format

Conventional Commits + Linear issue reference (team key `SPO`):

```
<type>(<scope>): <short description> SPO-<NNN>

[optional body]

[optional footer, e.g. BREAKING CHANGE: ...]
```

Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`, `perf`.

Examples:
```
feat(features): add rolling xG differential for away matches SPO-42
fix(scrapers): handle Fotmob 403 with exponential backoff SPO-87
refactor(database): split FootballDatabase into schema + CRUD classes SPO-19
chore(deps): bump lightgbm to 4.5.0 SPO-12
```

The old `ml_in_sports` repo used `[Type]` prefix format — not used in SportsLab.

### Branching

- `main` — always deployable, branch protection enforced
- `feature/SPO-<NNN>-<slug>` — new features
- `fix/SPO-<NNN>-<slug>` — bug fixes
- `refactor/SPO-<NNN>-<slug>` — refactoring
- `chore/SPO-<NNN>-<slug>` — infra, dependencies, CI

### Git safety

- Never force-push to `main`
- Never run `git reset --hard`, `rm -rf`, `git clean -f` without explicit user instruction
- Never skip hooks (`--no-verify`) unless the user explicitly asks
- Confirm before any destructive operation that touches shared state
- **All SportsLab repos MUST be private** — never create a public repo without explicit user approval (see `memory/feedback_repo_visibility.md`)

## Secrets and credentials

- **Never** commit secrets, tokens, passwords, API keys, `.env*` files
- Store in a password manager (choice pending in [SPO-9 / P0.15](../ideas/phase_0_foundations/tasks.md): 1Password vs Bitwarden)
- CI/CD secrets via Doppler or 1Password Connect (decision in SPO-27 / P0.23)
- `.mcp.json`, `.env*`, `secrets.json` are in `.gitignore`
- **If a secret appears in chat**: treat it as leaked, advise rotation, push for password manager (see `memory/feedback_secrets_in_chat.md`)

## Subagent team

10 specialized agents in [.claude/agents/](agents/). Delegate work to them via the `Agent` tool with `subagent_type` matching the `name` field.

### Role agents — matching [ideas/team.md](../ideas/team.md)

| Name | Role | When to delegate |
|---|---|---|
| `lead` | Founder-Engineer | Product decisions, prioritization, sales, budget, roadmap trade-offs |
| `drmat` | Doctor of sports mathematics | Calibration theory, Kelly portfolio, Bayesian, Dixon-Coles, Bradley-Terry, IP design, whitepapers |
| `mleng` | Senior ML Engineer | Model implementation, feature pipelines, MLflow, drift monitoring, SHAP, training loops |
| `dataeng` | Senior Data Engineer | Scrapers, Postgres/Timescale, Alembic, Prefect, bookmaker APIs, backup/DR |
| `swe` | Senior Software Engineer | FastAPI, Next.js, Stripe billing, Docker, Hetzner, observability |
| `designer` | Senior UI/UX Designer | Design system, dashboards, data viz, brand, moodboards, Figma handoff |

### Process agents

| Name | Role | When to delegate |
|---|---|---|
| `architect` | System architect | Cross-cutting design, ADRs in `docs/architecture/`, task breakdown across roles |
| `code-reviewer` | Harsh-phase reviewer | After code is written, "find every problem", 3 iterations, MUST/SHOULD/NICE classification |
| `acceptance-reviewer` | Acceptance reviewer | Final gate before merge, 2 iterations, blocks only on MUST-FIX |
| `reporter` | Markdown report author | Weekly reports, audits, retrospectives, betting slips, stakeholder updates |

## Review Process

**Team:** `architect`, `code-reviewer`, `mleng` (or relevant role agent: `drmat`/`dataeng`/`swe`/`designer`), `acceptance-reviewer` — see `.claude/agents/`

**Phase 1 — Harsh (3 iter):** "Find every problem." Classify: MUST-FIX (bugs/crashes) / SHOULD-FIX (naming/edge-cases) / NICE-TO-HAVE (style).
**Phase 2 — Acceptance (2 iter):** Only block on MUST-FIX. Zero MUST-FIX + tests pass + ruff clean → approved.

## Linear workspace

- Workspace: `https://linear.app/sportslab`, team key `SPO`
- Access via MCP `linear-sportslab` (configured in `~/.claude.json`)
- 7 projects (P0–P6), 25 issues in P0 (SPO-5 to SPO-29), 4 milestones in P0
- Labels: `type:*`, `persona:*`, `area:*` (21 total)
- Details: `memory/reference_linear_sportslab.md`
- **Critical**: there is a second Linear workspace `aiam.care` under the same email — **never** touch it from a SportsLab context

### Linear update rhythm (mandatory, not optional)

Every Linear issue that SportsLab works on must reflect reality in real time. The rhythm:

1. **When you start working on an issue** → move it to `In Progress` immediately, add a short comment "Starting work on X" if the work will take more than a single exchange
2. **When the DoD is met** → move it to `Done` in the **same turn** you produced the deliverable, never later. Add a Done comment with:
   - Checklist of DoD items, each marked ✅ or explaining why it's conditionally deferred
   - Link to the produced artifact (file path, URL)
   - Any scope limitations or caveats
3. **When blocked** → stay in `In Progress`, add a comment explaining the blocker and who/what is needed to unblock
4. **When the issue is partially complete** → either close as `Done (partial scope)` with a clear caveat, or stay `In Progress` with progress comment — never leave stale in `Backlog` after meaningful work
5. **When delegating to a subagent** → move to `In Progress` before spawning the agent, add comment naming the agent and ETA
6. **When a subagent returns** → update status and comment in the **same turn** as processing the output

**Anti-pattern**: producing a deliverable, commenting on the issue, but leaving status as `Backlog`. This happened on 2026-04-05 with SPO-19 (tech-debt audit) — fixed retroactively, must not repeat.

**Rule of thumb**: if the user ever asks "why is nothing marked Done in Linear", you've already failed. The rhythm exists so the user can see progress at a glance without asking.

### Subagents own their Linear updates too

Every subagent in `.claude/agents/` has Linear MCP tools in its `tools:` frontmatter (`save_issue`, `save_comment`, `list_issues`, etc.). When you delegate a Linear-tracked task to a subagent:

1. **Tell the subagent the issue ID** in the delegation prompt (e.g. "work on SPO-30, the full DoD is in the issue description")
2. **The subagent is responsible** for moving the issue to `In Progress` at start, `Done` at end, and posting the Done comment — **not** the main agent
3. **Main agent verifies** after the subagent returns: check that status is correct, artifact is on disk, and Done comment has the required checklist

If a subagent returns a deliverable but left the Linear issue in Backlog, the main agent must (a) fix the status itself, and (b) note the process gap so the subagent's persona definition can be tightened. Each agent's `Linear status rhythm` section in its `.md` file documents this contract.

## Memory

Persistent memory for this project lives in `~/.claude/projects/c--Users-Estera-Mateusz-sportslab/memory/`:

- `user_role.md` — user profile and preferences
- `project_sportslab_context.md` — project context
- `feedback_repo_visibility.md` — rule: all repos private
- `feedback_secrets_in_chat.md` — procedure for leaked secrets
- `reference_linear_sportslab.md` — Linear workspace reference
- `MEMORY.md` — index of all memory files

Load MEMORY.md when context calls for it; update rules as they emerge.

## Phase transitions

Phases don't end on a calendar — they end when their Definition of Done is met. See [ideas/phase_transitions.md](../ideas/phase_transitions.md) for exit criteria.

Current phase: **P0 Foundations**. Exit criteria include team contracts, legal setup, bookmaker accounts, Linear workspace, monorepo initialized, audit reports. Progress tracked in Linear (SPO-5 to SPO-29).

## Priorities (P0 specific)

When in doubt about what to do next in P0, prioritize in this order:

1. **User-blocking decisions** — help the user decide faster (legal form, company registration, budget, tool choices)
2. **Long lead-time critical path** — bookmaker KYC (2+ weeks, must start early)
3. **Audits and documentation** — things Claude Code can do without the user (tech-debt audit ✅, math audit, pricing research)
4. **Infrastructure scaffolding** — monorepo skeleton ✅, CI/CD templates, pre-commit hooks
5. **Team-ready artifacts** — contract templates, Figma moodboards, ADRs

Priorities for later phases live in their respective `ideas/phase_X_*/tasks.md` files.

## When unsure

1. Check this file
2. Check [ideas/](../ideas/) — specifically `ideas/phase_<current>_*/` for active phase details
3. Check `memory/` for prior rules and decisions
4. Check relevant subagent's persona for domain-specific conventions
5. **Ask the user before implementing** — don't guess on business rules or product decisions

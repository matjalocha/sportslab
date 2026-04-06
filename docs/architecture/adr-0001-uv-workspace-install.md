# ADR-0001: uv workspace install strategy — declare members as root dependencies

- **Status**: Accepted
- **Date**: 2026-04-05
- **Deciders**: `architect` (decision), `swe` (implementation), `mleng` (raised the issue in SPO-30)
- **Linear**: [SPO-31](https://linear.app/sportslab/issue/SPO-31)

## Context

During the SPO-30 pilot migration of `value_betting` into `packages/ml-in-sports/`, we discovered
that `uv sync --all-extras --dev` does **not** install workspace members into the root `.venv`.
The root `sportslab` package declares `dependencies = []`, so uv has no reason to pull
`ml-in-sports` in, and `from ml_in_sports...` fails with `ModuleNotFoundError` after a fresh
clone. We need one convention that will govern how ~20 workspace members (packages + apps) get
installed across P1–P6, how CI configures its venv, and how new contributors onboard.
**[PEWNE]** this is a one-time decision that affects every future migration issue.

## Options considered

1. **Option A — Declare each workspace member as a root dependency via `[tool.uv.sources]`.**
   Root `pyproject.toml` lists `dependencies = ["ml-in-sports", "shared-types", ...]` with
   `[tool.uv.sources] ml-in-sports = { workspace = true }`. This is uv's documented idiomatic
   pattern; workspace-sourced deps are installed **editable** by default.
   - Pros: default `uv sync` "just works"; identical command in docs, CI, onboarding, and
     every P1 task template; editable installs preserved; no special flag to remember.
   - Cons: one-line edit to root `pyproject.toml` each time a new workspace member lands
     (~20 times over P1–P6).

2. **Option B — Always use `uv sync --all-extras --dev --all-packages`.**
   Root keeps `dependencies = []`; every developer, CI job, task template, and doc uses the
   `--all-packages` flag. `mleng` recommended this in SPO-30 for scalability.
   - Pros: no root edits when adding workspace members.
   - Cons: the flag must live in everyone's muscle memory, CI config, CONTRIBUTING.md,
     CLAUDE.md, and every task template; divergence risk high; a new contributor running
     plain `uv sync` gets a broken venv with a confusing error.

3. **Option C — Path dependencies (`{ path = "packages/ml-in-sports" }`).**
   Rejected upfront: uv docs explicitly position path deps for "members with conflicting
   requirements or separate venvs" — neither applies here. We want one lockfile and one venv.

## Decision

We choose **Option A**. Root `pyproject.toml` will list every workspace member in
`[project].dependencies` and resolve them via `[tool.uv.sources] <name> = { workspace = true }`.
The canonical install command stays `uv sync --all-extras --dev` — the same string in
CONTRIBUTING, CLAUDE.md, CI, and task templates. The one-line edit per new workspace member is
cheap and amortized; forcing every developer and every CI job to remember `--all-packages`
forever is not. **[PEWNE]** this matches uv's documented idiomatic pattern and preserves
editable installs between members.

## Consequences

- **Positive**: `git clone && uv sync --all-extras --dev` produces a working venv on the first
  try for any contributor, any Claude Code session, and any CI runner — no flag drift, no
  onboarding footnote.
- **Negative**: adding a workspace member is now a two-file edit (new package's `pyproject.toml`
  **and** one line in root `pyproject.toml` + `[tool.uv.sources]`). **[RYZYKO]** low — will be
  baked into the P1 migration task template so it's a checklist item, not tribal knowledge.
- **Neutral**: `uv.lock` is regenerated on every workspace member addition regardless of which
  option we pick, so lockfile churn is unchanged. **[HIPOTEZA]** if we ever hit a case where one
  workspace member must be excluded from the default install (e.g. GPU-only training package
  that shouldn't land in the API venv), we revisit — at that point path deps or
  [dependency-groups](https://peps.python.org/pep-0735/) become relevant. **[DO SPRAWDZENIA]**
  in P5 when `apps/scheduler` + heavy ML deps land.

## References

- [SPO-30](https://linear.app/sportslab/issue/SPO-30) — pilot migration that surfaced the issue
- [SPO-31](https://linear.app/sportslab/issue/SPO-31) — this decision
- [uv workspaces docs](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- `ideas/phase_0_foundations/repo_strategy.md` — monorepo boundaries
- Implementation follow-up: **SPO-32** (root `pyproject.toml` edit + CONTRIBUTING.md,
  `.claude/CLAUDE.md`, `.github/workflows/ci.yml`, and P1 task template updates) — owned by
  `swe`

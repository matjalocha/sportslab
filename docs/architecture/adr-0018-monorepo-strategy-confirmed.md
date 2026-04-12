# ADR-0018: Monorepo strategy confirmed -- no split

- **Status**: Accepted
- **Date**: 2026-04-12
- **Deciders**: Architect, Lead, SWE, MLEng

## Context

After 6 days of active development, the monorepo at `sportslab/` has grown to ~95 source
files, ~75 test files, 1349 tests, 17 ADRs, 6 experiment configs, and substantial
documentation. The question arose whether the repository should be split into multiple repos
(e.g., `sportslab-ml`, `sportslab-web`, `sportslab-infra`) before it grows further.

This ADR re-evaluates the original monorepo decision from `ideas/phase_0_foundations/repo_strategy.md`
with concrete data from the current codebase.

### Triggers for this review

1. The repo now contains ML code, infrastructure scripts, documentation, experiment configs,
   and Claude Code agent definitions. Some of these have different deployment targets (Pi vs
   Dev PC vs VM).
2. A fourth machine (free VM) and fifth web property (potential user panel) are being
   considered, which could add deployment targets.
3. The alpha launch plan (4 weeks) creates time pressure -- if we are going to split, it is
   cheaper to do it before alpha than after.

## Options considered

1. **Keep monorepo (status quo)**
   - Pros: zero overhead, one `git clone`, one CI config, cross-cutting changes in one PR,
     Claude Code subagents work in one repo, solo founder has no coordination burden.
   - Cons: all code in one repo (conceptual clutter), docs changes trigger Python CI (unless
     path filtering), future TypeScript code would share repo with Python.

2. **Split into 2 repos: `sportslab` (ML+infra) + `sportslab-web` (panel/dashboard)**
   - Pros: clean separation between Python (ML engine) and TypeScript (web panel). Different
     CI pipelines. Different deployment targets.
   - Cons: cross-repo dependency management (API contract between ML and web), two places to
     update for schema changes, coordination overhead for one person.

3. **Split into 3 repos: `sportslab-ml` + `sportslab-web` + `sportslab-infra`**
   - Pros: maximum isolation. Each repo has one purpose.
   - Cons: maximum coordination overhead. Three repos for one person is pure overhead.
     Infrastructure changes often accompany ML changes (Dockerfile, docker-compose).

4. **Monorepo with strict path filtering in CI**
   - Pros: keeps single repo benefits but avoids unnecessary CI runs. Changes to `docs/`
     do not trigger `pytest`. Changes to `infra/` only trigger Docker build.
   - Cons: path filter config maintenance. But: this is 10 lines of YAML.

## Decision

We choose **Option 4: Monorepo with strict path filtering in CI** because:

1. **The repo is small.** ~300 tracked files is trivial. Git performs well up to tens of
   thousands of files. We are nowhere near that threshold.

2. **One contributor.** Split repos create coordination overhead with zero benefit for a
   solo founder. There is no team isolation to achieve because there are no teams.

3. **One runtime.** All production code is Python. The only non-Python code is Markdown
   documentation, YAML configs, and shell scripts. No TypeScript in the repo yet (landing
   page is Lovable/Framer, hosted externally).

4. **Low reversal cost.** If in R6 the repo needs splitting (e.g., large Next.js dashboard
   is added, team grows to 3+ people), `git subtree split` or `git filter-repo` extracts
   any subdirectory into its own repo in under an hour. The monorepo decision is reversible.

5. **Claude Code works better with one repo.** Subagents read the full context from one
   working directory. Polyrepo would require explicit context switching between repos.

### Path filtering (to be implemented in P1.8 GitHub Actions CI)

```yaml
on:
  push:
    paths:
      - 'packages/ml-in-sports/**'
      - 'pyproject.toml'
      - 'uv.lock'
jobs:
  test:
    # only runs when Python code changes
```

Separate workflows for `docs/` (markdown lint), `infra/` (Docker build), etc.

### When to re-evaluate

Re-evaluate this decision if ANY of the following become true:

- [ ] Team grows to 3+ developers working on different parts of the codebase
- [ ] CI time exceeds 15 minutes on full runs
- [ ] A TypeScript frontend (Next.js dashboard) is added to the repo with its own CI
- [ ] Independent release cycles are needed (ML package versioned separately from API)

None of these are expected before R5 (6-12 months from now).

## Consequences

- **Positive**: zero coordination overhead, one place for all code, one CI config with path
  filtering, subagents work seamlessly.
- **Positive**: alpha launch timeline unaffected (no migration work needed).
- **Negative**: docs changes and infra changes share the same repo. Mitigated by path filtering
  in CI and clear directory boundaries.
- **Neutral**: this decision does NOT prevent creating external repos for non-core purposes
  (e.g., a Lovable project for the landing page lives in its own Lovable-hosted repo). The
  monorepo decision applies only to the core SportsLab codebase.

## References

- `ideas/phase_0_foundations/repo_strategy.md` -- original monorepo decision
- `docs/team_discussion_infra_2026-04-12.md` -- full analysis with numbers
- ADR-0010: Solo founder roadmap (establishes constraints)
- ADR-0017: Dual-machine architecture (Pi + Dev PC)

# GitHub Setup

**Owner:** SWE (primary), Lead (governance)
**Status:** P0.13-P0.14 tasks
**Cel:** Skonfigurowanie GitHub organization + monorepo tak żeby 6-osobowy zespół mógł współpracować bezpiecznie i efektywnie.

## Organization

**Nazwa:** `sportslab-io` (lub dopasowana do wybranego brandu w P0)

**URL:** `github.com/sportslab-io`

**Plan:** GitHub Team ($4/user/m-c)

## Repositories

### Primary: `sportslab` (monorepo)

Struktura opisana w [phase_0_foundations/repo_strategy.md](../phase_0_foundations/repo_strategy.md).

### Dodatkowe (możliwe w przyszłości)

- `sportslab-docs` — osobny repo dla publicznej dokumentacji (jeśli używamy custom static site generator)
- `sportslab-examples` — publiczne przykłady API usage (dla marketingu)
- `sportslab-landing` — jeśli decydujemy wydzielić landing z monorepo

**P6 decyzja:** Landing + docs mogą być w monorepo pod `apps/landing/` i `apps/docs/` (rekomendacja) lub osobno (szybciej iterować, ale więcej CI/CD).

## Teams (GitHub Teams)

### 1. `@sportslab-io/admins`
- **Members:** Lead, SWE (backup)
- **Permissions:** Admin na wszystkie repos
- **Responsibilities:** Org settings, billing, security, secrets

### 2. `@sportslab-io/engineering`
- **Members:** MLEng, DataEng, SWE
- **Permissions:** Maintain na monorepo (can merge, cannot force-push to main)
- **Responsibilities:** Code review, merging, releases

### 3. `@sportslab-io/research`
- **Members:** DrMat, MLEng
- **Permissions:** Write na monorepo
- **Responsibilities:** `research/`, `docs/whitepaper/`, `docs/research/`

### 4. `@sportslab-io/design`
- **Members:** Designer, SWE (collaborator)
- **Permissions:** Write na monorepo
- **Responsibilities:** `packages/ui/`, `apps/web/`, `apps/landing/`

### 5. `@sportslab-io/leadership`
- **Members:** Lead
- **Permissions:** Admin
- **Responsibilities:** Strategic decisions, compliance oversight

## CODEOWNERS

Plik `.github/CODEOWNERS` w root monorepo:

```
# Global fallback
* @sportslab-io/engineering

# Root
/README.md @sportslab-io/leadership
/CONTRIBUTING.md @sportslab-io/engineering
/LICENSE @sportslab-io/leadership
/SECURITY.md @sportslab-io/leadership

# Ideas & planning (all must review)
/ideas/ @sportslab-io/leadership

# Python ML core
/packages/ml-in-sports/src/ml_in_sports/features/ @sportslab-io/engineering @sportslab-io/research
/packages/ml-in-sports/src/ml_in_sports/models/ @sportslab-io/engineering @sportslab-io/research
/packages/ml-in-sports/src/ml_in_sports/processing/ @sportslab-io/engineering
/packages/ml-in-sports/src/ml_in_sports/sports/ @sportslab-io/engineering @sportslab-io/research
/packages/ml-in-sports/src/ml_in_sports/db/ @sportslab-io/engineering
/packages/ml-in-sports/tests/ @sportslab-io/engineering

# Research notebooks
/research/ @sportslab-io/research

# Whitepaper + math docs
/docs/whitepaper/ @sportslab-io/research
/docs/research/ @sportslab-io/research

# Backend & Infra
/apps/api/ @sportslab-io/engineering
/apps/scheduler/ @sportslab-io/engineering
/infra/ @sportslab-io/engineering
/.github/workflows/ @sportslab-io/engineering @sportslab-io/admins

# Frontend & Design
/apps/web/ @sportslab-io/design @sportslab-io/engineering
/apps/landing/ @sportslab-io/design
/packages/ui/ @sportslab-io/design

# Docs
/docs/api/ @sportslab-io/engineering
/docs/tutorials/ @sportslab-io/engineering @sportslab-io/design

# Security
/.github/dependabot.yml @sportslab-io/admins
```

## Branch protection (na `main`)

### Settings

- **Require pull request before merging:** ✅
  - Required approvals: **1** (P0-P2), **2** (P3+)
  - Dismiss stale approvals when new commits pushed: ✅
  - Require review from CODEOWNERS: ✅
  - Require approval of most recent reviewable push: ✅

- **Require status checks to pass:** ✅
  - Required checks:
    - `lint` (ruff)
    - `typecheck` (mypy strict)
    - `test` (pytest)
    - `build` (monorepo build)
    - `security` (dependabot alerts)
  - Require branches to be up to date: ✅

- **Require conversation resolution:** ✅

- **Require signed commits:** ⚠️ (opcjonalnie, P5+)

- **Require linear history:** ✅ (wymusza squash merge)

- **Require deployments to succeed:** ⚠️ (P5+, gdy mamy deployment environments)

- **Lock branch:** ❌

- **Do not allow bypassing the above settings:** ✅

- **Allow force pushes:** ❌
- **Allow deletions:** ❌

## Branching strategy

### Main branches

- **`main`** — zawsze deployable, protected
- **`develop`** — opcjonalne integration branch (nie używamy na start — czysty GitFlow light)

### Feature branches

- **`feature/LIN-123-add-tennis-elo`** — nowa funkcjonalność
- **`fix/LIN-456-espn-scraper-retry`** — bugfix
- **`refactor/LIN-789-db-module-split`** — refactor
- **`docs/LIN-012-api-guide`** — documentation
- **`chore/LIN-345-upgrade-python`** — maintenance

**Format:** `<type>/<linear-id>-<slug>`

### Release branches (P5+)

- **`release/v0.1.0`** — stabilizacja przed release
- **`hotfix/v0.1.1-critical-bug`** — emergency patches

## PR workflow

### 1. Create PR
- **Title:** Conventional Commits format: `feat(features): add xg rolling per opposition`
- **Description:** Template (patrz poniżej)
- **Link Linear issue:** "Fixes LIN-123"
- **Labels:** Auto-assigned przez actions bazując na path changes
- **Assignees:** Author
- **Reviewers:** Auto-assigned przez CODEOWNERS + opcjonalnie manual

### 2. CI runs
- Status checks muszą przejść
- Jeśli nie: author fixuje lokalnie, push update

### 3. Code review
- Reviewer(s) zostawiają comments + approve lub changes requested
- Author addresuje comments
- Re-approve required jeśli significant changes

### 4. Merge
- **Squash merge** domyślnie (clean history)
- Merge commit message: Conventional Commits format
- Auto-delete branch po merge

### 5. Post-merge
- Linear issue auto-closes
- CI deploys do staging (P5+)
- Author monitoruje deployment (P5+)

## PR template (`.github/pull_request_template.md`)

```markdown
## Summary
Brief description of changes.

## Why
Context, linked issue.

Fixes #LIN-XXX

## Changes
- Change 1
- Change 2

## Testing
- [ ] Tests added/updated
- [ ] Tests pass locally (`just test`)
- [ ] Manual testing done (describe)

## Checklist
- [ ] Self-review done
- [ ] Documentation updated
- [ ] CHANGELOG entry added (if user-facing)
- [ ] Breaking changes documented (if any)
- [ ] Linear issue linked

## Screenshots / demos
(if applicable)
```

## Issue templates

Pliki w `.github/ISSUE_TEMPLATE/`:

### `bug_report.md`
Standard bug report template.

### `feature_request.md`
Standard feature request template.

### `security.md`
Security issue template → redirects do `SECURITY.md` i security@sportslab.xyz.

## GitHub Actions — CI/CD workflows

### `.github/workflows/ci.yml`

Uruchamiany na każdy PR + push do main.

**Jobs:**
1. **lint** — ruff check na Python, eslint na TS
2. **typecheck** — mypy strict na Python, tsc na TS
3. **test** — pytest na Python (unit + integration), vitest na TS
4. **build** — monorepo build (packages + apps)
5. **security** — dependabot + audit
6. **coverage** — coverage report (≥ 80% per package)

### `.github/workflows/deploy-staging.yml` (P5+)

Uruchamiany na push do main.
- Build Docker images
- Push do GitHub Container Registry
- SSH do staging VPS, docker-compose pull + up
- Health check po deployment
- Notify Slack

### `.github/workflows/deploy-production.yml` (P5+)

Uruchamiany manually (workflow_dispatch) lub na tag `v*.*.*`.
- Same jako staging, na production VPS
- Requires: admin approval (environment protection)
- Rollback capability

### `.github/workflows/nightly.yml` (P5+)

Uruchamiany na cron (`0 2 * * *`).
- Full integration tests
- E2E tests
- Dependency updates check
- Security audit
- Report do Slack

### `.github/workflows/release.yml` (P5+)

Uruchamiany na tag `v*.*.*`.
- Generate changelog
- Create GitHub Release
- Build + publish packages (jeśli publikujemy)

## Secrets

### Repository secrets
- `DOPPLER_TOKEN` — sync secrets z Doppler
- `GHCR_TOKEN` — Container Registry push
- `DEPLOY_SSH_KEY` — SSH key dla VPS deploys (P5+)
- `TELEGRAM_BOT_TOKEN` — CI notifications (P5+)
- `SLACK_WEBHOOK` — CI notifications (P5+)

### Environment secrets (P5+)
- **`staging`** environment secrets
- **`production`** environment secrets (with approvals)

## Dependabot

`.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/packages/ml-in-sports"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "python"
    
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "javascript"
  
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "monthly"
```

## Security

### Settings
- **Secret scanning:** enabled
- **Push protection:** enabled (block pushes with secrets)
- **Dependabot alerts:** enabled
- **Dependabot security updates:** enabled
- **Code scanning (CodeQL):** enabled dla main repo

### SECURITY.md
Plik w root z:
- Contact: `security@sportslab.xyz`
- Disclosure policy (responsible disclosure, 90 dni embargo)
- Supported versions
- Bug bounty program (jeśli będzie, P6+)

## Releases & changelog

### Versioning
- **Semantic Versioning:** MAJOR.MINOR.PATCH
- **Pre-P6:** v0.x.x (unstable)
- **Post-P6 launch:** v1.0.0

### Release process
1. Tag `v1.2.3` na main
2. CI runs `release.yml`
3. Auto-generated changelog (via `git-cliff` lub `standard-version`)
4. GitHub Release z notes
5. Notify Slack + users

### CHANGELOG.md
Keep a Changelog format. Editowany manually w PR dla user-facing changes.

## Conventional Commits

Wymagane dla squash merge messages i commit messages:

```
feat(scope): description
fix(scope): description
refactor(scope): description
docs(scope): description
chore(scope): description
test(scope): description
perf(scope): description
```

**Scopes:** `features`, `models`, `processing`, `cli`, `api`, `web`, `docs`, `infra`, `deps`, `ci`

**Breaking changes:** Dodanie `!` po typie, np. `feat!: remove deprecated endpoint`

**Commitlint enforce:** pre-commit hook + CI check

## Protecting IP

- **Private repo** — zawsze (do momentu gdy decydujemy open-source jakieś części)
- **NDA w umowach** — wszyscy członkowie podpisują w P0.10
- **IP assignment** — praca wykonana przez zespół należy do firmy
- **Git attribution** — commit emails matching team emails (nie personal leak)

## Koszt

- **GitHub Team:** $4/user × 6 = $24/m-c (+ CI minutes)
- **GitHub Actions:** Free tier 2000 min/m-c, większość zużycia w CI = możliwe że wystarczy. Monitoring w P5.
- **Private container registry:** GHCR free dla public, płatne dla private (wliczone w Team)

## Pierwsze kroki w P0.13

1. Lead tworzy organizację `sportslab-io` na GitHub
2. Upgrade do Team plan
3. Tworzenie teams (`@admins`, `@engineering`, `@design`, `@research`, `@leadership`)
4. Tworzenie repo `sportslab` (private)
5. Push initial monorepo structure
6. Branch protection na main
7. CODEOWNERS push
8. Issue + PR templates
9. Pierwszy `ci.yml` workflow
10. Dependabot setup

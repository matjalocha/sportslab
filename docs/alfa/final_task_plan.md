# SportsLab Alpha -- Final Task Plan

- **Status**: Accepted
- **Date**: 2026-04-06
- **Author**: System Architect
- **Timeline**: 5 weeks (35 working days)
- **Total tasks**: 48

---

## 0. Architectural Decisions (pre-plan)

### Repo strategy

After analysis of the founder's requirements and the existing ADR-0018 (monorepo confirmed),
the final repo structure is:

| Repo | Purpose | Rationale |
|------|---------|-----------|
| **sportslab** (monorepo) | ML package, FastAPI backend, CLI, infra, docs, experiments | ADR-0018: one contributor, one language, one deployable. Zero overhead. |
| **sportslab-web** (separate) | Next.js panel (6 user + 6 admin views) | Different runtime (Node.js), different deploy target (Vercel), different release cycle. Codex/Lovable generates bulk of this. |
| **sportslab-mlflow** (separate) | MLflow config, custom experiment report generator, model registry dashboards | Founder's explicit requirement. Keeps experiment tooling isolated from production code. Light repo: config + report templates + scripts. |

**Why sportslab-web is separate**: The panel is a Next.js app deployed to Vercel.
It has zero Python dependencies. Mixing Node.js tooling (package.json, node_modules,
next.config.js) into a Python monorepo creates CI complexity for no benefit. The panel
communicates with the backend via REST API -- a clean contract boundary. Codex can work
on the frontend repo without loading 170 Python files into context.

**Why sportslab-mlflow is separate**: MLflow configuration, custom plugins, and the
experiment report generator (dark-mode HTML template) are tooling for the founder, not
production code. Keeping them separate means the monorepo stays focused on the product
pipeline. The MLflow repo is small (~20 files) and changes infrequently.

### Experiment report design

The founder's dark-mode HTML report template becomes the standard for experiment reports
in the sportslab-mlflow repo. Design tokens:

```css
--c-bg: #09090b;
--c-surface: #18181b;
--c-primary: #a78bfa;
--c-accent: #2dd4bf;
--c-good: #4ade80;
--c-warn: #fbbf24;
--c-bad: #f87171;
```

Components: sticky TOC sidebar, gradient headers, summary cards (4-col grid), decision
banners, tradeoff tables, collapsible sections, sparkbars, metric badges (.m-good/.m-warn/.m-bad),
Inter + JetBrains Mono. Generated after each `sl backtest run --mlflow` as an MLflow artifact.

### Tool assignment philosophy

- **Claude Code**: architecture, complex backend logic, integrations, data pipelines, code review. Anything that requires reading existing codebase context.
- **Codex**: bulk frontend component generation, repetitive boilerplate, CRUD endpoints. Tasks where the spec is fully defined and context-loading is minimal.
- **Lovable**: landing page visual prototype (full page, not components). Generates deployable site from prompt.
- **Grok**: research tasks (legal, competitive analysis), content/copy writing. No code generation.
- **Nanobanana 2**: marketing graphics only. Hero images, social cards, favicons, icons.
- **Mateusz (founder)**: physical setup (Pi hardware, SSH), SaaS config (Stripe dashboard, Clerk dashboard, domain registrar, Telegram BotFather), beta user outreach, business decisions.

---

## 1. REPO SETUP (Week 1, Days 1-3)

### TASK-A-01: Initialize sportslab-web repo

```
Tool: Claude Code
Depends: none
Days: 0.5
Description:
  Create private GitHub repo sportslab-web. Initialize with:
  - Next.js 14+ (App Router) via create-next-app
  - TypeScript strict mode
  - Tailwind CSS + shadcn/ui
  - Biome for linting/formatting
  - .env.example with NEXT_PUBLIC_API_URL, CLERK_* placeholders
  - README with setup instructions
  - .github/CODEOWNERS
  - Branch protection rules on main (require PR, require CI pass)
Deliverable: github.com/mjalocha/sportslab-web repo with initial commit
```

### TASK-A-02: Initialize sportslab-mlflow repo

```
Tool: Claude Code
Depends: none
Days: 0.5
Description:
  Create private GitHub repo sportslab-mlflow. Structure:
  - config/ (MLflow server config, experiment definitions)
  - reports/ (experiment report HTML template + generator)
  - scripts/ (start-mlflow.sh, generate-report.py)
  - dashboards/ (placeholder for custom MLflow UI extensions)
  - pyproject.toml (uv project, deps: mlflow, jinja2, plotly)
  - README with usage
  - .github/CODEOWNERS + branch protection
Deliverable: github.com/mjalocha/sportslab-mlflow repo with initial commit
```

### TASK-A-03: GitHub Actions CI for sportslab monorepo

```
Tool: Claude Code
Depends: none
Days: 1
Description:
  Create .github/workflows/ci.yml for the sportslab monorepo:
  - Trigger: push to main, PR to main
  - Path filtering: only run Python CI when packages/ or apps/ change
  - Jobs:
    1. lint (ruff check + ruff format --check)
    2. typecheck (mypy packages/ apps/ --strict)
    3. test (pytest --cov --cov-fail-under=80)
  - Python 3.11, uv for dependency install
  - Cache: uv cache + .venv
  - Artifact: coverage report uploaded
  - Branch protection: require ci/lint + ci/test to pass
Deliverable: .github/workflows/ci.yml, branch protection configured
```

### TASK-A-04: GitHub Actions CI for sportslab-web

```
Tool: Codex
Depends: TASK-A-01
Days: 0.5
Description:
  Create .github/workflows/ci.yml for sportslab-web:
  - Trigger: push to main, PR to main
  - Jobs:
    1. lint (biome check)
    2. typecheck (tsc --noEmit)
    3. build (next build -- catches runtime errors)
  - Node 20, pnpm
  - Cache: pnpm store
Deliverable: sportslab-web/.github/workflows/ci.yml
```

### TASK-A-05: Secrets management setup

```
Tool: Mateusz
Depends: none
Days: 0.5
Description:
  Configure GitHub repository secrets for all 3 repos:
  - sportslab: PI_HOST, PI_SSH_KEY, B2_KEY_ID, B2_APP_KEY, TELEGRAM_BOT_TOKEN
  - sportslab-web: CLERK_SECRET_KEY, NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY, API_URL
  - sportslab-mlflow: (none needed initially)
  Create .env.example in each repo documenting all required variables.
  Store master copies in password manager (Bitwarden or 1Password personal).
Deliverable: GitHub secrets configured, .env.example files in repos
```

### TASK-A-06: Pre-commit hooks for sportslab monorepo

```
Tool: Claude Code
Depends: none
Days: 0.5
Description:
  Set up pre-commit in the sportslab monorepo:
  - ruff (lint + format)
  - mypy (type check)
  - check-yaml, check-toml
  - detect-secrets (prevent accidental secret commits)
  - no-commit-to-branch (block direct push to main)
  Configure .pre-commit-config.yaml + document in CONTRIBUTING.md.
Deliverable: .pre-commit-config.yaml, updated pyproject.toml
```

---

## 2. INFRA (Week 1, Days 2-5)

### TASK-A-07: Raspberry Pi OS setup + hardening

```
Tool: Mateusz
Depends: none
Days: 0.5
Description:
  Physical setup of Raspberry Pi 4:
  1. Flash Ubuntu Server 24.04 LTS ARM64 to USB SSD
  2. Boot, configure Ethernet, set static LAN IP
  3. SSH key auth only (disable password auth)
  4. UFW firewall: allow 22/tcp, deny all inbound
  5. Install fail2ban
  6. Set hostname: sportslab-pi
  7. Create sportslab user with sudo
Deliverable: Pi accessible via SSH at static LAN IP
```

### TASK-A-08: Postgres 16 on Pi + tuning

```
Tool: Mateusz (install) + Claude Code (tuning script)
Depends: TASK-A-07
Days: 0.5
Description:
  Install and configure Postgres:
  - sudo apt install postgresql-16 postgresql-client-16
  - Create sportslab user + database
  - Apply 4GB RAM tuning (shared_buffers=256MB, work_mem=32MB,
    effective_cache_size=1GB, max_connections=20)
  - Run Alembic migrations: uv run alembic upgrade head
  Claude Code writes scripts/setup_postgres_pi.sh for reproducibility.
Deliverable: Postgres running on Pi, 11-table schema migrated, tuning applied
```

### TASK-A-09: Data migration SQLite to Postgres

```
Tool: Claude Code
Depends: TASK-A-08
Days: 1
Description:
  Write and execute data migration:
  - Export all 11 tables from SQLite (dev PC) to CSV
  - SCP CSVs to Pi
  - COPY FROM CSV into Postgres tables on Pi
  - Verify row counts (95,374 matches, odds, player_matches, etc.)
  - Run sl features build on Pi to materialize Parquet
  - Smoke test: sl predict run with a model file
Deliverable: scripts/migrate_sqlite_to_postgres.py, data loaded and verified on Pi
```

### TASK-A-10: Cron pipeline + healthchecks on Pi

```
Tool: Claude Code (cron config) + Mateusz (healthchecks.io setup)
Depends: TASK-A-09
Days: 0.5
Description:
  Set up all cron jobs on Pi:
  - 06:00 morning pipeline (scrape + features + predict + notify)
  - 23:30 evening pipeline (results + notify)
  - Mon 07:30 weekly report
  - Tue 06:00 odds download
  - Wed 06:00 ELO update
  - 03:00 nightly Postgres backup to B2
  - Weekly log rotation
  Register 4 healthchecks.io checks with Telegram DM alerts.
Deliverable: infra/crontab.pi, healthchecks.io configured with 4 checks
```

### TASK-A-11: Backblaze B2 backup setup

```
Tool: Mateusz (B2 account) + Claude Code (backup script)
Depends: TASK-A-08
Days: 0.5
Description:
  - Create Backblaze B2 account + sportslab-backups bucket
  - Write scripts/backup_postgres.sh (pg_dump | gzip | b2 upload)
  - Configure 30-day lifecycle rule in B2 console
  - Test: run backup, verify file in B2, test restore
Deliverable: scripts/backup_postgres.sh, B2 bucket with lifecycle rule, tested restore
```

### TASK-A-12: Tailscale mesh network (all machines)

```
Tool: Mateusz
Depends: TASK-A-07
Days: 0.5
Description:
  Install Tailscale on all available machines:
  - Pi: tailscale up (always-on)
  - Dev PC: tailscale up
  - Laptop (if available): tailscale up
  - VM (if available): tailscale up
  Verify: all machines can SSH to each other via 100.x.x.x IPs.
  Document IPs in a private note (not in git).
Deliverable: Tailscale mesh operational, all machines reachable
```

### TASK-A-13: Monitoring + alerting baseline

```
Tool: Claude Code
Depends: TASK-A-10
Days: 0.5
Description:
  Add structured monitoring to the daily pipeline:
  - Morning pipeline: log start/end times, prediction count, model age
  - Evening pipeline: log W/L counts, daily P&L, ECE check
  - Alert via Telegram DM if: model >14 days old, ECE >0.08 for 7 days,
    CLV <0 for 14 days, 0 predictions for 3 consecutive match days
  - Pi system check: disk usage >70% alert, temperature >70C alert
  Write infra/monitoring.py (called from daily pipeline).
Deliverable: infra/monitoring.py, alerts integrated into daily_pipeline.py
```

---

## 3. MLFLOW (Week 2, Days 6-8)

### TASK-A-14: MLflow server setup in sportslab-mlflow repo

```
Tool: Claude Code
Depends: TASK-A-02
Days: 0.5
Description:
  In the sportslab-mlflow repo, set up:
  - scripts/start-mlflow.sh (sqlite backend, local artifact store)
  - config/mlflow-config.yaml (default experiments, artifact paths)
  - Experiment naming convention documented: football-<market>-<model>-v<N>
  - Model registry naming: football-<market>-predictor
  - Instructions for starting MLflow UI on Dev PC or VM
Deliverable: sportslab-mlflow/scripts/start-mlflow.sh, config documented
```

### TASK-A-15: MLflow integration in backtest runner

```
Tool: Claude Code
Depends: TASK-A-14
Days: 1
Description:
  In the sportslab monorepo, add --mlflow flag to sl backtest run:
  - Log params (n_estimators, learning_rate, features_count, leagues, etc.)
  - Log metrics (log_loss, ece, clv_mean, roi, sharpe, max_drawdown, n_bets)
  - Log artifacts (model.pkl, backtest_report.html, feature_importance.png)
  - Register model in MLflow Model Registry
  - Tag with market, calibration method, kelly_fraction, config_file, git_hash
  - Works with both local MLflow and remote (Tailscale) MLflow
Deliverable: Updated backtest/runner.py with --mlflow flag, tested
```

### TASK-A-16: Experiment report HTML template (dark-mode)

```
Tool: Claude Code
Depends: TASK-A-02
Days: 1.5
Description:
  In sportslab-mlflow repo, create the experiment report generator based on
  the founder's dark-mode HTML template. Features:
  - Sticky TOC sidebar with active section highlighting
  - Gradient header with experiment name + pulse animation
  - Summary cards grid (4 columns): CLV, ROI, Sharpe, ECE
    with color-coded borders (.m-good green, .m-warn yellow, .m-bad red)
    and hover lift effects
  - Decision banner (green gradient if model beats baseline, red if not)
  - Tradeoff table (model comparison) with best-row highlighting
  - Collapsible details sections for per-league breakdowns
  - Sparkbar visualizations for feature importance
  - Plotly interactive charts embedded: equity curve, calibration, CLV distribution
  - Design tokens: --c-bg:#09090b, --c-surface:#18181b, --c-primary:#a78bfa,
    --c-accent:#2dd4bf, --c-good:#4ade80, --c-warn:#fbbf24, --c-bad:#f87171
  - Fonts: Inter for text, JetBrains Mono for data/metrics
  - Jinja2 template + Python generator script
  - Input: JSON metrics blob (from MLflow run or backtest output)
  - Output: standalone HTML file (all CSS/JS inline, zero external deps)
  Integrate with sl backtest run --mlflow: report auto-generated and logged as artifact.
Deliverable: sportslab-mlflow/reports/templates/experiment_report.html.j2,
             sportslab-mlflow/reports/generate_report.py, sample output
```

### TASK-A-17: Model deploy script (Dev PC/VM to Pi)

```
Tool: Claude Code
Depends: TASK-A-12
Days: 0.5
Description:
  Write scripts/deploy_model_to_pi.sh:
  - Takes model path as argument
  - SCPs model.pkl + metadata.json to Pi:/app/models/production/
  - Verifies transfer (file size, sha256 checksum)
  - Prints next cron run time
  - Works over Tailscale (100.x.x.x) or LAN IP
  Also write scripts/promote_and_deploy.sh:
  - Queries MLflow for latest Production model
  - Extracts artifact path
  - Calls deploy_model_to_pi.sh
Deliverable: scripts/deploy_model_to_pi.sh, scripts/promote_and_deploy.sh
```

---

## 4. BACKEND (Week 2-3, Days 7-15)

### TASK-A-18: FastAPI project scaffold

```
Tool: Claude Code
Depends: TASK-A-03
Days: 1
Description:
  Create apps/api/ in sportslab monorepo:
  - FastAPI app with versioned router (/api/v1/)
  - Pydantic models for request/response (from shared-types)
  - Clerk JWT middleware for auth (verify token, extract user_id)
  - CORS configuration (allow sportslab-web origin)
  - Health check endpoint: GET /api/v1/health
  - OpenAPI docs at /docs (disabled in production)
  - Structured logging with structlog
  - pydantic-settings for configuration
  - Dockerfile for local dev
Deliverable: apps/api/ with working health endpoint, Clerk auth middleware
```

### TASK-A-19: Predictions API endpoint

```
Tool: Claude Code
Depends: TASK-A-18
Days: 1
Description:
  Implement prediction delivery endpoints:
  - GET /api/v1/predictions/{date} -- today's bet slip
  - GET /api/v1/predictions/{date}/results -- evening results
  - GET /api/v1/predictions/latest -- redirect to today
  Response schema: list[BetRecommendation] (reuse existing dataclass)
  Data source: read from Postgres predictions table (populated by cron pipeline)
  Auth: Clerk JWT required, user must have active subscription
  Rate limiting: 100 req/hour per user (basic, in-memory)
Deliverable: apps/api/routers/predictions.py with tests
```

### TASK-A-20: Track record API endpoint

```
Tool: Claude Code
Depends: TASK-A-18
Days: 0.5
Description:
  Implement track record endpoints:
  - GET /api/v1/track-record -- aggregate stats (total bets, hit rate, ROI, CLV)
  - GET /api/v1/track-record/monthly -- monthly breakdown
  - GET /api/v1/track-record/equity-curve -- time series for chart
  - GET /api/v1/track-record/by-league -- per-league performance
  Public endpoint (no auth required) -- this is the transparency differentiator.
Deliverable: apps/api/routers/track_record.py with tests
```

### TASK-A-21: User management API endpoints

```
Tool: Claude Code
Depends: TASK-A-18
Days: 1
Description:
  Implement user management:
  - POST /api/v1/users/onboard -- called after Clerk signup, creates user record
  - GET /api/v1/users/me -- current user profile (bankroll, leagues, settings)
  - PATCH /api/v1/users/me -- update settings
  - GET /api/v1/users/me/bets -- personal bet tracking
  - POST /api/v1/users/me/bets -- mark bet as placed (manual entry)
  Alembic migration for users table (id, clerk_id, settings JSONB, created_at).
Deliverable: apps/api/routers/users.py, Alembic migration, tests
```

### TASK-A-22: Admin API endpoints

```
Tool: Claude Code
Depends: TASK-A-21
Days: 1
Description:
  Implement admin-only endpoints (Clerk role check: admin):
  - GET /api/v1/admin/users -- list all users with engagement metrics
  - PATCH /api/v1/admin/users/{id} -- enable/disable, change plan
  - GET /api/v1/admin/system -- pipeline status, model info, infra stats
  - POST /api/v1/admin/model/rollback -- trigger model rollback on Pi
  - GET /api/v1/admin/revenue -- MRR, plan distribution (from Stripe)
  - GET /api/v1/admin/analytics -- DAU/WAU/MAU, feature usage
Deliverable: apps/api/routers/admin.py with tests
```

### TASK-A-23: Webhook endpoints (Clerk + Stripe)

```
Tool: Claude Code
Depends: TASK-A-18
Days: 1
Description:
  Implement webhook handlers:
  - POST /api/v1/webhooks/clerk -- user.created, user.deleted events
    -> create/deactivate user record in Postgres
  - POST /api/v1/webhooks/stripe -- invoice.paid, subscription.deleted events
    -> update user subscription status, enable/disable access
  Signature verification for both (Clerk svix, Stripe signature).
  Idempotency keys to prevent double-processing.
Deliverable: apps/api/routers/webhooks.py with tests
```

### TASK-A-24: Docker Compose for local development

```
Tool: Claude Code
Depends: TASK-A-18
Days: 0.5
Description:
  Create docker-compose.yml for local dev stack:
  - postgres:16 (with init script for schema)
  - api (FastAPI with hot reload)
  - Volumes for Postgres data persistence
  - .env.docker template
  - Makefile / scripts: make up, make down, make migrate, make test
Deliverable: docker-compose.yml, docker-compose.override.yml, Makefile
```

---

## 5. FRONTEND (Week 2-4, Days 8-20)

### TASK-A-25: Lovable builds full panel + landing prototype

```
Tool: Lovable
Depends: TASK-A-35 (copy), TASK-A-36 (graphics)
Days: 2
Description:
  Lovable builds the ENTIRE frontend as one project:

  USER PANEL (6 pages, dark mode, mobile-first):
  1. Dashboard: hero CLV metric, 4 KPI cards with sparklines, today's
     bets table, recent results, model confidence indicator
  2. Today's Predictions: full bet slip table, filters (league/market/edge),
     "Mark as placed" button, expandable model breakdown per row
  3. Track Record: equity curve chart, monthly P&L heatmap, per-league
     table, transparency banner, CSV download
  4. My Bets: personal bet log, "vs Model" comparison, manual entry form,
     personal ROI/P&L
  5. Settings: bankroll, leagues, markets, notifications, odds format, API key
  6. Alerts: notification center, read/unread, CLV degradation warnings

  ADMIN PANEL (6 pages, desktop-only):
  1. System Health: pipeline status, model quality KPIs, Pi infra stats
  2. Users: table with plan/engagement, invite/disable
  3. Model Management: current model, history, rollback
  4. Content: prediction notes, league/market toggles
  5. Revenue: MRR chart, plan distribution, Stripe link
  6. Analytics: DAU/WAU/MAU, feature usage, retention

  LANDING PAGE:
  - Hero + How It Works + Track Record + Methodology + Coverage +
    Alpha Access (waitlist) + FAQ + Footer

  DESIGN:
  - Dark mode: bg #0B0D14, surface #12141D, brand #5B67F2
  - Positive #22C55E, negative #EF4444, neutral #F59E0B
  - Inter + JetBrains Mono fonts
  - Sidebar navigation for panel, top nav for landing
  - Mobile responsive
  - Clerk auth integration (sign in/up pages)

  Lovable generates full React app with mock data and placeholder API calls.
  Output: deployable on Lovable hosting or exportable React code.

Deliverable: Live Lovable app with all 13 pages + landing, dark mode, auth flow
```

### TASK-A-26: Export Lovable code to sportslab-web repo

```
Tool: Claude Code
Depends: TASK-A-25, TASK-A-01
Days: 1
Description:
  Export generated React code from Lovable into sportslab-web repo:
  - Extract components, pages, styles from Lovable export
  - Set up Next.js App Router structure
  - Configure Tailwind with exact Lovable tokens
  - Set up TanStack Query for API data fetching
  - Replace Lovable's Supabase auth with Clerk
  - Add proper TypeScript types matching API schema
  - Ensure all pages render with mock data
Deliverable: sportslab-web repo with full page structure from Lovable
```

### TASK-A-27: Wire Dashboard to real API

```
Tool: Codex
Depends: TASK-A-26, TASK-A-19, TASK-A-20
Days: 0.5
Description:
  Replace mock data in Dashboard page with real API calls:
  - GET /api/v1/predictions/latest -> today's bets table
  - GET /api/v1/track-record -> hero CLV, KPI cards
  - TanStack Query hooks with loading/error states
  - Refresh on window focus
Deliverable: Dashboard connected to live API
```

### TASK-A-28: Wire Predictions page to real API

```
Tool: Codex
Depends: TASK-A-26, TASK-A-19
Days: 0.5
Description:
  Replace mock data in Predictions page:
  - GET /api/v1/predictions/{date} -> bet slip table
  - POST /api/v1/users/me/bets -> "Mark as placed" action
  - Filters work client-side on fetched data
  - Date navigation (prev/next day)
Deliverable: Predictions page connected to live API
```

### TASK-A-29: Wire Track Record page to real API

```
Tool: Codex
Depends: TASK-A-26, TASK-A-20
Days: 0.5
Description:
  Replace mock data in Track Record page:
  - GET /api/v1/track-record/equity-curve -> Recharts line chart
  - GET /api/v1/track-record/monthly -> heatmap data
  - GET /api/v1/track-record/by-league -> table data
  - CSV export from fetched data
Deliverable: Track Record page connected to live API
```

### TASK-A-30: Wire My Bets + Settings + Alerts to real API

```
Tool: Codex
Depends: TASK-A-26, TASK-A-21
Days: 1
Description:
  Wire remaining 3 user pages:
  - My Bets: GET/POST /api/v1/users/me/bets
  - Settings: GET/PATCH /api/v1/users/me (bankroll, leagues, etc.)
  - Alerts: GET /api/v1/users/me/alerts (placeholder for now)
Deliverable: My Bets, Settings, Alerts connected to API
```

### TASK-A-31: Wire Admin pages to real API

```
Tool: Codex
Depends: TASK-A-26, TASK-A-22
Days: 1
Description:
  Wire all 6 admin pages:
  - System Health: GET /api/v1/admin/system
  - Users: GET /api/v1/admin/users, PATCH enable/disable
  - Model: GET /api/v1/admin/system (model section)
  - Content: placeholder (manual content for alpha)
  - Revenue: link to Stripe dashboard
  - Analytics: GET /api/v1/admin/analytics
Deliverable: All admin pages connected to API
```

### TASK-A-32: Clerk auth integration (sportslab-web)

```
Tool: Claude Code
Depends: TASK-A-26
Days: 0.5
Description:
  Integrate Clerk authentication in sportslab-web:
  - ClerkProvider wrapping app layout
  - Sign-in / sign-up pages (Clerk hosted or embedded components)
  - Middleware: protect /dashboard/*, /predictions/*, /my-bets/*, /settings/*, /alerts/*
  - Admin routes: require admin role claim
  - Token forwarding to API (Clerk JWT in Authorization header)
  - User profile component in sidebar
Deliverable: middleware.ts, app/(auth)/ pages, ClerkProvider setup
```

### TASK-A-33: Vercel deployment + CI/CD for sportslab-web

```
Tool: Claude Code
Depends: TASK-A-26
Days: 0.5
Description:
  Deploy sportslab-web to Vercel:
  - Connect GitHub repo -> Vercel auto-deploy on push to main
  - Configure environment variables (CLERK keys, API URL)
  - Custom domain setup (app.sportslab.xyz or similar)
  - Preview deployments for PRs
Deliverable: Live panel at Vercel URL, auto-deploys on push
```

### TASK-A-34: Clerk auth integration (sportslab-web)

```
Tool: Claude Code
Depends: TASK-A-25
Days: 0.5
Description:
  Integrate Clerk authentication in sportslab-web:
  - ClerkProvider wrapping app layout
  - Sign-in / sign-up pages (Clerk hosted or embedded components)
  - Middleware: protect /dashboard/*, /predictions/*, /my-bets/*, /settings/*, /alerts/*
  - Admin routes: require admin role claim
  - Token forwarding to API (Clerk JWT in Authorization header)
  - User profile component in sidebar
Deliverable: middleware.ts, app/(auth)/ pages, ClerkProvider setup
```

---

## 6. LANDING (Week 3, Days 11-15)

### TASK-A-35: Landing page copy + content

```
Tool: Grok
Depends: none
Days: 0.5
Description:
  Write all landing page copy in English:
  - Hero: headline + subheadline (data-forward, not hype)
  - How It Works: 3-step visual description (Data -> Model -> Bet Slip)
  - Methodology: 4 cards (935 Features, Calibrated Probabilities,
    Portfolio Kelly, Closing Line Value)
  - Coverage: 14 leagues description
  - Alpha Access: what you get + CTA copy
  - FAQ: 6-8 questions (is this financial advice? how often? etc.)
  - Footer: legal disclaimer, contact
  - Meta: OG title, OG description, page title
Deliverable: docs/alfa/landing_copy.md with all sections
```

### TASK-A-36: Marketing graphics

```
Tool: Nanobanana 2
Depends: none
Days: 0.5
Description:
  Generate all visual assets for landing page:
  - Hero image (1920x1080): dark theme, abstract data viz + football,
    green/blue accents, professional not flashy
  - OG card (1200x630): social share image for Twitter/Discord
  - Favicon (32x32 + 192x192): SL monogram, green on dark
  - Methodology icons (4x 120x120): Features, Calibration, Kelly, CLV
  - Coverage map (800x600): Europe with highlighted league countries (optional)
  Style: dark background (#09090b-ish), clean lines, data aesthetic,
  no gambling imagery (no dice/slots).
Deliverable: assets/ folder with all images in PNG + WebP
```

### TASK-A-37: Build landing page in Lovable

```
Tool: Lovable
Depends: TASK-A-35, TASK-A-36
Days: 1
Description:
  Build complete landing page in Lovable:
  - Hero section with headline + CTA + hero image
  - How It Works (3-step visual)
  - Track Record section (initially "Starting soon" with placeholder stats)
  - Methodology (4 cards)
  - Coverage (14 leagues grid)
  - Alpha Access section with waitlist form (Tally.so embed or native)
  - FAQ (collapsible)
  - Footer with legal disclaimer
  - Dark theme, mobile-first, data-forward aesthetic
  - Configure custom domain or lovable.app subdomain
Deliverable: Live landing page at sportslab.lovable.app or custom domain
```

### TASK-A-38: Track record JSON exporter

```
Tool: Claude Code
Depends: TASK-A-10
Days: 0.5
Description:
  Write a script that exports weekly track record metrics to JSON:
  - Total bets, hit rate, ROI, CLV, Sharpe, max drawdown
  - Equity curve data points (date, bankroll value)
  - Per-league breakdown
  Output: reports/track_record_latest.json
  This JSON feeds the landing page track record section (manual upload
  to Lovable or auto-push via GitHub Action to a public JSON endpoint).
  Runs as part of weekly cron on Pi.
Deliverable: scripts/export_track_record.py, integrated into weekly cron
```

---

## 7. INTEGRATIONS (Week 3-4, Days 13-20)

### TASK-A-39: Telegram bot enhanced

```
Tool: Claude Code
Depends: TASK-A-10
Days: 0.5
Description:
  Enhance existing Telegram bot:
  - /today command: on-demand today's predictions
  - /track command: current track record summary
  - /subscribe command: placeholder for future email notifications
  - Improved bet slip format: league emoji, odds source, confidence tier
  - Results format: W/L with color indicators, daily P&L, running stats
  - Weekly report: link to HTML report (hosted or attached)
  Build on existing TelegramNotifier -- extend, don't rewrite.
Deliverable: Updated cli/notify_cmd.py, new bot commands
```

### TASK-A-40: Telegram bot token setup

```
Tool: Mateusz
Depends: none
Days: 0.25
Description:
  - Create Telegram bot via BotFather
  - Create private alpha channel
  - Set bot as admin in channel
  - Record bot token and chat ID in .env on Pi
  - Test: send a test message from Pi
Deliverable: Bot created, channel created, token in .env on Pi
```

### TASK-A-41: Stripe product + subscription setup

```
Tool: Mateusz
Depends: none
Days: 0.5
Description:
  Configure Stripe dashboard (test mode for alpha, live for launch):
  - Product: "SportsLab Predictions"
  - Plans: Free (alpha), Pro (EUR 49/mo), Enterprise (EUR 199/mo)
  - Annual discount: -20%
  - Webhook endpoint URL pointing to API
  - Tax configuration (Stripe Tax for EU)
  - Customer portal for self-service subscription management
  Note: billing is NOT active during alpha. This is pre-configuration
  for post-alpha monetization (weeks after alpha launch).
Deliverable: Stripe products/plans configured, webhook URL set
```

### TASK-A-42: Clerk project setup

```
Tool: Mateusz
Depends: none
Days: 0.5
Description:
  Configure Clerk dashboard:
  - Create SportsLab application
  - Enable email + social (Google) sign-in
  - Configure JWT template (include user_id, email, role claims)
  - Set allowed redirect URLs (localhost:3000 + production domain)
  - Create admin role
  - Webhook URL pointing to API
  - Customize sign-in/sign-up appearance (dark theme)
Deliverable: Clerk app configured, publishable + secret keys in secrets
```

### TASK-A-43: Domain + DNS setup

```
Tool: Mateusz
Depends: none
Days: 0.25
Description:
  - Register domain (sportslab.dev or sportslab.app or alternative)
  - Configure DNS:
    - A record -> Vercel (for panel, when deployed)
    - CNAME for landing -> Lovable custom domain
    - MX records if email needed (or use Clerk email)
  - Verify domain in Clerk, Stripe, Lovable
Deliverable: Domain registered, DNS configured
```

---

## 8. PRODUCTION READINESS (Week 4, Days 16-20)

### TASK-A-44: End-to-end integration test

```
Tool: Claude Code
Depends: TASK-A-19, TASK-A-34
Days: 1
Description:
  Write integration tests that validate the full flow:
  1. Pipeline runs on Pi -> predictions stored in Postgres
  2. API serves predictions from Postgres
  3. Frontend fetches and renders predictions
  4. Clerk auth protects endpoints
  5. Webhook processes Clerk user.created event
  6. Track record endpoint returns accurate aggregated data
  Tests run in CI with Docker Compose (Postgres + API).
  Separate from unit tests -- these test the contract between services.
Deliverable: tests/integration/ directory with test files, CI job
```

### TASK-A-45: Rollback plan + runbook

```
Tool: Claude Code
Depends: TASK-A-17
Days: 0.5
Description:
  Document operational runbooks:
  - Model rollback: how to revert to previous model on Pi
    (archive current, restore from /app/models/archive/)
  - Database rollback: Alembic downgrade + restore from B2 backup
  - Pipeline failure: manual trigger, skip day procedure
  - Pi failure: full recovery from B2 to new Pi or Hetzner CX32
  - API outage: panel shows cached data, Telegram continues independently
  - Hotfix procedure: branch from main, fix, PR, deploy
  Format: step-by-step with exact commands.
Deliverable: docs/alfa/runbooks/rollback.md, docs/alfa/runbooks/recovery.md
```

### TASK-A-46: Legal research (gambling regulations, ToS)

```
Tool: Grok
Depends: none
Days: 0.5
Description:
  Research and write:
  1. Legal status of providing betting tips in Poland and EU
     (is SportsLab a gambling service? do we need a license?)
  2. Required disclaimers for the landing page and Telegram channel
  3. Draft Terms of Service for alpha (free tier)
  4. Privacy Policy outline (GDPR-compliant: what data we collect,
     how we process it, data retention, user rights)
  5. Competitive landscape: how do existing tip services handle this?
Deliverable: docs/alfa/legal_research.md, docs/alfa/tos_draft.md
```

### TASK-A-47: Vercel deployment for sportslab-web

```
Tool: Mateusz (Vercel config) + Claude Code (deploy config)
Depends: TASK-A-34, TASK-A-01
Days: 0.5
Description:
  Deploy sportslab-web to Vercel:
  - Connect GitHub repo to Vercel
  - Configure environment variables (Clerk keys, API URL)
  - Set custom domain (app.sportslab.dev or panel.sportslab.dev)
  - Configure preview deployments on PR
  - Verify: sign in flow works, dashboard loads, API calls succeed
  Claude Code writes vercel.json if needed.
Deliverable: Panel live on Vercel, CI/CD auto-deploy on push to main
```

---

## 9. LAUNCH (Week 5, Days 21-25)

### TASK-A-48: Beta user outreach (inner circle)

```
Tool: Mateusz
Depends: TASK-A-40, TASK-A-37
Days: 1 (spread across week)
Description:
  - Invite 5-10 friends/contacts to private Telegram alpha channel
  - Share landing page link for context
  - Collect feedback on:
    - Bet slip readability and usefulness
    - Telegram format (timing, content, missing info)
    - Landing page impression
    - What would make them pay EUR 49/mo for this?
  - Iterate on bet slip format based on feedback
  - Document feedback in docs/alfa/beta_feedback.md
Deliverable: 5-10 users in Telegram channel, feedback documented
```

### TASK-A-49: Public announcement

```
Tool: Grok (copy) + Mateusz (posting)
Depends: TASK-A-48
Days: 0.5
Description:
  Write and post public announcements:
  - Reddit post for r/SoccerBetting (methodology-focused, transparent,
    not spammy -- emphasize CLV tracking and open track record)
  - Reddit post for r/sportsbook (similar, English-focused)
  - Twitter/X launch thread (5-7 tweets with charts/screenshots)
  - Polish betting forum post (if appropriate community found)
  Include link to landing page waitlist.
  Timing: post AFTER 1-2 weeks of live results to show track record.
Deliverable: docs/alfa/announcement_posts.md, posts published
```

### TASK-A-50: Waitlist processing + invite flow

```
Tool: Mateusz
Depends: TASK-A-37, TASK-A-40, TASK-A-49
Days: ongoing
Description:
  Process waitlist signups:
  - Review Tally.so form submissions
  - Manual approval (filter for quality: real Telegram handles, not bots)
  - Add approved users to Telegram alpha channel
  - Welcome message in DM with: what to expect, timing, how to give feedback
  Target: 25-50 users in first 2 weeks after announcement
Deliverable: Ongoing process, target 25+ alpha users
```

---

## Timeline Summary (Gantt-style)

```
Week 1 (Days 1-5): REPO SETUP + INFRA
  D1: TASK-A-01 (web repo), TASK-A-02 (mlflow repo), TASK-A-07 (Pi OS)
  D2: TASK-A-03 (CI mono), TASK-A-06 (pre-commit), TASK-A-08 (Postgres)
  D3: TASK-A-04 (CI web), TASK-A-05 (secrets), TASK-A-09 (data migration)
  D4: TASK-A-10 (cron), TASK-A-11 (B2 backup), TASK-A-12 (Tailscale)
  D5: TASK-A-13 (monitoring), buffer/catch-up

Week 2 (Days 6-10): MLFLOW + BACKEND starts + FRONTEND starts
  D6: TASK-A-14 (MLflow server), TASK-A-15 (MLflow integration starts)
  D7: TASK-A-15 (MLflow integration done), TASK-A-17 (deploy script)
  D8: TASK-A-16 (experiment report template starts), TASK-A-18 (FastAPI scaffold)
  D9: TASK-A-16 (report template done), TASK-A-25 (design system)
  D10: TASK-A-19 (predictions API), TASK-A-34 (Clerk auth)

Week 3 (Days 11-15): BACKEND done + FRONTEND bulk + LANDING
  D11: TASK-A-20 (track record API), TASK-A-26 (dashboard page)
  D12: TASK-A-21 (user API), TASK-A-27 (predictions page)
  D13: TASK-A-22 (admin API), TASK-A-28 (track record page)
  D14: TASK-A-23 (webhooks), TASK-A-35 (landing copy), TASK-A-36 (graphics)
  D15: TASK-A-37 (Lovable landing), TASK-A-29 (my bets page)

Week 4 (Days 16-20): FRONTEND done + INTEGRATIONS + PRODUCTION READINESS
  D16: TASK-A-30 (settings), TASK-A-31 (alerts), TASK-A-39 (Telegram enhanced)
  D17: TASK-A-32 (admin system), TASK-A-33 (admin pages start)
  D18: TASK-A-33 (admin pages done), TASK-A-24 (Docker Compose)
  D19: TASK-A-38 (track record exporter), TASK-A-41 (Stripe), TASK-A-42 (Clerk)
  D20: TASK-A-43 (domain), TASK-A-44 (integration tests), TASK-A-45 (rollback)

Week 5 (Days 21-25): LAUNCH
  D21: TASK-A-46 (legal research), TASK-A-47 (Vercel deploy)
  D22: TASK-A-48 (beta inner circle invite)
  D23: Pipeline running live, collecting track record
  D24: TASK-A-49 (public announcement -- after 1+ week of results)
  D25: TASK-A-50 (waitlist processing begins)
```

---

## Task Summary by Tool

| Tool | Tasks | Total days |
|------|-------|-----------|
| **Claude Code** | A-01, A-02, A-03, A-06, A-08p, A-09, A-10p, A-11p, A-13, A-14, A-15, A-16, A-17, A-18, A-19, A-20, A-21, A-22, A-23, A-24, A-34, A-38, A-39, A-44, A-45, A-47p | ~20 days |
| **Codex** | A-04, A-25, A-26, A-27, A-28, A-29, A-30, A-31, A-32, A-33 | ~10 days |
| **Lovable** | A-37 | ~1 day |
| **Grok** | A-35, A-46, A-49p | ~1.5 days |
| **Nanobanana 2** | A-36 | ~0.5 days |
| **Mateusz** | A-05, A-07, A-08p, A-10p, A-11p, A-12, A-40, A-41, A-42, A-43, A-47p, A-48, A-49p, A-50 | ~5 days |

(p = partial -- shared between tool and Mateusz)

**Note**: Claude Code and Codex tasks run in parallel. Claude Code handles the complex
backend + infrastructure while Codex generates frontend components from specs. This is the
key parallelism that compresses a 7-8 week sequential plan into 5 weeks.

---

## Task Summary by Category

| Category | Tasks | Count |
|----------|-------|-------|
| **1. REPO SETUP** | A-01 to A-06 | 6 |
| **2. INFRA** | A-07 to A-13 | 7 |
| **3. MLFLOW** | A-14 to A-17 | 4 |
| **4. BACKEND** | A-18 to A-24 | 7 |
| **5. FRONTEND** | A-25 to A-34 | 10 |
| **6. LANDING** | A-35 to A-38 | 4 |
| **7. INTEGRATIONS** | A-39 to A-43 | 5 |
| **8. PRODUCTION READINESS** | A-44 to A-47 | 4 |
| **9. LAUNCH** | A-48 to A-50 | 3 |
| **Total** | | **50** |

---

## Critical Path

The longest dependency chain determines the minimum timeline:

```
TASK-A-07 (Pi OS, D1)
  -> TASK-A-08 (Postgres, D2)
    -> TASK-A-09 (data migration, D3)
      -> TASK-A-10 (cron pipeline, D4)
        -> TASK-A-13 (monitoring, D5)
          -> [Pipeline running live]
            -> TASK-A-48 (beta users, D22)
              -> TASK-A-49 (public announcement, D24)
```

**Critical path length: 8 tasks, ~5 working days for pipeline + 2 weeks for track record accumulation + 2 days for launch.**

The frontend and MLflow tracks are off the critical path -- they can be delayed
without impacting the core pipeline launch. However, the panel should be ready
before public announcement to give a professional impression.

---

## Dependency Graph (simplified)

```
                    TASK-A-07 (Pi OS)
                   /        \
          TASK-A-08         TASK-A-12 (Tailscale)
          (Postgres)              |
              |              TASK-A-17 (deploy script)
          TASK-A-09
          (data migration)
              |
          TASK-A-10 -------- TASK-A-38 (track record export)
          (cron pipeline)         |
              |              TASK-A-37 (landing page)
          TASK-A-13              |
          (monitoring)      TASK-A-48 (beta users)
              |                  |
         [LIVE PIPELINE]    TASK-A-49 (announcement)

   TASK-A-01 (web repo)     TASK-A-02 (mlflow repo)
        |                        |
   TASK-A-25 (design)      TASK-A-14 (MLflow server)
        |                        |
   TASK-A-26..33 (pages)    TASK-A-15 (MLflow integration)
        |                        |
   TASK-A-34 (Clerk auth)  TASK-A-16 (experiment reports)
        |
   TASK-A-47 (Vercel)

   TASK-A-18 (FastAPI scaffold)
        |
   TASK-A-19..23 (endpoints)
        |
   TASK-A-24 (Docker)
        |
   TASK-A-44 (integration tests)
```

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Pi hardware failure during alpha | High | Laptop as standby (TASK-A-12 Tailscale). Recovery: 1-2h from B2 backup. |
| Model produces negative CLV live | High | Monitor daily (TASK-A-13). If CLV < -3% after 50 bets, pause and iterate. Be transparent with users. |
| Codex produces low-quality frontend components | Medium | Claude Code reviews all Codex output. TASK-A-44 integration tests catch contract mismatches. |
| Scraper breaks (STS, football-data.co.uk) | Medium | healthchecks.io alerts. Manual intervention. Never send garbage predictions. |
| Clerk/Stripe integration complexity | Medium | Both have excellent docs + SDK. Claude Code handles complex webhook logic. |
| Lovable limitations for landing page | Low | Lovable is MVP only. Migration to Next.js in sportslab-web is planned for post-alpha. |
| Zero waitlist signups | Low | Alpha validates the model regardless of user count. Telegram pipeline runs for self-tracking. |
| Frontend-backend contract mismatch | Medium | shared-types package with Pydantic models. OpenAPI spec generated from FastAPI. |

---

## Cost Estimate (Alpha Period)

| Item | Monthly cost | Notes |
|------|-------------|-------|
| Pi electricity | ~1 EUR | 5W x 24h x 30d |
| Domain | ~1 EUR/month | Annual registration |
| Vercel | 0 EUR | Hobby plan (free) |
| Clerk | 0 EUR | Free tier (10k MAU) |
| Stripe | 0 EUR | No charges during free alpha |
| Lovable | 0 EUR | Free tier |
| Backblaze B2 | 0 EUR | Free tier (10 GB) |
| healthchecks.io | 0 EUR | Free tier (20 checks) |
| **Total** | **~2 EUR/month** | |

---

## Post-Alpha Transition

After alpha success (CLV > 0, 25+ users, stable pipeline), the next steps are:

1. **Enable Stripe billing**: switch from free alpha to EUR 49/mo Pro plan
2. **Migrate Lovable landing to Next.js**: move landing page into sportslab-web repo
3. **Add O/U 2.5 market**: if 1X2 pipeline is stable
4. **Scale to 5 more leagues**: Championship, Eredivisie, Ekstraklasa, etc.
5. **Enterprise tier**: API access for programmatic clients
6. **MLflow on VM**: if VM is persistent, move MLflow from Dev PC to VM for always-on access

---

## References

- `docs/alfa/alpha_launch_plan.md` -- original 4-week plan (this supersedes task breakdown)
- `docs/alfa/panel_and_pricing_spec_summary.md` -- panel views and pricing tiers
- `docs/alfa/adr-0019-quad-machine-infrastructure.md` -- machine role assignments
- `docs/alfa/team_discussion_infra_2026-04-12.md` -- infrastructure discussion
- `ideas/solo_founder_roadmap.md` -- R0-R6 phases
- `docs/architecture/adr-0018-monorepo-strategy-confirmed.md` -- monorepo decision
- `docs/architecture/adr-0016-alpha-delivery-telegram.md` -- Telegram delivery

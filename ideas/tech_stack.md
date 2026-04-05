# Tech Stack — Single source of truth

**Cel:** Jedna kompletna lista technologii używanych w projekcie. Referencja dla całego zespołu i nowych członków.
**Aktualizowane:** Przy każdej zmianie stack'u (każda decyzja w planie fazowym musi być odzwierciedlona tutaj).

## Filozofia doboru

1. **Boring is beautiful** — dojrzałe, sprawdzone narzędzia ponad nowe
2. **Python + TypeScript only** — nie rozbijamy się na Go/Rust/Java w core'ze
3. **Open source first** — płatne tylko gdy OSS nie wystarcza
4. **Self-hostable gdy możliwe** — żeby uniknąć vendor lock-in
5. **Monorepo** — wszystko w jednym repo, uv + pnpm workspaces

---

## 1. Języki programowania

| Język | Gdzie | Dlaczego |
|---|---|---|
| **Python 3.13** | Core ML, pipeline, API backend, CLI | Ekosystem ML niezrównany, zespół zna |
| **TypeScript 5.x** | Frontend, shared types | Type safety, Next.js ecosystem |
| **SQL** | Postgres queries, Alembic migrations | Standard |

**NIE używamy:** Go, Rust, Java, C++ — niepotrzebna złożoność dla naszej skali.

---

## 2. Python ecosystem

### Core ML & Data Science

| Narzędzie | Zastosowanie | Wersja target |
|---|---|---|
| **pandas** | Data manipulation | 2.x |
| **polars** | Alternative dla heavy queries (P3+) | latest |
| **numpy** | Numerical | 2.x |
| **scikit-learn** | Classical ML, metrics, pipelines | latest |
| **LightGBM** | Gradient boosting (primary) | 4.x |
| **XGBoost** | Gradient boosting (ensemble member) | 2.x |
| **CatBoost** | Gradient boosting z categoricals | latest |
| **TabPFN** | Foundation tabular model (IP component) | latest |
| **Optuna** | Hyperparameter search | latest |
| **SHAP** | Feature importance, interpretability | latest |
| **PyMC** | Bayesian modeling (Dixon-Coles, priors) — P2+ | latest |
| **scipy** | Statistics | latest |
| **statsmodels** | Classical statistics, time series | latest |
| **PyTorch** | Dla TabPFN + potencjalne custom models | latest |

### Data processing & Storage

| Narzędzie | Zastosowanie |
|---|---|
| **SQLAlchemy 2.x** | ORM + Core |
| **Alembic** | DB migrations |
| **psycopg3** | Postgres driver (async) |
| **DuckDB** | Analytical queries na Parquet |
| **pyarrow** | Parquet I/O |
| **Pydantic 2.x** | Schemas, validation, settings |
| **Great Expectations** | Data quality checks (P5+) |

### Scraping & External APIs

| Narzędzie | Zastosowanie |
|---|---|
| **soccerdata** | Football data aggregator (obecny) |
| **requests / httpx** | HTTP client |
| **Selenium** lub **Playwright** | Browser automation (STS, LVBet scraping) |
| **BeautifulSoup** | HTML parsing |
| **tenacity** | Retry logic |

**Decyzja do P1:** Playwright > Selenium (szybszy, lepszy anti-detect).

### CLI & Configuration

| Narzędzie | Zastosowanie |
|---|---|
| **Typer** | CLI framework (zamiast click/argparse) |
| **Rich** | Pretty terminal output |
| **tqdm** | Progress bars |
| **pydantic-settings** | Config z env vars |
| **structlog** | Structured logging (zamiast stdlib logging + print) |

### Backend (FastAPI)

| Narzędzie | Zastosowanie |
|---|---|
| **FastAPI** | REST API framework |
| **uvicorn** | ASGI server |
| **SQLAlchemy async** | DB access |
| **Redis** (via redis-py) | Cache (P6+) |
| **celery** lub **arq** | Background jobs (opcjonalnie, prefer Prefect) |

**NIE używamy Django** — zbyt monolityczny, wolniejszy, mniej nowoczesny dla API-first. FastAPI + Pydantic + SQLAlchemy dają to samo taniej.

### Testing

| Narzędzie | Zastosowanie |
|---|---|
| **pytest** | Test framework |
| **pytest-cov** | Coverage |
| **pytest-xdist** | Parallel tests |
| **pytest-benchmark** | Performance regression tests |
| **hypothesis** | Property-based testing (selektywnie) |
| **responses** | HTTP mocking |
| **factory_boy** | Test fixtures |

### Code quality

| Narzędzie | Zastosowanie |
|---|---|
| **ruff** | Linter + formatter (zastępuje black, isort, flake8) |
| **mypy** | Type checking (strict mode) |
| **pre-commit** | Git hooks |
| **detect-secrets** | Secrets scanning |
| **bandit** | Security linting |

### Package management

| Narzędzie | Zastosowanie |
|---|---|
| **uv** | Python package manager (szybszy od Poetry, lepszy workspace) |
| **pyproject.toml** | Project config (PEP 621) |

**Migracja Poetry → uv** w P1.2.

---

## 3. TypeScript ecosystem

### Frontend (P6)

| Narzędzie | Zastosowanie |
|---|---|
| **Next.js 14+** | Full-stack React framework |
| **React 18** | UI library |
| **TypeScript** | Type safety |
| **Tailwind CSS** | Utility-first styling |
| **shadcn/ui** | Component library (copy-paste, no lock-in) |
| **TanStack Query** (React Query) | Server state |
| **TanStack Table** | Data tables |
| **Recharts** lub **Visx** | Data visualization |
| **D3.js** | Custom visualizations (pitch maps, court heatmaps) |
| **Zustand** lub **Jotai** | Client state (minimal) |
| **React Hook Form** + **Zod** | Forms + validation |
| **Framer Motion** | Animations (minimal) |
| **next-themes** | Dark mode |

### Shared tooling

| Narzędzie | Zastosowanie |
|---|---|
| **pnpm** | Package manager + workspaces |
| **ESLint** | Linting |
| **Prettier** | Formatting |
| **Vitest** | Unit tests |
| **Playwright** | E2E tests (P6+) |
| **openapi-typescript-codegen** | Generowanie TS types z FastAPI OpenAPI |

---

## 4. Database & Storage

| Narzędzie | Faza | Cel |
|---|---|---|
| **SQLite** | P0-P4 | Obecne, development |
| **Postgres 16** | P5+ | Production OLTP |
| **Timescale** extension | P5+ | Time-series (odds, CLV) |
| **Supabase** (managed PG) | P5-P6 opcja | Szybki start |
| **DuckDB** | P3+ | Analytical queries |
| **Parquet** | P1+ | Features storage |
| **Redis** | P6+ | API cache |
| **Backblaze B2** | P1+ | Object storage + backups |

---

## 5. ML Infrastructure

| Narzędzie | Zastosowanie | Faza |
|---|---|---|
| **MLflow** | Model registry + tracking | P2+ |
| **DVC** | Data versioning (opcjonalnie) | P2+ |
| **Weights & Biases** | Experiment tracking (opcjonalnie) | P2+ |
| **Feast** | Feature store (opcjonalnie) | P5+ |
| **RunPod / Lambda Labs** | GPU on-demand | P2+ |

---

## 6. Orchestration & Infra (P5+)

| Narzędzie | Zastosowanie |
|---|---|
| **Prefect 2.x** | Workflow orchestration (rekomendacja) |
| Alt: **Dagster** | Workflow orchestration (alternatywa) |
| **Docker** | Containerization |
| **docker-compose** | Local dev + production deployment |
| **Hetzner Cloud** | VPS (staging + production) |
| **Cloudflare** | DNS, CDN, WAF, SSL |
| **nginx** | Reverse proxy |
| **Terraform** lub **Ansible** | IaC |

**NIE używamy Kubernetes** w P5-P6 — overkill dla naszej skali. Ewentualnie P6++ gdy scale wymusi.

---

## 7. Monitoring & Observability (P5+)

| Narzędzie | Zastosowanie |
|---|---|
| **Better Stack** (Logtail + Uptime) | Primary w P5, szybki setup |
| Alt: **Grafana + Loki + Prometheus** | Self-hosted w P6+ |
| **Sentry** | Error tracking (P6+) |
| **PostHog** | Product analytics (P6+) |

---

## 8. Authentication & Payments (P6)

| Narzędzie | Zastosowanie |
|---|---|
| **Clerk** | Authentication (rekomendacja, szybki setup) |
| Alt: **Auth0** | Authentication (enterprise) |
| Alt: **Supabase Auth** | Authentication (jeśli używamy Supabase) |
| **Stripe** | Payments, subscriptions, invoicing |
| **Stripe Tax** | Automatic tax calculation |

---

## 9. Secrets & Security

| Narzędzie | Zastosowanie |
|---|---|
| **Doppler** | Secrets management (runtime) |
| **1Password Teams** | Credentials (human access) |
| **GitHub Secrets** | CI/CD secrets (sync z Doppler) |
| **Let's Encrypt** (via Cloudflare) | SSL certs |
| **fail2ban** | SSH brute-force protection |
| **UFW** | Firewall |

---

## 10. Communication & Email (P6)

| Narzędzie | Zastosowanie |
|---|---|
| **Resend** | Transactional email |
| Alt: **Postmark** | Transactional email (alternatywa) |
| **React Email** | Email templates |
| **Telegram Bot API** | Notification bot + Pro bot |

---

## 11. Collaboration tools (non-code)

| Narzędzie | Zastosowanie | Owner |
|---|---|---|
| **Linear** | Task tracking, sprints, issues | Lead |
| **GitHub** | Code, PRs, CI/CD, issues (alt/complement) | SWE |
| **Slack** | Team communication (alt: Discord) | Lead |
| **Google Workspace** | Email, Drive, Docs, Meet | Lead |
| **Notion** | Wiki, knowledge base, notes | Lead |
| **Figma** | Design, wireframes, prototypes, handoff | Designer |
| **1Password Teams** | Team password manager | Lead |
| **Miro** lub **FigJam** | Whiteboarding, diagrams | Designer |
| **Calendly** | Sales/interview booking (P6+) | Lead |
| **Loom** | Async video updates (opcjonalnie) | wszyscy |

---

## 12. Development tools

| Narzędzie | Zastosowanie |
|---|---|
| **VS Code** lub **Cursor** lub **PyCharm** | IDE (personal choice) |
| **just** | Command runner (alternative do Make) |
| **direnv** | Per-project env vars |
| **Docker Desktop** | Local containerization |
| **GitHub CLI (`gh`)** | GitHub from terminal |
| **httpie** | HTTP requests CLI |
| **jq** | JSON parsing |
| **fzf** | Fuzzy search |
| **Cloudflare Tunnel** | Local dev + production preview |

---

## 13. Documentation

| Narzędzie | Zastosowanie |
|---|---|
| **MkDocs Material** lub **Mintlify** | Developer docs site |
| **Mermaid** | Diagrams w markdown |
| **Excalidraw** | Sketchy diagrams |
| **Redoc** lub **Swagger UI** | API reference (z FastAPI OpenAPI) |
| **Markdown** | Wszystko (README, docs, ideas) |

---

## 14. Marketing & Growth (P6+)

| Narzędzie | Zastosowanie |
|---|---|
| **Vercel** | Landing page hosting (Next.js native) |
| **PostHog** | Product analytics |
| **Google Analytics 4** | Web analytics |
| **Plausible** | Privacy-friendly analytics (alternatywa) |
| **Customer.io** lub **Loops** | Marketing automation |
| **Tally** lub **Typeform** | Forms, waitlist |
| **Crisp** lub **Intercom** | Customer support chat |

---

## 15. Legal & Compliance (P6)

| Narzędzie | Zastosowanie |
|---|---|
| **Termly** lub **Iubenda** | ToS + Privacy Policy generator |
| **Cookiebot** | Cookie consent |
| **Notion** | DPA templates |

---

## Versioning & updates

### Update policy
- **Security patches:** natychmiast (Dependabot auto-PR)
- **Minor versions:** weekly review
- **Major versions:** per-faza planned upgrades
- **Breaking changes:** documented w CHANGELOG + migration guide

### Deprecation
- Gdy porzucamy technologię, zostawiamy notatkę w tym pliku w sekcji `Deprecated`
- Migration plan w PR description
- Archive obsolete code w gałęzi zamiast usuwania

---

## Decyzje do potwierdzenia (open questions)

1. **Prefect vs Dagster** — decyzja w P5
2. **Self-hosted vs Supabase Postgres** — decyzja w P5
3. **Clerk vs Auth0** — decyzja w P6
4. **Grafana vs Better Stack** — decyzja w P5
5. **Selenium vs Playwright** — decyzja w P1 (migracja)
6. **PyMC vs Stan vs NumPyro** dla Bayesian — decyzja w P2

---

## Deprecated / nie używamy

| Narzędzie | Dlaczego |
|---|---|
| **Django** | FastAPI jest szybszy, lżejszy, bardziej async-friendly |
| **Flask** | Mniej type-safe niż FastAPI, brak native OpenAPI |
| **Pipenv** | Wolniejszy, gorszy workspace support niż uv |
| **Poetry** | Wolniejszy niż uv (migracja w P1) |
| **black** | ruff to zastępuje |
| **flake8 / isort** | ruff to zastępuje |
| **MongoDB** | Preferujemy relacyjne, mamy structured data |
| **Kafka / RabbitMQ** | Overkill dla naszej skali, Prefect + Postgres wystarczą |
| **Kubernetes** | Overkill dla P5-P6, docker-compose wystarczy |
| **GraphQL** | REST + OpenAPI jest prostszy dla B2B API |
| **Yarn / npm** | pnpm jest szybszy, lepszy workspace |
| **CRA (Create React App)** | Deprecated, Next.js to zastępuje |
| **Tailwind v3** | Używamy latest v4 |
| **jQuery** | N/A |
| **SASS/LESS** | Tailwind to zastępuje |

---

## Summary table (kategoriach)

| Kategoria | Primary stack |
|---|---|
| **Backend language** | Python 3.13 |
| **Frontend language** | TypeScript |
| **Package manager (Py)** | uv |
| **Package manager (TS)** | pnpm |
| **Monorepo** | uv workspaces + pnpm workspaces |
| **Web framework (backend)** | FastAPI |
| **Web framework (frontend)** | Next.js |
| **Database** | Postgres 16 + Timescale |
| **ORM** | SQLAlchemy 2 |
| **Migrations** | Alembic |
| **Cache** | Redis |
| **Analytical** | DuckDB + Parquet |
| **ML core** | LightGBM + XGBoost + CatBoost + TabPFN |
| **Bayesian** | PyMC |
| **Model registry** | MLflow |
| **Orchestration** | Prefect |
| **Scraping** | Playwright + httpx + soccerdata |
| **Containers** | Docker + docker-compose |
| **Infra** | Hetzner + Cloudflare |
| **Backup** | Backblaze B2 |
| **Secrets** | Doppler + 1Password |
| **Monitoring** | Better Stack → Grafana |
| **Auth** | Clerk |
| **Payments** | Stripe |
| **Email** | Resend |
| **Design** | Figma |
| **Tasks** | Linear |
| **Docs** | Markdown + MkDocs Material |
| **CI/CD** | GitHub Actions |
| **IDE** | VS Code / Cursor / PyCharm |

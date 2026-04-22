# SportsLab API

FastAPI backend for the SportsLab B2B platform.

## Overview

- **Framework:** FastAPI 0.111+, Uvicorn, Pydantic 2
- **Auth:** Clerk JWT verification (JWKS-based, 1h cache)
- **Config:** `pydantic-settings`, `SPORTSLAB_` env prefix
- **Logging:** `structlog` (JSON in production, console in dev)
- **Packaging:** uv workspace member, `hatchling` build backend
- **Python:** 3.11+

## Local development

```bash
# From monorepo root — installs all workspace members including `api`
uv sync --all-extras --dev

# Run with reload on :8000 (default)
uv run uvicorn api.main:app --reload --port 8000

# Health check
curl http://localhost:8000/api/v1/health
```

### Required environment variables

The API reads config from env vars with the `SPORTSLAB_` prefix. See
`src/api/config.py` for the full `Settings` schema. Minimum for local:

```dotenv
# apps/api/.env (not committed — add to password manager)
SPORTSLAB_CLERK_PUBLISHABLE_KEY=pk_test_...
SPORTSLAB_DATABASE_URL=sqlite+aiosqlite:///./local.db
```

`CLERK_JWKS_URL`, `LOG_LEVEL`, `CORS_ORIGINS`, `ENV`, `API_VERSION` all have
sensible defaults.

## Endpoints

| Method | Path                  | Auth | Purpose                         |
|--------|-----------------------|------|---------------------------------|
| GET    | `/api/v1/health`      | none | Liveness / version probe        |
| GET    | `/docs`               | none | Swagger UI                      |
| GET    | `/openapi.json`       | none | OpenAPI schema (for codegen)    |

All other routes (added in follow-up tasks) are behind `ClerkAuthMiddleware`
and require `Authorization: Bearer <clerk-jwt>`.

## Testing

```bash
# All API tests
uv run pytest apps/api/tests/

# With coverage
uv run pytest apps/api/tests/ --cov=apps/api/src --cov-report=term-missing
```

## Database migrations

Schema lives in `src/api/db/models.py`; migrations are managed with
Alembic. The database URL comes from `SPORTSLAB_DATABASE_URL` (falls
back to `sqlite:///./local.db` if unset -- convenient for local dev,
never acceptable in CI or prod).

```bash
# Apply all pending migrations (prod-safe, idempotent)
uv run alembic -c apps/api/alembic.ini upgrade head

# Generate a new revision from the ORM diff (review before committing!)
uv run alembic -c apps/api/alembic.ini revision \
    -m "short description" --autogenerate

# Roll back one revision
uv run alembic -c apps/api/alembic.ini downgrade -1
```

Async drivers (`+asyncpg`, `+aiosqlite`) used by the runtime are
automatically coerced to their sync equivalents inside `alembic/env.py`;
the stored URL stays unchanged.

## Docker

```bash
docker build -f apps/api/Dockerfile -t sportslab/api:dev .
docker run --rm -p 8000:8000 \
  -e SPORTSLAB_CLERK_PUBLISHABLE_KEY=pk_test_... \
  -e SPORTSLAB_DATABASE_URL=sqlite+aiosqlite:///./local.db \
  sportslab/api:dev
```

## Structure

```
apps/api/
├── pyproject.toml
├── Dockerfile
├── README.md
├── src/api/
│   ├── main.py             # FastAPI app, lifespan, router registration
│   ├── config.py           # pydantic-settings
│   ├── logging_config.py   # structlog setup
│   ├── middleware/clerk_auth.py
│   ├── routers/health.py
│   └── models/common.py
└── tests/
    ├── conftest.py         # TestClient fixture with mocked settings
    ├── test_health.py
    └── test_clerk_auth.py
```

## Related tasks

- Scaffold: SPO-124 (this task)
- CI: SPO-A-03 (enforces ruff + mypy + pytest --cov-fail-under=80)
- Billing integration: follow-up
- Database models + Alembic: follow-up

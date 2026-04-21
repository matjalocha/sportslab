# syntax=docker/dockerfile:1.7
# SportsLab API — multi-stage image using uv for fast, reproducible installs.
#
# Build from the repo root so the uv workspace resolves correctly:
#   docker build -f apps/api/Dockerfile -t sportslab/api:dev .

# ---- Stage 1: builder -------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official distroless image (pinned version for reproducibility).
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app

# Copy the workspace manifests first so uv can resolve without source churn
# invalidating the dep layer.
COPY pyproject.toml uv.lock* ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY packages packages

# Sync only the API app with its optional postgres driver. We skip dev deps
# to keep the runtime image lean.
COPY apps/api/src apps/api/src
COPY apps/api/README.md apps/api/README.md

RUN uv sync --frozen --no-dev --package api --extra postgres \
    || uv sync --no-dev --package api --extra postgres

# ---- Stage 2: runtime -------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 sportslab \
    && useradd --system --uid 1001 --gid sportslab sportslab

WORKDIR /app

COPY --from=builder --chown=sportslab:sportslab /app/.venv /app/.venv
COPY --from=builder --chown=sportslab:sportslab /app/apps/api/src /app/apps/api/src
COPY --from=builder --chown=sportslab:sportslab /app/packages /app/packages

USER sportslab

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

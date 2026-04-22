"""FastAPI application entry point.

Layout:
    - ``lifespan`` handles structlog setup on startup, logs shutdown
    - CORS middleware is added first (outermost) so the preflight OPTIONS
      never hits Clerk auth
    - ``ClerkAuthMiddleware`` runs on all non-public routes
    - Versioned router at ``/api/v1`` — bump the prefix, not the app, for
      breaking changes
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import Settings, get_settings
from api.logging_config import configure_logging
from api.middleware import ClerkAuthMiddleware
from api.routers import health, predictions

_logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup / shutdown hooks.

    Intentionally does not open a DB pool yet — that lands in the
    follow-up task that wires SQLAlchemy. Keeping startup fast means
    Docker healthchecks don't race the first request.
    """
    settings = get_settings()
    configure_logging(json_logs=settings.env != "dev", level=settings.log_level)
    _logger.info(
        "api_startup",
        version=settings.api_version,
        env=settings.env,
        cors_origins=settings.cors_origins,
    )
    yield
    _logger.info("api_shutdown", version=settings.api_version)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Exposed as a factory (rather than a module-level ``app = FastAPI()``)
    so tests can construct isolated instances with overridden settings.
    """
    resolved = settings or get_settings()

    app = FastAPI(
        title="SportsLab API",
        version=resolved.api_version,
        description="B2B sports analytics and value-betting platform.",
        lifespan=lifespan,
    )

    # Order matters: CORS is outermost so OPTIONS preflight short-circuits
    # before ClerkAuthMiddleware would reject it for missing auth.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ClerkAuthMiddleware, settings=resolved)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(predictions.router, prefix="/api/v1")

    return app


app = create_app()

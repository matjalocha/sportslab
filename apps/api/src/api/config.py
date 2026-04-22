"""Centralized configuration for the SportsLab API.

All configurable values come from environment variables with the
``SPORTSLAB_`` prefix, or fall back to documented defaults. Never hardcode
a value here that might legitimately differ between environments.

Usage::

    from api.config import get_settings

    settings = get_settings()
    cors_origins = settings.cors_origins
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Env var prefix: ``SPORTSLAB_``. See ``apps/api/README.md`` for the
    minimal local-dev dotenv template.

    Attributes:
        api_version: Surfaced in ``/health`` response and OpenAPI metadata.
        cors_origins: List of allowed origins for CORS. Whitelist only —
            never use ``["*"]`` in combination with credentials.
        clerk_publishable_key: Non-secret Clerk key, used by the frontend
            but also logged here for environment-consistency checks.
        clerk_jwks_url: Endpoint the API fetches to verify Clerk JWTs.
            Cached in-process for 1 hour by ``ClerkAuthMiddleware``.
        clerk_webhook_secret: Shared secret Clerk uses to sign webhook
            payloads (Svix standard). Empty in dev -> webhook returns 503.
        stripe_api_key: Stripe secret (``sk_...``) for server-side API
            calls (invoices, subscriptions). Empty in dev -> Stripe calls
            not attempted.
        stripe_webhook_secret: Stripe webhook signing secret (``whsec_...``).
            Empty in dev -> webhook returns 503.
        database_url: SQLAlchemy async URL. Example:
            ``postgresql+asyncpg://user:pw@host:5432/db`` or
            ``sqlite+aiosqlite:///./local.db``.
        log_level: structlog minimum level (``DEBUG`` / ``INFO`` / ``WARNING``).
        env: Deployment environment tag (``dev`` / ``staging`` / ``prod``).
            Controls JSON vs console log rendering.
    """

    api_version: str = "0.1.0"
    cors_origins: list[str] = ["http://localhost:3000"]
    clerk_publishable_key: str = ""
    clerk_jwks_url: str = "https://api.clerk.dev/v1/jwks"
    clerk_webhook_secret: str = ""
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    database_url: str = ""
    log_level: str = "INFO"
    env: str = "dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SPORTSLAB_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance.

    Call this instead of ``Settings()`` directly to avoid re-parsing
    environment variables on every request. Tests that mutate the
    environment should call ``get_settings.cache_clear()`` between cases.
    """
    return Settings()

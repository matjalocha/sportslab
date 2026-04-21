"""Shared fixtures for API tests.

Every test runs with a fresh ``Settings`` instance whose secrets are
synthetic, so the test suite never touches real Clerk infra.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from api.config import Settings, get_settings
from api.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def settings() -> Settings:
    """Return a throwaway ``Settings`` with deterministic values."""
    return Settings(
        api_version="0.1.0-test",
        cors_origins=["http://localhost:3000"],
        clerk_publishable_key="pk_test_stub",
        clerk_jwks_url="https://test.clerk.invalid/v1/jwks",
        database_url="sqlite+aiosqlite:///./test.db",
        log_level="WARNING",
        env="test",
    )


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    """Build an isolated FastAPI app using the test settings."""
    # ``create_app`` calls ``get_settings()`` inside the lifespan context,
    # so we pin the cached settings for the duration of the test.
    get_settings.cache_clear()
    application = create_app(settings=settings)
    application.dependency_overrides[get_settings] = lambda: settings
    try:
        yield application
    finally:
        application.dependency_overrides.clear()
        get_settings.cache_clear()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Synchronous TestClient for endpoint tests."""
    with TestClient(app) as test_client:
        yield test_client

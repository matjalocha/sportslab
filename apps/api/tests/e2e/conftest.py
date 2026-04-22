"""Shared fixtures for E2E cross-router tests.

Three client flavours cover the access matrix:

``e2e_anon_client``
    Real :class:`ClerkAuthMiddleware` left intact. Used to assert the
    unauthenticated boundary (401 on protected routes, 200 on public).

``e2e_user_client``
    Middleware monkey-patched to inject ``user_id`` + ``user_role="user"``.
    Used for regular-user journeys and RBAC-denied paths.

``e2e_admin_client``
    Same as ``e2e_user_client`` but with ``user_role="admin"``. Used for
    admin RBAC-allowed paths.

Webhook secrets are pinned on the settings so the Clerk and Stripe
webhook endpoints can be signed for real in the cross-router idempotency
tests. Stub state (users, admin, idempotency store) is wiped per-test
via an autouse fixture so ordering never matters.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from api.config import Settings, get_settings
from api.main import create_app
from api.middleware.clerk_auth import ClerkAuthMiddleware
from api.routers.admin import StubAdminProvider
from api.routers.users import StubUsersProvider
from api.routers.webhooks import InMemoryIdempotencyStore
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.middleware.base import RequestResponseEndpoint

# Stable, synthetic IDs so assertions can reference them directly.
E2E_USER_ID = "user_e2e_regular"
E2E_ADMIN_ID = "user_e2e_admin"

# Same Svix-compatible secret shape used in ``tests/test_webhooks.py``.
E2E_CLERK_WEBHOOK_SECRET = "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"
E2E_STRIPE_WEBHOOK_SECRET = "whsec_stripe_test_secret_value_xyz"


@pytest.fixture(autouse=True)
def _reset_all_stubs() -> Iterator[None]:
    """Wipe every in-memory stub before AND after each test.

    The user, admin, and webhook idempotency stubs keep state on the
    class, so cross-test bleed is the default without this reset. The
    post-yield cleanup keeps state from leaking into unrelated suites
    that might run after us in the same process.
    """
    StubUsersProvider.reset()
    StubAdminProvider.reset()
    InMemoryIdempotencyStore.reset()
    yield
    StubUsersProvider.reset()
    StubAdminProvider.reset()
    InMemoryIdempotencyStore.reset()


@pytest.fixture
def e2e_settings() -> Settings:
    """Settings with webhook secrets populated for signed-body flows."""
    return Settings(
        api_version="0.1.0-e2e",
        cors_origins=["http://localhost:3000"],
        clerk_publishable_key="pk_test_stub",
        clerk_jwks_url="https://test.clerk.invalid/v1/jwks",
        clerk_webhook_secret=E2E_CLERK_WEBHOOK_SECRET,
        stripe_webhook_secret=E2E_STRIPE_WEBHOOK_SECRET,
        database_url="sqlite+aiosqlite:///./test.db",
        log_level="WARNING",
        # ``env="test"`` keeps ``require_admin`` strict; the dev escape
        # hatch only fires when ``env == "dev"``, so RBAC behaves like prod.
        env="test",
    )


def _make_bypass_dispatch(user_id: str, user_role: str | None):
    """Build a ``ClerkAuthMiddleware.dispatch`` replacement.

    The replacement injects ``user_id`` (and optionally ``user_role``) on
    ``request.state`` so ``get_current_user_id`` and ``require_admin``
    see an authenticated caller without the test having to mint a real
    Clerk JWT. Public path handling is preserved to match production
    behaviour for ``/health``, ``/openapi.json``, and ``/webhooks/*``.
    """

    async def _dispatch(
        self: ClerkAuthMiddleware,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Preserve real public-path bypass so webhook + health paths behave
        # like production and never get a user_id injected.
        if self._is_public(request.url.path):
            return await call_next(request)
        request.state.user_id = user_id
        request.state.claims = {"sub": user_id}
        if user_role is not None:
            request.state.user_role = user_role
        return await call_next(request)

    return _dispatch


def _build_app(settings: Settings) -> FastAPI:
    """Create a fresh FastAPI app wired to the shared e2e settings."""
    get_settings.cache_clear()
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
def e2e_anon_client(e2e_settings: Settings) -> Iterator[TestClient]:
    """TestClient with the real auth middleware -- boundary tests."""
    app = _build_app(e2e_settings)
    try:
        with TestClient(app, follow_redirects=False) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


@pytest.fixture
def e2e_user_client(
    e2e_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """TestClient with Clerk auth stubbed to a role=user caller."""
    monkeypatch.setattr(
        ClerkAuthMiddleware,
        "dispatch",
        _make_bypass_dispatch(E2E_USER_ID, "user"),
    )
    app = _build_app(e2e_settings)
    try:
        with TestClient(app, follow_redirects=False) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


@pytest.fixture
def e2e_admin_client(
    e2e_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """TestClient with Clerk auth stubbed to a role=admin caller."""
    monkeypatch.setattr(
        ClerkAuthMiddleware,
        "dispatch",
        _make_bypass_dispatch(E2E_ADMIN_ID, "admin"),
    )
    app = _build_app(e2e_settings)
    try:
        with TestClient(app, follow_redirects=False) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

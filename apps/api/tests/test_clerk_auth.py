"""Tests for ``ClerkAuthMiddleware``.

We don't exercise the full JWKS fetch path in unit tests — that would
require either a real Clerk test tenant or a non-trivial RSA fixture.
Instead, we assert:
    - Public routes bypass auth (covered by ``test_health``).
    - Protected routes without a token → 401.
    - Protected routes with a malformed token → 401.
    - The ``WWW-Authenticate: Bearer`` header is present on 401s.

Full JWKS round-trip is validated in integration tests (follow-up task).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


def _register_protected_route(app: FastAPI) -> None:
    """Add a dummy protected route so we can exercise the middleware."""

    @app.get("/api/v1/_protected_probe")
    async def probe(request: Request) -> dict[str, str]:
        # Never reached when auth fails — middleware short-circuits.
        return {"user_id": request.state.user_id}


def test_protected_route_without_header_returns_401(app: FastAPI) -> None:
    """No Authorization header → 401 with ``auth.missing_token``."""
    _register_protected_route(app)
    with TestClient(app) as client:
        response = client.get("/api/v1/_protected_probe")
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"
    payload = response.json()
    assert payload["code"] == "auth.missing_token"


def test_protected_route_with_non_bearer_returns_401(app: FastAPI) -> None:
    """Authorization present but not ``Bearer …`` → 401."""
    _register_protected_route(app)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/_protected_probe",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "auth.missing_token"


def test_protected_route_with_empty_bearer_returns_401(app: FastAPI) -> None:
    """``Bearer <empty>`` → 401 with ``auth.missing_token``."""
    _register_protected_route(app)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/_protected_probe",
            headers={"Authorization": "Bearer "},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "auth.missing_token"


def test_protected_route_with_malformed_token_returns_401(app: FastAPI) -> None:
    """Garbage token → JWT decode fails → 401 ``auth.invalid_token``."""
    _register_protected_route(app)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/_protected_probe",
            headers={"Authorization": "Bearer not.a.jwt"},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_token"

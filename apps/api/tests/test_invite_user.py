"""Tests for ``POST /api/v1/admin/users`` -- founder-invited accounts.

Reuses the admin-router isolation pattern from ``test_admin.py``: a
mini-FastAPI mounts just the admin router and swaps out ``require_admin``
so we can exercise the 200 / 201 / 403 / 401 paths without spinning up
``ClerkAuthMiddleware``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from api.routers import admin as admin_router_module
from api.routers.admin import (
    StubAdminProvider,
    get_admin_provider,
    require_admin,
)
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

_ADMIN_USER_ID = "user_admin_invite_test"


@pytest.fixture(autouse=True)
def _reset_stub_provider() -> Iterator[None]:
    """Fresh seeded admin provider per test."""
    StubAdminProvider.reset()
    yield
    StubAdminProvider.reset()


def _build_app(role: str | None) -> FastAPI:
    """Same harness as test_admin.py -- role drives require_admin override."""
    stub_app = FastAPI()
    stub_app.include_router(admin_router_module.router, prefix="/api/v1")
    provider = StubAdminProvider()
    stub_app.dependency_overrides[get_admin_provider] = lambda: provider

    if role == "admin":
        stub_app.dependency_overrides[require_admin] = lambda: _ADMIN_USER_ID
    elif role == "user":

        def _forbidden() -> str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required",
            )

        stub_app.dependency_overrides[require_admin] = _forbidden
    else:

        def _unauthorized() -> str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user context missing",
                headers={"WWW-Authenticate": "Bearer"},
            )

        stub_app.dependency_overrides[require_admin] = _unauthorized

    return stub_app


@pytest.fixture
def admin_client() -> Iterator[TestClient]:
    with TestClient(_build_app(role="admin")) as client:
        yield client


@pytest.fixture
def regular_client() -> Iterator[TestClient]:
    with TestClient(_build_app(role="user")) as client:
        yield client


def test_invite_user_as_admin_returns_201(admin_client: TestClient) -> None:
    """Admin invite creates a status=invited record and returns 201."""
    response = admin_client.post(
        "/api/v1/admin/users",
        json={
            "email": "newalpha@sportslab.example.com",
            "plan": "alpha",
            "notes": "Met at Cambridge analytics meetup",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "newalpha@sportslab.example.com"
    assert body["plan"] == "alpha"
    assert body["status"] == "invited"
    assert body["role"] == "user"
    assert body["mrrEur"] == 0.0
    assert body["betsTracked"] == 0
    assert body["id"].startswith("user_invited_")


def test_invite_user_defaults_to_alpha_plan(admin_client: TestClient) -> None:
    """Omitting ``plan`` applies the alpha default."""
    response = admin_client.post(
        "/api/v1/admin/users",
        json={"email": "defaulted@sportslab.example.com"},
    )
    assert response.status_code == 201
    assert response.json()["plan"] == "alpha"


def test_invite_user_duplicate_email_returns_409(admin_client: TestClient) -> None:
    """Inviting the same email twice surfaces 409, not 500."""
    first = admin_client.post(
        "/api/v1/admin/users",
        json={"email": "dup@sportslab.example.com"},
    )
    assert first.status_code == 201

    second = admin_client.post(
        "/api/v1/admin/users",
        json={"email": "dup@sportslab.example.com"},
    )
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"].lower()


def test_invite_user_as_regular_user_returns_403(regular_client: TestClient) -> None:
    """Non-admin callers are forbidden from inviting users."""
    response = regular_client.post(
        "/api/v1/admin/users",
        json={"email": "attempted@sportslab.example.com"},
    )
    assert response.status_code == 403


def test_invite_user_rejects_invalid_email(admin_client: TestClient) -> None:
    """Pydantic ``EmailStr`` validation fires before the provider does."""
    response = admin_client.post(
        "/api/v1/admin/users",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422

"""Tests for ``POST /api/v1/admin/model/promote``.

Same isolation pattern as ``test_admin.py`` / ``test_invite_user.py``:
the admin router is mounted in a mini-FastAPI, ``require_admin`` is
dependency-overridden, and the stub provider is reset between tests.
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

_ADMIN_USER_ID = "user_admin_promote_test"


@pytest.fixture(autouse=True)
def _reset_stub_provider() -> Iterator[None]:
    StubAdminProvider.reset()
    yield
    StubAdminProvider.reset()


def _build_app(role: str | None) -> FastAPI:
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


def test_promote_staging_as_admin_returns_200(admin_client: TestClient) -> None:
    """Happy path: staging candidate is promoted, system reflects the swap."""
    response = admin_client.post("/api/v1/admin/model/promote")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "v2.5.0-rc1"
    assert body["status"] == "deployed"
    # camelCase on the wire.
    assert "eceOverall" in body
    assert "deployedAt" in body

    # /admin/system now shows the promoted model as live.
    system = admin_client.get("/api/v1/admin/system").json()
    assert system["model"]["version"] == "v2.5.0-rc1"


def test_promote_staging_empty_slot_returns_409(admin_client: TestClient) -> None:
    """Second promote with nothing staged is a 409, not a silent re-promote."""
    first = admin_client.post("/api/v1/admin/model/promote")
    assert first.status_code == 200

    second = admin_client.post("/api/v1/admin/model/promote")
    assert second.status_code == 409
    assert "staging" in second.json()["detail"].lower()


def test_promote_staging_as_regular_user_returns_403(regular_client: TestClient) -> None:
    """Only admins may promote models."""
    response = regular_client.post("/api/v1/admin/model/promote")
    assert response.status_code == 403

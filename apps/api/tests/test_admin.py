"""Tests for ``/api/v1/admin/*`` endpoints.

Admin routes layer a second check on top of Clerk auth: the caller must
have ``user_role == "admin"`` on ``request.state``. The current
:class:`ClerkAuthMiddleware` doesn't inject roles yet (see the TODO in
:func:`require_admin`), so the tests go direct-to-router via
``dependency_overrides`` -- the same pattern as ``test_users.py``.

End-to-end 401 coverage (no Bearer token at all) uses the real app with
``ClerkAuthMiddleware`` still in place, so the auth-transport path stays
exercised.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from api.config import Settings
from api.routers import admin as admin_router_module
from api.routers.admin import (
    StubAdminProvider,
    get_admin_provider,
    require_admin,
)
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

_ADMIN_USER_ID = "user_admin_test"
_REGULAR_USER_ID = "user_regular_test"
_EXISTING_USER_ID = "user_alpha_abc"  # Seeded by StubAdminProvider.


@pytest.fixture(autouse=True)
def _reset_stub_provider() -> Iterator[None]:
    """Each test starts with a freshly seeded admin provider."""
    StubAdminProvider.reset()
    yield
    StubAdminProvider.reset()


def _build_app(role: str | None) -> FastAPI:
    """Build an admin-router app with ``require_admin`` overridden.

    ``role`` drives the override:

    - ``"admin"``   -> dependency returns the admin user id (200 path)
    - ``"user"``    -> dependency raises 403 (forbidden)
    - ``None``      -> dependency raises 401 (unauthenticated)
    """
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
    else:  # Unauthenticated.

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
    """TestClient whose dependency stack treats the caller as admin."""
    with TestClient(_build_app(role="admin")) as client:
        yield client


@pytest.fixture
def regular_client() -> Iterator[TestClient]:
    """TestClient whose dependency stack yields 403 on every admin route."""
    with TestClient(_build_app(role="user")) as client:
        yield client


@pytest.fixture
def anon_client() -> Iterator[TestClient]:
    """TestClient whose dependency stack yields 401 on every admin route."""
    with TestClient(_build_app(role=None)) as client:
        yield client


def test_list_users_as_admin_200(admin_client: TestClient) -> None:
    """Admin caller gets the full list in newest-first order."""
    response = admin_client.get("/api/v1/admin/users")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 4
    # camelCase on the wire.
    assert "mrrEur" in payload[0]
    assert "betsTracked" in payload[0]
    # Newest join first.
    joined = [item["joinedAt"] for item in payload]
    assert joined == sorted(joined, reverse=True)


def test_list_users_as_non_admin_403(regular_client: TestClient) -> None:
    """Non-admin authenticated users are explicitly forbidden."""
    response = regular_client.get("/api/v1/admin/users")
    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()


def test_list_users_unauthorized_401(anon_client: TestClient) -> None:
    """No user context -> 401 with Bearer challenge."""
    response = anon_client.get("/api/v1/admin/users")
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_patch_user_as_admin(admin_client: TestClient) -> None:
    """Admin PATCH flips plan + status without clobbering other fields."""
    before = admin_client.get("/api/v1/admin/users").json()
    target = next(item for item in before if item["id"] == _EXISTING_USER_ID)
    original_email = target["email"]
    original_bets = target["betsTracked"]

    response = admin_client.patch(
        f"/api/v1/admin/users/{_EXISTING_USER_ID}",
        json={"plan": "pro", "status": "active"},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["plan"] == "pro"
    assert updated["status"] == "active"
    # Untouched fields survived the patch.
    assert updated["email"] == original_email
    assert updated["betsTracked"] == original_bets


def test_patch_unknown_user_returns_404(admin_client: TestClient) -> None:
    """Patching a non-existent user id surfaces 404, not 500."""
    response = admin_client.patch(
        "/api/v1/admin/users/user_does_not_exist",
        json={"plan": "pro"},
    )
    assert response.status_code == 404


def test_get_system_returns_composite(admin_client: TestClient) -> None:
    """``/admin/system`` returns pipelines + model + infra in one payload."""
    response = admin_client.get("/api/v1/admin/system")
    assert response.status_code == 200
    body = response.json()
    assert "pipelines" in body
    assert "model" in body
    assert "infra" in body
    assert body["overallStatus"] in {"healthy", "degraded", "down"}
    assert len(body["pipelines"]) >= 1
    assert body["model"]["version"].startswith("v")
    assert body["infra"][0]["host"]


def test_rollback_model_returns_before_after(admin_client: TestClient) -> None:
    """Rollback records the swap and advances the deployed version."""
    system_before = admin_client.get("/api/v1/admin/system").json()
    previous_version = system_before["model"]["version"]

    response = admin_client.post(
        "/api/v1/admin/model/rollback",
        json={"targetVersion": "v2.3.9"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rolledBackFrom"] == previous_version
    assert body["rolledBackTo"] == "v2.3.9"
    assert "at" in body

    # Rolling back to the same version is a 409.
    conflict = admin_client.post(
        "/api/v1/admin/model/rollback",
        json={"targetVersion": "v2.3.9"},
    )
    assert conflict.status_code == 409


def test_rollback_rejects_empty_target(admin_client: TestClient) -> None:
    """Empty ``targetVersion`` never reaches the provider (schema 422)."""
    response = admin_client.post(
        "/api/v1/admin/model/rollback",
        json={"targetVersion": ""},
    )
    # Pydantic min_length=1 -> 422 at validation; no 400 needed.
    assert response.status_code == 422


def test_trigger_retrain_returns_queued(admin_client: TestClient) -> None:
    """Retrain endpoint returns a synthetic queued-job payload."""
    response = admin_client.post("/api/v1/admin/model/retrain")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["jobId"].startswith("retrain_")


def test_admin_unauthorized_without_token(client: TestClient) -> None:
    """No Clerk JWT -> middleware rejects with 401 before the router runs.

    Uses the shared ``client`` fixture (full app + ClerkAuthMiddleware) to
    exercise the real auth transport path end-to-end, just like
    ``test_users_unauthorized_without_token``.
    """
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_require_admin_dev_allows_missing_role() -> None:
    """Dev-mode escape hatch: authenticated-but-roleless user gets through.

    This exists because ``ClerkAuthMiddleware`` doesn't inject roles yet.
    Once role lookup lands (see the TODO in the router) this test flips
    to assert a 403 instead.
    """
    from starlette.requests import Request

    scope = {"type": "http", "headers": [], "state": {}}
    request = Request(scope)  # type: ignore[arg-type]
    request.state.user_id = "user_dev_xyz"
    # No user_role set at all.

    dev_settings = Settings(env="dev")
    assert require_admin(request, dev_settings) == "user_dev_xyz"


def test_require_admin_prod_requires_role() -> None:
    """In non-dev envs a missing / wrong role raises 403."""
    from starlette.requests import Request

    scope = {"type": "http", "headers": [], "state": {}}
    request = Request(scope)  # type: ignore[arg-type]
    request.state.user_id = "user_prod_xyz"
    request.state.user_role = "user"

    prod_settings = Settings(env="prod")
    with pytest.raises(HTTPException) as excinfo:
        require_admin(request, prod_settings)
    assert excinfo.value.status_code == 403

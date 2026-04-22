"""Tests for ``/api/v1/users/me/alerts/*`` endpoints.

Direct-to-router isolation (same pattern as ``test_users.py`` and
``test_admin.py``): we build a mini-FastAPI without
``ClerkAuthMiddleware`` and override ``get_current_user_id`` so each
test sees deterministic per-user state.

End-to-end 401 coverage (no Bearer token) uses the shared ``client``
fixture from ``conftest.py`` so the real auth path still runs.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from api.routers import alerts as alerts_router_module
from api.routers.alerts import (
    StubAlertsProvider,
    get_alerts_provider,
)
from api.routers.users import get_current_user_id
from fastapi import FastAPI
from fastapi.testclient import TestClient

_TEST_USER_ID = "user_alerts_test"


@pytest.fixture(autouse=True)
def _reset_stub_provider() -> Iterator[None]:
    """Fresh per-test alerts state -- class-backed stub needs explicit reset."""
    StubAlertsProvider.reset()
    yield
    StubAlertsProvider.reset()


@pytest.fixture
def authed_client() -> Iterator[TestClient]:
    """Direct-to-router TestClient with fixed user id + stub provider."""
    stub_app = FastAPI()
    stub_app.include_router(alerts_router_module.router, prefix="/api/v1")
    stub_app.dependency_overrides[get_current_user_id] = lambda: _TEST_USER_ID
    provider = StubAlertsProvider()
    stub_app.dependency_overrides[get_alerts_provider] = lambda: provider
    with TestClient(stub_app) as client:
        yield client


def test_list_alerts_returns_seeded_fixture(authed_client: TestClient) -> None:
    """First call seeds four alerts, newest first, with camelCase wire shape."""
    response = authed_client.get("/api/v1/users/me/alerts")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 4
    # camelCase on the wire.
    first = payload[0]
    assert "createdAt" in first
    assert "readAt" in first
    assert first["severity"] in {"info", "warning", "critical"}
    # Newest first.
    created = [entry["createdAt"] for entry in payload]
    assert created == sorted(created, reverse=True)


def test_mark_read_sets_read_at(authed_client: TestClient) -> None:
    """PATCH /read marks one alert read; subsequent list reflects it."""
    listing = authed_client.get("/api/v1/users/me/alerts").json()
    unread = next(entry for entry in listing if entry["readAt"] is None)
    alert_id = unread["id"]

    response = authed_client.patch(f"/api/v1/users/me/alerts/{alert_id}/read")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == alert_id
    assert body["readAt"] is not None

    # The listing now reflects the change.
    refreshed = authed_client.get("/api/v1/users/me/alerts").json()
    target = next(entry for entry in refreshed if entry["id"] == alert_id)
    assert target["readAt"] == body["readAt"]


def test_mark_read_idempotent(authed_client: TestClient) -> None:
    """Marking an already-read alert preserves the original timestamp."""
    listing = authed_client.get("/api/v1/users/me/alerts").json()
    unread = next(entry for entry in listing if entry["readAt"] is None)
    alert_id = unread["id"]

    first = authed_client.patch(f"/api/v1/users/me/alerts/{alert_id}/read").json()
    second = authed_client.patch(f"/api/v1/users/me/alerts/{alert_id}/read").json()
    assert first["readAt"] == second["readAt"]


def test_mark_read_unknown_alert_returns_404(authed_client: TestClient) -> None:
    """Unknown alert id is a 404 (not a silent success)."""
    response = authed_client.patch("/api/v1/users/me/alerts/does-not-exist/read")
    assert response.status_code == 404


def test_mark_all_read_returns_204(authed_client: TestClient) -> None:
    """POST /read-all clears every unread flag and returns 204."""
    response = authed_client.post("/api/v1/users/me/alerts/read-all")
    assert response.status_code == 204
    assert response.content == b""

    refreshed = authed_client.get("/api/v1/users/me/alerts").json()
    assert all(entry["readAt"] is not None for entry in refreshed)


def test_mark_all_read_idempotent(authed_client: TestClient) -> None:
    """Second call (nothing left to flip) is still 204."""
    first = authed_client.post("/api/v1/users/me/alerts/read-all")
    second = authed_client.post("/api/v1/users/me/alerts/read-all")
    assert first.status_code == 204
    assert second.status_code == 204


def test_alerts_unauthorized_without_token(client: TestClient) -> None:
    """Full app with ClerkAuthMiddleware -> 401 on anonymous caller."""
    listing = client.get("/api/v1/users/me/alerts")
    assert listing.status_code == 401
    assert listing.headers.get("WWW-Authenticate") == "Bearer"

    patch = client.patch("/api/v1/users/me/alerts/any/read")
    assert patch.status_code == 401

    post = client.post("/api/v1/users/me/alerts/read-all")
    assert post.status_code == 401

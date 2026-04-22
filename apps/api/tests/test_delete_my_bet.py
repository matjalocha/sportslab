"""Tests for ``DELETE /api/v1/users/me/bets/{bet_id}``.

Follows the direct-to-router pattern from ``test_users.py``: we build a
mini FastAPI app without ``ClerkAuthMiddleware`` and override
``get_current_user_id`` so the router logic is isolated from auth
transport. Full 401 coverage for the users surface lives in
``test_users.py::test_users_unauthorized_without_token``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from api.routers import users as users_router_module
from api.routers.users import (
    StubUsersProvider,
    get_current_user_id,
    get_users_provider,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

_TEST_USER_ID = "user_test_delete"


@pytest.fixture(autouse=True)
def _reset_stub_provider() -> Iterator[None]:
    """Fresh per-test provider state -- matches test_users.py."""
    StubUsersProvider.reset()
    yield
    StubUsersProvider.reset()


@pytest.fixture
def authed_client() -> Iterator[TestClient]:
    """Direct-to-router TestClient with fixed user id + stub provider."""
    stub_app = FastAPI()
    stub_app.include_router(users_router_module.router, prefix="/api/v1")
    stub_app.dependency_overrides[get_current_user_id] = lambda: _TEST_USER_ID
    provider = StubUsersProvider()
    stub_app.dependency_overrides[get_users_provider] = lambda: provider
    with TestClient(stub_app) as client:
        yield client


def _onboard(authed_client: TestClient) -> None:
    authed_client.post(
        "/api/v1/users/onboard",
        json={
            "email": "delete@sportslab.example.com",
            "telegramHandle": "@deletetest",
            "bankrollTier": "1k_5k",
            "experienceLevel": "intermediate",
        },
    )


def _create_bet(authed_client: TestClient) -> str:
    response = authed_client.post(
        "/api/v1/users/me/bets",
        json={
            "matchId": "match_del_1",
            "market": "1X2",
            "selection": "home",
            "stakeEur": 20.0,
            "odds": 1.9,
            "bookmaker": "Pinnacle",
        },
    )
    assert response.status_code == 201
    bet_id = response.json()["id"]
    assert isinstance(bet_id, str) and bet_id
    return bet_id


def test_delete_my_bet_existing_returns_204(authed_client: TestClient) -> None:
    """Deleting a present bet returns 204 and drops it from the listing."""
    _onboard(authed_client)
    bet_id = _create_bet(authed_client)

    response = authed_client.delete(f"/api/v1/users/me/bets/{bet_id}")
    assert response.status_code == 204
    assert response.content == b""

    listing = authed_client.get("/api/v1/users/me/bets")
    assert listing.status_code == 200
    assert listing.json() == []


def test_delete_my_bet_idempotent_returns_204(authed_client: TestClient) -> None:
    """Second delete (or delete of an unknown id) is still 204, not 404."""
    _onboard(authed_client)
    bet_id = _create_bet(authed_client)

    first = authed_client.delete(f"/api/v1/users/me/bets/{bet_id}")
    second = authed_client.delete(f"/api/v1/users/me/bets/{bet_id}")
    ghost = authed_client.delete("/api/v1/users/me/bets/does-not-exist")

    assert first.status_code == 204
    assert second.status_code == 204
    assert ghost.status_code == 204


def test_delete_my_bet_unauthorized_without_token(client: TestClient) -> None:
    """No Clerk JWT -> middleware rejects with 401 before router runs."""
    response = client.delete("/api/v1/users/me/bets/any_id")
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"

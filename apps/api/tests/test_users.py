"""Tests for ``/api/v1/users/*`` endpoints.

The ``authed_client`` fixture builds a mini-FastAPI that mounts just the
users router without ``ClerkAuthMiddleware`` and injects a fixed user id
via a dependency override -- full JWT validation is covered end-to-end
in ``test_clerk_auth.py`` and by :func:`test_users_unauthorized_without_token`
below, which uses the real app. This keeps router logic tests decoupled
from auth transport concerns.

:class:`StubUsersProvider` is class-backed, so we reset state between
tests for order independence.
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

_TEST_USER_ID = "user_test_abc123"


@pytest.fixture(autouse=True)
def _reset_stub_provider() -> Iterator[None]:
    """Ensure each test starts with an empty in-memory provider."""
    StubUsersProvider.reset()
    yield
    StubUsersProvider.reset()


@pytest.fixture
def authed_client() -> Iterator[TestClient]:
    """TestClient against an app with auth stripped -- router logic only.

    Using the real ``create_app`` would drag in ``ClerkAuthMiddleware``,
    which rejects requests before our ``get_current_user_id`` override
    runs. A minimal app that mounts only the users router lets us test
    router behaviour in isolation.
    """
    stub_app = FastAPI()
    stub_app.include_router(users_router_module.router, prefix="/api/v1")
    stub_app.dependency_overrides[get_current_user_id] = lambda: _TEST_USER_ID
    provider = StubUsersProvider()
    stub_app.dependency_overrides[get_users_provider] = lambda: provider
    with TestClient(stub_app) as client:
        yield client


def _onboard_payload() -> dict[str, str]:
    return {
        "email": "alpha@sportslab.example.com",
        "telegramHandle": "@alpha_tester",
        "bankrollTier": "1k_5k",
        "experienceLevel": "intermediate",
    }


def test_onboard_creates_user(authed_client: TestClient) -> None:
    """First call creates the profile with tier-derived bankroll default."""
    response = authed_client.post("/api/v1/users/onboard", json=_onboard_payload())
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == _TEST_USER_ID
    assert payload["email"] == "alpha@sportslab.example.com"
    assert payload["plan"] == "alpha"
    assert payload["role"] == "user"
    # Mid-point of the 1k-5k tier.
    assert payload["bankrollEur"] == 2500.0


def test_onboard_idempotent(authed_client: TestClient) -> None:
    """Calling onboard twice returns the same profile, unchanged."""
    first = authed_client.post("/api/v1/users/onboard", json=_onboard_payload())
    second_payload = _onboard_payload() | {"bankrollTier": "25k_plus"}
    second = authed_client.post("/api/v1/users/onboard", json=second_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    # Idempotency: the tier change on the second call is ignored.
    assert first.json() == second.json()
    assert second.json()["bankrollEur"] == 2500.0


def test_get_me_returns_profile(authed_client: TestClient) -> None:
    """After onboarding, GET /users/me returns the same profile."""
    authed_client.post("/api/v1/users/onboard", json=_onboard_payload())
    response = authed_client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json()["id"] == _TEST_USER_ID


def test_get_me_not_onboarded_returns_404(authed_client: TestClient) -> None:
    """Authenticated but never-onboarded user -> 404, frontend sends to wizard."""
    response = authed_client.get("/api/v1/users/me")
    assert response.status_code == 404
    assert "onboard" in response.json()["detail"].lower()


def test_patch_me_partial_update(authed_client: TestClient) -> None:
    """Only explicitly-set fields change; others are preserved."""
    authed_client.post("/api/v1/users/onboard", json=_onboard_payload())
    patch_response = authed_client.patch(
        "/api/v1/users/me",
        json={"bankrollEur": 9999.0, "leaguesSelected": ["EPL", "La Liga"]},
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["bankrollEur"] == 9999.0
    assert body["leaguesSelected"] == ["EPL", "La Liga"]
    # Untouched fields survived.
    assert body["email"] == "alpha@sportslab.example.com"
    assert body["telegramHandle"] == "@alpha_tester"
    assert body["oddsFormat"] == "decimal"


def test_patch_me_before_onboard_returns_404(authed_client: TestClient) -> None:
    """PATCH without a prior profile is a 404, not an implicit create."""
    response = authed_client.patch("/api/v1/users/me", json={"bankrollEur": 100.0})
    assert response.status_code == 404


def test_get_my_bets_empty_list(authed_client: TestClient) -> None:
    """Newly-onboarded user has no bets; endpoint returns ``[]``, not 404."""
    authed_client.post("/api/v1/users/onboard", json=_onboard_payload())
    response = authed_client.get("/api/v1/users/me/bets")
    assert response.status_code == 200
    assert response.json() == []


def test_post_my_bet_creates_entry(authed_client: TestClient) -> None:
    """POST /users/me/bets appends a pending bet with server-assigned id."""
    authed_client.post("/api/v1/users/onboard", json=_onboard_payload())
    bet_body = {
        "matchId": "match_123",
        "market": "1X2",
        "selection": "home",
        "stakeEur": 50.0,
        "odds": 2.1,
        "bookmaker": "Pinnacle",
    }
    create_response = authed_client.post("/api/v1/users/me/bets", json=bet_body)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"]
    assert created["outcome"] == "pending"
    assert created["pnlEur"] is None
    # Stub can't attribute to the pick catalog -- A-09 scope.
    assert created["followsModel"] is False

    listing = authed_client.get("/api/v1/users/me/bets")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_post_my_bet_before_onboard_returns_404(authed_client: TestClient) -> None:
    """Bet-tracking requires a profile; create-bet without it is a 404."""
    response = authed_client.post(
        "/api/v1/users/me/bets",
        json={
            "matchId": "m1",
            "market": "1X2",
            "selection": "draw",
            "stakeEur": 10.0,
            "odds": 3.2,
            "bookmaker": "Bet365",
        },
    )
    assert response.status_code == 404


def test_users_unauthorized_without_token(client: TestClient) -> None:
    """No Clerk JWT -> middleware rejects with 401 before the router runs.

    Uses the base ``client`` fixture (no dependency override), so the real
    ``ClerkAuthMiddleware`` path is exercised end-to-end.
    """
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"

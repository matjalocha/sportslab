"""Tests for ``/api/v1/predictions/*`` routes.

The production routes sit behind Clerk auth. These tests bypass the
JWT check by overriding ``ClerkAuthMiddleware`` only where the test
asserts the happy path — the 401 test intentionally skips the override
to exercise the real middleware.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from api.config import Settings, get_settings
from api.main import create_app
from api.middleware.clerk_auth import ClerkAuthMiddleware
from api.models.predictions import BetRecommendation, BetResult, Match, Team
from api.routers.predictions import (
    PredictionsProvider,
    StubPredictionsProvider,
    get_predictions_provider,
)
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.middleware.base import RequestResponseEndpoint

_WARSAW = ZoneInfo("Europe/Warsaw")


async def _bypass_dispatch(
    self: ClerkAuthMiddleware,
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Drop-in replacement for ``ClerkAuthMiddleware.dispatch`` that lets
    every request through. Used only for routes that test business logic,
    not the auth boundary itself.
    """
    request.state.user_id = "user_test"
    request.state.claims = {"sub": "user_test"}
    return await call_next(request)


@pytest.fixture
def authed_app(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Iterator[FastAPI]:
    """Variant of the shared ``app`` fixture with Clerk auth stubbed out."""
    monkeypatch.setattr(ClerkAuthMiddleware, "dispatch", _bypass_dispatch)
    get_settings.cache_clear()
    application = create_app(settings=settings)
    application.dependency_overrides[get_settings] = lambda: settings
    try:
        yield application
    finally:
        application.dependency_overrides.clear()
        get_settings.cache_clear()


@pytest.fixture
def authed_client(authed_app: FastAPI) -> Iterator[TestClient]:
    """TestClient that skips Clerk. ``follow_redirects=False`` so the 302
    test can assert the redirect location without the client transparently
    following it."""
    with TestClient(authed_app, follow_redirects=False) as test_client:
        yield test_client


def test_get_predictions_returns_200_with_list(authed_client: TestClient) -> None:
    """Happy path: picks endpoint returns a non-empty array for any date."""
    yesterday = (datetime.now(_WARSAW) - timedelta(days=1)).date().isoformat()
    response = authed_client.get(f"/api/v1/predictions/{yesterday}")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 1


def test_get_predictions_response_shape(authed_client: TestClient) -> None:
    """Response payload must use camelCase aliases (frontend contract)."""
    target = (datetime.now(_WARSAW) - timedelta(days=1)).date().isoformat()
    response = authed_client.get(f"/api/v1/predictions/{target}")
    assert response.status_code == 200
    first = response.json()[0]

    expected_camel_keys = {
        "modelProbability",
        "bookmakerProbability",
        "edgePercent",
        "bestOdds",
        "kellyStake",
        "kellyFraction",
    }
    assert expected_camel_keys.issubset(first.keys()), (
        f"Missing camelCase keys: {expected_camel_keys - set(first.keys())}"
    )
    # snake_case must NOT leak — otherwise the frontend type-check breaks.
    assert "model_probability" not in first
    assert "best_odds" not in first

    # Nested Match / Team also follow camelCase.
    assert "kickoffUtc" in first["match"]
    assert "shortName" in first["match"]["home"]


def test_get_latest_redirects_302(authed_client: TestClient) -> None:
    """``/latest`` redirects to today's date in Europe/Warsaw."""
    response = authed_client.get("/api/v1/predictions/latest")
    assert response.status_code == 302
    today_iso = datetime.now(_WARSAW).date().isoformat()
    assert response.headers["location"] == f"/api/v1/predictions/{today_iso}"


def test_get_results_future_date_returns_425(authed_client: TestClient) -> None:
    """Results for today or a future date are 425 Too Early."""
    future = (datetime.now(_WARSAW) + timedelta(days=7)).date().isoformat()
    response = authed_client.get(f"/api/v1/predictions/{future}/results")
    assert response.status_code == 425


def test_get_results_unauthorized_returns_401(client: TestClient) -> None:
    """No Bearer token → 401 from ClerkAuthMiddleware.

    Uses the un-stubbed ``client`` fixture so the real middleware runs.
    """
    yesterday = (datetime.now(_WARSAW) - timedelta(days=1)).date().isoformat()
    response = client.get(f"/api/v1/predictions/{yesterday}/results")
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_get_predictions_dependency_override(authed_app: FastAPI) -> None:
    """Provider injection via ``dependency_overrides`` works end-to-end."""

    class _EmptyProvider(PredictionsProvider):
        async def get_predictions(self, target_date: date) -> list[BetRecommendation]:
            return []

        async def get_results(self, target_date: date) -> list[BetResult]:
            return []

    authed_app.dependency_overrides[get_predictions_provider] = _EmptyProvider
    with TestClient(authed_app) as test_client:
        yesterday = (datetime.now(_WARSAW) - timedelta(days=1)).date().isoformat()
        response = test_client.get(f"/api/v1/predictions/{yesterday}")
        assert response.status_code == 404
        assert response.json()["detail"] == "No predictions for this date"


def test_stub_provider_produces_valid_models() -> None:
    """Sanity: StubPredictionsProvider output round-trips through Pydantic."""
    stub = StubPredictionsProvider()
    yesterday = date.today() - timedelta(days=1)

    import asyncio

    picks = asyncio.run(stub.get_predictions(yesterday))
    assert len(picks) == 5
    assert all(isinstance(pick, BetRecommendation) for pick in picks)

    # Each Match is fully typed (catches accidental dict leakage).
    for pick in picks:
        assert isinstance(pick.match, Match)
        assert isinstance(pick.match.home, Team)
        assert 0.0 <= pick.model_probability <= 1.0
        assert pick.best_odds > 1.0
        assert pick.published.tzinfo is UTC

"""Tests for ``/api/v1/track-record/*`` routes.

Like ``test_predictions``, the happy-path tests override
``ClerkAuthMiddleware`` so we can exercise the business logic end to
end. A single boundary test uses the un-stubbed ``client`` fixture to
confirm the real middleware still rejects unauthenticated requests.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from api.config import Settings, get_settings
from api.main import create_app
from api.middleware.clerk_auth import ClerkAuthMiddleware
from api.routers.track_record import (
    StubTrackRecordProvider,
    TrackRecordProvider,
    get_track_record_provider,
)
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.middleware.base import RequestResponseEndpoint


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
    """TestClient that skips Clerk auth for happy-path tests."""
    with TestClient(authed_app) as test_client:
        yield test_client


def test_get_track_record_returns_200_with_stats(authed_client: TestClient) -> None:
    """Happy path: aggregate endpoint returns a well-formed object."""
    response = authed_client.get("/api/v1/track-record")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload["bets"] > 0
    assert 0.0 <= payload["winRate"] <= 1.0


def test_get_track_record_response_shape_camelcase(authed_client: TestClient) -> None:
    """Response payload must use camelCase aliases (frontend contract)."""
    response = authed_client.get("/api/v1/track-record")
    assert response.status_code == 200
    payload = response.json()

    expected_camel_keys = {
        "winRate",
        "roiPercent",
        "clvPercent",
        "profitEur",
        "avgEdgePercent",
        "maxDrawdownPercent",
        "currentStreakType",
        "currentStreakCount",
        "sinceDate",
    }
    assert expected_camel_keys.issubset(payload.keys()), (
        f"Missing camelCase keys: {expected_camel_keys - set(payload.keys())}"
    )
    # snake_case must NOT leak — otherwise the frontend type-check breaks.
    for forbidden in ("win_rate", "roi_percent", "profit_eur", "since_date"):
        assert forbidden not in payload


def test_get_track_record_with_since_filter(authed_client: TestClient) -> None:
    """``?since=`` narrows the window and is echoed back in ``sinceDate``."""
    response = authed_client.get("/api/v1/track-record?since=2025-11-01")
    assert response.status_code == 200
    payload = response.json()
    assert payload["sinceDate"] == "2025-11-01"
    # The stub's last two months contribute 46 + 39 = 85 bets.
    assert payload["bets"] == 85


def test_get_monthly_returns_list(authed_client: TestClient) -> None:
    """Monthly endpoint returns the full list, oldest first, camelCase keys."""
    response = authed_client.get("/api/v1/track-record/monthly")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 6
    assert payload[0]["month"] < payload[-1]["month"]
    first = payload[0]
    assert {"month", "bets", "winRate", "roiPercent", "clvPercent", "profitEur"} <= first.keys()


def test_get_equity_curve_default_180_days(authed_client: TestClient) -> None:
    """With no query params the curve spans 180 days ending today."""
    response = authed_client.get("/api/v1/track-record/equity-curve")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 180
    last_date = date.fromisoformat(payload[-1]["date"])
    first_date = date.fromisoformat(payload[0]["date"])
    assert last_date == date.today()
    assert (last_date - first_date).days == 179
    # Bankroll starts near 10k (allow small wobble) and the final P&L is positive.
    assert payload[0]["bankrollEur"] > 0
    assert payload[-1]["pnlEur"] > 0


def test_get_equity_curve_since_until_params(authed_client: TestClient) -> None:
    """Explicit ``since`` / ``until`` window is honoured inclusively."""
    since = "2025-06-01"
    until = "2025-06-30"
    response = authed_client.get(
        f"/api/v1/track-record/equity-curve?since={since}&until={until}"
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 30
    assert payload[0]["date"] == since
    assert payload[-1]["date"] == until


def test_get_by_league_sorted_by_bets_desc(authed_client: TestClient) -> None:
    """Leagues are ordered from most-active to least-active."""
    response = authed_client.get("/api/v1/track-record/by-league")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 3
    bets_sequence = [row["bets"] for row in payload]
    assert bets_sequence == sorted(bets_sequence, reverse=True)
    assert {"league", "bets", "winRate", "roiPercent", "clvPercent", "profitEur"} <= set(
        payload[0].keys()
    )


def test_track_record_unauthorized_returns_401(client: TestClient) -> None:
    """No Bearer token → 401 from ClerkAuthMiddleware.

    Uses the un-stubbed ``client`` fixture so the real middleware runs.
    """
    response = client.get("/api/v1/track-record")
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_get_track_record_dependency_override(authed_app: FastAPI) -> None:
    """Provider injection via ``dependency_overrides`` works end-to-end."""

    class _FixedProvider(TrackRecordProvider):
        async def get_stats(self, since: date | None) -> object:  # type: ignore[override]
            stub = StubTrackRecordProvider()
            return await stub.get_stats(date(2025, 12, 1))

        async def get_monthly(self) -> list[object]:  # type: ignore[override]
            return []

        async def get_equity_curve(
            self, since: date | None, until: date | None
        ) -> list[object]:  # type: ignore[override]
            stub = StubTrackRecordProvider()
            # Only return 5 days regardless of inputs — proves override is live.
            reference = until or date(2025, 12, 31)
            return await stub.get_equity_curve(reference - timedelta(days=4), reference)

        async def get_by_league(self) -> list[object]:  # type: ignore[override]
            return []

    authed_app.dependency_overrides[get_track_record_provider] = _FixedProvider
    with TestClient(authed_app) as test_client:
        monthly = test_client.get("/api/v1/track-record/monthly")
        assert monthly.status_code == 200
        assert monthly.json() == []

        equity = test_client.get("/api/v1/track-record/equity-curve")
        assert equity.status_code == 200
        assert len(equity.json()) == 5

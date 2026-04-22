"""Cross-router end-to-end user journeys.

Each test here chains multiple endpoints across routers. Unlike the
per-router suites which mount a single router on a throwaway FastAPI
app, these run against the full :func:`api.main.create_app` so middleware,
dependency wiring, and router prefixes all match production.

The journeys cover:

* New-user onboarding (users router) and profile mutation round-trip.
* Predictions -> my-bets flow (predictions + users routers).
* Public endpoint bypass of Clerk auth (health + webhooks + openapi).
* Protected endpoint auth enforcement (401 without Bearer).
* Admin RBAC (403 for role=user, 200 for role=admin) across /admin/*.
* Webhook idempotency across providers (Clerk + Stripe) on the same app.
* Track-record ``?since`` filter consistency between windowed and
  unbounded queries.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from svix.webhooks import Webhook as SvixWebhook
from tests.e2e.conftest import (
    E2E_ADMIN_ID,
    E2E_CLERK_WEBHOOK_SECRET,
    E2E_STRIPE_WEBHOOK_SECRET,
    E2E_USER_ID,
)

_WARSAW = ZoneInfo("Europe/Warsaw")


def _onboard_payload() -> dict[str, str]:
    """Canonical onboard body used by the journey tests."""
    return {
        "email": "journey@sportslab.example.com",
        "telegramHandle": "@journey_tester",
        "bankrollTier": "1k_5k",
        "experienceLevel": "intermediate",
    }


def _stripe_sign(body: bytes, secret: str, timestamp: int | None = None) -> str:
    """Reuse the same Stripe signing helper as ``tests/test_webhooks.py``.

    Kept as a local helper rather than importing across the test tree so
    this e2e suite stays self-contained -- the other suites are free to
    rearrange without breaking this one.
    """
    timestamp = timestamp or int(time.time())
    signed_payload = f"{timestamp}.{body.decode('utf-8')}".encode()
    digest = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


# ---------------------------------------------------------------------------
# New-user onboarding flow
# ---------------------------------------------------------------------------


def test_new_user_onboarding_flow(e2e_user_client: TestClient) -> None:
    """Onboard -> GET me -> PATCH me -> GET me round-trip.

    Covers the happy path the onboarding wizard drives: sign-in (mocked
    via dependency override), POST /users/onboard, then profile edits
    from the settings screen.
    """
    onboard_response = e2e_user_client.post("/api/v1/users/onboard", json=_onboard_payload())
    assert onboard_response.status_code == 200, onboard_response.text
    assert onboard_response.json()["id"] == E2E_USER_ID

    initial_profile = e2e_user_client.get("/api/v1/users/me")
    assert initial_profile.status_code == 200
    assert initial_profile.json()["bankrollEur"] == 2500.0
    assert initial_profile.json()["plan"] == "alpha"

    patch_response = e2e_user_client.patch(
        "/api/v1/users/me",
        json={"bankrollEur": 7777.0, "oddsFormat": "fractional"},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["bankrollEur"] == 7777.0
    assert patched["oddsFormat"] == "fractional"

    # Second GET sees the patch (not just the patch response body).
    refetch = e2e_user_client.get("/api/v1/users/me")
    assert refetch.status_code == 200
    assert refetch.json()["bankrollEur"] == 7777.0
    assert refetch.json()["oddsFormat"] == "fractional"
    # Untouched fields (email, telegramHandle) survived both calls.
    assert refetch.json()["email"] == "journey@sportslab.example.com"
    assert refetch.json()["telegramHandle"] == "@journey_tester"


# ---------------------------------------------------------------------------
# Predictions -> my-bets flow
# ---------------------------------------------------------------------------


def test_predictions_to_my_bets_flow(e2e_user_client: TestClient) -> None:
    """GET picks -> POST bet derived from a pick -> GET bets.

    Exercises the predictions router and the users router together, the
    way the web app does when a user clicks "Track this pick" on the
    daily slip.
    """
    e2e_user_client.post("/api/v1/users/onboard", json=_onboard_payload())

    # Use a past date so results routes would also be valid -- picks
    # themselves work for any date with the stub provider.
    target = (datetime.now(_WARSAW) - timedelta(days=1)).date().isoformat()
    picks_response = e2e_user_client.get(f"/api/v1/predictions/{target}")
    assert picks_response.status_code == 200, picks_response.text
    picks = picks_response.json()
    assert len(picks) >= 1
    first_pick = picks[0]

    # Derive the bet body from the pick so the test matches what the
    # frontend does in production.
    bet_body = {
        "matchId": first_pick["match"]["id"],
        "market": first_pick["market"],
        "selection": first_pick["selection"].lower(),
        "stakeEur": 25.0,
        "odds": first_pick["bestOdds"],
        "bookmaker": first_pick["bookmaker"],
    }
    create_bet = e2e_user_client.post("/api/v1/users/me/bets", json=bet_body)
    assert create_bet.status_code == 201, create_bet.text
    created = create_bet.json()
    assert created["id"]
    assert created["outcome"] == "pending"
    # Stub attribution: follows_model is always False until the DB-backed
    # provider can join against the pick catalog (A-09). This assertion
    # is the contract: the field MUST be present in the response shape,
    # even if the value is False for now.
    assert created["followsModel"] is False

    listing = e2e_user_client.get("/api/v1/users/me/bets")
    assert listing.status_code == 200
    bets = listing.json()
    assert len(bets) == 1
    assert bets[0]["matchId"] == first_pick["match"]["id"]


# ---------------------------------------------------------------------------
# Public endpoints bypass Clerk auth
# ---------------------------------------------------------------------------


def test_public_endpoints_bypass_auth(e2e_anon_client: TestClient) -> None:
    """Public routes are reachable without any Bearer token.

    ``/health``, ``/openapi.json``, ``/webhooks/*`` are on the public
    prefix list. Webhooks still enforce provider signatures, but the
    response must NOT be 401 from :class:`ClerkAuthMiddleware` -- it must
    reach the handler first.
    """
    # /health -> 200 without any Authorization header.
    health = e2e_anon_client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    # /openapi.json -> 200 without auth (needed for client codegen).
    openapi = e2e_anon_client.get("/openapi.json")
    assert openapi.status_code == 200
    assert openapi.json()["info"]["title"] == "SportsLab API"

    # Webhook with invalid signature reaches the handler (signature
    # rejected with 401 from the handler, not the middleware). The
    # fixture pins the webhook secret, so this is a real signature fail,
    # not a missing-secret 503.
    clerk_response = e2e_anon_client.post(
        "/api/v1/webhooks/clerk",
        content=b'{"type":"user.created","data":{"id":"u"}}',
        headers={
            "svix-id": "msg_public_bypass",
            "svix-timestamp": str(int(time.time())),
            # Needs to be base64-shaped so Svix raises
            # ``WebhookVerificationError`` rather than ``binascii.Error``.
            # Same pattern as ``tests/test_webhooks.py``.
            "svix-signature": "v1,completely-bogus-signature",
        },
    )
    # 401 here is the webhook handler's signature-check rejection.
    # The middleware would have returned 401 with WWW-Authenticate: Bearer.
    # The handler returns 401 with detail "Invalid webhook signature"
    # and NO WWW-Authenticate header -- that's how we know the middleware
    # did not intercept.
    assert clerk_response.status_code == 401
    assert "WWW-Authenticate" not in clerk_response.headers
    assert clerk_response.json()["detail"] == "Invalid webhook signature"


# ---------------------------------------------------------------------------
# Protected endpoints require Clerk auth
# ---------------------------------------------------------------------------


def test_protected_endpoints_require_auth(e2e_anon_client: TestClient) -> None:
    """Every non-public route must return 401 without a Bearer token.

    Spot-checks predictions (frontend-facing), users (frontend-facing),
    and admin (operator-facing). All three flow through
    :class:`ClerkAuthMiddleware`, so a regression anywhere in the
    public-path logic is caught here.
    """
    today = datetime.now(_WARSAW).date().isoformat()

    predictions = e2e_anon_client.get(f"/api/v1/predictions/{today}")
    assert predictions.status_code == 401
    assert predictions.headers.get("WWW-Authenticate") == "Bearer"

    me = e2e_anon_client.get("/api/v1/users/me")
    assert me.status_code == 401
    assert me.headers.get("WWW-Authenticate") == "Bearer"

    admin_users = e2e_anon_client.get("/api/v1/admin/users")
    assert admin_users.status_code == 401
    assert admin_users.headers.get("WWW-Authenticate") == "Bearer"


# ---------------------------------------------------------------------------
# Admin RBAC enforcement
# ---------------------------------------------------------------------------


def test_admin_rbac_denies_regular_user(e2e_user_client: TestClient) -> None:
    """role=user gets 403 on every ``/admin/*`` endpoint.

    Covers GET /admin/users AND GET /admin/system -- a single list would
    let a broken dispatch mask a failure on one of them.
    """
    for path in ("/api/v1/admin/users", "/api/v1/admin/system"):
        response = e2e_user_client.get(path)
        assert response.status_code == 403, f"{path} should be 403 for role=user"
        assert "admin" in response.json()["detail"].lower()


def test_admin_rbac_allows_admin_user(e2e_admin_client: TestClient) -> None:
    """role=admin gets 200 on every ``/admin/*`` endpoint."""
    users_response = e2e_admin_client.get("/api/v1/admin/users")
    assert users_response.status_code == 200
    payload = users_response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 1

    system_response = e2e_admin_client.get("/api/v1/admin/system")
    assert system_response.status_code == 200
    system_payload = system_response.json()
    assert "pipelines" in system_payload
    assert "model" in system_payload
    assert "infra" in system_payload

    # Sanity check: the admin id we stubbed shouldn't matter for these
    # handlers, but we can at least confirm the retrain endpoint works.
    retrain = e2e_admin_client.post("/api/v1/admin/model/retrain")
    assert retrain.status_code == 200
    assert retrain.json()["status"] == "queued"
    # We didn't use E2E_ADMIN_ID anywhere observable in the response, but
    # referencing it here keeps the import honest and pins the expectation
    # for future handlers that DO return the acting admin.
    assert E2E_ADMIN_ID  # no-op assertion documenting the fixture contract


# ---------------------------------------------------------------------------
# Webhook idempotency -- Clerk + Stripe on the same app
# ---------------------------------------------------------------------------


def test_webhook_idempotency_cross_providers(e2e_anon_client: TestClient) -> None:
    """Replays dedupe, and provider keys don't collide with one another.

    Fires four requests against the single app:

    1. Clerk evt_1 -> processed=True
    2. Clerk evt_1 again -> processed=False (dedup)
    3. Stripe with the same raw id ``evt_1`` -> processed=True
       (provider-keyed store keeps Clerk and Stripe separate)
    4. Stripe evt_2 -> processed=True (different id)
    """
    clerk_payload = json.dumps({"type": "user.created", "data": {"id": "u1"}}).encode("utf-8")
    clerk_id = "msg_evt_1"
    now = datetime.now(UTC)
    clerk_webhook = SvixWebhook(E2E_CLERK_WEBHOOK_SECRET)
    clerk_signature = clerk_webhook.sign(clerk_id, now, clerk_payload.decode("utf-8"))
    clerk_headers = {
        "svix-id": clerk_id,
        "svix-timestamp": str(int(now.timestamp())),
        "svix-signature": clerk_signature,
        "content-type": "application/json",
    }

    first_clerk = e2e_anon_client.post(
        "/api/v1/webhooks/clerk", content=clerk_payload, headers=clerk_headers
    )
    second_clerk = e2e_anon_client.post(
        "/api/v1/webhooks/clerk", content=clerk_payload, headers=clerk_headers
    )
    assert first_clerk.status_code == 200, first_clerk.text
    assert second_clerk.status_code == 200, second_clerk.text
    assert first_clerk.json()["processed"] is True
    assert second_clerk.json()["processed"] is False

    # Stripe event whose raw ``id`` happens to collide with the Clerk
    # svix-id string. The idempotency store is keyed by
    # ``(provider, event_id)``, so this MUST still process fresh.
    stripe_payload = json.dumps(
        {
            "id": clerk_id,  # deliberate collision with the Clerk id above
            "type": "invoice.paid",
            "data": {"object": {"customer": "cus_1", "amount_paid": 1900}},
        }
    ).encode("utf-8")
    stripe_signature = _stripe_sign(stripe_payload, E2E_STRIPE_WEBHOOK_SECRET)
    stripe_headers = {
        "stripe-signature": stripe_signature,
        "content-type": "application/json",
    }
    first_stripe = e2e_anon_client.post(
        "/api/v1/webhooks/stripe", content=stripe_payload, headers=stripe_headers
    )
    assert first_stripe.status_code == 200, first_stripe.text
    assert first_stripe.json()["processed"] is True
    assert first_stripe.json()["event_id"] == clerk_id

    # Different Stripe event id -> still processed.
    second_stripe_payload = json.dumps(
        {
            "id": "evt_stripe_other",
            "type": "invoice.paid",
            "data": {"object": {"customer": "cus_2", "amount_paid": 2900}},
        }
    ).encode("utf-8")
    second_stripe_signature = _stripe_sign(second_stripe_payload, E2E_STRIPE_WEBHOOK_SECRET)
    second_stripe = e2e_anon_client.post(
        "/api/v1/webhooks/stripe",
        content=second_stripe_payload,
        headers={
            "stripe-signature": second_stripe_signature,
            "content-type": "application/json",
        },
    )
    assert second_stripe.status_code == 200
    assert second_stripe.json()["processed"] is True
    assert second_stripe.json()["event_id"] == "evt_stripe_other"


# ---------------------------------------------------------------------------
# Track-record filter consistency
# ---------------------------------------------------------------------------


def test_track_record_filter_consistency(e2e_user_client: TestClient) -> None:
    """``?since=`` is observable and narrower than the unbounded window.

    The stub provider's monthly rows run 2025-01 .. 2025-12. Calling with
    ``since=2025-11-01`` must return fewer bets than an unbounded call,
    and the echoed ``sinceDate`` must match the query argument.
    """
    unbounded = e2e_user_client.get("/api/v1/track-record")
    assert unbounded.status_code == 200
    unbounded_body = unbounded.json()

    windowed = e2e_user_client.get("/api/v1/track-record?since=2025-11-01")
    assert windowed.status_code == 200
    windowed_body = windowed.json()

    assert windowed_body["sinceDate"] == "2025-11-01"
    # A non-empty later-in-the-year window has strictly fewer bets than
    # the full 12-month window.
    assert windowed_body["bets"] < unbounded_body["bets"]
    assert windowed_body["bets"] > 0

    # When no ``since`` is passed, the provider's epoch is earlier than
    # the windowed ``sinceDate``.
    unbounded_since = date.fromisoformat(unbounded_body["sinceDate"])
    windowed_since = date.fromisoformat(windowed_body["sinceDate"])
    assert unbounded_since < windowed_since

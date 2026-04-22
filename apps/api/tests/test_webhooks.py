"""Tests for ``/api/v1/webhooks/*`` endpoints.

Two transport concerns are mocked in different ways:

* **Clerk (Svix):** we use ``svix.Webhook.sign`` to compute a valid
  signature over the actual JSON body, so the verification code path
  executes for real. That keeps the test honest about the shape of the
  Svix headers.
* **Stripe:** ``stripe.Webhook`` signs over the raw bytes with a secret
  and a timestamp. Stripe doesn't expose a public ``sign`` helper, so we
  either (a) reconstruct the signing string manually with HMAC-SHA256 or
  (b) dependency-override the verifier. We do (a) -- it's 5 lines and
  doesn't hide verification bugs behind a mock.

Each test resets ``InMemoryIdempotencyStore`` so state doesn't leak
across cases.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from api.config import Settings, get_settings
from api.main import create_app
from api.routers import webhooks as webhooks_router_module
from api.routers.webhooks import InMemoryIdempotencyStore
from fastapi.testclient import TestClient
from svix.webhooks import Webhook as SvixWebhook

# Svix secrets are base64-encoded; the library expects the ``whsec_`` prefix.
# Any 16+ byte random base64 value works for tests.
_CLERK_TEST_SECRET = "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"
_STRIPE_TEST_SECRET = "whsec_stripe_test_secret_value_xyz"


@pytest.fixture(autouse=True)
def _reset_idempotency_store() -> Iterator[None]:
    """Each test starts with an empty idempotency store."""
    InMemoryIdempotencyStore.reset()
    yield
    InMemoryIdempotencyStore.reset()


def _build_client(
    *,
    clerk_secret: str = "",
    stripe_secret: str = "",
) -> TestClient:
    """Build a TestClient with per-test webhook secrets.

    We construct a fresh ``Settings`` so the ``get_settings`` dependency
    override returns the exact secrets this test needs. The default
    ``client`` fixture in ``conftest.py`` pins secrets we can't control
    here, so we bypass it.
    """
    settings = Settings(
        api_version="0.1.0-test",
        cors_origins=["http://localhost:3000"],
        clerk_publishable_key="pk_test_stub",
        clerk_jwks_url="https://test.clerk.invalid/v1/jwks",
        clerk_webhook_secret=clerk_secret,
        stripe_webhook_secret=stripe_secret,
        database_url="sqlite+aiosqlite:///./test.db",
        log_level="WARNING",
        env="test",
    )
    get_settings.cache_clear()
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


# -----------------------------
# Clerk webhook -- signature paths
# -----------------------------


def test_clerk_webhook_missing_secret_returns_503() -> None:
    """Missing ``clerk_webhook_secret`` -> 503, not 200 with skipped verify."""
    client = _build_client(clerk_secret="")
    response = client.post(
        "/api/v1/webhooks/clerk",
        content=b"{}",
        headers={
            "svix-id": "msg_test_1",
            "svix-timestamp": str(int(time.time())),
            "svix-signature": "v1,invalid",
        },
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_clerk_webhook_invalid_signature_returns_401() -> None:
    """A correctly-shaped but wrong-signed request -> 401."""
    client = _build_client(clerk_secret=_CLERK_TEST_SECRET)
    response = client.post(
        "/api/v1/webhooks/clerk",
        content=b'{"type":"user.created","data":{"id":"user_x"}}',
        headers={
            "svix-id": "msg_test_2",
            "svix-timestamp": str(int(time.time())),
            "svix-signature": "v1,completely-bogus-signature",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid webhook signature"


def test_clerk_webhook_valid_signature_returns_200() -> None:
    """Valid Svix signature -> 200 and ``processed=True``."""
    client = _build_client(clerk_secret=_CLERK_TEST_SECRET)
    payload = {"type": "user.created", "data": {"id": "user_abc"}}
    body = json.dumps(payload).encode("utf-8")
    svix_id = "msg_test_valid_001"
    now = datetime.now(UTC)
    svix_timestamp = str(int(now.timestamp()))

    webhook = SvixWebhook(_CLERK_TEST_SECRET)
    signature = webhook.sign(svix_id, now, body.decode("utf-8"))

    response = client.post(
        "/api/v1/webhooks/clerk",
        content=body,
        headers={
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": signature,
            "content-type": "application/json",
        },
    )
    assert response.status_code == 200, response.text
    body_json = response.json()
    assert body_json["status"] == "ok"
    assert body_json["event_id"] == svix_id
    assert body_json["processed"] is True


def test_clerk_webhook_idempotent_replay() -> None:
    """Sending the same event twice -> second response has ``processed=False``."""
    client = _build_client(clerk_secret=_CLERK_TEST_SECRET)
    payload = {"type": "user.updated", "data": {"id": "user_replay"}}
    body = json.dumps(payload).encode("utf-8")
    svix_id = "msg_test_replay_001"
    now = datetime.now(UTC)
    svix_timestamp = str(int(now.timestamp()))

    webhook = SvixWebhook(_CLERK_TEST_SECRET)
    signature = webhook.sign(svix_id, now, body.decode("utf-8"))
    headers = {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": signature,
        "content-type": "application/json",
    }

    first = client.post("/api/v1/webhooks/clerk", content=body, headers=headers)
    second = client.post("/api/v1/webhooks/clerk", content=body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["processed"] is True
    assert second.json()["processed"] is False
    assert first.json()["event_id"] == second.json()["event_id"] == svix_id


def test_clerk_webhook_unknown_event_type_still_200() -> None:
    """An unknown ``type`` is accepted (logged + marked processed)."""
    client = _build_client(clerk_secret=_CLERK_TEST_SECRET)
    payload = {"type": "session.created", "data": {"id": "sess_x"}}
    body = json.dumps(payload).encode("utf-8")
    svix_id = "msg_test_unknown_001"
    now = datetime.now(UTC)
    svix_timestamp = str(int(now.timestamp()))

    webhook = SvixWebhook(_CLERK_TEST_SECRET)
    signature = webhook.sign(svix_id, now, body.decode("utf-8"))

    response = client.post(
        "/api/v1/webhooks/clerk",
        content=body,
        headers={
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": signature,
            "content-type": "application/json",
        },
    )
    assert response.status_code == 200
    assert response.json()["processed"] is True


# -----------------------------
# Stripe webhook -- signature paths
# -----------------------------


def _stripe_sign(body: bytes, secret: str, timestamp: int | None = None) -> str:
    """Build a valid ``stripe-signature`` header for ``body`` + ``secret``.

    Stripe format: ``t=<timestamp>,v1=<hex_hmac_sha256(timestamp.body)>``.
    ``stripe.Webhook.construct_event`` accepts this shape directly.
    """
    timestamp = timestamp or int(time.time())
    signed_payload = f"{timestamp}.{body.decode('utf-8')}".encode()
    digest = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_stripe_webhook_missing_secret_returns_503() -> None:
    """Missing ``stripe_webhook_secret`` -> 503."""
    client = _build_client(stripe_secret="")
    response = client.post(
        "/api/v1/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_stripe_webhook_invalid_signature_returns_401() -> None:
    """Wrong signature -> 401."""
    client = _build_client(stripe_secret=_STRIPE_TEST_SECRET)
    response = client.post(
        "/api/v1/webhooks/stripe",
        content=b'{"id":"evt_1","type":"invoice.paid"}',
        headers={"stripe-signature": "t=1,v1=notavalidsignature"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid webhook signature"


def test_stripe_webhook_valid_signature_returns_200() -> None:
    """Valid HMAC signature -> 200 with ``processed=True``."""
    client = _build_client(stripe_secret=_STRIPE_TEST_SECRET)
    payload = {
        "id": "evt_test_001",
        "type": "invoice.paid",
        "data": {"object": {"customer": "cus_abc", "amount_paid": 1900}},
    }
    body = json.dumps(payload).encode("utf-8")
    signature = _stripe_sign(body, _STRIPE_TEST_SECRET)

    response = client.post(
        "/api/v1/webhooks/stripe",
        content=body,
        headers={"stripe-signature": signature, "content-type": "application/json"},
    )
    assert response.status_code == 200, response.text
    body_json = response.json()
    assert body_json["status"] == "ok"
    assert body_json["event_id"] == "evt_test_001"
    assert body_json["processed"] is True


def test_stripe_webhook_idempotent_replay() -> None:
    """Duplicate ``evt_...`` -> second response has ``processed=False``."""
    client = _build_client(stripe_secret=_STRIPE_TEST_SECRET)
    payload = {
        "id": "evt_test_replay",
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_x", "customer": "cus_x", "status": "active"}},
    }
    body = json.dumps(payload).encode("utf-8")
    signature = _stripe_sign(body, _STRIPE_TEST_SECRET)
    headers = {"stripe-signature": signature, "content-type": "application/json"}

    first = client.post("/api/v1/webhooks/stripe", content=body, headers=headers)
    second = client.post("/api/v1/webhooks/stripe", content=body, headers=headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["processed"] is True
    assert second.json()["processed"] is False
    assert first.json()["event_id"] == second.json()["event_id"] == "evt_test_replay"


def test_stripe_webhook_subscription_deleted_dispatch() -> None:
    """customer.subscription.deleted hits the log branch and acks 200."""
    client = _build_client(stripe_secret=_STRIPE_TEST_SECRET)
    payload = {
        "id": "evt_sub_del",
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_deleted", "customer": "cus_1"}},
    }
    body = json.dumps(payload).encode("utf-8")
    signature = _stripe_sign(body, _STRIPE_TEST_SECRET)

    response = client.post(
        "/api/v1/webhooks/stripe",
        content=body,
        headers={"stripe-signature": signature, "content-type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["processed"] is True


# -----------------------------
# Middleware bypass
# -----------------------------


def test_webhooks_bypass_clerk_auth() -> None:
    """POST to ``/api/v1/webhooks/*`` without a Bearer token must NOT 401.

    If the Clerk middleware's public-path list drops ``/api/v1/webhooks``,
    every legitimate Stripe / Clerk delivery would be rejected before the
    webhook router even runs. This test guards that regression.
    """
    # No clerk token, no stripe token -- only signature headers.
    # With an empty secret the endpoint returns 503, but crucially NOT 401
    # from the middleware. We assert the code path reaches the router.
    client = _build_client(clerk_secret="", stripe_secret="")

    clerk_response = client.post(
        "/api/v1/webhooks/clerk",
        content=b"{}",
        headers={
            "svix-id": "msg_bypass_test",
            "svix-timestamp": "1",
            "svix-signature": "v1,x",
        },
    )
    stripe_response = client.post(
        "/api/v1/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=x"},
    )

    # Both endpoints return 503 (secret unset), proving middleware bypassed
    # and routing reached the handler. A 401 from Clerk auth would mean the
    # middleware intercepted ahead of the public-path check.
    assert clerk_response.status_code == 503
    assert stripe_response.status_code == 503


# -----------------------------
# Idempotency store direct unit tests
# -----------------------------


@pytest.mark.asyncio
async def test_in_memory_idempotency_store_is_keyed_by_provider() -> None:
    """Same ``event_id`` across providers does NOT collide."""
    store = webhooks_router_module.InMemoryIdempotencyStore()
    store.reset()

    await store.mark_processed("clerk", "evt_same")
    assert await store.seen("clerk", "evt_same") is True
    # Stripe side is still untouched.
    assert await store.seen("stripe", "evt_same") is False

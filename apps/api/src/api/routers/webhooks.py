"""Provider webhook endpoints -- Clerk (user lifecycle) and Stripe (billing).

Webhooks live at ``/api/v1/webhooks/...`` and are explicitly **not** covered
by :class:`api.middleware.clerk_auth.ClerkAuthMiddleware`: each provider
authenticates its own POSTs with a signed header, and no Clerk JWT exists
at the time a webhook fires.

Signature verification is non-optional. If a secret isn't configured
(empty env var) the endpoint returns 503 instead of accepting an
unverifiable payload -- fail closed, not open. In real deploys the secret
is always set; 503 is the "dev machine forgot to ``export``" signal.

Idempotency lives behind a provider-keyed :class:`IdempotencyStore`. In
alpha the store is a process-local dict (good enough for a single-worker
deploy + development). The DB-backed replacement lands in A-09 together
with the Postgres migration -- that's when ``UNIQUE(provider, event_id)``
starts doing real work across horizontal workers.

Scope caveat: handlers currently log-only. Downstream side effects
(creating ``UsersProvider`` entries from Clerk user.created, flipping
``plan`` on Stripe invoice.paid) wire up when the DB-backed providers
arrive -- see A-09, A-22.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Annotated, Any, ClassVar

import stripe as stripe_sdk
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from svix.webhooks import Webhook, WebhookVerificationError

from api.config import Settings, get_settings
from api.models.webhooks import WebhookResponse

_logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class IdempotencyStore(ABC):
    """Track processed webhook event IDs to dedupe retries.

    Providers retry on non-2xx responses and occasionally retry on 2xx as
    well (network timeouts between the provider and us). A replay that
    re-runs the handler is a correctness bug -- especially for Stripe
    invoice.paid, which must not double-apply billing state changes.

    Contract:
        - Keyed by ``(provider, event_id)`` so a Clerk and a Stripe event
          sharing an ID (shouldn't happen but cheap safety) don't collide.
        - ``seen`` returns ``True`` only if ``mark_processed`` has been
          called with the same key.
        - Implementations must be safe for concurrent access; the API runs
          a single event loop but multiple workers will land in A-09.

    In production this is backed by Postgres with a UNIQUE index. The
    in-memory stub below matches the contract for dev + tests.
    """

    @abstractmethod
    async def seen(self, provider: str, event_id: str) -> bool:
        """Return True iff the (provider, event_id) tuple was processed."""

    @abstractmethod
    async def mark_processed(self, provider: str, event_id: str) -> None:
        """Record the (provider, event_id) tuple as processed."""


class InMemoryIdempotencyStore(IdempotencyStore):
    """Process-local idempotency store.

    State lives on the class so a single FastAPI process sees consistent
    data across requests without explicit wiring. Tests reset via
    :meth:`reset`. Replaced by a Postgres-backed implementation in A-09.

    Note: this is NOT safe across workers. A multi-worker deploy with this
    store will process the same event once per worker. That's acceptable
    during alpha (single-worker Docker container) but must flip before any
    horizontal scale-out.
    """

    _events: ClassVar[dict[tuple[str, str], datetime]] = {}

    @classmethod
    def reset(cls) -> None:
        """Wipe state. Tests only -- production callers must never rely on this."""
        cls._events.clear()

    async def seen(self, provider: str, event_id: str) -> bool:
        return (provider, event_id) in self._events

    async def mark_processed(self, provider: str, event_id: str) -> None:
        self._events[(provider, event_id)] = datetime.now(UTC)


_DEFAULT_STORE = InMemoryIdempotencyStore()


def get_idempotency_store() -> IdempotencyStore:
    """Return the process-wide idempotency store.

    Overridden in tests via ``app.dependency_overrides`` to inject a fresh
    store per test case, or swap to a Postgres-backed implementation once
    the DB is wired (A-09).
    """
    return _DEFAULT_STORE


@router.post(
    "/clerk",
    response_model=WebhookResponse,
    summary="Clerk user lifecycle webhook (user.created / updated / deleted)",
    responses={
        401: {"description": "Invalid Svix signature."},
        503: {"description": "Clerk webhook secret not configured."},
    },
)
async def clerk_webhook(
    request: Request,
    svix_id: Annotated[str, Header(alias="svix-id")],
    svix_timestamp: Annotated[str, Header(alias="svix-timestamp")],
    svix_signature: Annotated[str, Header(alias="svix-signature")],
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[IdempotencyStore, Depends(get_idempotency_store)],
) -> WebhookResponse:
    """Handle a Clerk webhook POST.

    Flow:
        1. 503 if the signing secret isn't configured (fail-closed dev).
        2. Verify the Svix signature against the raw body -- a single byte
           of tampering fails verification.
        3. Dedupe on ``svix-id`` via the idempotency store.
        4. Dispatch by ``payload["type"]``. Stub handlers log only; the
           real side effects land when the Postgres users provider is in
           place (A-09).

    The Clerk signature is computed over the raw bytes; we MUST read the
    body before any downstream code touches ``request.json()`` (which
    would otherwise swallow the buffer on FastAPI older than 0.111).
    """
    if not settings.clerk_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk webhook secret not configured",
        )

    body = await request.body()
    try:
        webhook = Webhook(settings.clerk_webhook_secret)
        payload: dict[str, Any] = webhook.verify(
            body,
            {
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature,
            },
        )
    except WebhookVerificationError as error:
        # Don't echo the error verbatim -- it can leak whether the secret is
        # set or the signature shape is wrong. A single 401 is enough.
        _logger.warning("clerk_webhook_invalid_signature", reason=str(error))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        ) from error

    event_id = svix_id
    if await store.seen("clerk", event_id):
        _logger.info("clerk_webhook_replay", event_id=event_id)
        return WebhookResponse(event_id=event_id, processed=False)

    _dispatch_clerk_event(payload)

    await store.mark_processed("clerk", event_id)
    return WebhookResponse(event_id=event_id, processed=True)


@router.post(
    "/stripe",
    response_model=WebhookResponse,
    summary="Stripe billing webhook (invoice.paid, subscription lifecycle)",
    responses={
        401: {"description": "Invalid Stripe signature."},
        503: {"description": "Stripe webhook secret not configured."},
    },
)
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str, Header(alias="stripe-signature")],
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[IdempotencyStore, Depends(get_idempotency_store)],
) -> WebhookResponse:
    """Handle a Stripe webhook POST.

    Mirrors the Clerk handler but uses Stripe's HMAC-SHA256 scheme via
    :func:`stripe_sdk.Webhook.construct_event`. ``construct_event`` both
    verifies the signature and parses the JSON -- the returned event is a
    ``stripe.Event`` that behaves like a dict for our purposes.

    Scope caveat: the handlers below only log. Real side effects
    (updating user ``plan``, toggling access, recording invoices) land in
    A-09 once Postgres is wired -- billing mutations must be in a
    transaction with the idempotency write.
    """
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret not configured",
        )

    body = await request.body()
    try:
        event = stripe_sdk.Webhook.construct_event(
            payload=body,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except (ValueError, stripe_sdk.SignatureVerificationError) as error:
        # ``ValueError`` covers malformed JSON; ``SignatureVerificationError``
        # covers tampering, wrong secret, or expired timestamp.
        _logger.warning("stripe_webhook_invalid_signature", reason=str(error))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        ) from error

    event_id: str = event["id"]
    if await store.seen("stripe", event_id):
        _logger.info("stripe_webhook_replay", event_id=event_id)
        return WebhookResponse(event_id=event_id, processed=False)

    _dispatch_stripe_event(event)

    await store.mark_processed("stripe", event_id)
    return WebhookResponse(event_id=event_id, processed=True)


def _dispatch_clerk_event(payload: dict[str, Any]) -> None:
    """Log-only dispatch for Clerk events.

    Kept as a pure function (no ``async``, no I/O) so tests can cover
    dispatch shape independently of HTTP transport. Real side effects
    land in A-09 when the Postgres users provider is in place.
    """
    event_type = payload.get("type")
    data = payload.get("data") or {}
    user_id = data.get("id") if isinstance(data, dict) else None

    if event_type == "user.created":
        _logger.info("clerk_user_created", user_id=user_id)
    elif event_type == "user.deleted":
        _logger.info("clerk_user_deleted", user_id=user_id)
    elif event_type == "user.updated":
        _logger.info("clerk_user_updated", user_id=user_id)
    else:
        _logger.info("clerk_event_ignored", event_type=event_type)


def _dispatch_stripe_event(event: Any) -> None:
    """Log-only dispatch for Stripe events.

    ``event`` is the ``stripe.Event`` object returned by
    :func:`stripe_sdk.Webhook.construct_event`. It exposes dict-style
    access for ``id``, ``type``, and ``data.object``.
    """
    event_type: str = event["type"]
    # ``event["data"]["object"]`` shape varies per event_type; we only touch
    # the fields the specific branch cares about.
    data_object = event["data"]["object"]

    if event_type == "invoice.paid":
        _logger.info(
            "stripe_invoice_paid",
            customer=data_object.get("customer"),
            amount_paid=data_object.get("amount_paid"),
        )
    elif event_type == "customer.subscription.deleted":
        _logger.info(
            "stripe_subscription_deleted",
            customer=data_object.get("customer"),
            subscription=data_object.get("id"),
        )
    elif event_type == "customer.subscription.updated":
        _logger.info(
            "stripe_subscription_updated",
            customer=data_object.get("customer"),
            subscription=data_object.get("id"),
            status_=data_object.get("status"),
        )
    else:
        _logger.info("stripe_event_ignored", event_type=event_type)

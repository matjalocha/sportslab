"""Response payloads for provider webhook endpoints.

These are tiny by design -- webhooks acknowledge receipt; they don't return
domain data. ``processed`` distinguishes a fresh event (``True``) from an
idempotent replay (``False``) so senders can distinguish "we did work" from
"we've seen this before, no-op".

Scope caveat: richer payloads (e.g. returning the resolved ``user_id`` for
Clerk user.created) land when the webhook handlers wire into the Postgres-
backed providers in A-09.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class WebhookResponse(BaseModel):
    """Successful webhook acknowledgement.

    Attributes:
        status: Always ``"ok"``. Kept as a field (rather than HTTP-implicit)
            so clients logging the body see something useful.
        event_id: Provider-side event identifier (Svix ``svix-id`` for Clerk,
            Stripe ``evt_...`` for Stripe). Logged and used as the idempotency
            key so retries are cheap to correlate.
        processed: ``True`` if the event was newly processed; ``False`` if
            we've seen this ``event_id`` before (idempotent replay).
    """

    model_config = ConfigDict(populate_by_name=True)

    status: str = "ok"
    event_id: str
    processed: bool


class WebhookErrorResponse(BaseModel):
    """Documented error payload -- surfaces in the OpenAPI schema.

    FastAPI's default ``HTTPException`` renderer returns ``{"detail": "..."}``;
    this schema exists so the generated TypeScript client has a named type
    for the 401 / 503 branches rather than ``any``.
    """

    model_config = ConfigDict(populate_by_name=True)

    status: str = "error"
    message: str

"""User-facing alert payloads for the inbox / notifications page.

Alerts are the inbound side of the notification system: calibration
drift reports, new-league announcements, large-edge pings, pipeline
delay notices, and generic system messages surface here. The outbound
side (Telegram / email dispatch) is a separate concern driven by
``NotificationPrefs`` -- this model only describes what the user sees
in-app.

Wire shape matches ``sportslab-web``'s TypeScript types: camelCase on
the wire, snake_case in Python, ``populate_by_name=True`` so callers
can send either.

Scope caveat: the models are the contract; persistence (Postgres
``user_alerts`` table, per-user fan-out on publish, retention policy)
is deferred. :class:`StubAlertsProvider` returns deterministic
fixtures so the frontend can wire the page end-to-end.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AlertSeverity = Literal["info", "warning", "critical"]
AlertType = Literal[
    "calibration_drift",
    "new_league",
    "large_edge",
    "pipeline_delay",
    "system",
]


class Alert(BaseModel):
    """A single user-visible alert row.

    ``read_at`` is ``None`` for unread alerts -- the UI uses this field
    both to badge the inbox count and to style unread rows. Marking an
    alert read sets the server's ``datetime.utcnow()``; clients never
    supply this timestamp so it stays monotonic across devices.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    body: str
    created_at: datetime = Field(..., alias="createdAt")
    read_at: datetime | None = Field(None, alias="readAt")

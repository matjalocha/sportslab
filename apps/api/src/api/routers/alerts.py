"""User-inbox alert endpoints -- ``/api/v1/users/me/alerts/...``.

Every route here is authenticated (Clerk JWT via ``ClerkAuthMiddleware``)
and scoped to the calling user -- ``user_id`` is resolved from
``request.state`` by the shared :func:`get_current_user_id` dependency
and never trusted from the body or URL.

Routes:

    GET    /users/me/alerts                -> list[Alert]   (most recent first)
    PATCH  /users/me/alerts/{id}/read      -> Alert         (mark single as read)
    POST   /users/me/alerts/read-all       -> 204           (mark all unread as read)

:class:`StubAlertsProvider` holds a per-user in-memory fixture keyed on
``user_id``. The real provider will read from a Postgres ``user_alerts``
table (per-user fan-out at publish time). Until then, every user sees
the same deterministic four-alert fixture so the UI can be wired and
reviewed before the DB lands.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Annotated, ClassVar

from fastapi import APIRouter, Depends, HTTPException, status

from api.models.alerts import Alert
from api.routers.users import get_current_user_id


class AlertsProvider(ABC):
    """Storage contract for per-user alerts.

    Alerts are per-user, so every method takes a ``user_id``. Tests and
    the dev stack use :class:`StubAlertsProvider`; the Postgres-backed
    provider lands in a follow-up ticket.
    """

    @abstractmethod
    async def list_alerts(self, user_id: str) -> list[Alert]: ...

    @abstractmethod
    async def mark_read(self, user_id: str, alert_id: str) -> Alert: ...

    @abstractmethod
    async def mark_all_read(self, user_id: str) -> int: ...


def _seed_alerts(now: datetime) -> list[Alert]:
    """Produce a deterministic four-alert fixture.

    Matches the intent of the sportslab-web panel mock: one of each
    severity so gauges / badges / empty-state logic all get exercised.
    Timestamps are relative to ``now`` so tests can assert "recent" order
    without freezing the clock.
    """
    return [
        Alert(
            id="alert_0001",
            type="calibration_drift",
            severity="critical",
            title="Calibration drift on 1X2 market",
            body=(
                "ECE for EPL 1X2 crossed the 0.03 threshold over the last 7 days. "
                "Review the latest retrain candidate before promoting."
            ),
            created_at=now - timedelta(hours=2),
            read_at=None,
        ),
        Alert(
            id="alert_0002",
            type="large_edge",
            severity="warning",
            title="Large edge detected: Arsenal -- Man City",
            body=(
                "Model edge 8.2% on BTTS Yes vs Pinnacle closing line. "
                "Stake capped at 1% bankroll per risk policy."
            ),
            created_at=now - timedelta(hours=14),
            read_at=None,
        ),
        Alert(
            id="alert_0003",
            type="new_league",
            severity="info",
            title="New league available: Eredivisie",
            body=(
                "Backtest coverage now includes Eredivisie matches from 2022-23 "
                "onward. Toggle it on under Settings -> Leagues."
            ),
            created_at=now - timedelta(days=1, hours=6),
            read_at=now - timedelta(hours=20),
        ),
        Alert(
            id="alert_0004",
            type="pipeline_delay",
            severity="warning",
            title="Scraper delay: Fotmob",
            body=(
                "Fotmob scraper was 42 minutes late on the last run. Odds data "
                "for tonight's matches may be partially stale."
            ),
            created_at=now - timedelta(days=2),
            read_at=now - timedelta(days=1, hours=22),
        ),
    ]


class StubAlertsProvider(AlertsProvider):
    """In-memory per-user alert store.

    Class-level storage so the provider survives per-request instances,
    matching the pattern used by :class:`StubUsersProvider` and
    :class:`StubAdminProvider`. First access for any user lazily seeds
    the four-alert fixture so the frontend sees data on first load.
    """

    _alerts: ClassVar[dict[str, list[Alert]]] = {}

    @classmethod
    def reset(cls) -> None:
        """Wipe state. Tests only -- never call from production code."""
        cls._alerts.clear()

    def _ensure_seeded(self, user_id: str) -> list[Alert]:
        """Lazily materialise the seed fixture for a first-time caller."""
        if user_id not in self._alerts:
            self._alerts[user_id] = _seed_alerts(datetime.now(UTC))
        return self._alerts[user_id]

    async def list_alerts(self, user_id: str) -> list[Alert]:
        alerts = self._ensure_seeded(user_id)
        # Newest first -- matches how an email inbox renders.
        return sorted(alerts, key=lambda entry: entry.created_at, reverse=True)

    async def mark_read(self, user_id: str, alert_id: str) -> Alert:
        alerts = self._ensure_seeded(user_id)
        for index, alert in enumerate(alerts):
            if alert.id != alert_id:
                continue
            if alert.read_at is not None:
                # Idempotent: already-read alerts return unchanged.
                return alert
            updated = alert.model_copy(update={"read_at": datetime.now(UTC)})
            alerts[index] = updated
            return updated
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    async def mark_all_read(self, user_id: str) -> int:
        alerts = self._ensure_seeded(user_id)
        now = datetime.now(UTC)
        changed = 0
        for index, alert in enumerate(alerts):
            if alert.read_at is not None:
                continue
            alerts[index] = alert.model_copy(update={"read_at": now})
            changed += 1
        return changed


_DEFAULT_PROVIDER: AlertsProvider = StubAlertsProvider()


def get_alerts_provider() -> AlertsProvider:
    """Return the process-wide alerts provider (overridden in tests)."""
    return _DEFAULT_PROVIDER


router = APIRouter(prefix="/users/me/alerts", tags=["alerts"])


@router.get(
    "",
    response_model=list[Alert],
    response_model_by_alias=True,
    summary="List the authenticated user's alerts (newest first)",
)
async def list_alerts(
    provider: Annotated[AlertsProvider, Depends(get_alerts_provider)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> list[Alert]:
    """Return the user's alerts sorted newest first.

    No pagination yet -- alpha users see tens of alerts, not thousands.
    Add cursor pagination once we cross a meaningful volume or introduce
    retention (drop alerts older than 90 days).
    """
    return await provider.list_alerts(user_id)


@router.patch(
    "/{alert_id}/read",
    response_model=Alert,
    response_model_by_alias=True,
    summary="Mark a single alert as read",
)
async def mark_read(
    alert_id: str,
    provider: Annotated[AlertsProvider, Depends(get_alerts_provider)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> Alert:
    """Set ``read_at`` on the target alert, returning the updated row.

    Idempotent: marking an already-read alert returns it unchanged with
    the original ``read_at`` timestamp, so retries on flaky networks
    don't rewrite history.
    """
    return await provider.mark_read(user_id, alert_id)


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all unread alerts as read",
)
async def mark_all_read(
    provider: Annotated[AlertsProvider, Depends(get_alerts_provider)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> None:
    """Bulk-clear the unread badge.

    Returns 204 -- the frontend already has the rows in cache and just
    needs to invalidate the unread count. Idempotent: a second call
    flips zero alerts and still returns 204.
    """
    await provider.mark_all_read(user_id)

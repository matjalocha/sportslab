"""Liveness / version probe endpoint.

Public (no auth) — mounted at ``/api/v1/health``. Used by load balancers,
Docker healthchecks, and uptime monitors. Intentionally does NOT touch
the database so a DB outage does not take the whole pod out of rotation.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from api.config import Settings, get_settings
from api.models.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Return ``{status, version, timestamp}``.

    Always 200 while the process is alive. Database reachability is
    checked by a separate ``/readyz`` endpoint (follow-up task).
    """
    return HealthResponse(
        status="ok",
        version=settings.api_version,
        timestamp=datetime.now(UTC).isoformat(),
    )

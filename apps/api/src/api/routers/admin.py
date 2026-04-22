"""Admin endpoints -- operational control plane under ``/api/v1/admin/*``.

Every route here requires an authenticated Clerk session AND the
``admin`` role on the user profile. Regular users get 403, anonymous
callers get 401.

Routes:

    GET    /admin/users              -> list[AdminUser]
    PATCH  /admin/users/{user_id}    -> AdminUser       (plan, status)
    GET    /admin/system             -> SystemStatus    (pipelines + model + infra)
    POST   /admin/model/rollback     -> ModelRollbackResponse
    POST   /admin/model/retrain      -> {status, jobId} (queued)

Providers follow the same ABC-pattern as :mod:`api.routers.users`:
:class:`AdminProvider` is the storage contract, :class:`StubAdminProvider`
returns deterministic in-memory fixtures so the admin dashboard can
integrate before the DB / MLflow / node-exporter wiring lands.

Scope caveat: ``user_role`` is resolved from ``request.state.user_role``,
which the current :class:`ClerkAuthMiddleware` does NOT set -- role lookup
against the users table is a follow-up (see the ``TODO`` in
:func:`require_admin`). Until then tests override the dependency directly
and the dev deployment treats any authenticated caller as admin only when
``env == "dev"`` (enforced below).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Annotated, ClassVar

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.config import Settings, get_settings
from api.models.admin import (
    AdminUser,
    InfraMetric,
    ModelRollbackRequest,
    ModelRollbackResponse,
    ModelVersion,
    OverallStatus,
    PipelineRun,
    SystemStatus,
    UserUpdateAdmin,
)


class AdminProvider(ABC):
    """Storage contract for the admin surface.

    A single process-wide instance is plenty -- admin endpoints are
    low-QPS and every stateful operation goes through the DB in the real
    implementation. Tests inject fresh stubs via
    ``app.dependency_overrides``.
    """

    @abstractmethod
    async def list_users(self) -> list[AdminUser]: ...

    @abstractmethod
    async def update_user(self, user_id: str, update: UserUpdateAdmin) -> AdminUser: ...

    @abstractmethod
    async def get_system_status(self) -> SystemStatus: ...

    @abstractmethod
    async def rollback_model(self, target_version: str) -> ModelRollbackResponse: ...

    @abstractmethod
    async def trigger_retrain(self) -> dict[str, str]: ...


class StubAdminProvider(AdminProvider):
    """Deterministic in-memory fixtures.

    Mirrors the fake admin data the sportslab-web mockups render so the
    frontend hits the real endpoint shape from day one. Replace with a
    Postgres / MLflow / node-exporter-backed provider in a follow-up
    ticket.
    """

    # Class-level state so the stub survives request-scoped instances.
    _users: ClassVar[dict[str, AdminUser]] = {}
    _deployed_version: ClassVar[str] = "v2.4.1"

    @classmethod
    def reset(cls) -> None:
        """Wipe state. Tests only -- never call from production code."""
        cls._users.clear()
        cls._deployed_version = "v2.4.1"
        cls._seed()

    @classmethod
    def _seed(cls) -> None:
        """Populate the stub with a handful of representative rows."""
        if cls._users:
            return
        now = datetime.now(UTC)
        seeds: list[AdminUser] = [
            AdminUser(
                id="user_admin_001",
                email="founder@sportslab.example.com",
                full_name="Mat Jalocha",
                plan="enterprise",
                role="admin",
                status="active",
                last_active_at=now,
                mrr_eur=0.0,
                bets_tracked=42,
                joined_at=now - timedelta(days=120),
            ),
            AdminUser(
                id="user_alpha_abc",
                email="alpha1@sportslab.example.com",
                full_name="Alpha Tester One",
                plan="alpha",
                role="user",
                status="active",
                last_active_at=now - timedelta(hours=3),
                mrr_eur=0.0,
                bets_tracked=17,
                joined_at=now - timedelta(days=30),
            ),
            AdminUser(
                id="user_pro_xyz",
                email="pro@sportslab.example.com",
                full_name="Pro Subscriber",
                plan="pro",
                role="user",
                status="active",
                last_active_at=now - timedelta(days=1),
                mrr_eur=49.0,
                bets_tracked=218,
                joined_at=now - timedelta(days=60),
            ),
            AdminUser(
                id="user_disabled_404",
                email="disabled@sportslab.example.com",
                full_name="Disabled Account",
                plan="alpha",
                role="user",
                status="disabled",
                last_active_at=now - timedelta(days=14),
                mrr_eur=0.0,
                bets_tracked=3,
                joined_at=now - timedelta(days=45),
            ),
        ]
        for profile in seeds:
            cls._users[profile.id] = profile

    def __init__(self) -> None:
        self._seed()

    async def list_users(self) -> list[AdminUser]:
        # Sort by join date descending -- newest first matches the UI.
        return sorted(self._users.values(), key=lambda user: user.joined_at, reverse=True)

    async def update_user(self, user_id: str, update: UserUpdateAdmin) -> AdminUser:
        existing = self._users.get(user_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admin user {user_id} not found",
            )
        patch = update.model_dump(exclude_unset=True, exclude_none=True)
        updated = existing.model_copy(update=patch)
        self._users[user_id] = updated
        return updated

    async def get_system_status(self) -> SystemStatus:
        now = datetime.now(UTC)
        pipelines = [
            PipelineRun(
                name="scrapers.fotmob",
                status="ok",
                last_run_at=now - timedelta(minutes=18),
                duration_seconds=142.7,
                next_run_at=now + timedelta(minutes=42),
                message="ok",
            ),
            PipelineRun(
                name="features.rolling_xg",
                status="ok",
                last_run_at=now - timedelta(hours=3),
                duration_seconds=88.1,
                next_run_at=now + timedelta(hours=21),
                message="ok",
            ),
            PipelineRun(
                name="publish.daily_picks",
                status="running",
                last_run_at=now - timedelta(minutes=2),
                duration_seconds=0.0,
                next_run_at=None,
                message="in-flight",
            ),
        ]
        model = ModelVersion(
            version=type(self)._deployed_version,
            deployed_at=now - timedelta(days=2),
            status="deployed",
            ece_overall=0.021,
            log_loss=0.612,
            brier=0.214,
            trained_on="2026-04-15",
            features_count=87,
        )
        infra = [
            InfraMetric(
                host="api-01",
                cpu_percent=17.4,
                ram_percent=42.1,
                disk_percent=33.8,
                temperature_c=54.0,
                uptime_hours=312.5,
            ),
            InfraMetric(
                host="db-01",
                cpu_percent=8.2,
                ram_percent=61.7,
                disk_percent=48.9,
                temperature_c=49.0,
                uptime_hours=720.0,
            ),
        ]
        # Rollup: any "failed" pipeline is degraded; all ok + deployed is healthy.
        overall: OverallStatus = (
            "degraded" if any(pipe.status == "failed" for pipe in pipelines) else "healthy"
        )
        return SystemStatus(
            pipelines=pipelines,
            model=model,
            infra=infra,
            overall_status=overall,
        )

    async def rollback_model(self, target_version: str) -> ModelRollbackResponse:
        previous = type(self)._deployed_version
        if not target_version.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_version must be non-empty",
            )
        if target_version == previous:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Model {target_version} is already deployed",
            )
        type(self)._deployed_version = target_version
        return ModelRollbackResponse(
            rolled_back_from=previous,
            rolled_back_to=target_version,
            at=datetime.now(UTC),
        )

    async def trigger_retrain(self) -> dict[str, str]:
        # Real impl fires a Prefect flow / queue message; stub returns a
        # synthetic job id so the UI can show "Retrain queued".
        return {"status": "queued", "jobId": f"retrain_{uuid.uuid4().hex[:8]}"}


_DEFAULT_PROVIDER: AdminProvider = StubAdminProvider()


def get_admin_provider() -> AdminProvider:
    """Return the process-wide admin provider (overridden in tests)."""
    return _DEFAULT_PROVIDER


def require_admin(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Enforce an authenticated admin caller.

    Reads ``user_id`` and ``user_role`` off ``request.state`` (set by
    :class:`ClerkAuthMiddleware`). Raises 401 if the user id is missing
    (middleware didn't run / token was invalid) and 403 if the role is
    anything other than ``admin``.

    TODO(SPO-A-09): the Clerk middleware currently only injects
    ``user_id``. Role must come from the users table (or a Clerk public
    metadata claim) before this dependency is production-safe. Until
    then, the ``env == "dev"`` escape hatch below lets the local stack
    treat any authenticated user as admin -- in ``test`` / ``prod`` the
    strict check applies.
    """
    user_id = getattr(request.state, "user_id", None)
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user context missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_role = getattr(request.state, "user_role", None)
    if settings.env == "dev" and user_role is None:
        # Dev-only convenience: stub middleware hasn't been extended yet.
        # In prod / staging / test this branch doesn't fire, so the strict
        # check below is authoritative.
        return user_id

    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user_id


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=list[AdminUser],
    response_model_by_alias=True,
    summary="List all users with engagement + revenue metadata",
)
async def list_users(
    admin_id: Annotated[str, Depends(require_admin)],
    provider: Annotated[AdminProvider, Depends(get_admin_provider)],
) -> list[AdminUser]:
    """Return every user, newest join first.

    No pagination yet -- in alpha the list is small. Add cursor-based
    pagination once we cross 200 accounts.
    """
    return await provider.list_users()


@router.patch(
    "/users/{user_id}",
    response_model=AdminUser,
    response_model_by_alias=True,
    summary="Admin patch for a single user (plan, status)",
)
async def update_user(
    user_id: str,
    update: UserUpdateAdmin,
    admin_id: Annotated[str, Depends(require_admin)],
    provider: Annotated[AdminProvider, Depends(get_admin_provider)],
) -> AdminUser:
    """Change a user's plan or activation status.

    Partial-update semantics match ``PATCH /users/me``: unset fields are
    left alone; explicit ``null`` is rejected by the Pydantic model.
    """
    return await provider.update_user(user_id, update)


@router.get(
    "/system",
    response_model=SystemStatus,
    response_model_by_alias=True,
    summary="Composite system status (pipelines + model + infra)",
)
async def get_system(
    admin_id: Annotated[str, Depends(require_admin)],
    provider: Annotated[AdminProvider, Depends(get_admin_provider)],
) -> SystemStatus:
    """Return pipelines, the deployed model, and per-host infra metrics.

    Single-fetch design so the admin dashboard renders on page load
    without a waterfall of requests.
    """
    return await provider.get_system_status()


@router.post(
    "/model/rollback",
    response_model=ModelRollbackResponse,
    response_model_by_alias=True,
    summary="Emergency rollback to a previous model version",
)
async def rollback_model(
    body: ModelRollbackRequest,
    admin_id: Annotated[str, Depends(require_admin)],
    provider: Annotated[AdminProvider, Depends(get_admin_provider)],
) -> ModelRollbackResponse:
    """Point the serving infra at ``body.target_version``.

    Returns both the previous and new versions so the admin UI can show
    the swap in a toast and the audit log captures both ends.
    """
    return await provider.rollback_model(body.target_version)


@router.post(
    "/model/retrain",
    summary="Kick off a training pipeline run",
)
async def trigger_retrain(
    admin_id: Annotated[str, Depends(require_admin)],
    provider: Annotated[AdminProvider, Depends(get_admin_provider)],
) -> dict[str, str]:
    """Enqueue a retrain job.

    Returns ``{"status": "queued", "jobId": "..."}``. The stub is fully
    synchronous -- production fires a Prefect flow and the job id is the
    flow-run uuid.
    """
    return await provider.trigger_retrain()

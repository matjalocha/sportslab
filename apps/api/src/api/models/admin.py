"""Admin-surface payloads for operational dashboards.

These models back ``/api/v1/admin/...`` -- the control plane the founder
(and later ops team) use to see user engagement, pipeline health, model
drift, and infra load at a glance. They are *not* exposed to ordinary
customers: every handler sits behind :func:`require_admin`.

Wire shape mirrors the sportslab-web admin dashboard's TypeScript types
so the generated OpenAPI client round-trips without hand rewrites --
camelCase on the wire, snake_case in Python, ``populate_by_name=True``
on every model.

Scope caveat: exactly like :mod:`api.models.users`, the schemas are the
contract; persistence (DB-backed providers reading from Postgres, MLflow,
and node-exporter) lands in later tickets. Until then
:class:`StubAdminProvider` returns deterministic fixtures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from api.models.users import Plan, Role

UserStatus = Literal["active", "disabled", "invited"]
PipelineStatus = Literal["ok", "running", "failed", "stale"]
ModelStatus = Literal["deployed", "canary", "retired"]
OverallStatus = Literal["healthy", "degraded", "down"]


class AdminUser(BaseModel):
    """A user row in the admin console.

    Adds engagement and revenue fields to :class:`UserProfile`: MRR,
    tracked-bet count, last-seen timestamp, account status. Admins edit
    ``plan`` and ``status`` via :class:`UserUpdateAdmin`; everything else
    is read-only on this surface.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    email: EmailStr
    full_name: str | None = Field(None, alias="fullName")
    plan: Plan
    role: Role
    status: UserStatus
    last_active_at: datetime | None = Field(None, alias="lastActiveAt")
    mrr_eur: float = Field(..., alias="mrrEur")
    bets_tracked: int = Field(..., alias="betsTracked")
    joined_at: datetime = Field(..., alias="joinedAt")


class UserUpdateAdmin(BaseModel):
    """Admin-level patch body for ``PATCH /admin/users/{id}``.

    Admins can change ``plan`` (e.g. comp an account up to ``pro``) and
    ``status`` (disable a bad actor, invite a new alpha). ``None`` means
    "leave untouched" -- explicit ``null`` is rejected by the schema.
    """

    model_config = ConfigDict(populate_by_name=True)

    plan: Plan | None = None
    status: UserStatus | None = None


class PipelineRun(BaseModel):
    """A single batch-pipeline snapshot for the system-status page.

    One row per named pipeline (scrapers, feature-builder, training,
    publish). ``message`` is the last human-readable status line -- green
    runs carry ``"ok"``, failures carry the exception summary.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str
    status: PipelineStatus
    last_run_at: datetime = Field(..., alias="lastRunAt")
    duration_seconds: float = Field(..., alias="durationSeconds")
    next_run_at: datetime | None = Field(None, alias="nextRunAt")
    message: str


class ModelVersion(BaseModel):
    """Currently-deployed model summary, shown on the admin dashboard.

    ``ece_overall`` / ``log_loss`` / ``brier`` are read off the latest
    MLflow run. ``trained_on`` is the training cutoff (ISO date). The
    rollback endpoint uses ``version`` as its target identifier.
    """

    model_config = ConfigDict(populate_by_name=True)

    version: str
    deployed_at: datetime = Field(..., alias="deployedAt")
    status: ModelStatus
    ece_overall: float = Field(..., alias="eceOverall")
    log_loss: float = Field(..., alias="logLoss")
    brier: float
    trained_on: str = Field(..., alias="trainedOn")
    features_count: int = Field(..., alias="featuresCount")


class InfraMetric(BaseModel):
    """Per-host resource snapshot (Hetzner node, worker, db).

    Sourced from node-exporter in production. In the stub we return
    deterministic fake numbers so the frontend can render gauges without
    waiting on infra wiring.
    """

    model_config = ConfigDict(populate_by_name=True)

    host: str
    cpu_percent: float = Field(..., alias="cpuPercent")
    ram_percent: float = Field(..., alias="ramPercent")
    disk_percent: float = Field(..., alias="diskPercent")
    temperature_c: float | None = Field(None, alias="temperatureC")
    uptime_hours: float = Field(..., alias="uptimeHours")


class SystemStatus(BaseModel):
    """Composite system-status payload for ``GET /admin/system``.

    Aggregates pipeline runs, the live model, and per-host infra metrics
    into a single response so the admin dashboard only needs one fetch
    on page load. ``overall_status`` is a computed rollup.
    """

    model_config = ConfigDict(populate_by_name=True)

    pipelines: list[PipelineRun]
    model: ModelVersion
    infra: list[InfraMetric]
    overall_status: OverallStatus = Field(..., alias="overallStatus")


class ModelRollbackRequest(BaseModel):
    """Body for ``POST /admin/model/rollback``.

    ``target_version`` must match a retired MLflow run. The stub accepts
    any non-empty string; production validates against MLflow.
    """

    model_config = ConfigDict(populate_by_name=True)

    target_version: str = Field(..., alias="targetVersion", min_length=1)


class ModelRollbackResponse(BaseModel):
    """Response payload confirming a rollback.

    Includes both ``rolled_back_from`` and ``rolled_back_to`` so the
    audit log (and the admin UI toast) can show the exact swap.
    """

    model_config = ConfigDict(populate_by_name=True)

    rolled_back_from: str = Field(..., alias="rolledBackFrom")
    rolled_back_to: str = Field(..., alias="rolledBackTo")
    at: datetime


class InviteUserRequest(BaseModel):
    """Body for ``POST /admin/users`` -- founder-invited alpha/pro accounts.

    Admin-only flow: the caller supplies an email and optional initial
    plan; the backend creates a ``status="invited"`` record and (in
    production) dispatches the invite email via the transactional-email
    provider. ``notes`` is a private admin-facing memo (why they were
    invited, which partner referred them) and is NOT surfaced to the
    invitee.
    """

    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    plan: Plan = "alpha"
    notes: str | None = None

"""Response / error payloads shared across routers."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Payload returned by ``GET /api/v1/health``."""

    status: str = Field(description="Always ``ok`` when the process is alive.")
    version: str = Field(description="API semver, mirrors ``Settings.api_version``.")
    timestamp: str = Field(description="ISO-8601 UTC timestamp at response time.")


class ErrorResponse(BaseModel):
    """Generic error payload used by exception handlers.

    OpenAPI consumers (e.g. the generated TypeScript client) use this
    schema when a 4xx / 5xx response is documented.
    """

    detail: str = Field(description="Human-readable error message.")
    code: str | None = Field(
        default=None,
        description="Stable machine-readable code (e.g. ``auth.token_expired``).",
    )

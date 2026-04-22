"""Clerk JWT verification middleware.

Verifies the ``Authorization: Bearer <jwt>`` header against Clerk's JWKS
endpoint and injects ``request.state.user_id`` for downstream routers.

Public routes (health, docs, OpenAPI schema) bypass verification. Every
other route returns 401 on missing or invalid token.

Notes:
    - JWKS is fetched lazily on first request and cached in-process for
      1 hour (``_JWKS_TTL``). On token verification failure we refetch
      once in case of key rotation.
    - We verify ``kid`` against the cached JWKS and, if missing, force a
      refresh before failing.
    - ``python-jose`` is used over ``authlib`` because it has simpler JWKS
      handling and is already widely deployed at Clerk's own docs.
"""

from __future__ import annotations

import time
from typing import Any, ClassVar

import httpx
import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from jose import jwt
from jose.exceptions import JWTError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from api.config import Settings

_JWKS_TTL_SECONDS = 3_600  # 1 hour
# ``/api/v1/webhooks/*`` bypasses Clerk JWT auth because each webhook carries
# its own provider-specific signature (Svix for Clerk, HMAC for Stripe). No
# Clerk session exists when Stripe or Clerk's own webhook dispatcher POSTs
# to us, so enforcing Bearer auth would 401 every legitimate delivery.
_PUBLIC_PATH_PREFIXES = (
    "/api/v1/health",
    "/api/v1/webhooks",
    "/docs",
    "/openapi.json",
    "/redoc",
)

_logger = structlog.get_logger(__name__)


class ClerkJWKSCache:
    """Process-local JWKS cache with TTL and forced-refresh support.

    Not thread-safe in the strict sense, but FastAPI's async event loop
    serializes access to the middleware instance and a stale read just
    triggers one extra HTTP roundtrip — acceptable.
    """

    def __init__(self, jwks_url: str, ttl_seconds: int = _JWKS_TTL_SECONDS) -> None:
        self._jwks_url = jwks_url
        self._ttl_seconds = ttl_seconds
        self._cache: dict[str, Any] | None = None
        self._expires_at: float = 0.0

    async def get(self, *, force_refresh: bool = False) -> dict[str, Any]:
        """Return the JWKS payload, refetching if stale or forced."""
        now = time.monotonic()
        if not force_refresh and self._cache is not None and now < self._expires_at:
            return self._cache

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(self._jwks_url)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        self._cache = payload
        self._expires_at = now + self._ttl_seconds
        _logger.debug("clerk_jwks_refreshed", url=self._jwks_url, keys=len(payload.get("keys", [])))
        return payload


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces Clerk JWT auth on protected routes."""

    # Clerk RS256 is the default; HS256 is not supported on JWKS-based flows.
    _ALLOWED_ALGORITHMS: ClassVar[tuple[str, ...]] = ("RS256",)

    def __init__(self, app: Any, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings
        self._jwks = ClerkJWKSCache(settings.clerk_jwks_url)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if self._is_public(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _unauthorized("Missing or malformed Authorization header", "auth.missing_token")

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return _unauthorized("Empty bearer token", "auth.missing_token")

        try:
            claims = await self._verify_token(token)
        except JWTError as error:
            _logger.warning("clerk_jwt_invalid", reason=str(error))
            return _unauthorized("Invalid or expired token", "auth.invalid_token")
        except httpx.HTTPError as error:
            _logger.error("clerk_jwks_fetch_failed", reason=str(error))
            return _unauthorized("Auth provider unavailable", "auth.provider_unavailable")

        user_id = claims.get("sub")
        if not isinstance(user_id, str) or not user_id:
            _logger.warning("clerk_jwt_missing_sub", claims_keys=list(claims.keys()))
            return _unauthorized("Token missing subject claim", "auth.invalid_token")

        request.state.user_id = user_id
        request.state.claims = claims
        return await call_next(request)

    @staticmethod
    def _is_public(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in _PUBLIC_PATH_PREFIXES)

    async def _verify_token(self, token: str) -> dict[str, Any]:
        """Validate ``token`` against Clerk JWKS. Raises ``JWTError`` on failure."""
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise JWTError("Token header missing 'kid'")

        signing_key = await self._find_key(kid, force_refresh=False)
        if signing_key is None:
            # Possible key rotation — force refresh and retry once.
            signing_key = await self._find_key(kid, force_refresh=True)
        if signing_key is None:
            raise JWTError(f"No JWKS key matches kid={kid}")

        # Clerk issues audienceless tokens for session JWTs; skip aud verification.
        # Issuer check is left to Clerk's own JWT template configuration.
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key,
            algorithms=list(self._ALLOWED_ALGORITHMS),
            options={"verify_aud": False},
        )
        return claims

    async def _find_key(self, kid: str, *, force_refresh: bool) -> dict[str, Any] | None:
        jwks = await self._jwks.get(force_refresh=force_refresh)
        keys = jwks.get("keys", [])
        for key in keys:
            if key.get("kid") == kid:
                return key  # type: ignore[no-any-return]
        return None


def _unauthorized(detail: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": detail, "code": code},
        headers={"WWW-Authenticate": "Bearer"},
    )

"""User management endpoints -- onboarding, profile, bet tracking.

All routes live at ``/api/v1/users/...`` and require a valid Clerk JWT
(enforced by :class:`api.middleware.clerk_auth.ClerkAuthMiddleware`).
``user_id`` is resolved from ``request.state.user_id`` via the
:func:`get_current_user_id` dependency -- never trusted from the body.

Current backing store is an in-memory :class:`StubUsersProvider`. The DB
schema (Postgres ``users`` + ``user_bets`` tables, Alembic migration,
foreign keys, uniqueness constraints) is explicitly deferred to A-09
(SQLite -> Postgres). Until then, restarting the API drops all users --
acceptable for dev and CI, not for staging.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, date, datetime
from typing import Annotated, ClassVar

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.models.users import (
    BankrollTier,
    OnboardRequest,
    UserBet,
    UserBetCreate,
    UserProfile,
    UserProfileUpdate,
)

# Rough mid-point EUR per bankroll tier. Users can override via PATCH.
_BANKROLL_TIER_DEFAULTS: dict[BankrollTier, float] = {
    "under_1k": 500.0,
    "1k_5k": 2_500.0,
    "5k_25k": 12_500.0,
    "25k_plus": 50_000.0,
}


class UsersProvider(ABC):
    """Storage contract for user profiles and tracked bets.

    Implementations must be safe to call concurrently per-user -- the API
    layer runs multiple workers and a single user may fire overlapping
    PATCH/POST requests.
    """

    @abstractmethod
    async def onboard(self, user_id: str, request: OnboardRequest) -> UserProfile: ...

    @abstractmethod
    async def get_profile(self, user_id: str) -> UserProfile | None: ...

    @abstractmethod
    async def update_profile(self, user_id: str, update: UserProfileUpdate) -> UserProfile: ...

    @abstractmethod
    async def get_bets(
        self,
        user_id: str,
        since: date | None,
        status_filter: str | None,
    ) -> list[UserBet]: ...

    @abstractmethod
    async def create_bet(self, user_id: str, bet: UserBetCreate) -> UserBet: ...


class StubUsersProvider(UsersProvider):
    """In-memory dict-backed provider for dev, CI, and tests.

    State lives on the class (not instance) so a single FastAPI process
    sees consistent data across requests without explicit wiring. Replaced
    by a SQLAlchemy-backed provider in A-09.

    Scope caveat: ``follows_model`` on new bets is always ``False`` here
    -- matching against the pick catalog is a DB join that belongs in the
    Postgres-backed provider.
    """

    _users: ClassVar[dict[str, UserProfile]] = {}
    _bets: ClassVar[dict[str, list[UserBet]]] = {}

    @classmethod
    def reset(cls) -> None:
        """Wipe state. Tests only -- production callers must never rely on this."""
        cls._users.clear()
        cls._bets.clear()

    async def onboard(self, user_id: str, request: OnboardRequest) -> UserProfile:
        profile = UserProfile(
            id=user_id,
            email=request.email,
            full_name=None,
            telegram_handle=request.telegram_handle,
            plan="alpha",
            role="user",
            bankroll_eur=_BANKROLL_TIER_DEFAULTS[request.bankroll_tier],
            leagues_selected=[],
            markets_selected=[],
            odds_format="decimal",
            created_at=datetime.now(UTC),
        )
        self._users[user_id] = profile
        self._bets.setdefault(user_id, [])
        return profile

    async def get_profile(self, user_id: str) -> UserProfile | None:
        return self._users.get(user_id)

    async def update_profile(self, user_id: str, update: UserProfileUpdate) -> UserProfile:
        existing = self._users.get(user_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found; call /users/onboard first.",
            )

        # ``model_dump(exclude_unset=True)`` preserves "untouched" semantics --
        # explicit ``null`` in the body still clears the field.
        patch = update.model_dump(exclude_unset=True)
        updated = existing.model_copy(update=patch)
        self._users[user_id] = updated
        return updated

    async def get_bets(
        self,
        user_id: str,
        since: date | None,
        status_filter: str | None,
    ) -> list[UserBet]:
        bets = self._bets.get(user_id, [])
        if since is not None:
            bets = [bet for bet in bets if bet.placed_at.date() >= since]
        if status_filter is not None:
            bets = [bet for bet in bets if bet.outcome == status_filter]
        return bets

    async def create_bet(self, user_id: str, bet: UserBetCreate) -> UserBet:
        if user_id not in self._users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found; call /users/onboard first.",
            )
        new_bet = UserBet(
            id=str(uuid.uuid4()),
            match_id=bet.match_id,
            market=bet.market,
            selection=bet.selection,
            stake_eur=bet.stake_eur,
            odds=bet.odds,
            bookmaker=bet.bookmaker,
            placed_at=datetime.now(UTC),
            outcome="pending",
            pnl_eur=None,
            # Real attribution requires a lookup in the pick catalog --
            # deferred to the Postgres-backed provider.
            follows_model=False,
        )
        self._bets.setdefault(user_id, []).append(new_bet)
        return new_bet


_DEFAULT_PROVIDER = StubUsersProvider()


def get_users_provider() -> UsersProvider:
    """Return the process-wide users provider.

    Overridden in tests via ``app.dependency_overrides`` to inject a fresh
    stub per test case.
    """
    return _DEFAULT_PROVIDER


def get_current_user_id(request: Request) -> str:
    """Pull ``user_id`` off the request state set by ``ClerkAuthMiddleware``.

    A missing value means the middleware didn't run (route misconfigured
    as public) or the test harness bypassed it -- either way, 401 is the
    correct response from the router's perspective.
    """
    user_id = getattr(request.state, "user_id", None)
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user context missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


router = APIRouter(tags=["users"])


@router.post(
    "/users/onboard",
    response_model=UserProfile,
    summary="Create (idempotent) the current user's profile",
)
async def onboard_user(
    request_body: OnboardRequest,
    provider: Annotated[UsersProvider, Depends(get_users_provider)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UserProfile:
    """Idempotent onboarding.

    Called by the web onboarding wizard after Clerk sign-up. If a profile
    already exists for this ``user_id``, we return it unchanged so client
    retries (network flakes, double-submits) stay safe.
    """
    existing = await provider.get_profile(user_id)
    if existing is not None:
        return existing
    return await provider.onboard(user_id, request_body)


@router.get(
    "/users/me",
    response_model=UserProfile,
    summary="Get the authenticated user's profile",
    responses={404: {"description": "Profile not onboarded yet."}},
)
async def get_me(
    provider: Annotated[UsersProvider, Depends(get_users_provider)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UserProfile:
    """Return the full profile.

    A 404 here tells the frontend to redirect to the onboarding wizard --
    Clerk auth succeeded but we've never seen this ``user_id`` before.
    """
    profile = await provider.get_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found; call /users/onboard first.",
        )
    return profile


@router.patch(
    "/users/me",
    response_model=UserProfile,
    summary="Partially update the authenticated user's profile",
)
async def update_me(
    update: UserProfileUpdate,
    provider: Annotated[UsersProvider, Depends(get_users_provider)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UserProfile:
    """Apply a partial update.

    Only fields explicitly present in the body are modified -- unset fields
    are left alone. ``plan`` and ``role`` are deliberately not patchable
    here; those change via billing webhooks / admin actions respectively.
    """
    return await provider.update_profile(user_id, update)


@router.get(
    "/users/me/bets",
    response_model=list[UserBet],
    summary="List the authenticated user's tracked bets",
)
async def get_my_bets(
    provider: Annotated[UsersProvider, Depends(get_users_provider)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    since: Annotated[
        date | None,
        Query(description="Only return bets placed on or after this date (UTC)."),
    ] = None,
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            description="Filter by outcome (pending, won, lost, push, void).",
        ),
    ] = None,
) -> list[UserBet]:
    """Return the user's tracked bets with optional filters.

    No pagination yet -- alpha users track tens of bets, not thousands. Add
    cursor pagination in A-09 when the DB is in play.
    """
    return await provider.get_bets(user_id, since, status_filter)


@router.post(
    "/users/me/bets",
    response_model=UserBet,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new tracked bet for the authenticated user",
)
async def create_my_bet(
    bet: UserBetCreate,
    provider: Annotated[UsersProvider, Depends(get_users_provider)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UserBet:
    """Record a new tracked bet.

    Server sets ``id``, ``placed_at``, ``outcome=pending``. Settlement
    (updating outcome / pnl_eur) happens via a separate endpoint in A-09.
    """
    return await provider.create_bet(user_id, bet)

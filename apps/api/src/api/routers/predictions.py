"""Predictions API — published value bets and settled results.

Endpoints mounted at ``/api/v1/predictions``:

    GET /latest                  -> 302 redirect to today's date (Europe/Warsaw)
    GET /{target_date}           -> list[BetRecommendation]
    GET /{target_date}/results   -> list[BetResult] (refuses future dates)

A ``PredictionsProvider`` ABC separates the HTTP surface from the data
source. ``StubPredictionsProvider`` returns hand-rolled mock rows so the
frontend (and tests) can integrate against the real endpoint shape
before the SQLAlchemy-backed provider lands in SPO-A-09.

Auth: all three routes sit behind ``ClerkAuthMiddleware`` — a missing
or malformed Bearer token results in 401 with ``WWW-Authenticate: Bearer``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import RedirectResponse

from api.models.predictions import (
    BetRecommendation,
    BetResult,
    Match,
    Team,
)

_WARSAW = ZoneInfo("Europe/Warsaw")


class PredictionsProvider(ABC):
    """Data source abstraction — stub today, SQLAlchemy tomorrow."""

    @abstractmethod
    async def get_predictions(self, target_date: date) -> list[BetRecommendation]:
        """Return published picks for ``target_date`` (Europe/Warsaw calendar day)."""

    @abstractmethod
    async def get_results(self, target_date: date) -> list[BetResult]:
        """Return settled results for ``target_date``."""


class StubPredictionsProvider(PredictionsProvider):
    """Hand-rolled deterministic fixtures.

    Intentionally returns the same 5 picks for any date so the frontend
    gets predictable content during integration. Replace with a real
    SQLAlchemy-backed provider once SPO-A-09 (DB schema) lands.
    """

    async def get_predictions(self, target_date: date) -> list[BetRecommendation]:
        kickoff_base = datetime.combine(
            target_date, datetime.min.time(), tzinfo=_WARSAW
        ).astimezone(UTC) + timedelta(hours=18)
        published = datetime.now(UTC) - timedelta(hours=12)

        fixtures: list[tuple[str, str, str, str, str, str, str]] = [
            (
                "mancity",
                "Manchester City",
                "Man City",
                "arsenal",
                "Arsenal",
                "Arsenal",
                "Premier League",
            ),
            ("realmadrid", "Real Madrid", "Real", "barcelona", "FC Barcelona", "Barca", "La Liga"),
            (
                "bayern",
                "Bayern München",
                "Bayern",
                "dortmund",
                "Borussia Dortmund",
                "BVB",
                "Bundesliga",
            ),
            ("inter", "Inter Milan", "Inter", "juventus", "Juventus", "Juve", "Serie A"),
            ("psg", "Paris Saint-Germain", "PSG", "lyon", "Olympique Lyon", "Lyon", "Ligue 1"),
        ]

        picks: list[BetRecommendation] = []
        for index, (
            home_id,
            home_name,
            home_short,
            away_id,
            away_name,
            away_short,
            league,
        ) in enumerate(fixtures):
            match = Match(
                id=f"match_{target_date.isoformat()}_{home_id}_{away_id}",
                kickoff_utc=kickoff_base + timedelta(hours=index * 2),
                league=league,
                home=Team(id=f"team_{home_id}", name=home_name, short_name=home_short),
                away=Team(id=f"team_{away_id}", name=away_name, short_name=away_short),
            )
            model_probability = 0.55 + index * 0.02
            best_odds = 2.10 - index * 0.05
            bookmaker_probability = 1.0 / best_odds
            edge_percent = (
                (model_probability - bookmaker_probability) / bookmaker_probability * 100.0
            )
            kelly_fraction = 0.25
            kelly_stake = round(kelly_fraction * edge_percent, 2) if edge_percent > 0 else 0.0
            confidence_tier = "high" if index < 2 else "medium" if index < 4 else "low"

            picks.append(
                BetRecommendation(
                    id=f"rec_{target_date.isoformat()}_{index}",
                    match=match,
                    market="1X2",
                    selection="HOME",
                    model_probability=round(model_probability, 4),
                    bookmaker_probability=round(bookmaker_probability, 4),
                    edge_percent=round(edge_percent, 2),
                    best_odds=round(best_odds, 2),
                    bookmaker="Pinnacle",
                    kelly_stake=kelly_stake,
                    kelly_fraction=kelly_fraction,
                    confidence=confidence_tier,
                    ece=0.015 + index * 0.002,
                    published=published,
                )
            )
        return picks

    async def get_results(self, target_date: date) -> list[BetResult]:
        predictions = await self.get_predictions(target_date)
        settled_at = datetime.combine(
            target_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC
        )
        outcomes: list[tuple[str, float]] = [
            ("won", 1.0),
            ("won", 1.0),
            ("lost", -1.0),
            ("won", 1.0),
            ("void", 0.0),
        ]

        results: list[BetResult] = []
        for recommendation, (outcome, multiplier) in zip(predictions, outcomes, strict=False):
            stake = 10.0
            if outcome == "won":
                profit = round(stake * (recommendation.best_odds - 1.0), 2)
            elif outcome == "lost":
                profit = -stake
            else:
                profit = 0.0
            results.append(
                BetResult(
                    id=f"result_{recommendation.id}",
                    recommendation=recommendation,
                    status=outcome,  # type: ignore[arg-type]
                    placed_at_odds=recommendation.best_odds,
                    stake_eur=stake,
                    profit_eur=profit * multiplier / 1.0 if multiplier else profit,
                    clv=0.015,
                    settled_at=settled_at,
                )
            )
        return results


_default_provider: PredictionsProvider = StubPredictionsProvider()


def get_predictions_provider() -> PredictionsProvider:
    """Dependency hook — tests override this via ``app.dependency_overrides``."""
    return _default_provider


router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/latest", summary="Redirect to today's predictions")
async def latest() -> RedirectResponse:
    """302 to ``/api/v1/predictions/{today}`` using Europe/Warsaw as the
    publishing calendar (matches when picks actually become visible).
    """
    today = datetime.now(_WARSAW).date()
    return RedirectResponse(
        url=f"/api/v1/predictions/{today.isoformat()}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get(
    "/{target_date}",
    response_model=list[BetRecommendation],
    response_model_by_alias=True,
    summary="List published picks for a given date",
)
async def get_predictions(
    target_date: date,
    provider: Annotated[PredictionsProvider, Depends(get_predictions_provider)],
) -> list[BetRecommendation]:
    """Return all value-bet recommendations scheduled to kick off on ``target_date``."""
    picks = await provider.get_predictions(target_date)
    if not picks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No predictions for this date",
        )
    return picks


@router.get(
    "/{target_date}/results",
    response_model=list[BetResult],
    response_model_by_alias=True,
    summary="List settled results for a past date",
)
async def get_results(
    target_date: date,
    provider: Annotated[PredictionsProvider, Depends(get_predictions_provider)],
) -> list[BetResult]:
    """Return settled results. Future or same-day requests get 425 Too Early."""
    today = datetime.now(_WARSAW).date()
    if target_date >= today:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="Results not yet available",
        )
    results = await provider.get_results(target_date)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No settled results",
        )
    return results

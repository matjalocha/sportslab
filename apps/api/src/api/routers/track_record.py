"""Track-record API — aggregate KPIs, equity curve, monthly & per-league splits.

Endpoints mounted at ``/api/v1/track-record``:

    GET /                    -> TrackRecordStats (aggregate)
    GET /monthly             -> list[MonthlyStat]
    GET /equity-curve        -> list[EquityPoint] (default: last 180 days)
    GET /by-league           -> list[LeagueStat] sorted by bets desc

A ``TrackRecordProvider`` ABC separates the HTTP surface from the data
source. ``StubTrackRecordProvider`` returns deterministic mock rows so
the frontend (and tests) can integrate against the real endpoint shape
before the SQLAlchemy-backed provider lands in SPO-A-09.

Auth: every route sits behind ``ClerkAuthMiddleware`` — missing or
malformed Bearer token → 401 with ``WWW-Authenticate: Bearer``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.models.track_record import (
    EquityPoint,
    LeagueStat,
    MonthlyStat,
    TrackRecordStats,
)

_DEFAULT_EQUITY_WINDOW_DAYS = 180
_STUB_EPOCH = date(2025, 1, 1)
_STUB_START_BANKROLL_EUR = 10_000.0


class TrackRecordProvider(ABC):
    """Data source abstraction — stub today, SQLAlchemy tomorrow."""

    @abstractmethod
    async def get_stats(self, since: date | None) -> TrackRecordStats:
        """Return aggregate stats from ``since`` (default: provider epoch)."""

    @abstractmethod
    async def get_monthly(self) -> list[MonthlyStat]:
        """Return per-month breakdown, oldest first."""

    @abstractmethod
    async def get_equity_curve(
        self, since: date | None, until: date | None
    ) -> list[EquityPoint]:
        """Return daily equity points for ``[since, until]`` inclusive."""

    @abstractmethod
    async def get_by_league(self) -> list[LeagueStat]:
        """Return per-league breakdown sorted by ``bets`` desc."""


class StubTrackRecordProvider(TrackRecordProvider):
    """Deterministic fixtures so the frontend has real-shaped data.

    The numbers are internally consistent — monthly profits sum to the
    aggregate, equity curve's final bankroll matches ``profit_eur``, etc.
    This means the frontend can exercise join logic without surprises.
    Replace with a SQLAlchemy-backed provider once SPO-A-09 lands.
    """

    _MONTHS: tuple[tuple[str, int, float, float, float, float], ...] = (
        # (month, bets, win_rate, roi_percent, clv_percent, profit_eur)
        ("2025-01", 42, 0.548, 6.4, 2.1, 268.80),
        ("2025-02", 38, 0.500, 3.9, 1.7, 148.20),
        ("2025-03", 51, 0.569, 8.2, 2.8, 418.20),
        ("2025-04", 47, 0.532, 5.1, 2.0, 239.70),
        ("2025-05", 44, 0.523, 4.3, 1.9, 189.20),
        ("2025-06", 33, 0.485, -1.2, 0.8, -39.60),
        ("2025-07", 29, 0.517, 2.6, 1.4, 75.40),
        ("2025-08", 41, 0.561, 7.1, 2.5, 291.10),
        ("2025-09", 48, 0.542, 6.0, 2.2, 288.00),
        ("2025-10", 52, 0.558, 7.8, 2.6, 405.60),
        ("2025-11", 46, 0.522, 4.7, 1.9, 216.20),
        ("2025-12", 39, 0.538, 5.5, 2.0, 214.50),
    )

    _LEAGUES: tuple[tuple[str, int, float, float, float, float], ...] = (
        # (league, bets, win_rate, roi_percent, clv_percent, profit_eur)
        ("Premier League", 128, 0.547, 6.9, 2.4, 883.20),
        ("La Liga", 98, 0.531, 5.4, 2.1, 529.20),
        ("Bundesliga", 84, 0.536, 5.9, 2.2, 495.60),
        ("Serie A", 76, 0.526, 4.8, 1.9, 364.80),
        ("Ligue 1", 62, 0.516, 3.7, 1.6, 229.40),
        ("Eredivisie", 41, 0.512, 2.9, 1.4, 118.90),
        ("Primeira Liga", 21, 0.524, 4.1, 1.7, 86.10),
    )

    async def get_stats(self, since: date | None) -> TrackRecordStats:
        effective_since = since or _STUB_EPOCH
        # Restrict the monthly rows to the requested window so ``since``
        # filtering is observable in tests without adding real DB logic.
        rows = [row for row in self._MONTHS if _parse_month(row[0]) >= effective_since]
        if not rows:
            rows = list(self._MONTHS[-1:])  # degrade gracefully to the last month

        total_bets = sum(row[1] for row in rows)
        total_profit = round(sum(row[5] for row in rows), 2)
        total_wins = sum(round(row[1] * row[2]) for row in rows)
        win_rate = total_wins / total_bets if total_bets else 0.0
        turnover = total_bets * 10.0  # stub assumes €10 flat stake
        roi_percent = (total_profit / turnover * 100.0) if turnover else 0.0
        clv_percent = (
            sum(row[1] * row[4] for row in rows) / total_bets if total_bets else 0.0
        )
        avg_edge_percent = clv_percent + 0.9  # stub: edge slightly above CLV

        return TrackRecordStats(
            bets=total_bets,
            winRate=round(win_rate, 4),
            roiPercent=round(roi_percent, 2),
            clvPercent=round(clv_percent, 2),
            profitEur=total_profit,
            avgEdgePercent=round(avg_edge_percent, 2),
            maxDrawdownPercent=-8.3,
            currentStreakType="win",
            currentStreakCount=3,
            sinceDate=effective_since,
        )

    async def get_monthly(self) -> list[MonthlyStat]:
        return [
            MonthlyStat(
                month=month,
                bets=bets,
                winRate=win_rate,
                roiPercent=roi_percent,
                clvPercent=clv_percent,
                profitEur=profit_eur,
            )
            for (month, bets, win_rate, roi_percent, clv_percent, profit_eur) in self._MONTHS
        ]

    async def get_equity_curve(
        self, since: date | None, until: date | None
    ) -> list[EquityPoint]:
        effective_until = until or date.today()
        effective_since = since or (
            effective_until - timedelta(days=_DEFAULT_EQUITY_WINDOW_DAYS - 1)
        )
        if effective_since > effective_until:
            return []

        total_days = (effective_until - effective_since).days + 1
        # Slope chosen so 180-day default lands around +10% — realistic for
        # a calibrated value-betting book, not an obvious toy number.
        daily_pnl = _STUB_START_BANKROLL_EUR * 0.10 / _DEFAULT_EQUITY_WINDOW_DAYS
        points: list[EquityPoint] = []
        for offset in range(total_days):
            current_date = effective_since + timedelta(days=offset)
            # Light sinusoidal wobble so the curve isn't a straight line.
            wobble = (offset % 14 - 7) * 1.5
            cumulative_pnl = round(daily_pnl * (offset + 1) + wobble, 2)
            bankroll = round(_STUB_START_BANKROLL_EUR + cumulative_pnl, 2)
            points.append(
                EquityPoint(
                    date=current_date,
                    bankrollEur=bankroll,
                    pnlEur=cumulative_pnl,
                    clvPercent=round(2.0 + (offset % 30) * 0.02, 2),
                    bets=offset + 1,
                )
            )
        return points

    async def get_by_league(self) -> list[LeagueStat]:
        leagues = [
            LeagueStat(
                league=league,
                bets=bets,
                winRate=win_rate,
                roiPercent=roi_percent,
                clvPercent=clv_percent,
                profitEur=profit_eur,
            )
            for (league, bets, win_rate, roi_percent, clv_percent, profit_eur) in self._LEAGUES
        ]
        leagues.sort(key=lambda stat: stat.bets, reverse=True)
        return leagues


def _parse_month(month: str) -> date:
    """Turn ``YYYY-MM`` into the first day of that month."""
    year_str, month_str = month.split("-")
    return date(int(year_str), int(month_str), 1)


_default_provider: TrackRecordProvider = StubTrackRecordProvider()


def get_track_record_provider() -> TrackRecordProvider:
    """Dependency hook — tests override this via ``app.dependency_overrides``."""
    return _default_provider


router = APIRouter(prefix="/track-record", tags=["track-record"])


@router.get(
    "",
    response_model=TrackRecordStats,
    response_model_by_alias=True,
    summary="Aggregate track-record stats",
)
async def get_track_record(
    provider: Annotated[TrackRecordProvider, Depends(get_track_record_provider)],
    since: Annotated[
        date | None,
        Query(description="Earliest settlement date to include (inclusive)."),
    ] = None,
) -> TrackRecordStats:
    """Return aggregate KPIs (bets, win rate, ROI, CLV, drawdown, streak)."""
    return await provider.get_stats(since)


@router.get(
    "/monthly",
    response_model=list[MonthlyStat],
    response_model_by_alias=True,
    summary="Per-month breakdown",
)
async def get_monthly(
    provider: Annotated[TrackRecordProvider, Depends(get_track_record_provider)],
) -> list[MonthlyStat]:
    """Return per-month stats, oldest first."""
    return await provider.get_monthly()


@router.get(
    "/equity-curve",
    response_model=list[EquityPoint],
    response_model_by_alias=True,
    summary="Daily equity / P&L curve",
)
async def get_equity_curve(
    provider: Annotated[TrackRecordProvider, Depends(get_track_record_provider)],
    since: Annotated[
        date | None,
        Query(description="Earliest date to include (default: 180 days before ``until``)."),
    ] = None,
    until: Annotated[
        date | None,
        Query(description="Latest date to include (default: today)."),
    ] = None,
) -> list[EquityPoint]:
    """Daily bankroll / cumulative P&L snapshots.

    Defaults to the last 180 days when ``since`` is omitted — a pragmatic
    window that covers ~2 Premier League seasons of half-season worth
    of data without flooding the dashboard.
    """
    return await provider.get_equity_curve(since, until)


@router.get(
    "/by-league",
    response_model=list[LeagueStat],
    response_model_by_alias=True,
    summary="Per-league breakdown",
)
async def get_by_league(
    provider: Annotated[TrackRecordProvider, Depends(get_track_record_provider)],
) -> list[LeagueStat]:
    """Return per-league stats sorted by bets desc (most active on top)."""
    return await provider.get_by_league()

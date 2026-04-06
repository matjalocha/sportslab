"""Weekly performance aggregation for SportsLab predictions."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import TypeAlias

from ml_in_sports.prediction.results import BetResult, ResultsTracker

MetricRow: TypeAlias = dict[str, str | int | float]


@dataclass(frozen=True)
class WeeklyData:
    """Aggregated weekly betting performance."""

    week_start: dt.date
    week_end: dt.date
    total_bets: int
    wins: int
    losses: int
    pnl: float
    bankroll_start: float
    bankroll_end: float
    clv_7d: float
    roi_7d: float
    daily_pnl: dict[str, float]
    per_league: list[MetricRow]
    per_market: list[MetricRow]
    best_bets: list[BetResult]
    worst_bets: list[BetResult]


class WeeklyReporter:
    """Build weekly aggregates from a ResultsTracker."""

    def __init__(self, results_tracker: ResultsTracker) -> None:
        """Initialize the reporter.

        Args:
            results_tracker: Tracker that owns processed daily result files.
        """
        self._results_tracker = results_tracker

    def generate(self, week_start: dt.date) -> WeeklyData:
        """Generate a weekly aggregate for a Monday-Sunday window.

        Args:
            week_start: Inclusive first day of the week.

        Returns:
            Weekly aggregated performance data.
        """
        week_end = week_start + dt.timedelta(days=6)
        all_results = self._results_tracker.load_processed_results()
        results = [
            result
            for result in all_results
            if week_start <= result.recommendation.kickoff_dt.date() <= week_end
        ]
        results.sort(key=lambda result: result.recommendation.kickoff_dt)

        bankroll_start = self._results_tracker.initial_bankroll + sum(
            result.pnl
            for result in all_results
            if result.recommendation.kickoff_dt.date() < week_start
        )
        pnl = sum(result.pnl for result in results)
        total_staked = sum(result.recommendation.stake_eur for result in results)
        clv_values = [result.clv for result in results if result.clv is not None]
        wins = sum(1 for result in results if result.hit)

        return WeeklyData(
            week_start=week_start,
            week_end=week_end,
            total_bets=len(results),
            wins=wins,
            losses=len(results) - wins,
            pnl=round(pnl, 2),
            bankroll_start=round(bankroll_start, 2),
            bankroll_end=round(bankroll_start + pnl, 2),
            clv_7d=sum(clv_values) / len(clv_values) if clv_values else 0.0,
            roi_7d=pnl / total_staked if total_staked else 0.0,
            daily_pnl=_daily_pnl(results, week_start, week_end),
            per_league=_aggregate_by(results, key_name="league"),
            per_market=_aggregate_by(results, key_name="market"),
            best_bets=sorted(results, key=lambda result: result.pnl, reverse=True)[:3],
            worst_bets=sorted(results, key=lambda result: result.pnl)[:3],
        )


def _daily_pnl(
    results: list[BetResult],
    week_start: dt.date,
    week_end: dt.date,
) -> dict[str, float]:
    values: dict[str, float] = {}
    current = week_start
    while current <= week_end:
        values[current.isoformat()] = 0.0
        current += dt.timedelta(days=1)

    for result in results:
        key = result.recommendation.kickoff_dt.date().isoformat()
        values[key] = round(values.get(key, 0.0) + result.pnl, 2)
    return values


def _aggregate_by(results: list[BetResult], key_name: str) -> list[MetricRow]:
    groups: dict[str, list[BetResult]] = {}
    for result in results:
        key = (
            result.recommendation.league
            if key_name == "league"
            else result.recommendation.market
        )
        groups.setdefault(key, []).append(result)

    rows: list[MetricRow] = []
    for key, group in sorted(groups.items()):
        bets = len(group)
        wins = sum(1 for result in group if result.hit)
        losses = bets - wins
        pnl = sum(result.pnl for result in group)
        total_staked = sum(result.recommendation.stake_eur for result in group)
        clv_values = [result.clv for result in group if result.clv is not None]
        rows.append(
            {
                key_name: key,
                "bets": bets,
                "wins": wins,
                "losses": losses,
                "pnl": round(pnl, 2),
                "roi": pnl / total_staked if total_staked else 0.0,
                "clv": sum(clv_values) / len(clv_values) if clv_values else 0.0,
            }
        )
    return rows

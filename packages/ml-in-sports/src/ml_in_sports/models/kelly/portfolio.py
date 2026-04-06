"""Portfolio Kelly staking with exposure constraints.

Extends basic Kelly fraction with position limits to manage portfolio risk.
Designed for multi-bet rounds where correlation and concentration must be
controlled.

Algorithm overview:
    1. Compute raw Kelly fraction for each bet.
    2. Apply shrinkage (optional) to guard against suspicious edges.
    3. Multiply by the global ``kelly_fraction`` (e.g. quarter-Kelly = 0.25).
    4. Apply exposure caps: per-match, per-round, per-league, per-team.
    5. Return ``StakeRecommendation`` with full audit trail.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PortfolioConstraints:
    """Exposure limits for Kelly portfolio.

    All exposure values are fractions of bankroll (0.0 to 1.0).

    Attributes:
        kelly_fraction: Global Kelly multiplier (0.1-0.5 typical, 0.25 = quarter-Kelly).
        max_exposure_per_match: Max stake on a single match as fraction of bankroll.
        max_exposure_per_round: Max total stake in a single round.
        max_exposure_per_league: Max total stake on a single league.
        max_exposure_per_team: Max stake involving a single team.
    """

    kelly_fraction: float = 0.25
    max_exposure_per_match: float = 0.03
    max_exposure_per_round: float = 0.15
    max_exposure_per_league: float = 0.20
    max_exposure_per_team: float = 0.06


@dataclass(frozen=True)
class BetOpportunity:
    """A single betting opportunity.

    Attributes:
        match_id: Unique match identifier.
        league: League name.
        home_team: Home team name.
        away_team: Away team name.
        market: Market type (e.g. "1x2_home", "over_25").
        model_prob: Model's predicted probability.
        odds: Decimal odds offered by bookmaker.
        closing_odds: Pinnacle closing odds (for CLV, optional).
        round_id: Round/gameweek identifier (for round exposure).
    """

    match_id: str
    league: str
    home_team: str
    away_team: str
    market: str
    model_prob: float
    odds: float
    closing_odds: float | None = None
    round_id: str | None = None


@dataclass(frozen=True)
class StakeRecommendation:
    """Output of the staking algorithm for one bet.

    Attributes:
        bet: Original bet opportunity.
        raw_kelly: Unconstrained Kelly fraction.
        adjusted_kelly: After shrinkage and fraction multiplier.
        final_stake_frac: After portfolio constraints (fraction of bankroll).
        edge: ``model_prob - (1 / odds)`` -- expected advantage over market.
        constraint_applied: Which constraint was binding, if any.
    """

    bet: BetOpportunity
    raw_kelly: float
    adjusted_kelly: float
    final_stake_frac: float
    edge: float
    constraint_applied: str | None = None


def _raw_kelly_fraction(model_prob: float, odds: float) -> float:
    """Compute unconstrained Kelly fraction.

    Formula: ``f* = (p * b - q) / b`` where ``b = odds - 1``, ``q = 1 - p``.

    Args:
        model_prob: Model probability for the outcome.
        odds: Decimal odds.

    Returns:
        Raw Kelly fraction, floored at 0.0 (no negative stakes).
    """
    if odds <= 1.0:
        return 0.0
    b = odds - 1.0
    f_star = (model_prob * b - (1.0 - model_prob)) / b
    return max(f_star, 0.0)


class PortfolioKelly:
    """Compute stakes for a portfolio of bets with exposure constraints.

    This class is stateless after ``__init__`` -- calling ``compute_stakes``
    multiple times with different inputs is safe and produces independent
    results.

    Algorithm:
        1. Compute raw Kelly fraction for each bet.
        2. Apply shrinkage (optional).
        3. Multiply by global ``kelly_fraction``.
        4. Apply per-match, per-round, per-league, per-team caps.
        5. Return final stake fractions.
    """

    def __init__(
        self,
        constraints: PortfolioConstraints | None = None,
        shrinkage_fn: Callable[[float, BetOpportunity], float] | None = None,
    ) -> None:
        """Initialize portfolio Kelly calculator.

        Args:
            constraints: Exposure limits. Uses defaults if None.
            shrinkage_fn: Optional callable ``(raw_kelly, bet) -> shrunk_kelly``.
                When provided, raw Kelly is passed through this function before
                the global fraction multiplier is applied.
        """
        self._constraints = constraints or PortfolioConstraints()
        self._shrinkage_fn = shrinkage_fn

    def compute_stakes(
        self,
        opportunities: list[BetOpportunity],
        bankroll: float = 10000.0,
    ) -> list[StakeRecommendation]:
        """Compute constrained Kelly stakes for a portfolio of bets.

        Processing order:
            1. Raw Kelly for each bet (independent).
            2. Shrinkage (independent per bet).
            3. Global fraction multiplier.
            4. Per-match cap.
            5. Per-round cap (proportional reduction within round).
            6. Per-league cap (proportional reduction within league).
            7. Per-team cap (proportional reduction per team).

        Args:
            opportunities: List of bet opportunities to size.
            bankroll: Total bankroll in currency units (used for logging only;
                all output fractions are bankroll-independent).

        Returns:
            List of ``StakeRecommendation`` in the same order as input.
        """
        if not opportunities:
            return []

        constraints = self._constraints

        # --- Step 1-3: Raw Kelly, shrinkage, fraction ---
        fractions: list[float] = []
        raw_kellys: list[float] = []
        edges: list[float] = []

        for bet in opportunities:
            edge = bet.model_prob - 1.0 / bet.odds
            raw = _raw_kelly_fraction(bet.model_prob, bet.odds)

            if self._shrinkage_fn is not None and raw > 0.0:
                shrunk = self._shrinkage_fn(raw, bet)
            else:
                shrunk = raw

            adjusted = shrunk * constraints.kelly_fraction

            fractions.append(adjusted)
            raw_kellys.append(raw)
            edges.append(edge)

        # --- Step 4: Per-match cap ---
        constraint_labels: list[str | None] = [None] * len(opportunities)
        for i, _bet in enumerate(opportunities):
            if fractions[i] > constraints.max_exposure_per_match:
                fractions[i] = constraints.max_exposure_per_match
                constraint_labels[i] = "max_exposure_per_match"

        # --- Step 5: Per-round cap ---
        fractions, constraint_labels = self._apply_group_cap(
            opportunities=opportunities,
            fractions=fractions,
            constraint_labels=constraint_labels,
            group_key=lambda bet: bet.round_id,
            cap=constraints.max_exposure_per_round,
            cap_name="max_exposure_per_round",
        )

        # --- Step 6: Per-league cap ---
        fractions, constraint_labels = self._apply_group_cap(
            opportunities=opportunities,
            fractions=fractions,
            constraint_labels=constraint_labels,
            group_key=lambda bet: bet.league,
            cap=constraints.max_exposure_per_league,
            cap_name="max_exposure_per_league",
        )

        # --- Step 7: Per-team cap ---
        fractions, constraint_labels = self._apply_team_cap(
            opportunities=opportunities,
            fractions=fractions,
            constraint_labels=constraint_labels,
        )

        # --- Build results ---
        results: list[StakeRecommendation] = []
        for i, bet in enumerate(opportunities):
            results.append(
                StakeRecommendation(
                    bet=bet,
                    raw_kelly=raw_kellys[i],
                    adjusted_kelly=raw_kellys[i] * constraints.kelly_fraction,
                    final_stake_frac=fractions[i],
                    edge=edges[i],
                    constraint_applied=constraint_labels[i],
                )
            )

        total_exposure = sum(fractions)
        logger.info(
            "portfolio_kelly_computed",
            extra={
                "num_bets": len(results),
                "total_exposure_frac": round(total_exposure, 4),
                "total_exposure_currency": round(total_exposure * bankroll, 2),
                "bankroll": bankroll,
            },
        )

        return results

    @staticmethod
    def _apply_group_cap(
        opportunities: list[BetOpportunity],
        fractions: list[float],
        constraint_labels: list[str | None],
        group_key: Callable[[BetOpportunity], str | None],
        cap: float,
        cap_name: str,
    ) -> tuple[list[float], list[str | None]]:
        """Apply a group-level exposure cap with proportional reduction.

        Bets sharing the same group key have their total exposure capped.
        When the cap is binding, all bets in the group are scaled down
        proportionally to preserve relative sizing.

        Args:
            opportunities: All bet opportunities.
            fractions: Current stake fractions (mutable copy expected).
            constraint_labels: Current constraint labels.
            group_key: Function mapping bet to group identifier.
            cap: Maximum total exposure for the group.
            cap_name: Label for the binding constraint.

        Returns:
            Updated (fractions, constraint_labels) lists.
        """
        fractions = list(fractions)
        constraint_labels = list(constraint_labels)

        groups: dict[str | None, list[int]] = defaultdict(list)
        for i, bet in enumerate(opportunities):
            key = group_key(bet)
            if key is not None:
                groups[key].append(i)

        for _key, indices in groups.items():
            group_total = sum(fractions[i] for i in indices)
            if group_total > cap and group_total > 0.0:
                scale = cap / group_total
                for i in indices:
                    fractions[i] *= scale
                    constraint_labels[i] = cap_name

        return fractions, constraint_labels

    def _apply_team_cap(
        self,
        opportunities: list[BetOpportunity],
        fractions: list[float],
        constraint_labels: list[str | None],
    ) -> tuple[list[float], list[str | None]]:
        """Apply per-team exposure cap.

        A team can appear as home or away in different matches. The total
        exposure across all bets involving a given team is capped.

        When the cap is binding, all bets involving that team are scaled
        proportionally.

        Args:
            opportunities: All bet opportunities.
            fractions: Current stake fractions.
            constraint_labels: Current constraint labels.

        Returns:
            Updated (fractions, constraint_labels) lists.
        """
        fractions = list(fractions)
        constraint_labels = list(constraint_labels)
        cap = self._constraints.max_exposure_per_team

        # Build team -> bet indices mapping
        team_indices: dict[str, list[int]] = defaultdict(list)
        for i, bet in enumerate(opportunities):
            team_indices[bet.home_team].append(i)
            team_indices[bet.away_team].append(i)

        for _team, indices in team_indices.items():
            team_total = sum(fractions[i] for i in indices)
            if team_total > cap and team_total > 0.0:
                scale = cap / team_total
                for i in indices:
                    fractions[i] *= scale
                    constraint_labels[i] = "max_exposure_per_team"

        return fractions, constraint_labels

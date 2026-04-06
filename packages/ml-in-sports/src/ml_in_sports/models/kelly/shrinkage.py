"""Shrinkage functions for Kelly stakes.

Shrinks Kelly fraction toward market-implied probability when:
- Edge is suspiciously large (outlier)
- Odds are extreme (> 5.0 or < 1.20)
- Market is illiquid (spread is wide)

All functions are pure: no side effects, no state mutation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ml_in_sports.models.kelly.portfolio import BetOpportunity


def shrink_toward_market(
    raw_kelly: float,
    model_prob: float,
    odds: float,
    max_edge: float = 0.15,
    odds_extreme_low: float = 1.20,
    odds_extreme_high: float = 5.00,
) -> float:
    """Shrink Kelly fraction when edge looks suspicious.

    Applies two independent shrinkage factors multiplicatively:

    1. **Edge shrinkage**: When edge exceeds ``max_edge``, linearly reduces the
       Kelly fraction. At ``edge = 2 * max_edge`` the fraction is halved; beyond
       that, it continues to shrink but never reaches zero (clamped at 0).

    2. **Extreme-odds shrinkage**: When odds fall outside the
       ``[odds_extreme_low, odds_extreme_high]`` range, applies a flat 0.5
       multiplier because extreme odds indicate less reliable markets.

    Args:
        raw_kelly: Unconstrained Kelly fraction (non-negative).
        model_prob: Model's probability estimate for the outcome.
        odds: Bookmaker decimal odds.
        max_edge: Above this edge magnitude, linear shrinkage begins.
        odds_extreme_low: Below this odds value, apply extreme-odds penalty.
        odds_extreme_high: Above this odds value, apply extreme-odds penalty.

    Returns:
        Shrunk Kelly fraction. Always ``>= 0`` and ``<= raw_kelly``.
    """
    if raw_kelly <= 0.0:
        return 0.0

    edge = model_prob - 1.0 / odds

    # --- Edge shrinkage factor ---
    # Linear ramp: factor=1.0 at edge<=max_edge, factor=0.5 at edge=2*max_edge,
    # factor=0.0 at edge=3*max_edge, clamped to [0, 1].
    if edge <= max_edge:
        edge_factor = 1.0
    else:
        excess = edge - max_edge
        edge_factor = max(1.0 - 0.5 * excess / max_edge, 0.0)

    # --- Extreme-odds shrinkage factor ---
    odds_factor = 0.5 if odds < odds_extreme_low or odds > odds_extreme_high else 1.0

    shrunk = raw_kelly * edge_factor * odds_factor
    return min(shrunk, raw_kelly)


def create_shrinkage_fn(
    max_edge: float = 0.15,
    odds_extreme_low: float = 1.20,
    odds_extreme_high: float = 5.00,
) -> Callable[[float, BetOpportunity], float]:
    """Create a shrinkage function with configured parameters.

    Returns a callable compatible with ``PortfolioKelly(shrinkage_fn=...)``.
    The returned function signature is ``(raw_kelly, bet) -> shrunk_kelly``.

    Args:
        max_edge: Above this edge, linear shrinkage kicks in.
        odds_extreme_low: Below this odds, apply extreme-odds penalty.
        odds_extreme_high: Above this odds, apply extreme-odds penalty.

    Returns:
        A callable ``(raw_kelly: float, bet: BetOpportunity) -> float``.
    """

    def _shrinkage(raw_kelly: float, bet: BetOpportunity) -> float:
        return shrink_toward_market(
            raw_kelly=raw_kelly,
            model_prob=bet.model_prob,
            odds=bet.odds,
            max_edge=max_edge,
            odds_extreme_low=odds_extreme_low,
            odds_extreme_high=odds_extreme_high,
        )

    return _shrinkage

"""Stake sizing via variance-constrained fractional Kelly criterion.

Shrinks model probability by ECE before computing Kelly fraction,
guarding against overconfident estimates.
"""


def compute_kelly_stake(
    p_model: float,
    odds: float,
    ece: float,
    bankroll: float,
    fraction: float = 0.25,
    max_stake_pct: float = 0.02,
    z: float = 1.0,
) -> tuple[float, float, float]:
    """Compute variance-constrained fractional Kelly stake.

    Args:
        p_model: Model probability estimate [0, 1].
        odds: Decimal odds (e.g. 1.80).
        ece: Expected Calibration Error as fraction [0, 1].
        bankroll: Total bankroll in currency units.
        fraction: Kelly fraction (0.25 = quarter-Kelly).
        max_stake_pct: Hard cap as fraction of bankroll.
        z: Std-dev multiplier for ECE shrinkage (1.0 = conservative).

    Returns:
        Tuple of (p_conservative, f_star, stake).
        stake is 0.0 when there is no positive edge after shrinkage.
    """
    p_conservative = max(p_model - z * ece, 0.01)
    b = odds - 1.0
    f_star = (b * p_conservative - (1.0 - p_conservative)) / b

    if f_star <= 0:
        return p_conservative, f_star, 0.0

    raw_stake = fraction * f_star * bankroll
    capped_stake = min(raw_stake, max_stake_pct * bankroll)
    return p_conservative, f_star, capped_stake


def scale_to_budget(
    stakes: list[float],
    weekly_budget: float,
) -> list[float]:
    """Scale stakes proportionally to fit within weekly budget.

    Preserves relative bet sizes — higher-edge bets keep larger share.

    Args:
        stakes: Computed Kelly stakes (one per bet).
        weekly_budget: Maximum total to stake in a week.

    Returns:
        Scaled stakes. Unchanged when total <= weekly_budget.
    """
    if not stakes:
        return stakes

    total = sum(stakes)
    if total == 0 or total <= weekly_budget:
        return stakes

    scale = weekly_budget / total
    return [s * scale for s in stakes]

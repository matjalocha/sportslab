"""Tests for value_betting module (variance-constrained Kelly criterion)."""

import pytest
from ml_in_sports.models.value_betting import compute_kelly_stake, scale_to_budget


def test_compute_kelly_stake_positive_ev() -> None:
    """Kelly stake > 0 when model has genuine positive edge."""
    _, f_star, stake = compute_kelly_stake(
        p_model=0.60, odds=2.10, ece=0.02, bankroll=10_000.0
    )
    assert f_star > 0
    assert stake > 0


def test_compute_kelly_stake_no_edge() -> None:
    """Kelly stake = 0 when model edge is zero or negative."""
    _, f_star, stake = compute_kelly_stake(
        p_model=0.40, odds=1.80, ece=0.02, bankroll=10_000.0
    )
    assert f_star <= 0
    assert stake == 0.0


def test_compute_kelly_stake_break_even_odds() -> None:
    """Kelly stake = 0 when implied prob equals model prob."""
    # odds=2.0 → implied=0.50, model=0.50 → edge=0
    _, f_star, stake = compute_kelly_stake(
        p_model=0.50, odds=2.00, ece=0.00, bankroll=10_000.0
    )
    assert f_star == pytest.approx(0.0, abs=1e-9)
    assert stake == 0.0


def test_compute_kelly_stake_max_cap() -> None:
    """Stake is capped at max_stake_pct of bankroll regardless of edge size."""
    _, _, stake = compute_kelly_stake(
        p_model=0.90, odds=3.00, ece=0.00, bankroll=10_000.0,
        fraction=0.25, max_stake_pct=0.02,
    )
    assert stake <= 200.0  # 2% of 10_000


def test_compute_kelly_stake_scales_with_bankroll() -> None:
    """Stake proportional to bankroll when cap not hit."""
    _, _, stake_small = compute_kelly_stake(
        p_model=0.55, odds=2.00, ece=0.01, bankroll=1_000.0,
        max_stake_pct=1.0,
    )
    _, _, stake_large = compute_kelly_stake(
        p_model=0.55, odds=2.00, ece=0.01, bankroll=10_000.0,
        max_stake_pct=1.0,
    )
    assert stake_large == pytest.approx(stake_small * 10.0, rel=1e-6)


def test_compute_kelly_stake_uncertainty_shrinkage() -> None:
    """Higher ECE yields lower stake (more conservative), tested without cap."""
    _, _, stake_low_ece = compute_kelly_stake(
        p_model=0.60, odds=2.10, ece=0.01, bankroll=10_000.0, max_stake_pct=1.0
    )
    _, _, stake_high_ece = compute_kelly_stake(
        p_model=0.60, odds=2.10, ece=0.05, bankroll=10_000.0, max_stake_pct=1.0
    )
    assert stake_low_ece > stake_high_ece


def test_compute_kelly_stake_ece_eliminates_edge() -> None:
    """Returns 0 when ECE shrinkage removes entire edge."""
    # p=0.52, odds=1.80 → implied=0.556 → already below break-even;
    # with ece=0.10 shrinkage makes it worse
    _, _, stake = compute_kelly_stake(
        p_model=0.52, odds=1.80, ece=0.10, bankroll=10_000.0, z=1.0
    )
    assert stake == 0.0


def test_compute_kelly_stake_fraction_scales_proportionally() -> None:
    """Half-Kelly gives half the stake of full-Kelly (pre-cap)."""
    _, _, stake_full = compute_kelly_stake(
        p_model=0.55, odds=2.10, ece=0.01, bankroll=10_000.0,
        fraction=1.0, max_stake_pct=1.0,
    )
    _, _, stake_half = compute_kelly_stake(
        p_model=0.55, odds=2.10, ece=0.01, bankroll=10_000.0,
        fraction=0.5, max_stake_pct=1.0,
    )
    assert stake_half == pytest.approx(stake_full * 0.5, rel=1e-6)


# --- scale_to_budget ---

def test_scale_to_budget_under_limit() -> None:
    """Stakes unchanged when total is within weekly budget."""
    stakes = [100.0, 200.0, 50.0]
    result = scale_to_budget(stakes, weekly_budget=1_000.0)
    assert result == stakes


def test_scale_to_budget_at_limit() -> None:
    """Stakes unchanged when total equals weekly budget exactly."""
    stakes = [400.0, 600.0]
    result = scale_to_budget(stakes, weekly_budget=1_000.0)
    assert result == stakes


def test_scale_to_budget_proportional_scaling() -> None:
    """Stakes scaled proportionally and sum to weekly budget."""
    stakes = [200.0, 400.0, 400.0]  # total 1000, budget 500
    result = scale_to_budget(stakes, weekly_budget=500.0)
    assert abs(sum(result) - 500.0) < 0.01
    assert abs(result[1] / result[0] - 2.0) < 1e-6  # proportions preserved


def test_scale_to_budget_empty() -> None:
    """Empty stakes list returns empty list."""
    assert scale_to_budget([], weekly_budget=500.0) == []


def test_scale_to_budget_all_zero() -> None:
    """All-zero stakes returns zeros without division error."""
    result = scale_to_budget([0.0, 0.0], weekly_budget=500.0)
    assert result == [0.0, 0.0]

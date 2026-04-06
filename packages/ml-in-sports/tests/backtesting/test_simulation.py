"""Tests for simulation helpers: flat betting and Kelly staking.

Covers ``simulate_kelly_betting`` with scenarios for positive edge,
negative edge, fraction ordering, exposure caps, missing odds, and
bankroll non-negativity.
"""

from __future__ import annotations

import numpy as np
import pytest
from ml_in_sports.backtesting.simulation import simulate_kelly_betting

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def positive_edge_data() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Scenario where model has a clear edge (prob > implied prob).

    50 bets on a binary outcome at odds 2.0 (implied 50%).
    Model predicts 70% for class 1, and class 1 wins every time.
    """
    n = 50
    predictions = np.column_stack([np.full(n, 0.3), np.full(n, 0.7)])
    actuals = np.ones(n, dtype=int)
    odds = np.column_stack([np.full(n, 3.0), np.full(n, 2.0)])
    return predictions, actuals, odds


@pytest.fixture
def negative_edge_data() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Scenario where model has negative edge.

    50 bets: model predicts 70% for class 1 at odds 2.0, but class 0
    wins every time.
    """
    n = 50
    predictions = np.column_stack([np.full(n, 0.3), np.full(n, 0.7)])
    actuals = np.zeros(n, dtype=int)
    odds = np.column_stack([np.full(n, 3.0), np.full(n, 2.0)])
    return predictions, actuals, odds


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSimulateKellyBettingPositiveEdge:
    """Kelly simulation with a winning model should grow the bankroll."""

    def test_bankroll_grows(
        self,
        positive_edge_data: tuple[np.ndarray, np.ndarray, np.ndarray],
    ) -> None:
        """Bankroll should exceed initial value after winning streak."""
        predictions, actuals, odds = positive_edge_data
        bankroll_hist, _returns = simulate_kelly_betting(
            predictions=predictions,
            actuals=actuals,
            odds=odds,
            kelly_fraction=0.25,
            initial_bankroll=1000.0,
        )
        assert bankroll_hist[-1] > 1000.0

    def test_returns_are_positive(
        self,
        positive_edge_data: tuple[np.ndarray, np.ndarray, np.ndarray],
    ) -> None:
        """All individual bet returns should be positive when every bet wins."""
        predictions, actuals, odds = positive_edge_data
        _bankroll_hist, bet_returns = simulate_kelly_betting(
            predictions=predictions,
            actuals=actuals,
            odds=odds,
            kelly_fraction=0.25,
            initial_bankroll=1000.0,
        )
        assert np.all(bet_returns > 0.0)


class TestSimulateKellyBettingNegativeEdge:
    """Kelly simulation when every bet loses should shrink the bankroll."""

    def test_bankroll_shrinks(
        self,
        negative_edge_data: tuple[np.ndarray, np.ndarray, np.ndarray],
    ) -> None:
        """Bankroll should be below initial after a losing streak."""
        predictions, actuals, odds = negative_edge_data
        bankroll_hist, _returns = simulate_kelly_betting(
            predictions=predictions,
            actuals=actuals,
            odds=odds,
            kelly_fraction=0.25,
            initial_bankroll=1000.0,
        )
        assert bankroll_hist[-1] < 1000.0


class TestSimulateKellyBettingFractionOrdering:
    """Quarter-Kelly should produce less volatile growth than half-Kelly."""

    def test_quarter_kelly_grows_slower_than_half_kelly(
        self,
        positive_edge_data: tuple[np.ndarray, np.ndarray, np.ndarray],
    ) -> None:
        """With all bets winning, half-Kelly compounds faster than quarter.

        Uses a high exposure cap (1.0) so the fraction multiplier is the
        sole differentiator -- the default 0.03 cap would bind both.
        """
        predictions, actuals, odds = positive_edge_data

        bankroll_quarter, _ = simulate_kelly_betting(
            predictions=predictions,
            actuals=actuals,
            odds=odds,
            kelly_fraction=0.25,
            max_exposure_per_match=1.0,
            initial_bankroll=1000.0,
        )

        bankroll_half, _ = simulate_kelly_betting(
            predictions=predictions,
            actuals=actuals,
            odds=odds,
            kelly_fraction=0.50,
            max_exposure_per_match=1.0,
            initial_bankroll=1000.0,
        )

        assert bankroll_half[-1] > bankroll_quarter[-1]


class TestSimulateKellyBettingExposureCap:
    """Max exposure per match must be respected."""

    def test_stake_fraction_never_exceeds_cap(self) -> None:
        """Even with huge edge, stake fraction is capped."""
        n = 10
        # Model probability 0.99 at odds 2.0 => raw Kelly ~ 0.98
        predictions = np.column_stack([np.full(n, 0.01), np.full(n, 0.99)])
        actuals = np.ones(n, dtype=int)
        odds = np.column_stack([np.full(n, 10.0), np.full(n, 2.0)])

        cap = 0.02
        _bankroll_hist, bet_returns = simulate_kelly_betting(
            predictions=predictions,
            actuals=actuals,
            odds=odds,
            kelly_fraction=1.0,
            max_exposure_per_match=cap,
            initial_bankroll=1000.0,
        )

        # First bet: stake should be cap * 1000 = 20, win payout = 20*(2-1) = 20
        # Verify the first return is consistent with the cap
        expected_first_pnl = cap * 1000.0 * (2.0 - 1.0)
        assert abs(bet_returns[0] - expected_first_pnl) < 1e-8


class TestSimulateKellyBettingNoOdds:
    """When odds are None, Kelly falls back to flat betting."""

    def test_fallback_to_flat(self) -> None:
        """Without odds, returns should match flat-bet simulation shape."""
        n = 20
        predictions = np.column_stack([np.full(n, 0.4), np.full(n, 0.6)])
        actuals = np.ones(n, dtype=int)

        bankroll_hist, bet_returns = simulate_kelly_betting(
            predictions=predictions,
            actuals=actuals,
            odds=None,
            kelly_fraction=0.25,
            initial_bankroll=1000.0,
        )

        assert len(bankroll_hist) == n
        assert len(bet_returns) == n
        # Flat bet: each bet wins 1 unit at implied odds 2.0 => return = +1.0
        assert np.allclose(bet_returns, 1.0)


class TestSimulateKellyBettingBankrollNonNegative:
    """Bankroll must never go negative (Kelly stakes a fraction)."""

    def test_bankroll_stays_non_negative(self) -> None:
        """Even with many losses, fractional staking keeps bankroll >= 0."""
        n = 200
        predictions = np.column_stack([np.full(n, 0.3), np.full(n, 0.7)])
        actuals = np.zeros(n, dtype=int)  # All losses
        odds = np.column_stack([np.full(n, 3.0), np.full(n, 2.0)])

        bankroll_hist, _returns = simulate_kelly_betting(
            predictions=predictions,
            actuals=actuals,
            odds=odds,
            kelly_fraction=0.50,
            initial_bankroll=1000.0,
        )

        assert np.all(bankroll_hist >= 0.0)

    def test_output_shapes_match_input_length(self) -> None:
        """Both outputs have the same length as the number of bets."""
        n = 30
        predictions = np.column_stack([np.full(n, 0.5), np.full(n, 0.5)])
        actuals = np.ones(n, dtype=int)
        odds = np.column_stack([np.full(n, 2.0), np.full(n, 2.0)])

        bankroll_hist, bet_returns = simulate_kelly_betting(
            predictions=predictions,
            actuals=actuals,
            odds=odds,
        )

        assert bankroll_hist.shape == (n,)
        assert bet_returns.shape == (n,)


class TestSimulateKellyBettingNoEdge:
    """When model prob equals implied prob, Kelly stakes zero."""

    def test_zero_edge_stakes_nothing(self) -> None:
        """Fair odds produce zero Kelly fraction => bankroll unchanged."""
        n = 10
        # Model probability 0.5, odds 2.0 => implied 0.5, zero edge
        predictions = np.column_stack([np.full(n, 0.5), np.full(n, 0.5)])
        actuals = np.ones(n, dtype=int)
        odds = np.column_stack([np.full(n, 2.0), np.full(n, 2.0)])

        bankroll_hist, bet_returns = simulate_kelly_betting(
            predictions=predictions,
            actuals=actuals,
            odds=odds,
            kelly_fraction=0.25,
            initial_bankroll=1000.0,
        )

        assert np.allclose(bankroll_hist, 1000.0)
        assert np.allclose(bet_returns, 0.0)

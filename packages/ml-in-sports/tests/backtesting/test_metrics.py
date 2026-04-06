"""Tests for backtesting evaluation metrics."""

import numpy as np
import pytest
from ml_in_sports.backtesting.metrics import (
    compute_brier_score,
    compute_clv,
    compute_clv_mean,
    compute_ece,
    compute_hit_rate,
    compute_log_loss,
    compute_max_drawdown,
    compute_max_losing_streak,
    compute_roi,
    compute_sharpe,
    compute_yield,
)


class TestLogLoss:
    """Tests for log loss computation."""

    def test_perfect_predictions(self) -> None:
        """Perfect binary predictions give near-zero log loss."""
        y_true = np.array([0, 1, 0, 1])
        y_prob = np.array([0.01, 0.99, 0.01, 0.99])
        assert compute_log_loss(y_true, y_prob) < 0.05

    def test_random_predictions(self) -> None:
        """Random predictions give log loss near ln(2) ≈ 0.693."""
        y_true = np.array([0, 1, 0, 1])
        y_prob = np.array([0.5, 0.5, 0.5, 0.5])
        assert compute_log_loss(y_true, y_prob) == pytest.approx(0.6931, abs=0.01)

    def test_multiclass(self) -> None:
        """Multiclass log loss works with 2D probabilities."""
        y_true = np.array([0, 1, 2])
        y_prob = np.array([[0.8, 0.1, 0.1], [0.1, 0.8, 0.1], [0.1, 0.1, 0.8]])
        assert compute_log_loss(y_true, y_prob) < 0.5

    def test_empty_raises(self) -> None:
        """Empty input raises ValueError."""
        with pytest.raises(ValueError):
            compute_log_loss(np.array([]), np.array([]))


class TestECE:
    """Tests for Expected Calibration Error."""

    def test_perfectly_calibrated(self) -> None:
        """Perfectly calibrated predictions have ECE ≈ 0."""
        rng = np.random.default_rng(42)
        n = 10000
        y_prob = rng.uniform(0, 1, n)
        y_true = (rng.uniform(0, 1, n) < y_prob).astype(int)
        ece = compute_ece(y_true, y_prob, n_bins=20)
        assert ece < 0.02

    def test_overconfident(self) -> None:
        """Overconfident predictions have positive ECE."""
        y_true = np.array([0, 0, 0, 1, 1, 1, 1, 1])
        y_prob = np.array([0.1, 0.1, 0.1, 0.95, 0.95, 0.95, 0.95, 0.95])
        ece = compute_ece(y_true, y_prob, n_bins=5)
        assert ece > 0

    def test_empty_raises(self) -> None:
        """Empty input raises ValueError."""
        with pytest.raises(ValueError):
            compute_ece(np.array([]), np.array([]))

    def test_multiclass_ece(self) -> None:
        """Multiclass ECE works with 2D probabilities."""
        y_true = np.array([0, 1, 2, 0, 1])
        y_prob = np.array([
            [0.7, 0.2, 0.1],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
            [0.6, 0.2, 0.2],
            [0.2, 0.6, 0.2],
        ])
        ece = compute_ece(y_true, y_prob, n_bins=3)
        assert 0 <= ece <= 1


class TestBrierScore:
    """Tests for Brier score."""

    def test_perfect_predictions(self) -> None:
        """Perfect predictions give Brier score = 0."""
        y_true = np.array([0, 1, 0, 1])
        y_prob = np.array([0.0, 1.0, 0.0, 1.0])
        assert compute_brier_score(y_true, y_prob) == pytest.approx(0.0)

    def test_random_predictions(self) -> None:
        """Random predictions give Brier score = 0.25."""
        y_true = np.array([0, 1, 0, 1])
        y_prob = np.array([0.5, 0.5, 0.5, 0.5])
        assert compute_brier_score(y_true, y_prob) == pytest.approx(0.25)

    def test_empty_raises(self) -> None:
        """Empty input raises ValueError."""
        with pytest.raises(ValueError):
            compute_brier_score(np.array([]), np.array([]))


class TestCLV:
    """Tests for Closing Line Value."""

    def test_positive_clv(self) -> None:
        """Model prob > market implied → positive CLV."""
        model_prob = np.array([0.60])
        closing_odds = np.array([2.0])  # implied = 0.50
        clv = compute_clv(model_prob, closing_odds)
        assert clv[0] == pytest.approx(0.10)

    def test_negative_clv(self) -> None:
        """Model prob < market implied → negative CLV."""
        model_prob = np.array([0.40])
        closing_odds = np.array([2.0])  # implied = 0.50
        clv = compute_clv(model_prob, closing_odds)
        assert clv[0] == pytest.approx(-0.10)

    def test_mean_clv(self) -> None:
        """Mean CLV across multiple bets."""
        model_prob = np.array([0.60, 0.40])
        closing_odds = np.array([2.0, 2.0])
        mean = compute_clv_mean(model_prob, closing_odds)
        assert mean == pytest.approx(0.0)

    def test_empty_raises(self) -> None:
        """Empty input raises ValueError."""
        with pytest.raises(ValueError):
            compute_clv(np.array([]), np.array([]))

    def test_length_mismatch_raises(self) -> None:
        """Different lengths raise ValueError."""
        with pytest.raises(ValueError, match="same length"):
            compute_clv(np.array([0.5]), np.array([2.0, 3.0]))


class TestROI:
    """Tests for Return on Investment."""

    def test_profitable(self) -> None:
        """Positive returns give positive ROI."""
        stakes = np.array([100, 100, 100])
        returns = np.array([50, -100, 80])  # net: +30
        assert compute_roi(stakes, returns) == pytest.approx(0.10)

    def test_break_even(self) -> None:
        """Zero returns give zero ROI."""
        stakes = np.array([100, 100])
        returns = np.array([50, -50])
        assert compute_roi(stakes, returns) == pytest.approx(0.0)

    def test_empty_raises(self) -> None:
        """Empty input raises ValueError."""
        with pytest.raises(ValueError):
            compute_roi(np.array([]), np.array([]))


class TestSharpe:
    """Tests for Sharpe ratio."""

    def test_constant_positive_returns(self) -> None:
        """Constant positive returns → Sharpe = 0 (zero std)."""
        returns = np.array([1.0, 1.0, 1.0, 1.0])
        assert compute_sharpe(returns) == 0.0

    def test_variable_returns(self) -> None:
        """Variable returns give finite Sharpe."""
        returns = np.array([0.1, -0.05, 0.08, -0.02, 0.06])
        sharpe = compute_sharpe(returns)
        assert sharpe > 0  # mean is positive

    def test_empty_raises(self) -> None:
        """Empty input raises ValueError."""
        with pytest.raises(ValueError):
            compute_sharpe(np.array([]))


class TestMaxDrawdown:
    """Tests for maximum drawdown."""

    def test_monotonic_increase(self) -> None:
        """Monotonically increasing equity → zero drawdown."""
        equity = np.array([100, 110, 120, 130])
        assert compute_max_drawdown(equity) == pytest.approx(0.0)

    def test_known_drawdown(self) -> None:
        """Known equity curve with specific drawdown."""
        equity = np.array([100, 120, 90, 110, 80])
        # Peak 120, trough 80 → drawdown = 40/120 = 0.333
        dd = compute_max_drawdown(equity)
        assert dd == pytest.approx(40 / 120, abs=0.01)

    def test_empty_raises(self) -> None:
        """Empty input raises ValueError."""
        with pytest.raises(ValueError):
            compute_max_drawdown(np.array([]))


class TestMaxLosingStreak:
    """Tests for maximum losing streak."""

    def test_no_losses(self) -> None:
        """All wins → zero losing streak."""
        outcomes = np.array([1, 1, 1, 1])
        assert compute_max_losing_streak(outcomes) == 0

    def test_all_losses(self) -> None:
        """All losses → streak = length."""
        outcomes = np.array([0, 0, 0, 0])
        assert compute_max_losing_streak(outcomes) == 4

    def test_mixed(self) -> None:
        """Mixed outcomes: WLLLWLW → max streak = 3."""
        outcomes = np.array([1, 0, 0, 0, 1, 0, 1])
        assert compute_max_losing_streak(outcomes) == 3

    def test_empty(self) -> None:
        """Empty input → zero."""
        assert compute_max_losing_streak(np.array([])) == 0


class TestHitRate:
    """Tests for hit rate."""

    def test_all_wins(self) -> None:
        """All wins → 1.0."""
        outcomes = np.array([1, 1, 1])
        assert compute_hit_rate(outcomes) == pytest.approx(1.0)

    def test_half_wins(self) -> None:
        """50/50 → 0.5."""
        outcomes = np.array([1, 0, 1, 0])
        assert compute_hit_rate(outcomes) == pytest.approx(0.5)

    def test_empty_raises(self) -> None:
        """Empty input raises ValueError."""
        with pytest.raises(ValueError):
            compute_hit_rate(np.array([]))


class TestYield:
    """Tests for yield computation."""

    def test_positive_yield(self) -> None:
        """Profit → positive yield."""
        assert compute_yield(50.0, 1000.0) == pytest.approx(0.05)

    def test_zero_staked_raises(self) -> None:
        """Zero staked raises ValueError."""
        with pytest.raises(ValueError):
            compute_yield(10.0, 0.0)

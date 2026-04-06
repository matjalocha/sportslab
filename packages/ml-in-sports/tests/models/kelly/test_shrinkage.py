"""Tests for Kelly shrinkage functions."""

import pytest
from ml_in_sports.models.kelly.portfolio import BetOpportunity
from ml_in_sports.models.kelly.shrinkage import create_shrinkage_fn, shrink_toward_market


def _make_bet(
    model_prob: float = 0.55,
    odds: float = 2.00,
    **kwargs: object,
) -> BetOpportunity:
    """Helper to create a BetOpportunity with sensible defaults."""
    defaults = {
        "match_id": "m1",
        "league": "EPL",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "market": "1x2_home",
        "model_prob": model_prob,
        "odds": odds,
    }
    defaults.update(kwargs)
    return BetOpportunity(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# shrink_toward_market
# ---------------------------------------------------------------------------


class TestShrinkTowardMarket:
    """Tests for the pure shrinkage function."""

    def test_small_edge_no_shrinkage(self) -> None:
        """Small edge (1%) within normal odds produces no shrinkage."""
        # model_prob=0.51, odds=2.0 -> edge=0.01, well below default max_edge=0.15
        raw_kelly = 0.02
        result = shrink_toward_market(raw_kelly, model_prob=0.51, odds=2.00)
        assert result == pytest.approx(raw_kelly)

    def test_normal_edge_normal_odds_no_shrinkage(self) -> None:
        """5% edge with normal odds (2.50) produces no shrinkage."""
        # model_prob=0.45, odds=2.50 -> implied=0.40, edge=0.05
        raw_kelly = 0.05
        result = shrink_toward_market(raw_kelly, model_prob=0.45, odds=2.50)
        assert result == pytest.approx(raw_kelly)

    def test_large_edge_significant_shrinkage(self) -> None:
        """Edge of 20% (above max_edge=15%) triggers meaningful shrinkage."""
        # model_prob=0.70, odds=2.0 -> implied=0.50, edge=0.20
        # excess=0.05, factor=1 - 0.5*(0.05/0.15) = 1 - 0.1667 = 0.8333
        raw_kelly = 0.10
        result = shrink_toward_market(raw_kelly, model_prob=0.70, odds=2.00)
        assert result < raw_kelly
        assert result == pytest.approx(raw_kelly * (1.0 - 0.5 * 0.05 / 0.15), rel=1e-6)

    def test_very_large_edge_halved(self) -> None:
        """At edge = 2 * max_edge, Kelly is halved."""
        # edge = 0.30 with max_edge=0.15 -> excess=0.15, factor=0.5
        raw_kelly = 0.20
        result = shrink_toward_market(raw_kelly, model_prob=0.80, odds=2.00, max_edge=0.15)
        # edge = 0.80 - 0.50 = 0.30, excess=0.15, factor=1-0.5*(0.15/0.15)=0.5
        assert result == pytest.approx(raw_kelly * 0.5, rel=1e-6)

    def test_extreme_odds_low_halved(self) -> None:
        """Very low odds (1.10) trigger extreme-odds penalty."""
        raw_kelly = 0.05
        result = shrink_toward_market(raw_kelly, model_prob=0.95, odds=1.10)
        assert result == pytest.approx(raw_kelly * 0.5, rel=1e-6)

    def test_extreme_odds_high_halved(self) -> None:
        """Very high odds (8.00) trigger extreme-odds penalty."""
        raw_kelly = 0.05
        # model_prob=0.20, odds=8.0 -> implied=0.125, edge=0.075 (below max_edge)
        result = shrink_toward_market(raw_kelly, model_prob=0.20, odds=8.00)
        assert result == pytest.approx(raw_kelly * 0.5, rel=1e-6)

    def test_shrinkage_never_increases_kelly(self) -> None:
        """Shrinkage output is always <= raw_kelly for any valid input."""
        test_cases = [
            (0.10, 0.55, 2.00),   # normal
            (0.20, 0.80, 2.00),   # big edge
            (0.05, 0.95, 1.10),   # extreme low odds
            (0.05, 0.20, 8.00),   # extreme high odds
            (0.15, 0.90, 1.05),   # both extreme odds and big edge
        ]
        for raw, prob, odds in test_cases:
            result = shrink_toward_market(raw, model_prob=prob, odds=odds)
            assert result <= raw, f"Shrinkage increased kelly for ({raw}, {prob}, {odds})"
            assert result >= 0.0, f"Shrinkage went negative for ({raw}, {prob}, {odds})"

    def test_zero_kelly_stays_zero(self) -> None:
        """Zero raw Kelly remains zero regardless of other inputs."""
        result = shrink_toward_market(0.0, model_prob=0.80, odds=2.00)
        assert result == 0.0

    def test_negative_kelly_stays_zero(self) -> None:
        """Negative raw Kelly is treated as zero."""
        result = shrink_toward_market(-0.05, model_prob=0.80, odds=2.00)
        assert result == 0.0

    def test_combined_edge_and_extreme_odds(self) -> None:
        """Both edge shrinkage and extreme-odds penalty apply multiplicatively."""
        # model_prob=0.85, odds=1.10 -> implied=0.909, edge=-0.059 (negative)
        # but raw_kelly > 0 is provided externally, so test with high-odds combo
        # model_prob=0.40, odds=8.0 -> implied=0.125, edge=0.275
        # max_edge=0.15, excess=0.125, edge_factor=1-0.5*(0.125/0.15)=0.5833
        # odds_factor=0.5 (>5.0)
        # combined = 0.5833 * 0.5 = 0.2917
        raw_kelly = 0.10
        result = shrink_toward_market(raw_kelly, model_prob=0.40, odds=8.00, max_edge=0.15)
        edge_factor = 1.0 - 0.5 * (0.275 - 0.15) / 0.15
        expected = raw_kelly * edge_factor * 0.5
        assert result == pytest.approx(expected, rel=1e-6)

    def test_boundary_at_max_edge_no_shrinkage(self) -> None:
        """Edge exactly at max_edge produces no shrinkage (edge factor = 1.0)."""
        # model_prob=0.65, odds=2.0 -> edge=0.15 exactly
        raw_kelly = 0.08
        result = shrink_toward_market(raw_kelly, model_prob=0.65, odds=2.00, max_edge=0.15)
        assert result == pytest.approx(raw_kelly, rel=1e-6)

    def test_boundary_at_extreme_odds_low(self) -> None:
        """Odds exactly at extreme_low boundary: no penalty (boundary is exclusive)."""
        raw_kelly = 0.05
        # odds=1.20 is the boundary -> below means <1.20
        result = shrink_toward_market(raw_kelly, model_prob=0.90, odds=1.20)
        assert result == pytest.approx(raw_kelly, rel=1e-6)

    def test_boundary_at_extreme_odds_high(self) -> None:
        """Odds exactly at extreme_high boundary: no penalty (boundary is exclusive)."""
        raw_kelly = 0.05
        result = shrink_toward_market(raw_kelly, model_prob=0.25, odds=5.00)
        assert result == pytest.approx(raw_kelly, rel=1e-6)


# ---------------------------------------------------------------------------
# create_shrinkage_fn
# ---------------------------------------------------------------------------


class TestCreateShrinkageFn:
    """Tests for the shrinkage function factory."""

    def test_returns_callable(self) -> None:
        """Factory returns a callable."""
        fn = create_shrinkage_fn()
        assert callable(fn)

    def test_no_shrinkage_for_small_edge(self) -> None:
        """Created function passes through small-edge bets unchanged."""
        fn = create_shrinkage_fn(max_edge=0.15)
        bet = _make_bet(model_prob=0.51, odds=2.00)
        raw = 0.02
        result = fn(raw, bet)
        assert result == pytest.approx(raw)

    def test_shrinks_large_edge(self) -> None:
        """Created function shrinks bets with large edge."""
        fn = create_shrinkage_fn(max_edge=0.10)
        # model_prob=0.70, odds=2.0 -> edge=0.20, excess=0.10, factor=0.5
        bet = _make_bet(model_prob=0.70, odds=2.00)
        raw = 0.10
        result = fn(raw, bet)
        assert result < raw

    def test_custom_parameters_respected(self) -> None:
        """Custom extreme-odds thresholds are applied correctly."""
        fn = create_shrinkage_fn(odds_extreme_low=1.50, odds_extreme_high=4.00)
        # odds=1.40 is below custom threshold 1.50 -> halved
        bet = _make_bet(model_prob=0.75, odds=1.40)
        raw = 0.05
        result = fn(raw, bet)
        assert result == pytest.approx(raw * 0.5, rel=1e-6)

    def test_compatible_with_portfolio_kelly_signature(self) -> None:
        """Function signature matches PortfolioKelly's expected (raw_kelly, bet) -> float."""
        fn = create_shrinkage_fn()
        bet = _make_bet()
        result = fn(0.05, bet)
        assert isinstance(result, float)

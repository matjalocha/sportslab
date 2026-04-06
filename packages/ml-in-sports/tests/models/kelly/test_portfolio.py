"""Tests for Portfolio Kelly staking system."""

import pytest
from ml_in_sports.models.kelly.portfolio import (
    BetOpportunity,
    PortfolioConstraints,
    PortfolioKelly,
    StakeRecommendation,
    _raw_kelly_fraction,
)
from ml_in_sports.models.kelly.shrinkage import create_shrinkage_fn


def _make_bet(
    match_id: str = "m1",
    league: str = "EPL",
    home_team: str = "Arsenal",
    away_team: str = "Chelsea",
    market: str = "1x2_home",
    model_prob: float = 0.55,
    odds: float = 2.00,
    round_id: str | None = "R1",
    **kwargs: object,
) -> BetOpportunity:
    """Helper to create a BetOpportunity with sensible defaults."""
    return BetOpportunity(
        match_id=match_id,
        league=league,
        home_team=home_team,
        away_team=away_team,
        market=market,
        model_prob=model_prob,
        odds=odds,
        round_id=round_id,
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# _raw_kelly_fraction
# ---------------------------------------------------------------------------


class TestRawKellyFraction:
    """Tests for the raw Kelly computation helper."""

    def test_zero_edge_zero_kelly(self) -> None:
        """Exactly break-even odds produce zero Kelly fraction."""
        # model_prob=0.50, odds=2.0 -> f*=(0.5*1 - 0.5)/1 = 0
        result = _raw_kelly_fraction(0.50, 2.00)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_positive_edge_positive_kelly(self) -> None:
        """Model edge above implied produces positive Kelly fraction."""
        # model_prob=0.60, odds=2.10 -> f*=(0.60*1.10 - 0.40)/1.10 = 0.2364
        result = _raw_kelly_fraction(0.60, 2.10)
        assert result > 0.0
        expected = (0.60 * 1.10 - 0.40) / 1.10
        assert result == pytest.approx(expected, rel=1e-6)

    def test_negative_edge_zero_kelly(self) -> None:
        """Negative edge produces zero Kelly fraction (floored)."""
        # model_prob=0.40, odds=2.00 -> f*=(0.40*1 - 0.60)/1 = -0.20
        result = _raw_kelly_fraction(0.40, 2.00)
        assert result == 0.0

    def test_odds_at_one_returns_zero(self) -> None:
        """Degenerate odds=1.0 returns zero (no potential profit)."""
        result = _raw_kelly_fraction(0.90, 1.00)
        assert result == 0.0

    def test_odds_below_one_returns_zero(self) -> None:
        """Invalid odds < 1.0 returns zero."""
        result = _raw_kelly_fraction(0.90, 0.50)
        assert result == 0.0


# ---------------------------------------------------------------------------
# PortfolioKelly — Basic behavior
# ---------------------------------------------------------------------------


class TestPortfolioKellyBasic:
    """Tests for basic Kelly stake computation."""

    def test_empty_opportunities_empty_results(self) -> None:
        """Empty input list returns empty output list."""
        pk = PortfolioKelly()
        results = pk.compute_stakes([])
        assert results == []

    def test_zero_edge_zero_stake(self) -> None:
        """Zero-edge bet gets zero stake."""
        pk = PortfolioKelly()
        bet = _make_bet(model_prob=0.50, odds=2.00)
        results = pk.compute_stakes([bet])
        assert len(results) == 1
        assert results[0].final_stake_frac == pytest.approx(0.0, abs=1e-9)
        assert results[0].edge == pytest.approx(0.0, abs=1e-9)

    def test_positive_edge_positive_stake(self) -> None:
        """Positive-edge bet gets positive stake."""
        pk = PortfolioKelly()
        bet = _make_bet(model_prob=0.60, odds=2.10)
        results = pk.compute_stakes([bet])
        assert len(results) == 1
        assert results[0].final_stake_frac > 0.0
        assert results[0].edge > 0.0

    def test_negative_edge_zero_stake(self) -> None:
        """Negative-edge bet gets zero stake."""
        pk = PortfolioKelly()
        bet = _make_bet(model_prob=0.40, odds=2.00)
        results = pk.compute_stakes([bet])
        assert len(results) == 1
        assert results[0].final_stake_frac == 0.0
        assert results[0].edge < 0.0

    def test_quarter_kelly_reduces_by_four(self) -> None:
        """Quarter-Kelly (0.25) produces 4x smaller stake than full-Kelly (1.0)."""
        bet = _make_bet(model_prob=0.60, odds=2.10)

        pk_full = PortfolioKelly(
            constraints=PortfolioConstraints(
                kelly_fraction=1.0,
                max_exposure_per_match=1.0,
                max_exposure_per_round=1.0,
                max_exposure_per_league=1.0,
                max_exposure_per_team=1.0,
            ),
        )
        pk_quarter = PortfolioKelly(
            constraints=PortfolioConstraints(
                kelly_fraction=0.25,
                max_exposure_per_match=1.0,
                max_exposure_per_round=1.0,
                max_exposure_per_league=1.0,
                max_exposure_per_team=1.0,
            ),
        )

        result_full = pk_full.compute_stakes([bet])
        result_quarter = pk_quarter.compute_stakes([bet])

        assert result_quarter[0].final_stake_frac == pytest.approx(
            result_full[0].final_stake_frac * 0.25, rel=1e-6
        )

    def test_result_is_stake_recommendation(self) -> None:
        """Results are StakeRecommendation instances with correct fields."""
        pk = PortfolioKelly()
        bet = _make_bet(model_prob=0.60, odds=2.10)
        results = pk.compute_stakes([bet])
        rec = results[0]
        assert isinstance(rec, StakeRecommendation)
        assert rec.bet is bet
        assert rec.raw_kelly >= 0.0
        assert rec.adjusted_kelly >= 0.0
        assert rec.final_stake_frac >= 0.0

    def test_bankroll_does_not_affect_fractions(self) -> None:
        """Stake fractions are bankroll-independent."""
        pk = PortfolioKelly()
        bet = _make_bet(model_prob=0.60, odds=2.10)

        results_small = pk.compute_stakes([bet], bankroll=1_000.0)
        results_large = pk.compute_stakes([bet], bankroll=100_000.0)

        assert results_small[0].final_stake_frac == pytest.approx(
            results_large[0].final_stake_frac, rel=1e-9
        )

    def test_bankroll_scales_currency_stakes(self) -> None:
        """Multiplying fraction by bankroll gives correct currency amount."""
        pk = PortfolioKelly()
        bet = _make_bet(model_prob=0.60, odds=2.10)
        bankroll = 10_000.0

        results = pk.compute_stakes([bet], bankroll=bankroll)
        currency_stake = results[0].final_stake_frac * bankroll
        assert currency_stake > 0.0
        assert currency_stake <= bankroll


# ---------------------------------------------------------------------------
# PortfolioKelly — Per-match cap
# ---------------------------------------------------------------------------


class TestPortfolioKellyPerMatchCap:
    """Tests for per-match exposure cap."""

    def test_huge_edge_capped_at_per_match_limit(self) -> None:
        """Single bet with very high edge is capped at max_exposure_per_match."""
        constraints = PortfolioConstraints(
            kelly_fraction=1.0,
            max_exposure_per_match=0.03,
            max_exposure_per_round=1.0,
            max_exposure_per_league=1.0,
            max_exposure_per_team=1.0,
        )
        pk = PortfolioKelly(constraints=constraints)
        # model_prob=0.90, odds=3.0 -> raw_kelly=0.85, very large
        bet = _make_bet(model_prob=0.90, odds=3.00)
        results = pk.compute_stakes([bet])

        assert results[0].final_stake_frac == pytest.approx(0.03, rel=1e-6)
        assert results[0].constraint_applied == "max_exposure_per_match"

    def test_small_edge_not_capped(self) -> None:
        """Small stake below per-match cap is not constrained."""
        constraints = PortfolioConstraints(
            kelly_fraction=0.25,
            max_exposure_per_match=0.03,
        )
        pk = PortfolioKelly(constraints=constraints)
        # model_prob=0.53, odds=2.0 -> raw_kelly=0.06, adjusted=0.015 < 0.03
        bet = _make_bet(model_prob=0.53, odds=2.00)
        results = pk.compute_stakes([bet])

        assert results[0].final_stake_frac < 0.03
        assert results[0].constraint_applied is None


# ---------------------------------------------------------------------------
# PortfolioKelly — Per-round cap
# ---------------------------------------------------------------------------


class TestPortfolioKellyPerRoundCap:
    """Tests for per-round exposure cap."""

    def test_round_cap_binds(self) -> None:
        """10 bets in same round with high edge are collectively capped."""
        constraints = PortfolioConstraints(
            kelly_fraction=1.0,
            max_exposure_per_match=1.0,
            max_exposure_per_round=0.15,
            max_exposure_per_league=1.0,
            max_exposure_per_team=1.0,
        )
        pk = PortfolioKelly(constraints=constraints)

        bets = [
            _make_bet(
                match_id=f"m{i}",
                model_prob=0.65,
                odds=2.00,
                round_id="R10",
                home_team=f"TeamH{i}",
                away_team=f"TeamA{i}",
            )
            for i in range(10)
        ]
        results = pk.compute_stakes(bets)
        total = sum(r.final_stake_frac for r in results)

        assert total == pytest.approx(0.15, rel=1e-6)
        assert all(r.constraint_applied == "max_exposure_per_round" for r in results)

    def test_different_rounds_independent(self) -> None:
        """Bets in different rounds are capped independently."""
        constraints = PortfolioConstraints(
            kelly_fraction=1.0,
            max_exposure_per_match=1.0,
            max_exposure_per_round=0.10,
            max_exposure_per_league=1.0,
            max_exposure_per_team=1.0,
        )
        pk = PortfolioKelly(constraints=constraints)

        bets = [
            _make_bet(
                match_id="m1",
                model_prob=0.70,
                odds=2.00,
                round_id="R1",
                home_team="TeamA",
                away_team="TeamB",
            ),
            _make_bet(
                match_id="m2",
                model_prob=0.70,
                odds=2.00,
                round_id="R2",
                home_team="TeamC",
                away_team="TeamD",
            ),
        ]
        results = pk.compute_stakes(bets)
        # Each bet is in its own round, so each can go up to 0.10
        for r in results:
            assert r.final_stake_frac <= 0.10 + 1e-9

    def test_no_round_id_skips_round_cap(self) -> None:
        """Bets with round_id=None are not grouped for round cap."""
        constraints = PortfolioConstraints(
            kelly_fraction=1.0,
            max_exposure_per_match=1.0,
            max_exposure_per_round=0.01,  # very tight, but shouldn't matter
            max_exposure_per_league=1.0,
            max_exposure_per_team=1.0,
        )
        pk = PortfolioKelly(constraints=constraints)

        bet = _make_bet(model_prob=0.70, odds=2.00, round_id=None)
        results = pk.compute_stakes([bet])
        # Should not be capped by round (round_id is None)
        raw = _raw_kelly_fraction(0.70, 2.00)
        assert results[0].final_stake_frac == pytest.approx(raw, rel=1e-6)


# ---------------------------------------------------------------------------
# PortfolioKelly — Per-league cap
# ---------------------------------------------------------------------------


class TestPortfolioKellyPerLeagueCap:
    """Tests for per-league exposure cap."""

    def test_league_cap_binds(self) -> None:
        """Many bets in the same league are collectively capped."""
        constraints = PortfolioConstraints(
            kelly_fraction=1.0,
            max_exposure_per_match=1.0,
            max_exposure_per_round=1.0,
            max_exposure_per_league=0.20,
            max_exposure_per_team=1.0,
        )
        pk = PortfolioKelly(constraints=constraints)

        bets = [
            _make_bet(
                match_id=f"m{i}",
                model_prob=0.65,
                odds=2.00,
                league="Bundesliga",
                round_id=f"R{i}",
                home_team=f"BundesH{i}",
                away_team=f"BundesA{i}",
            )
            for i in range(8)
        ]
        results = pk.compute_stakes(bets)
        total = sum(r.final_stake_frac for r in results)

        assert total == pytest.approx(0.20, rel=1e-6)

    def test_different_leagues_independent(self) -> None:
        """Bets in different leagues are capped independently."""
        constraints = PortfolioConstraints(
            kelly_fraction=1.0,
            max_exposure_per_match=1.0,
            max_exposure_per_round=1.0,
            max_exposure_per_league=0.10,
            max_exposure_per_team=1.0,
        )
        pk = PortfolioKelly(constraints=constraints)

        bets = [
            _make_bet(
                match_id="m1",
                model_prob=0.70,
                odds=2.00,
                league="EPL",
                round_id="R1",
                home_team="TeamA",
                away_team="TeamB",
            ),
            _make_bet(
                match_id="m2",
                model_prob=0.70,
                odds=2.00,
                league="LaLiga",
                round_id="R1",
                home_team="TeamC",
                away_team="TeamD",
            ),
        ]
        results = pk.compute_stakes(bets)
        for r in results:
            assert r.final_stake_frac <= 0.10 + 1e-9


# ---------------------------------------------------------------------------
# PortfolioKelly — Per-team cap
# ---------------------------------------------------------------------------


class TestPortfolioKellyPerTeamCap:
    """Tests for per-team exposure cap."""

    def test_team_appears_home_and_away(self) -> None:
        """Team exposure sums across home and away appearances."""
        constraints = PortfolioConstraints(
            kelly_fraction=1.0,
            max_exposure_per_match=1.0,
            max_exposure_per_round=1.0,
            max_exposure_per_league=1.0,
            max_exposure_per_team=0.06,
        )
        pk = PortfolioKelly(constraints=constraints)

        bets = [
            _make_bet(
                match_id="m1",
                model_prob=0.70,
                odds=2.00,
                home_team="Arsenal",
                away_team="Chelsea",
                round_id="R1",
            ),
            _make_bet(
                match_id="m2",
                model_prob=0.70,
                odds=2.00,
                home_team="Liverpool",
                away_team="Arsenal",
                round_id="R1",
            ),
        ]
        results = pk.compute_stakes(bets)

        # Arsenal appears in both bets, total exposure on Arsenal must be <= 0.06
        arsenal_exposure = sum(r.final_stake_frac for r in results)
        assert arsenal_exposure <= 0.06 + 1e-9

    def test_team_cap_proportional_reduction(self) -> None:
        """When team cap binds, bets involving that team are scaled proportionally."""
        constraints = PortfolioConstraints(
            kelly_fraction=1.0,
            max_exposure_per_match=1.0,
            max_exposure_per_round=1.0,
            max_exposure_per_league=1.0,
            max_exposure_per_team=0.06,
        )
        pk = PortfolioKelly(constraints=constraints)

        bets = [
            _make_bet(
                match_id="m1",
                model_prob=0.65,
                odds=2.00,
                home_team="Arsenal",
                away_team="Chelsea",
                round_id="R1",
            ),
            _make_bet(
                match_id="m2",
                model_prob=0.75,
                odds=2.00,
                home_team="Liverpool",
                away_team="Arsenal",
                round_id="R2",
            ),
        ]
        results = pk.compute_stakes(bets)

        # Both bets involve Arsenal, so both are scaled down
        for r in results:
            assert r.constraint_applied == "max_exposure_per_team"


# ---------------------------------------------------------------------------
# PortfolioKelly — With shrinkage
# ---------------------------------------------------------------------------


class TestPortfolioKellyWithShrinkage:
    """Tests for portfolio Kelly with shrinkage function."""

    def test_shrinkage_reduces_stakes(self) -> None:
        """Using shrinkage produces smaller stakes than without."""
        bet = _make_bet(model_prob=0.70, odds=2.00)
        constraints = PortfolioConstraints(
            kelly_fraction=0.25,
            max_exposure_per_match=1.0,
            max_exposure_per_round=1.0,
            max_exposure_per_league=1.0,
            max_exposure_per_team=1.0,
        )

        pk_no_shrink = PortfolioKelly(constraints=constraints)
        pk_with_shrink = PortfolioKelly(
            constraints=constraints,
            shrinkage_fn=create_shrinkage_fn(max_edge=0.10),
        )

        result_no = pk_no_shrink.compute_stakes([bet])
        result_with = pk_with_shrink.compute_stakes([bet])

        # edge = 0.70 - 0.50 = 0.20, above max_edge=0.10 -> shrinkage applies
        assert result_with[0].final_stake_frac < result_no[0].final_stake_frac

    def test_shrinkage_not_applied_to_zero_kelly(self) -> None:
        """Shrinkage function is not called when raw Kelly is zero."""
        call_count = 0

        def counting_shrinkage(raw_kelly: float, bet: BetOpportunity) -> float:
            nonlocal call_count
            call_count += 1
            return raw_kelly

        pk = PortfolioKelly(shrinkage_fn=counting_shrinkage)
        bet = _make_bet(model_prob=0.40, odds=2.00)  # negative edge
        pk.compute_stakes([bet])

        assert call_count == 0


# ---------------------------------------------------------------------------
# PortfolioKelly — Multiple constraints interaction
# ---------------------------------------------------------------------------


class TestPortfolioKellyConstraintInteraction:
    """Tests for constraint ordering and interaction."""

    def test_tighter_match_cap_overrides_round_cap(self) -> None:
        """Per-match cap applied first; round cap sees already-capped values."""
        constraints = PortfolioConstraints(
            kelly_fraction=1.0,
            max_exposure_per_match=0.02,
            max_exposure_per_round=0.50,  # loose, won't bind
            max_exposure_per_league=1.0,
            max_exposure_per_team=1.0,
        )
        pk = PortfolioKelly(constraints=constraints)

        bets = [
            _make_bet(
                match_id=f"m{i}",
                model_prob=0.80,
                odds=2.50,
                round_id="R1",
                home_team=f"TeamH{i}",
                away_team=f"TeamA{i}",
            )
            for i in range(5)
        ]
        results = pk.compute_stakes(bets)

        # Each bet capped at 0.02, total = 0.10 < 0.50 round cap
        for r in results:
            assert r.final_stake_frac == pytest.approx(0.02, rel=1e-6)
            assert r.constraint_applied == "max_exposure_per_match"

    def test_order_preserved(self) -> None:
        """Output order matches input order."""
        pk = PortfolioKelly()
        bets = [
            _make_bet(match_id="first", model_prob=0.55, odds=2.00),
            _make_bet(match_id="second", model_prob=0.60, odds=2.10),
            _make_bet(match_id="third", model_prob=0.45, odds=2.00),
        ]
        results = pk.compute_stakes(bets)

        assert results[0].bet.match_id == "first"
        assert results[1].bet.match_id == "second"
        assert results[2].bet.match_id == "third"

    def test_multiple_bets_mixed_edges(self) -> None:
        """Portfolio with positive, zero, and negative edge bets."""
        pk = PortfolioKelly()
        bets = [
            _make_bet(match_id="m1", model_prob=0.60, odds=2.10, home_team="A", away_team="B"),
            _make_bet(match_id="m2", model_prob=0.50, odds=2.00, home_team="C", away_team="D"),
            _make_bet(match_id="m3", model_prob=0.30, odds=2.00, home_team="E", away_team="F"),
        ]
        results = pk.compute_stakes(bets)

        assert results[0].final_stake_frac > 0.0   # positive edge
        assert results[1].final_stake_frac == 0.0   # zero edge
        assert results[2].final_stake_frac == 0.0   # negative edge


# ---------------------------------------------------------------------------
# PortfolioConstraints — Defaults
# ---------------------------------------------------------------------------


class TestPortfolioConstraints:
    """Tests for constraint dataclass defaults."""

    def test_default_values(self) -> None:
        """Default constraints match expected conservative values."""
        c = PortfolioConstraints()
        assert c.kelly_fraction == 0.25
        assert c.max_exposure_per_match == 0.03
        assert c.max_exposure_per_round == 0.15
        assert c.max_exposure_per_league == 0.20
        assert c.max_exposure_per_team == 0.06

    def test_frozen(self) -> None:
        """Constraints are immutable."""
        c = PortfolioConstraints()
        with pytest.raises(AttributeError):
            c.kelly_fraction = 0.50  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BetOpportunity — Immutability
# ---------------------------------------------------------------------------


class TestBetOpportunity:
    """Tests for bet opportunity dataclass."""

    def test_frozen(self) -> None:
        """BetOpportunity is immutable."""
        bet = _make_bet()
        with pytest.raises(AttributeError):
            bet.model_prob = 0.99  # type: ignore[misc]

    def test_optional_fields_default_none(self) -> None:
        """Optional fields default to None."""
        bet = BetOpportunity(
            match_id="m1",
            league="EPL",
            home_team="A",
            away_team="B",
            market="1x2",
            model_prob=0.5,
            odds=2.0,
        )
        assert bet.closing_odds is None
        assert bet.round_id is None

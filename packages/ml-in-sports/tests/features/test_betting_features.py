"""Tests for the betting features module."""

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.features.betting_features import (
    add_betting_features,
    compute_fair_probabilities,
    compute_implied_probabilities,
    compute_market_consensus,
    compute_overround,
)


@pytest.fixture
def odds_1x2() -> pd.DataFrame:
    """DataFrame with 1X2 odds from two bookmakers and averages."""
    return pd.DataFrame({
        "b365_home": [1.80, 2.50],
        "b365_draw": [3.50, 3.20],
        "b365_away": [4.50, 2.90],
        "avg_home": [1.85, 2.45],
        "avg_draw": [3.40, 3.30],
        "avg_away": [4.20, 2.85],
    })


@pytest.fixture
def odds_over_under() -> pd.DataFrame:
    """DataFrame with over/under 2.5 odds."""
    return pd.DataFrame({
        "b365_over_25": [1.90, 2.10],
        "b365_under_25": [1.95, 1.75],
        "avg_over_25": [1.92, 2.05],
        "avg_under_25": [1.93, 1.80],
    })


@pytest.fixture
def full_odds(
    odds_1x2: pd.DataFrame,
    odds_over_under: pd.DataFrame,
) -> pd.DataFrame:
    """DataFrame with all odds columns."""
    return pd.concat([odds_1x2, odds_over_under], axis=1)


class TestComputeImpliedProbabilities:
    """Tests for compute_implied_probabilities."""

    def test_home_implied_probability(
        self, odds_1x2: pd.DataFrame,
    ) -> None:
        """Implied prob = 1 / odds for home."""
        result = compute_implied_probabilities(odds_1x2)
        expected = 1.0 / 1.85
        assert result["implied_prob_home"].iloc[0] == pytest.approx(expected)

    def test_draw_implied_probability(
        self, odds_1x2: pd.DataFrame,
    ) -> None:
        """Implied prob = 1 / odds for draw."""
        result = compute_implied_probabilities(odds_1x2)
        expected = 1.0 / 3.40
        assert result["implied_prob_draw"].iloc[0] == pytest.approx(expected)

    def test_away_implied_probability(
        self, odds_1x2: pd.DataFrame,
    ) -> None:
        """Implied prob = 1 / odds for away."""
        result = compute_implied_probabilities(odds_1x2)
        expected = 1.0 / 4.20
        assert result["implied_prob_away"].iloc[0] == pytest.approx(expected)

    def test_over_25_implied_probability(
        self, full_odds: pd.DataFrame,
    ) -> None:
        """Implied prob for over 2.5 goals."""
        result = compute_implied_probabilities(full_odds)
        expected = 1.0 / 1.92
        assert result["implied_prob_over_25"].iloc[0] == pytest.approx(
            expected,
        )

    def test_under_25_implied_probability(
        self, full_odds: pd.DataFrame,
    ) -> None:
        """Implied prob for under 2.5 goals."""
        result = compute_implied_probabilities(full_odds)
        expected = 1.0 / 1.93
        assert result["implied_prob_under_25"].iloc[0] == pytest.approx(
            expected,
        )

    def test_missing_odds_produce_nan(self) -> None:
        """NaN odds produce NaN implied probabilities."""
        df = pd.DataFrame({
            "avg_home": [np.nan],
            "avg_draw": [3.40],
            "avg_away": [4.20],
        })
        result = compute_implied_probabilities(df)
        assert pd.isna(result["implied_prob_home"].iloc[0])

    def test_preserves_original_columns(
        self, odds_1x2: pd.DataFrame,
    ) -> None:
        """Original columns remain after adding implied probs."""
        original_cols = set(odds_1x2.columns)
        result = compute_implied_probabilities(odds_1x2)
        assert original_cols.issubset(set(result.columns))

    def test_uses_avg_odds(self, odds_1x2: pd.DataFrame) -> None:
        """Implied probabilities are derived from avg odds."""
        result = compute_implied_probabilities(odds_1x2)
        assert "implied_prob_home" in result.columns
        assert "implied_prob_draw" in result.columns
        assert "implied_prob_away" in result.columns


class TestComputeOverround:
    """Tests for compute_overround."""

    def test_overround_1x2_positive(
        self, odds_1x2: pd.DataFrame,
    ) -> None:
        """1X2 overround is positive (market has margin)."""
        with_probs = compute_implied_probabilities(odds_1x2)
        result = compute_overround(with_probs)
        assert result["overround_1x2"].iloc[0] > 0

    def test_overround_1x2_value(
        self, odds_1x2: pd.DataFrame,
    ) -> None:
        """Overround = sum of implied probs - 1."""
        with_probs = compute_implied_probabilities(odds_1x2)
        result = compute_overround(with_probs)
        implied_sum = (
            1.0 / 1.85 + 1.0 / 3.40 + 1.0 / 4.20
        )
        expected = implied_sum - 1.0
        assert result["overround_1x2"].iloc[0] == pytest.approx(expected)

    def test_overround_ou_value(
        self, full_odds: pd.DataFrame,
    ) -> None:
        """Over/under overround = sum of implied probs - 1."""
        with_probs = compute_implied_probabilities(full_odds)
        result = compute_overround(with_probs)
        implied_sum = 1.0 / 1.92 + 1.0 / 1.93
        expected = implied_sum - 1.0
        assert result["overround_ou"].iloc[0] == pytest.approx(expected)

    def test_overround_missing_probs_produce_nan(self) -> None:
        """Missing implied probs produce NaN overround."""
        df = pd.DataFrame({
            "implied_prob_home": [np.nan],
            "implied_prob_draw": [0.30],
            "implied_prob_away": [0.25],
        })
        result = compute_overround(df)
        assert pd.isna(result["overround_1x2"].iloc[0])


class TestComputeFairProbabilities:
    """Tests for compute_fair_probabilities."""

    def test_fair_probs_sum_to_one(
        self, odds_1x2: pd.DataFrame,
    ) -> None:
        """Fair probabilities for 1X2 sum to 1.0."""
        with_probs = compute_implied_probabilities(odds_1x2)
        result = compute_fair_probabilities(with_probs)
        total = (
            result["fair_prob_home"].iloc[0]
            + result["fair_prob_draw"].iloc[0]
            + result["fair_prob_away"].iloc[0]
        )
        assert total == pytest.approx(1.0)

    def test_fair_prob_home_value(
        self, odds_1x2: pd.DataFrame,
    ) -> None:
        """Fair home probability = implied / sum(implied)."""
        with_probs = compute_implied_probabilities(odds_1x2)
        result = compute_fair_probabilities(with_probs)
        imp_h = 1.0 / 1.85
        imp_d = 1.0 / 3.40
        imp_a = 1.0 / 4.20
        expected = imp_h / (imp_h + imp_d + imp_a)
        assert result["fair_prob_home"].iloc[0] == pytest.approx(expected)

    def test_fair_prob_over_under_sum_to_one(
        self, full_odds: pd.DataFrame,
    ) -> None:
        """Fair over/under probabilities sum to 1.0."""
        with_probs = compute_implied_probabilities(full_odds)
        result = compute_fair_probabilities(with_probs)
        total = (
            result["fair_prob_over_25"].iloc[0]
            + result["fair_prob_under_25"].iloc[0]
        )
        assert total == pytest.approx(1.0)

    def test_fair_probs_less_than_implied(
        self, odds_1x2: pd.DataFrame,
    ) -> None:
        """Fair probs are smaller than implied probs (overround removed)."""
        with_probs = compute_implied_probabilities(odds_1x2)
        result = compute_fair_probabilities(with_probs)
        assert (
            result["fair_prob_home"].iloc[0]
            < with_probs["implied_prob_home"].iloc[0]
        )


class TestComputeMarketConsensus:
    """Tests for compute_market_consensus."""

    def test_consensus_home_averages_bookmakers(self) -> None:
        """Consensus home = mean of all bookmaker implied probs."""
        df = pd.DataFrame({
            "b365_home": [1.80],
            "avg_home": [1.85],
            "b365_draw": [3.50],
            "avg_draw": [3.40],
            "b365_away": [4.50],
            "avg_away": [4.20],
        })
        result = compute_market_consensus(df)
        b365_imp = 1.0 / 1.80
        avg_imp = 1.0 / 1.85
        expected = (b365_imp + avg_imp) / 2.0
        assert result["consensus_home"].iloc[0] == pytest.approx(expected)

    def test_consensus_draw(self) -> None:
        """Consensus draw = mean of bookmaker implied draw probs."""
        df = pd.DataFrame({
            "b365_home": [1.80],
            "avg_home": [1.85],
            "b365_draw": [3.50],
            "avg_draw": [3.40],
            "b365_away": [4.50],
            "avg_away": [4.20],
        })
        result = compute_market_consensus(df)
        b365_imp = 1.0 / 3.50
        avg_imp = 1.0 / 3.40
        expected = (b365_imp + avg_imp) / 2.0
        assert result["consensus_draw"].iloc[0] == pytest.approx(expected)

    def test_consensus_away(self) -> None:
        """Consensus away = mean of bookmaker implied away probs."""
        df = pd.DataFrame({
            "b365_home": [1.80],
            "avg_home": [1.85],
            "b365_draw": [3.50],
            "avg_draw": [3.40],
            "b365_away": [4.50],
            "avg_away": [4.20],
        })
        result = compute_market_consensus(df)
        b365_imp = 1.0 / 4.50
        avg_imp = 1.0 / 4.20
        expected = (b365_imp + avg_imp) / 2.0
        assert result["consensus_away"].iloc[0] == pytest.approx(expected)

    def test_consensus_with_missing_bookmaker(self) -> None:
        """Consensus still works when one bookmaker has NaN."""
        df = pd.DataFrame({
            "b365_home": [np.nan],
            "avg_home": [1.85],
            "b365_draw": [np.nan],
            "avg_draw": [3.40],
            "b365_away": [np.nan],
            "avg_away": [4.20],
        })
        result = compute_market_consensus(df)
        expected = 1.0 / 1.85
        assert result["consensus_home"].iloc[0] == pytest.approx(expected)


class TestAddBettingFeatures:
    """Tests for the top-level add_betting_features function."""

    def test_adds_all_feature_groups(
        self, full_odds: pd.DataFrame,
    ) -> None:
        """All betting feature groups are added."""
        result = add_betting_features(full_odds)
        expected_cols = [
            "implied_prob_home",
            "implied_prob_draw",
            "implied_prob_away",
            "overround_1x2",
            "fair_prob_home",
            "fair_prob_draw",
            "fair_prob_away",
            "consensus_home",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_preserves_original_data(
        self, full_odds: pd.DataFrame,
    ) -> None:
        """Original data is unchanged."""
        original_values = full_odds["b365_home"].copy()
        result = add_betting_features(full_odds)
        pd.testing.assert_series_equal(
            result["b365_home"], original_values,
        )

    def test_handles_empty_dataframe(self) -> None:
        """Returns empty DataFrame with no errors."""
        df = pd.DataFrame()
        result = add_betting_features(df)
        assert isinstance(result, pd.DataFrame)

    def test_handles_partial_odds_columns(self) -> None:
        """Works with only 1X2 odds (no over/under)."""
        df = pd.DataFrame({
            "avg_home": [1.85],
            "avg_draw": [3.40],
            "avg_away": [4.20],
        })
        result = add_betting_features(df)
        assert "implied_prob_home" in result.columns
        assert "overround_1x2" in result.columns

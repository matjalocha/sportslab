"""Closing Line Value (CLV) tracking.

CLV measures whether our model's predictions beat the market's closing line.
Positive CLV = genuine edge. Negative CLV = no edge (profits from variance).

The closing line — especially from a sharp book like Pinnacle — is the
best available proxy for the true probability at kickoff. A model that
consistently beats the closing line has a sustainable edge; one that
doesn't is relying on luck.

Key metrics:
- Per-bet CLV = model_prob - closing_implied_prob
- Rolling CLV = moving average over N bets (tracks edge stability)
- CLV summary = mean, SE, CI — statistical significance of the edge
"""

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


def compute_match_clv(
    model_probs: np.ndarray,
    closing_odds: np.ndarray,
) -> np.ndarray:
    """Compute per-bet CLV.

    CLV = model_implied_prob - market_implied_prob

    where market_implied_prob = 1 / closing_odds.

    Positive CLV means the model assigns a higher probability to the
    outcome than the closing line implies, i.e. the model identified
    value that the market priced out by close.

    Args:
        model_probs: Model's predicted probabilities, shape (N,).
            Values should be in [0, 1].
        closing_odds: Pinnacle closing decimal odds, shape (N,).
            Values must be > 1.0 (decimal format).

    Returns:
        Array of per-bet CLV values, shape (N,).  NaN where
        closing_odds is NaN or <= 0.

    Raises:
        ValueError: If arrays have different shapes.
    """
    model_probs = np.asarray(model_probs, dtype=np.float64)
    closing_odds = np.asarray(closing_odds, dtype=np.float64)

    if model_probs.shape != closing_odds.shape:
        raise ValueError(
            f"Shape mismatch: model_probs {model_probs.shape} vs closing_odds {closing_odds.shape}"
        )

    # Guard against invalid odds (NaN, zero, negative).
    valid_mask = np.isfinite(closing_odds) & (closing_odds > 0)
    market_implied = np.full_like(closing_odds, np.nan)
    market_implied[valid_mask] = 1.0 / closing_odds[valid_mask]

    clv: np.ndarray = model_probs - market_implied

    invalid_count = int((~valid_mask).sum())
    if invalid_count > 0:
        logger.warning(
            "invalid_closing_odds",
            invalid_count=invalid_count,
            total=len(closing_odds),
        )

    return clv


def compute_rolling_clv(
    clv_values: np.ndarray,
    window: int = 100,
) -> np.ndarray:
    """Compute rolling mean CLV over a window of bets.

    Uses pandas internally for NaN-aware rolling mean, then returns
    the result as a numpy array.

    Args:
        clv_values: Per-bet CLV values, shape (N,).
        window: Rolling window size. Must be >= 1.

    Returns:
        Rolling mean CLV array, shape (N,).  The first (window - 1)
        values are NaN because the window is not yet full.

    Raises:
        ValueError: If window < 1.
    """
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")

    clv_values = np.asarray(clv_values, dtype=np.float64)
    series = pd.Series(clv_values)
    rolling_mean = series.rolling(window=window, min_periods=window).mean()
    return rolling_mean.to_numpy()


def clv_summary(
    clv_values: np.ndarray,
) -> dict[str, float]:
    """Compute summary statistics for CLV distribution.

    Provides mean, median, standard deviation, percentage of positive
    CLV bets, standard error of the mean, and a 95% confidence interval.

    The confidence interval uses the normal approximation (z = 1.96).
    For small samples (< 30), consider using a t-distribution instead.

    Args:
        clv_values: Per-bet CLV values. NaN values are excluded.

    Returns:
        Dictionary with keys: ``mean``, ``median``, ``std``,
        ``pct_positive``, ``se``, ``ci_lower``, ``ci_upper``,
        ``count``.  All values are float.  If the input is empty
        (or all NaN), all values are NaN except ``count`` which is 0.
    """
    clv_values = np.asarray(clv_values, dtype=np.float64)
    clean = clv_values[np.isfinite(clv_values)]

    if len(clean) == 0:
        return {
            "mean": float("nan"),
            "median": float("nan"),
            "std": float("nan"),
            "pct_positive": float("nan"),
            "se": float("nan"),
            "ci_lower": float("nan"),
            "ci_upper": float("nan"),
            "count": 0.0,
        }

    mean = float(np.mean(clean))
    std = float(np.std(clean, ddof=1)) if len(clean) > 1 else 0.0
    se = std / np.sqrt(len(clean)) if len(clean) > 0 else 0.0
    z_95 = 1.96

    return {
        "mean": mean,
        "median": float(np.median(clean)),
        "std": std,
        "pct_positive": float(np.mean(clean > 0) * 100),
        "se": se,
        "ci_lower": mean - z_95 * se,
        "ci_upper": mean + z_95 * se,
        "count": float(len(clean)),
    }


def merge_closing_odds(
    predictions_df: pd.DataFrame,
    odds_df: pd.DataFrame,
    on: list[str] | None = None,
) -> pd.DataFrame:
    """Merge model predictions with closing odds for CLV computation.

    Performs a left join so that all predictions are preserved; matches
    without closing odds will have NaN in the odds columns.

    Args:
        predictions_df: DataFrame with model predictions.  Must have
            the join columns (default: league, season, home_team,
            away_team).
        odds_df: DataFrame with closing odds from
            :func:`~ml_in_sports.processing.odds.pinnacle.load_pinnacle_odds`.
        on: Join columns.  Default:
            ``["league", "season", "home_team", "away_team"]``.

    Returns:
        Merged DataFrame with both predictions and closing odds columns.

    Raises:
        ValueError: If required join columns are missing from either
            DataFrame.
    """
    if on is None:
        on = ["league", "season", "home_team", "away_team"]

    # Validate join columns exist.
    for name, frame in [("predictions_df", predictions_df), ("odds_df", odds_df)]:
        missing = set(on) - set(frame.columns)
        if missing:
            raise ValueError(
                f"{name} missing join columns: {sorted(missing)}. "
                f"Available: {sorted(frame.columns)}"
            )

    merged = predictions_df.merge(
        odds_df,
        on=on,
        how="left",
        suffixes=("", "_odds"),
    )

    matched = merged["pinnacle_home"].notna().sum() if "pinnacle_home" in merged.columns else 0
    total = len(predictions_df)
    match_rate = matched / total * 100 if total > 0 else 0.0

    logger.info(
        "closing_odds_merged",
        total_predictions=total,
        matched=int(matched),
        match_rate_pct=round(match_rate, 1),
    )

    return merged

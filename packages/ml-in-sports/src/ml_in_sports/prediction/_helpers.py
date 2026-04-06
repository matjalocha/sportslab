"""Internal helpers for daily prediction data selection and candidate building."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from ml_in_sports.models.kelly.portfolio import BetOpportunity
from ml_in_sports.prediction._constants import (
    EXCLUDED_COLS,
    MARKET_SPECS,
    MAX_NAN_FRACTION,
    TARGET_COL,
    TARGET_ENCODING,
)
from ml_in_sports.prediction.models import _BetCandidate


def select_upcoming_matches(df: pd.DataFrame, prediction_date: dt.date) -> pd.DataFrame:
    """Filter to upcoming/unresolved matches, preferring same-day if available."""
    result_missing = (
        df[TARGET_COL].isna()
        if TARGET_COL in df.columns
        else pd.Series(False, index=df.index)
    )
    match_dates = _match_dates(df)
    future_or_today = (
        match_dates >= pd.Timestamp(prediction_date)
        if match_dates is not None
        else pd.Series(False, index=df.index)
    )
    upcoming_df = df[result_missing | future_or_today].copy()

    if match_dates is not None and not upcoming_df.empty:
        same_day = upcoming_df[
            match_dates.loc[upcoming_df.index] == pd.Timestamp(prediction_date)
        ].copy()
        if not same_day.empty:
            upcoming_df = same_day

    return upcoming_df.reset_index(drop=True)


def select_recent_training_matches(
    df: pd.DataFrame,
    prediction_date: dt.date,
) -> pd.DataFrame:
    """Select completed matches from the two most recent seasons before ``prediction_date``."""
    if TARGET_COL not in df.columns:
        return pd.DataFrame()

    completed_df = df[df[TARGET_COL].isin(TARGET_ENCODING)].copy()
    match_dates = _match_dates(completed_df)
    if match_dates is not None:
        completed_df = completed_df[match_dates < pd.Timestamp(prediction_date)].copy()

    if "season" not in completed_df.columns or completed_df.empty:
        return completed_df.reset_index(drop=True)

    seasons = sorted(completed_df["season"].dropna().astype(str).unique().tolist())
    recent_df = completed_df[
        completed_df["season"].astype(str).isin(seasons[-2:])
    ].copy()
    return recent_df.reset_index(drop=True)


def select_feature_columns(train_df: pd.DataFrame) -> list[str]:
    """Identify numeric feature columns with NaN rate below ``MAX_NAN_FRACTION``."""
    if train_df.empty:
        return []

    numeric_cols = train_df.select_dtypes(include="number").columns.tolist()
    feature_cols = [col for col in numeric_cols if col not in EXCLUDED_COLS]
    if not feature_cols:
        return []

    nan_fractions = train_df[feature_cols].isna().mean()
    return [
        col for col in feature_cols
        if float(nan_fractions.loc[col]) <= MAX_NAN_FRACTION
    ]


def prepare_features(
    train_df: pd.DataFrame,
    upcoming_df: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame]:
    """Impute NaNs and encode the target column.

    Args:
        train_df: Training data with target column.
        upcoming_df: Upcoming matches to predict.
        feature_cols: Columns to use as features.

    Returns:
        Tuple of (x_train, y_train, x_upcoming).
    """
    medians = train_df[feature_cols].median()
    x_train = train_df[feature_cols].fillna(medians).fillna(0.0)
    x_upcoming = upcoming_df.reindex(columns=feature_cols).fillna(medians).fillna(0.0)
    y_train = train_df[TARGET_COL].map(TARGET_ENCODING).to_numpy(dtype=np.int64)
    return x_train, y_train, x_upcoming


def collect_candidates(
    upcoming_df: pd.DataFrame,
    probabilities: np.ndarray,
    prediction_date: dt.date,
    min_edge: float,
) -> list[_BetCandidate]:
    """Scan all matches and markets for value bets above the edge threshold.

    Args:
        upcoming_df: Upcoming match DataFrame.
        probabilities: Model probabilities of shape ``(n, 3)``.
        prediction_date: Date used for kickoff fallback.
        min_edge: Minimum edge to include a candidate.

    Returns:
        List of bet candidates passing the edge filter.
    """
    candidates: list[_BetCandidate] = []
    for row_idx, (_, row) in enumerate(upcoming_df.iterrows()):
        candidates.extend(
            _candidates_for_match(row, int(row_idx), probabilities, prediction_date, min_edge)
        )
    return candidates


def mock_candidate(
    suffix: str,
    home_team: str,
    away_team: str,
    market: str,
    model_prob: float,
    best_odds: float,
    kickoff: dt.datetime,
    prediction_date: dt.date,
) -> _BetCandidate:
    """Create a placeholder bet candidate for fallback predictions."""
    return _BetCandidate(
        opportunity=BetOpportunity(
            match_id=f"mock-{prediction_date.isoformat()}-{suffix}",
            league="Mock League",
            home_team=home_team,
            away_team=away_team,
            market=market,
            model_prob=model_prob,
            odds=best_odds,
            round_id=kickoff.date().isoformat(),
        ),
        kickoff=kickoff,
        bookmaker_prob=1.0 / best_odds,
        min_odds=1.0 / model_prob,
        model_agreement=1,
        best_bookmaker="MockBook",
    )


def _candidates_for_match(
    row: pd.Series,
    row_idx: int,
    probabilities: np.ndarray,
    prediction_date: dt.date,
    min_edge: float,
) -> list[_BetCandidate]:
    """Build bet candidates for a single match across all markets."""
    kickoff = _row_kickoff(row, prediction_date)
    league = _row_string(row, "league", "Mock League")
    home_team = _row_string(row, "home_team", "Home")
    away_team = _row_string(row, "away_team", "Away")
    match_id = _row_string(
        row, "match_id",
        _row_string(row, "id", f"{league}:{home_team}:{away_team}:{kickoff.date()}"),
    )

    candidates: list[_BetCandidate] = []
    for market, class_idx, odds_specs in MARKET_SPECS:
        candidate = _evaluate_market(
            row, row_idx, probabilities, market, class_idx, odds_specs,
            match_id, league, home_team, away_team, kickoff, min_edge,
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _evaluate_market(
    row: pd.Series,
    row_idx: int,
    probabilities: np.ndarray,
    market: str,
    class_idx: int,
    odds_specs: tuple[tuple[str, str], ...],
    match_id: str,
    league: str,
    home_team: str,
    away_team: str,
    kickoff: dt.datetime,
    min_edge: float,
) -> _BetCandidate | None:
    """Evaluate a single market and return a candidate if edge is sufficient."""
    model_prob = float(probabilities[row_idx, class_idx])
    odds_result = _best_odds(row, odds_specs)
    if odds_result is None or model_prob <= 0.0:
        return None

    best_bookmaker, best_odds_val = odds_result
    bookmaker_prob = 1.0 / best_odds_val
    if model_prob - bookmaker_prob < min_edge:
        return None

    return _BetCandidate(
        opportunity=BetOpportunity(
            match_id=match_id, league=league, home_team=home_team,
            away_team=away_team, market=market, model_prob=model_prob,
            odds=best_odds_val, round_id=kickoff.date().isoformat(),
        ),
        kickoff=kickoff,
        bookmaker_prob=bookmaker_prob,
        min_odds=1.0 / model_prob,
        model_agreement=1,
        best_bookmaker=best_bookmaker,
    )


def _match_dates(df: pd.DataFrame) -> pd.Series | None:
    """Extract normalized match dates from kickoff or date column."""
    for col in ("kickoff", "date"):
        if col in df.columns:
            return pd.to_datetime(df[col], errors="coerce").dt.normalize()
    return None


def _row_string(row: pd.Series, column: str, default: str) -> str:
    """Safely extract a string value from a row."""
    value = row.get(column, default)
    if pd.isna(value):
        return default
    return str(value)


def _row_kickoff(row: pd.Series, prediction_date: dt.date) -> dt.datetime:
    """Extract kickoff datetime from a row, falling back to noon."""
    value = row.get("kickoff", row.get("date", None))
    if value is None or pd.isna(value):
        return dt.datetime.combine(prediction_date, dt.time(hour=12))
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return dt.datetime.combine(prediction_date, dt.time(hour=12))
    return timestamp.to_pydatetime()


def _best_odds(
    row: pd.Series,
    odds_specs: tuple[tuple[str, str], ...],
) -> tuple[str, float] | None:
    """Find the best available odds across bookmakers."""
    best_bookmaker = ""
    best_odds = 0.0
    for bookmaker, column in odds_specs:
        if column not in row.index:
            continue
        value = row[column]
        if pd.isna(value):
            continue
        odds = float(value)
        if odds > best_odds:
            best_bookmaker = bookmaker
            best_odds = odds
    if best_odds <= 1.0:
        return None
    return best_bookmaker, best_odds

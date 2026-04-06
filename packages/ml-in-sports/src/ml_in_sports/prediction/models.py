"""Data models for daily bet recommendation pipeline."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd

from ml_in_sports.models.kelly.portfolio import BetOpportunity


class ProbabilityModel(Protocol):
    """Minimal model interface used by the daily predictor."""

    def fit(self, x: pd.DataFrame, y: np.ndarray) -> None:
        """Fit the model on feature data."""
        ...

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        """Return class probabilities for ``X``."""
        ...


@dataclass(frozen=True)
class BetRecommendation:
    """A single daily betting recommendation."""

    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff: dt.datetime | str
    market: str
    model_prob: float
    bookmaker_prob: float
    edge: float
    min_odds: float
    kelly_fraction: float
    stake_eur: float
    model_agreement: int
    best_bookmaker: str
    best_odds: float

    @property
    def kickoff_dt(self) -> dt.datetime:
        """Return kickoff as a datetime object."""
        return parse_kickoff_datetime(self.kickoff)


@dataclass(frozen=True)
class _BetCandidate:
    """Internal candidate before Kelly sizing."""

    opportunity: BetOpportunity
    kickoff: dt.datetime
    bookmaker_prob: float
    min_odds: float
    model_agreement: int
    best_bookmaker: str


def parse_kickoff_datetime(value: dt.datetime | str) -> dt.datetime:
    """Parse a kickoff value into a datetime object.

    Args:
        value: Either a datetime instance or an ISO-format string.

    Returns:
        Parsed datetime.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    if isinstance(value, dt.datetime):
        return value
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        timestamp = pd.Timestamp(value)
        if pd.isna(timestamp):
            raise ValueError(f"Invalid kickoff datetime: {value!r}") from None
        return timestamp.to_pydatetime()

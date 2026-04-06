"""Track bet results and compute daily P&L."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import structlog

from ml_in_sports.prediction.daily import BetRecommendation, DailyPredictor

logger = structlog.get_logger(__name__)

_RESULT_BY_MARKET: dict[str, str] = {
    "1x2_home": "home",
    "1x2_draw": "draw",
    "1x2_away": "away",
}


@dataclass(frozen=True)
class BetResult:
    """Result of a placed bet.

    Attributes:
        recommendation: Original bet recommendation.
        actual_score: Match score, e.g. ``"2-1"``.
        actual_result: Match result: ``"home"``, ``"draw"``, or ``"away"``.
        hit: Whether the bet was correct.
        closing_odds: Pinnacle/market closing odds for CLV. None if unavailable.
        clv: Closing Line Value as ``model_prob - 1 / closing_odds``.
        pnl: Profit/loss in EUR.
        bankroll_after: Running bankroll after this bet.
    """

    recommendation: BetRecommendation
    actual_score: str
    actual_result: str
    hit: bool
    closing_odds: float | None
    clv: float | None
    pnl: float
    bankroll_after: float


class ResultsTracker:
    """Track bet results across days.

    Loads predictions JSON, matches with actual results, computes P&L and CLV.

    Args:
        predictions_dir: Directory with prediction JSON files.
        results_dir: Directory with manual results JSON files and processed outputs.
        initial_bankroll: Starting bankroll for running totals.
    """

    def __init__(
        self,
        predictions_dir: Path = Path("predictions"),
        results_dir: Path = Path("results"),
        initial_bankroll: float = 5000.0,
    ) -> None:
        self._predictions_dir = predictions_dir
        self._results_dir = results_dir
        self._initial_bankroll = initial_bankroll

    def process_day(self, day: dt.date) -> list[BetResult]:
        """Process results for a given day.

        Args:
            day: Date to process.

        Returns:
            Processed bet results. Returns an empty list when predictions or
            manual results are unavailable.
        """
        predictions = self._load_predictions(day)
        if not predictions:
            logger.warning("results_tracker_no_predictions", day=day.isoformat())
            return []

        actual_results = self._load_actual_results(day)
        if not actual_results:
            logger.warning("results_tracker_no_actual_results", day=day.isoformat())
            return []

        bankroll = self._bankroll_before(day)
        processed: list[BetResult] = []
        for recommendation in predictions:
            actual = actual_results.get(recommendation.match_id)
            if actual is None:
                logger.warning(
                    "results_tracker_prediction_unmatched",
                    match_id=recommendation.match_id,
                    day=day.isoformat(),
                )
                continue

            actual_result = str(actual["result"])
            hit = _market_result(recommendation.market) == actual_result
            pnl = _compute_pnl(recommendation, hit)
            bankroll += pnl
            closing_odds = _optional_float(actual.get("closing_odds"))
            clv = (
                recommendation.model_prob - 1.0 / closing_odds
                if closing_odds is not None and closing_odds > 1.0
                else None
            )
            processed.append(
                BetResult(
                    recommendation=recommendation,
                    actual_score=str(actual["score"]),
                    actual_result=actual_result,
                    hit=hit,
                    closing_odds=closing_odds,
                    clv=round(clv, 6) if clv is not None else None,
                    pnl=round(pnl, 2),
                    bankroll_after=round(bankroll, 2),
                )
            )

        self._save_processed_results(day, processed)
        logger.info("results_tracker_day_processed", day=day.isoformat(), bets=len(processed))
        return processed

    def running_totals(self) -> dict[str, float]:
        """Compute cumulative stats across all tracked days.

        Returns:
            Dictionary with total bets, wins, losses, hit rate, P&L, ROI,
            mean CLV, current bankroll, max drawdown, and current streak.
        """
        results = self._load_all_processed_results()
        total_bets = len(results)
        wins = sum(1 for result in results if result.hit)
        losses = total_bets - wins
        total_pnl = sum(result.pnl for result in results)
        total_staked = sum(result.recommendation.stake_eur for result in results)
        clv_values = [result.clv for result in results if result.clv is not None]

        bankroll = self._initial_bankroll
        peak = bankroll
        max_drawdown = 0.0
        for result in results:
            bankroll += result.pnl
            peak = max(peak, bankroll)
            if peak > 0.0:
                max_drawdown = max(max_drawdown, (peak - bankroll) / peak)

        return {
            "total_bets": float(total_bets),
            "wins": float(wins),
            "losses": float(losses),
            "hit_rate": wins / total_bets if total_bets else 0.0,
            "total_pnl": round(total_pnl, 2),
            "roi": total_pnl / total_staked if total_staked else 0.0,
            "mean_clv": sum(clv_values) / len(clv_values) if clv_values else 0.0,
            "current_bankroll": round(self._initial_bankroll + total_pnl, 2),
            "max_drawdown": max_drawdown,
            "current_streak": float(_current_streak(results)),
        }

    @property
    def initial_bankroll(self) -> float:
        """Starting bankroll used by this tracker."""
        return self._initial_bankroll

    def load_processed_results(
        self,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
    ) -> list[BetResult]:
        """Load processed bet results, optionally filtered by kickoff date.

        Args:
            start_date: Inclusive start date.
            end_date: Inclusive end date.

        Returns:
            Processed results sorted by kickoff datetime.
        """
        results = self._load_all_processed_results()
        if start_date is not None:
            results = [
                result
                for result in results
                if result.recommendation.kickoff_dt.date() >= start_date
            ]
        if end_date is not None:
            results = [
                result
                for result in results
                if result.recommendation.kickoff_dt.date() <= end_date
            ]
        return sorted(results, key=lambda result: result.recommendation.kickoff_dt)

    def _load_predictions(self, day: dt.date) -> list[BetRecommendation]:
        candidates = [
            self._predictions_dir / f"predictions_{day.isoformat()}.json",
            self._predictions_dir / f"bet_recommendations_{day.isoformat()}.json",
        ]
        for path in candidates:
            if path.exists():
                return DailyPredictor.load_predictions(path)
        return []

    def _load_actual_results(self, day: dt.date) -> dict[str, dict[str, object]]:
        path = self._results_dir / f"results_{day.isoformat()}.json"
        if not path.exists():
            return {}

        raw = json.loads(path.read_text(encoding="utf-8"))
        data = raw["results"] if isinstance(raw, dict) and "results" in raw else raw
        if not isinstance(data, list):
            raise ValueError(f"Unexpected results JSON structure in {path}")

        actuals: dict[str, dict[str, object]] = {}
        for item in data:
            if isinstance(item, dict) and "match_id" in item:
                actuals[str(item["match_id"])] = item
        return actuals

    def _save_processed_results(self, day: dt.date, results: list[BetResult]) -> Path:
        self._results_dir.mkdir(parents=True, exist_ok=True)
        path = self._processed_results_path(day)
        payload = [_result_to_json(result) for result in results]
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def _bankroll_before(self, day: dt.date) -> float:
        pnl_before = 0.0
        for path in sorted(self._results_dir.glob("processed_results_*.json")):
            result_day = _date_from_processed_path(path)
            if result_day is not None and result_day < day:
                pnl_before += sum(result.pnl for result in _load_processed_results(path))
        return self._initial_bankroll + pnl_before

    def _load_all_processed_results(self) -> list[BetResult]:
        results: list[BetResult] = []
        for path in sorted(self._results_dir.glob("processed_results_*.json")):
            results.extend(_load_processed_results(path))
        return results

    def _processed_results_path(self, day: dt.date) -> Path:
        return self._results_dir / f"processed_results_{day.isoformat()}.json"


def _compute_pnl(recommendation: BetRecommendation, hit: bool) -> float:
    if hit:
        return recommendation.stake_eur * (recommendation.best_odds - 1.0)
    return -recommendation.stake_eur


def _market_result(market: str) -> str:
    return _RESULT_BY_MARKET.get(market, "")


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float | str):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _result_to_json(result: BetResult) -> dict[str, object]:
    item = asdict(result)
    item["recommendation"]["kickoff"] = result.recommendation.kickoff_dt.isoformat()
    return item


def _load_processed_results(path: Path) -> list[BetResult]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []

    results: list[BetResult] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        recommendation_raw = item.get("recommendation")
        if not isinstance(recommendation_raw, dict):
            continue
        recommendation = BetRecommendation(**recommendation_raw)
        results.append(
            BetResult(
                recommendation=recommendation,
                actual_score=str(item.get("actual_score", "")),
                actual_result=str(item.get("actual_result", "")),
                hit=bool(item.get("hit", False)),
                closing_odds=_optional_float(item.get("closing_odds")),
                clv=_optional_float(item.get("clv")),
                pnl=float(item.get("pnl", 0.0)),
                bankroll_after=float(item.get("bankroll_after", 0.0)),
            )
        )
    return results


def _date_from_processed_path(path: Path) -> dt.date | None:
    stem = path.stem.replace("processed_results_", "")
    try:
        return dt.date.fromisoformat(stem)
    except ValueError:
        return None


def _current_streak(results: list[BetResult]) -> int:
    streak = 0
    for result in reversed(results):
        if result.hit:
            if streak < 0:
                break
            streak += 1
        else:
            if streak > 0:
                break
            streak -= 1
    return streak

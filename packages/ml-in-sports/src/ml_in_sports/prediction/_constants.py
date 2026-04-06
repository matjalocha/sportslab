"""Shared constants for the daily prediction pipeline."""

TARGET_COL = "result_1x2"
TARGET_ENCODING: dict[str, int] = {"H": 0, "D": 1, "A": 2}
MAX_NAN_FRACTION = 0.50

EXCLUDED_COLS: frozenset[str] = frozenset({
    "id",
    "match_id",
    "league",
    "season",
    "game",
    "date",
    "kickoff",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    TARGET_COL,
    "target",
    "source_updated_at",
    "b365_home",
    "b365_draw",
    "b365_away",
    "avg_home",
    "avg_draw",
    "avg_away",
    "pinnacle_home",
    "pinnacle_draw",
    "pinnacle_away",
    "implied_prob_home",
    "implied_prob_draw",
    "implied_prob_away",
    "fair_prob_home",
    "fair_prob_draw",
    "fair_prob_away",
    "overround_1x2",
})

MARKET_SPECS: tuple[tuple[str, int, tuple[tuple[str, str], ...]], ...] = (
    (
        "1x2_home",
        0,
        (("Pinnacle", "pinnacle_home"), ("Market Avg", "avg_home"), ("Bet365", "b365_home")),
    ),
    (
        "1x2_draw",
        1,
        (("Pinnacle", "pinnacle_draw"), ("Market Avg", "avg_draw"), ("Bet365", "b365_draw")),
    ),
    (
        "1x2_away",
        2,
        (("Pinnacle", "pinnacle_away"), ("Market Avg", "avg_away"), ("Bet365", "b365_away")),
    ),
)

"""Basic feature pipeline for leagues without xG data.

Uses only stats available from football-data.co.uk: goals, shots, corners,
fouls, cards, and odds. Every team rolling feature is shifted by one match to
avoid looking at the current result while creating pre-match features.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

_DEFAULT_WINDOWS: tuple[int, ...] = (3, 5, 10)


def build_basic_features(
    df: pd.DataFrame,
    windows: Sequence[int] | None = None,
) -> pd.DataFrame:
    """Build rolling features from basic match stats with no xG dependency.

    Args:
        df: Match-level DataFrame. Expected columns include ``date``,
            ``home_team``, ``away_team``, ``home_goals`` and ``away_goals``.
            Optional stats such as shots on target, corners, fouls and cards
            are used when present.
        windows: Rolling window sizes. Defaults to 3, 5 and 10 matches.

    Returns:
        Copy of ``df`` with shifted rolling team features and odds-implied
        features added.
    """
    target_windows = tuple(windows or _DEFAULT_WINDOWS)
    if not target_windows:
        return df.copy()

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["__row_id"] = np.arange(len(out))

    home_rows = _build_team_rows(out, side="home")
    away_rows = _build_team_rows(out, side="away")
    team_rows = pd.concat([home_rows, away_rows], ignore_index=True)
    team_rows = team_rows.sort_values(["league", "team", "date", "__row_id"])

    rolling_cols = [
        "goals_for",
        "goals_against",
        "goal_diff",
        "shots_on_target_for",
        "shots_on_target_against",
        "corners_for",
        "corners_against",
        "fouls_for",
        "fouls_against",
        "yellow_cards_for",
        "yellow_cards_against",
        "points",
        "win",
        "draw",
        "loss",
        "home_win",
    ]
    group = team_rows.groupby(["league", "team"], sort=False)
    for window in target_windows:
        for col in rolling_cols:
            feature_name = f"{col}_roll_{window}"
            team_rows[feature_name] = group[col].transform(
                lambda values, window=window: values.shift(1)
                .rolling(window=window, min_periods=1)
                .mean()
            )
            team_rows[feature_name] = team_rows[feature_name].fillna(0.0)

    feature_cols = [
        col
        for col in team_rows.columns
        if any(col.endswith(f"_roll_{window}") for window in target_windows)
    ]
    home_features = _prefix_team_features(team_rows, "home", feature_cols)
    away_features = _prefix_team_features(team_rows, "away", feature_cols)

    out = out.merge(home_features, on="__row_id", how="left")
    out = out.merge(away_features, on="__row_id", how="left")
    out = _add_odds_features(out)
    out = _add_table_features(out)
    return out.sort_values("__row_id").drop(columns=["__row_id"]).reset_index(drop=True)


def _build_team_rows(df: pd.DataFrame, side: str) -> pd.DataFrame:
    """Build one team-centric row per match side."""
    opponent_side = "away" if side == "home" else "home"
    goals_for = _numeric_required_col(df, f"{side}_goals")
    goals_against = _numeric_required_col(df, f"{opponent_side}_goals")

    rows = pd.DataFrame(
        {
            "__row_id": df["__row_id"],
            "league": df.get("league", "unknown"),
            "date": df["date"],
            "team": df[f"{side}_team"],
            "side": side,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "shots_on_target_for": _numeric_col(df, side, "shots_on_target"),
            "shots_on_target_against": _numeric_col(
                df, opponent_side, "shots_on_target"
            ),
            "corners_for": _numeric_col(df, side, "corners"),
            "corners_against": _numeric_col(df, opponent_side, "corners"),
            "fouls_for": _numeric_col(df, side, "fouls"),
            "fouls_against": _numeric_col(df, opponent_side, "fouls"),
            "yellow_cards_for": _numeric_col(df, side, "yellow_cards"),
            "yellow_cards_against": _numeric_col(df, opponent_side, "yellow_cards"),
        }
    )
    rows["goal_diff"] = rows["goals_for"] - rows["goals_against"]
    rows["win"] = (rows["goals_for"] > rows["goals_against"]).astype(float)
    rows["draw"] = (rows["goals_for"] == rows["goals_against"]).astype(float)
    rows["loss"] = (rows["goals_for"] < rows["goals_against"]).astype(float)
    rows["points"] = rows["win"] * 3.0 + rows["draw"]
    rows["home_win"] = np.where(side == "home", rows["win"], np.nan)
    return rows


def _numeric_col(df: pd.DataFrame, side: str, stat: str) -> pd.Series:
    """Return a numeric stat column or all-NaN fallback."""
    candidates = [
        f"{side}_{stat}",
        f"{side}_{stat.replace('_', '')}",
    ]
    if stat == "shots_on_target":
        candidates.extend([f"{side}_shots_on_goal", f"{side}_sot"])
    if stat == "corners":
        candidates.append(f"{side}_won_corners")

    for candidate in candidates:
        if candidate in df.columns:
            return pd.to_numeric(df[candidate], errors="coerce")
    return pd.Series(np.nan, index=df.index, dtype=float)


def _numeric_required_col(df: pd.DataFrame, col: str) -> pd.Series:
    """Return a required match stat as numeric with an all-NaN fallback."""
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index, dtype=float)


def _prefix_team_features(
    team_rows: pd.DataFrame,
    side: str,
    feature_cols: list[str],
) -> pd.DataFrame:
    """Return side-prefixed team rolling features keyed by row id."""
    features = team_rows.loc[team_rows["side"] == side, ["__row_id", *feature_cols]].copy()
    return features.rename(columns={col: f"{side}_{col}" for col in feature_cols})


def _add_odds_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add 1X2 odds-implied features when odds columns are available."""
    home_odds = _first_available_numeric(df, ["avg_home", "max_home", "b365_home"])
    draw_odds = _first_available_numeric(df, ["avg_draw", "max_draw", "b365_draw"])
    away_odds = _first_available_numeric(df, ["avg_away", "max_away", "b365_away"])

    if home_odds is None or draw_odds is None or away_odds is None:
        return df

    df["implied_prob_home"] = 1.0 / home_odds
    df["implied_prob_draw"] = 1.0 / draw_odds
    df["implied_prob_away"] = 1.0 / away_odds
    df["overround_1x2"] = (
        df["implied_prob_home"] + df["implied_prob_draw"] + df["implied_prob_away"]
    )
    df["fair_prob_home"] = df["implied_prob_home"] / df["overround_1x2"]
    df["fair_prob_draw"] = df["implied_prob_draw"] / df["overround_1x2"]
    df["fair_prob_away"] = df["implied_prob_away"] / df["overround_1x2"]
    return df


def _first_available_numeric(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.Series | None:
    """Return first present odds column as numeric values."""
    for col in columns:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce")
            return values.replace(0.0, np.nan)
    return None


def _add_table_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add table-position deltas if standings columns are present."""
    if {"home_table_position", "away_table_position"}.issubset(df.columns):
        home_pos = pd.to_numeric(df["home_table_position"], errors="coerce")
        away_pos = pd.to_numeric(df["away_table_position"], errors="coerce")
        df["table_position_diff"] = away_pos - home_pos
    return df

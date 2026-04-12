"""Integrate ClubElo ratings into features parquet.

ClubElo provides ELO ratings for 630+ teams across Europe.
For expansion leagues where soccerdata's ClubElo adapter only maps
Top-5 league names, we match by country code + normalized team name.

Rate limit: 1 request per 2 seconds (free service).
All ELO lookups use the most recent snapshot BEFORE the match date
to prevent lookahead bias.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.processing.extractors import ClubEloExtractor
from ml_in_sports.utils.team_names import normalize_team_name

logger = structlog.get_logger(__name__)

# Maps our league identifiers to ClubElo country codes.
# ClubElo only fills the `league` column for Top-5; for the rest
# we rely on `country` + `level` to identify the correct teams.
LEAGUE_TO_COUNTRY: dict[str, str] = {
    "ENG-Premier League": "ENG",
    "ENG-Championship": "ENG",
    "ESP-La Liga": "ESP",
    "ESP-Segunda": "ESP",
    "GER-Bundesliga": "GER",
    "GER-Bundesliga 2": "GER",
    "ITA-Serie A": "ITA",
    "ITA-Serie B": "ITA",
    "FRA-Ligue 1": "FRA",
    "FRA-Ligue 2": "FRA",
    "NED-Eredivisie": "NED",
    "POR-Primeira Liga": "POR",
    "BEL-Jupiler Pro League": "BEL",
    "TUR-Süper Lig": "TUR",
    "GRE-Super League": "GRE",
    "SCO-Premiership": "SCO",
}

# Maps our league identifiers to ClubElo tier level (1=top, 2=second).
# Used to disambiguate teams that appear in both tiers for the same
# country (e.g. ENG teams in Championship vs Premier League).
LEAGUE_TO_LEVEL: dict[str, int] = {
    "ENG-Premier League": 1,
    "ENG-Championship": 2,
    "ESP-La Liga": 1,
    "ESP-Segunda": 2,
    "GER-Bundesliga": 1,
    "GER-Bundesliga 2": 2,
    "ITA-Serie A": 1,
    "ITA-Serie B": 2,
    "FRA-Ligue 1": 1,
    "FRA-Ligue 2": 2,
    "NED-Eredivisie": 1,
    "POR-Primeira Liga": 1,
    "BEL-Jupiler Pro League": 1,
    "TUR-Süper Lig": 1,
    "GRE-Super League": 1,
    "SCO-Premiership": 1,
}

_REQUEST_INTERVAL_SECONDS = 2.0
_DEFAULT_CACHE_DIR = Path("data/elo")


def fetch_elo_for_date_range(
    start_date: str,
    end_date: str,
    step_days: int = 7,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Fetch ELO ratings for a date range, one snapshot per step_days.

    Caches each snapshot as a CSV in cache_dir to avoid redundant
    network requests on re-runs.  Respects ClubElo rate limits with
    a 2-second sleep between requests.

    Args:
        start_date: First date to fetch (YYYY-MM-DD).
        end_date: Last date to fetch (YYYY-MM-DD), inclusive.
        step_days: Days between successive snapshots.
        cache_dir: Directory for cached CSV files.

    Returns:
        DataFrame with columns: team, date, elo, country, level.
        One row per team per snapshot date.
    """
    if cache_dir is None:
        cache_dir = _DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    dates = pd.date_range(start=start_date, end=end_date, freq=f"{step_days}D")
    extractor = ClubEloExtractor()

    frames: list[pd.DataFrame] = []
    fetched_count = 0

    for snapshot_date in dates:
        date_str = snapshot_date.strftime("%Y-%m-%d")
        csv_path = cache_dir / f"elo_{date_str}.csv"

        if csv_path.exists():
            cached = pd.read_csv(csv_path)
            frames.append(cached)
            continue

        logger.info("fetching_elo_snapshot", date=date_str)

        if fetched_count > 0:
            time.sleep(_REQUEST_INTERVAL_SECONDS)

        raw = extractor.extract_ratings(date_str)
        if raw is None or raw.empty:
            logger.warning("elo_snapshot_empty", date=date_str)
            fetched_count += 1
            continue

        snapshot = _normalize_elo_snapshot(raw, date_str)
        snapshot.to_csv(csv_path, index=False)
        frames.append(snapshot)
        fetched_count += 1

        logger.info(
            "elo_snapshot_saved",
            date=date_str,
            teams=len(snapshot),
            path=str(csv_path),
        )

    if not frames:
        logger.warning("no_elo_data_fetched")
        return pd.DataFrame(columns=["team", "date", "elo", "country", "level"])

    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    logger.info(
        "elo_fetch_complete",
        snapshots=len(frames),
        total_rows=len(combined),
        dates_fetched=fetched_count,
    )
    return combined


def _normalize_elo_snapshot(
    raw: pd.DataFrame,
    date_str: str,
) -> pd.DataFrame:
    """Convert a raw ClubElo snapshot to our standard schema.

    Applies normalize_team_name to the index (team name) and
    keeps only the columns we need.

    Args:
        raw: DataFrame from ClubEloExtractor (indexed by team name).
        date_str: The snapshot date as YYYY-MM-DD.

    Returns:
        DataFrame with columns: team, date, elo, country, level.
    """
    result = pd.DataFrame({
        "team": raw.index.map(normalize_team_name),
        "date": date_str,
        "elo": raw["elo"].values,
        "country": raw["country"].values,
        "level": raw["level"].values,
    })
    return result


def match_elo_to_features(
    features_df: pd.DataFrame,
    elo_df: pd.DataFrame,
) -> pd.DataFrame:
    """Join ELO ratings to features parquet by team name + nearest date.

    For each match in features_df:
    1. Find the ELO snapshot closest BEFORE the match date (no lookahead).
    2. Match by normalized team name + country code from the league.
    3. Add columns: home_elo, away_elo.

    When a team has ELO entries at multiple levels (e.g. a promoted team
    appearing as both level-1 and level-2), we prefer the level matching
    the league tier. If no tier match exists, we fall back to any level.

    Args:
        features_df: The features parquet DataFrame.
        elo_df: Combined ELO snapshots from fetch_elo_for_date_range.

    Returns:
        features_df with home_elo and away_elo columns populated.
    """
    result = features_df.copy()
    elo = elo_df.copy()
    elo["date"] = pd.to_datetime(elo["date"])

    # Pre-sort ELO by date for efficient merge_asof
    elo = elo.sort_values("date").reset_index(drop=True)

    # Build home_elo
    home_elo = _lookup_elo_for_side(
        result, elo, team_col="home_team", side="home",
    )
    result["home_elo"] = home_elo

    # Build away_elo
    away_elo = _lookup_elo_for_side(
        result, elo, team_col="away_team", side="away",
    )
    result["away_elo"] = away_elo

    matched_home = result["home_elo"].notna().sum()
    matched_away = result["away_elo"].notna().sum()
    total = len(result)
    logger.info(
        "elo_match_complete",
        total_matches=total,
        home_elo_filled=matched_home,
        away_elo_filled=matched_away,
        home_fill_pct=round(matched_home / total * 100, 1) if total > 0 else 0.0,
        away_fill_pct=round(matched_away / total * 100, 1) if total > 0 else 0.0,
    )
    return result


def _lookup_elo_for_side(
    features: pd.DataFrame,
    elo: pd.DataFrame,
    team_col: str,
    side: str,
) -> pd.Series:
    """Look up ELO for one side (home or away) using merge_asof.

    For each match row, finds the most recent ELO snapshot strictly
    before the match date for the given team, filtered by country
    and preferred level.

    Args:
        features: Features DataFrame with date, league, and team columns.
        elo: Sorted ELO DataFrame with team, date, elo, country, level.
        team_col: Column name for the team (home_team or away_team).
        side: "home" or "away" (used for logging only).

    Returns:
        Series of ELO values aligned to features index.
    """
    # Prepare the match side: team name + date + country + preferred level
    match_side = features[["date", "league", team_col]].copy()
    match_side = match_side.rename(columns={team_col: "team"})
    # Normalize team names so parquet names align with ELO names
    match_side["team"] = match_side["team"].map(normalize_team_name)
    match_side["country"] = match_side["league"].map(LEAGUE_TO_COUNTRY)
    match_side["preferred_level"] = match_side["league"].map(LEAGUE_TO_LEVEL)
    match_side["date"] = pd.to_datetime(match_side["date"])
    match_side["_orig_idx"] = features.index

    # For each (team, country) combination, do a merge_asof
    # to find the most recent ELO before the match date.
    # Group approach: merge_asof requires sorted keys.

    match_side = match_side.sort_values("date").reset_index(drop=True)

    elo_values = pd.Series(np.nan, index=match_side.index, dtype=float)

    # Group by (team, country) for efficient batch lookup
    for (team, country), group in match_side.groupby(
        ["team", "country"], sort=False,
    ):
        if pd.isna(country):
            continue

        # Filter ELO to matching team + country
        elo_mask = (elo["team"] == team) & (elo["country"] == country)
        team_elo = elo[elo_mask].copy()

        if team_elo.empty:
            continue

        # Prefer the level matching the league tier
        preferred_levels = group["preferred_level"].dropna().unique()
        if len(preferred_levels) > 0:
            preferred = preferred_levels[0]
            level_filtered = team_elo[team_elo["level"] == preferred]
            if not level_filtered.empty:
                team_elo = level_filtered

        # merge_asof: find most recent ELO strictly before match date
        team_elo_sorted = team_elo[["date", "elo"]].sort_values("date")
        group_sorted = group[["date"]].copy()
        group_sorted["_group_idx"] = group.index

        merged = pd.merge_asof(
            group_sorted.sort_values("date"),
            team_elo_sorted,
            on="date",
            direction="backward",
            allow_exact_matches=False,
        )

        for row_idx, elo_val in zip(
            merged["_group_idx"], merged["elo"], strict=True,
        ):
            if pd.notna(elo_val):
                elo_values.iloc[row_idx] = elo_val

    # Re-align to original index
    result = pd.Series(np.nan, index=features.index, dtype=float)
    idx_map = match_side["_orig_idx"].values
    for i, orig_idx in enumerate(idx_map):
        if pd.notna(elo_values.iloc[i]):
            result.loc[orig_idx] = elo_values.iloc[i]

    return result


def compute_elo_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived ELO features from home_elo and away_elo.

    Features produced:
    - diff_elo: home_elo - away_elo
    - home_elo_form_3/5/10: rolling ELO change over last N home matches
    - away_elo_form_3/5/10: rolling ELO change over last N away matches
    - diff_elo_form_3/5/10: difference of home and away ELO form
    - elo_x_form_home/away: elo * form interaction terms

    All rolling features use shift(1) to prevent lookahead.

    Args:
        df: DataFrame with home_elo, away_elo, home_team, away_team,
            date columns.

    Returns:
        DataFrame with derived ELO feature columns added.
    """
    result = df.copy()
    result["date"] = pd.to_datetime(result["date"])
    result = result.sort_values("date").reset_index(drop=True)

    # Basic differential
    result["diff_elo"] = result["home_elo"] - result["away_elo"]

    # Rolling ELO form: how much has a team's ELO changed recently?
    # This captures momentum -- a team whose ELO is rising is in form.
    for window in (3, 5, 10):
        result = _add_elo_form(result, "home", window)
        result = _add_elo_form(result, "away", window)

        result[f"diff_elo_form_{window}"] = (
            result[f"home_elo_form_{window}"]
            - result[f"away_elo_form_{window}"]
        )

    # Interaction: ELO * form (captures "strong team in good form")
    if "home_form_points_5" in result.columns:
        result["elo_x_form_home"] = (
            result["home_elo"] * result["home_form_points_5"]
        )
        result["elo_x_form_away"] = (
            result["away_elo"] * result["away_form_points_5"]
        )
    elif "home_elo_form_5" in result.columns:
        # Fallback: use ELO form as the form signal
        result["elo_x_form_home"] = (
            result["home_elo"] * result["home_elo_form_5"].fillna(0)
        )
        result["elo_x_form_away"] = (
            result["away_elo"] * result["away_elo_form_5"].fillna(0)
        )

    # Cross features with xG if available
    if "home_xg" in result.columns:
        result["elo_x_xg_home"] = result["home_elo"] * result["home_xg"]
        result["elo_x_xg_away"] = result["away_elo"] * result["away_xg"]
        result["diff_elo_x_form"] = (
            result["diff_elo"]
            * result.get("home_form_points_5", pd.Series(0, index=result.index))
        )

    return result


def _add_elo_form(
    df: pd.DataFrame,
    side: str,
    window: int,
) -> pd.DataFrame:
    """Add rolling ELO change (form) for one side.

    Computes the difference between the current ELO and the ELO
    from N matches ago for the same team, using shift to prevent
    lookahead.

    Args:
        df: DataFrame sorted by date.
        side: "home" or "away".
        window: Number of past matches to look back.

    Returns:
        DataFrame with {side}_elo_form_{window} column added.
    """
    elo_col = f"{side}_elo"
    team_col = f"{side}_team"
    form_col = f"{side}_elo_form_{window}"

    if elo_col not in df.columns:
        df[form_col] = np.nan
        return df

    shifted_current = df.groupby(team_col)[elo_col].shift(1)
    shifted_past = df.groupby(team_col)[elo_col].shift(window)
    df[form_col] = shifted_current - shifted_past

    return df

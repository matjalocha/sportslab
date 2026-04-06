"""Player features from FIFA/FC ratings CSVs.

Reads FIFA 15-26 CSV files in various formats, normalizes them to a
common schema, then aggregates per-team per-season features (avg overall,
squad depth, positional breakdowns, etc.) for joining to match data.
"""

from pathlib import Path

import pandas as pd
import structlog

from ml_in_sports.utils.team_names import normalize_team_name

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Position group constants
# ---------------------------------------------------------------------------

POSITION_GROUP_GK: frozenset[str] = frozenset({"GK"})

POSITION_GROUP_DEF: frozenset[str] = frozenset({
    "CB", "LB", "RB", "LWB", "RWB",
})

POSITION_GROUP_MID: frozenset[str] = frozenset({
    "CM", "CDM", "CAM", "LM", "RM",
})

POSITION_GROUP_FWD: frozenset[str] = frozenset({
    "ST", "CF", "LW", "RW", "LF", "RF",
})

_SQUAD_DEPTH_THRESHOLD = 75

# ---------------------------------------------------------------------------
# Standard column definitions
# ---------------------------------------------------------------------------

_CORE_COLUMNS = [
    "club_name", "overall", "potential", "age",
    "player_positions", "season",
]

_MAIN_ATTRIBUTE_COLUMNS = [
    "pace", "shooting", "passing", "dribbling", "defending", "physic",
]

_ATTACKING_COLUMNS = [
    "attacking_crossing", "attacking_finishing",
    "attacking_heading_accuracy", "attacking_short_passing",
    "attacking_volleys",
]

_SKILL_COLUMNS = [
    "skill_dribbling", "skill_curve", "skill_fk_accuracy",
    "skill_long_passing", "skill_ball_control",
]

_MOVEMENT_COLUMNS = [
    "movement_acceleration", "movement_sprint_speed",
    "movement_agility", "movement_reactions", "movement_balance",
]

_POWER_COLUMNS = [
    "power_shot_power", "power_jumping", "power_stamina",
    "power_strength", "power_long_shots",
]

_MENTALITY_COLUMNS = [
    "mentality_aggression", "mentality_interceptions",
    "mentality_positioning", "mentality_vision",
    "mentality_penalties", "mentality_composure",
]

_DEFENDING_COLUMNS = [
    "defending_marking_awareness", "defending_standing_tackle",
    "defending_sliding_tackle",
]

_GOALKEEPING_COLUMNS = [
    "goalkeeping_diving", "goalkeeping_handling",
    "goalkeeping_kicking", "goalkeeping_positioning",
    "goalkeeping_reflexes",
]

_PLAYER_META_COLUMNS = [
    "value_eur", "wage_eur", "international_reputation",
    "skill_moves", "weak_foot", "work_rate",
    "height_cm", "weight_kg", "preferred_foot",
]

_EXTENDED_ATTRIBUTE_COLUMNS = (
    _MAIN_ATTRIBUTE_COLUMNS
    + _ATTACKING_COLUMNS
    + _SKILL_COLUMNS
    + _MOVEMENT_COLUMNS
    + _POWER_COLUMNS
    + _MENTALITY_COLUMNS
    + _DEFENDING_COLUMNS
    + _GOALKEEPING_COLUMNS
    + _PLAYER_META_COLUMNS
)

_STANDARD_COLUMNS = _CORE_COLUMNS + _EXTENDED_ATTRIBUTE_COLUMNS

# ---------------------------------------------------------------------------
# FC24 column name mapping (FC24 short names -> standard names)
# ---------------------------------------------------------------------------

_FC24_COLUMN_MAP: dict[str, str] = {
    "Club": "club_name",
    "Overall": "overall",
    "Age": "age",
    "Position": "player_positions",
    "Pace": "pace",
    "Shooting": "shooting",
    "Passing": "passing",
    "Dribbling": "dribbling",
    "Defending": "defending",
    "Physicality": "physic",
    "Crossing": "attacking_crossing",
    "Finishing": "attacking_finishing",
    "Heading": "attacking_heading_accuracy",
    "Volleys": "attacking_volleys",
    "Curve": "skill_curve",
    "Free": "skill_fk_accuracy",
    "Ball": "skill_ball_control",
    "Acceleration": "movement_acceleration",
    "Sprint": "movement_sprint_speed",
    "Agility": "movement_agility",
    "Reactions": "movement_reactions",
    "Balance": "movement_balance",
    "Shot": "power_shot_power",
    "Jumping": "power_jumping",
    "Stamina": "power_stamina",
    "Strength": "power_strength",
    "Long": "power_long_shots",
    "Aggression": "mentality_aggression",
    "Interceptions": "mentality_interceptions",
    "Positioning": "mentality_positioning",
    "Vision": "mentality_vision",
    "Penalties": "mentality_penalties",
    "Composure": "mentality_composure",
    "Def": "defending_marking_awareness",
    "Standing": "defending_standing_tackle",
    "Sliding": "defending_sliding_tackle",
    "Weak foot": "weak_foot",
    "Skill moves": "skill_moves",
    "Preferred foot": "preferred_foot",
}

# ---------------------------------------------------------------------------
# FC25 column name mapping (FC25 names -> standard names)
# ---------------------------------------------------------------------------

_FC25_COLUMN_MAP: dict[str, str] = {
    "Team": "club_name",
    "OVR": "overall",
    "Age": "age",
    "Position": "player_positions",
    "PAC": "pace",
    "SHO": "shooting",
    "PAS": "passing",
    "DRI": "dribbling",
    "DEF": "defending",
    "PHY": "physic",
    "Crossing": "attacking_crossing",
    "Finishing": "attacking_finishing",
    "Heading Accuracy": "attacking_heading_accuracy",
    "Short Passing": "attacking_short_passing",
    "Volleys": "attacking_volleys",
    "Long Passing": "skill_long_passing",
    "Curve": "skill_curve",
    "Free Kick Accuracy": "skill_fk_accuracy",
    "Ball Control": "skill_ball_control",
    "Acceleration": "movement_acceleration",
    "Sprint Speed": "movement_sprint_speed",
    "Agility": "movement_agility",
    "Reactions": "movement_reactions",
    "Balance": "movement_balance",
    "Shot Power": "power_shot_power",
    "Jumping": "power_jumping",
    "Stamina": "power_stamina",
    "Strength": "power_strength",
    "Long Shots": "power_long_shots",
    "Aggression": "mentality_aggression",
    "Interceptions": "mentality_interceptions",
    "Positioning": "mentality_positioning",
    "Vision": "mentality_vision",
    "Penalties": "mentality_penalties",
    "Composure": "mentality_composure",
    "Def Awareness": "defending_marking_awareness",
    "Standing Tackle": "defending_standing_tackle",
    "Sliding Tackle": "defending_sliding_tackle",
    "GK Diving": "goalkeeping_diving",
    "GK Handling": "goalkeeping_handling",
    "GK Kicking": "goalkeeping_kicking",
    "GK Positioning": "goalkeeping_positioning",
    "GK Reflexes": "goalkeeping_reflexes",
    "Weak foot": "weak_foot",
    "Skill moves": "skill_moves",
    "Preferred foot": "preferred_foot",
    "Height": "height_cm",
    "Weight": "weight_kg",
}


# ---------------------------------------------------------------------------
# FIFA version to season mapping
# ---------------------------------------------------------------------------

def fifa_version_to_season(version: int) -> str:
    """Convert FIFA/FC version number to season code.

    Args:
        version: FIFA version (15-26).

    Returns:
        Season code like "1415", "2223", etc.
    """
    start_year = version - 1 + 2000
    end_year = version + 2000
    return f"{start_year % 100:02d}{end_year % 100:02d}"


# ---------------------------------------------------------------------------
# Position classification
# ---------------------------------------------------------------------------

def classify_position_group(positions: str | None) -> str | None:
    """Classify a player into a position group from their positions string.

    Uses the first listed position for classification.

    Args:
        positions: Comma-separated positions (e.g. "CB, LB") or None.

    Returns:
        One of "GK", "DEF", "MID", "FWD", or None if unrecognized.
    """
    if not positions or not isinstance(positions, str):
        return None

    primary = positions.split(",")[0].strip()

    if primary in POSITION_GROUP_GK:
        return "GK"
    if primary in POSITION_GROUP_DEF:
        return "DEF"
    if primary in POSITION_GROUP_MID:
        return "MID"
    if primary in POSITION_GROUP_FWD:
        return "FWD"

    return None


# ---------------------------------------------------------------------------
# Column extraction helpers
# ---------------------------------------------------------------------------

def _safe_extract_columns(
    raw: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Extract columns from a DataFrame, filling missing ones with NaN.

    Args:
        raw: Source DataFrame.
        columns: List of column names to extract.

    Returns:
        DataFrame with requested columns (missing ones filled with NaN).
    """
    present = [col for col in columns if col in raw.columns]
    missing = [col for col in columns if col not in raw.columns]

    result = raw[present].copy()
    for col in missing:
        result[col] = pd.NA

    if missing:
        logger.debug(f"Missing columns filled with NaN: {missing}")

    return result


def _remap_columns(
    raw: pd.DataFrame,
    column_map: dict[str, str],
) -> pd.DataFrame:
    """Remap columns from source names to standard names.

    Args:
        raw: Source DataFrame with original column names.
        column_map: Mapping from source column name to standard name.

    Returns:
        DataFrame with standard column names.
    """
    result = pd.DataFrame()
    for source_name, standard_name in column_map.items():
        if source_name in raw.columns:
            result[standard_name] = raw[source_name]
    return result


# ---------------------------------------------------------------------------
# CSV loaders (one per format)
# ---------------------------------------------------------------------------

def load_sofifa_csv(csv_path: Path, fifa_version: int) -> pd.DataFrame:
    """Load a sofifa-format CSV and standardize columns.

    Works for players_15-22.csv, male_players_23.csv, and FC26.

    Args:
        csv_path: Path to the CSV file.
        fifa_version: FIFA version number (15-26).

    Returns:
        DataFrame with standardized columns.
    """
    try:
        raw = pd.read_csv(csv_path, low_memory=False)
    except Exception as error:
        logger.warning(f"Could not read {csv_path}: {error}")
        return pd.DataFrame(columns=_STANDARD_COLUMNS)

    season = fifa_version_to_season(fifa_version)

    core_cols = ["club_name", "overall", "potential", "age",
                 "player_positions"]
    result = _safe_extract_columns(raw, core_cols)

    extended = _safe_extract_columns(raw, _EXTENDED_ATTRIBUTE_COLUMNS)
    for col in extended.columns:
        result[col] = extended[col]

    result["season"] = season
    return result


def load_ea_fc24_csv(csv_path: Path) -> pd.DataFrame:
    """Load an EA FC24-format CSV and standardize columns.

    FC24 uses 'Club', 'Overall', 'Age', 'Position' column names.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        DataFrame with standardized columns.
    """
    try:
        raw = pd.read_csv(csv_path, low_memory=False)
    except Exception as error:
        logger.warning(f"Could not read {csv_path}: {error}")
        return pd.DataFrame(columns=_STANDARD_COLUMNS)

    result = _remap_columns(raw, _FC24_COLUMN_MAP)
    result["potential"] = pd.NA
    result["season"] = "2324"

    _fill_missing_standard_columns(result)
    return result


def load_ea_fc25_csv(csv_path: Path) -> pd.DataFrame:
    """Load an EA FC25-format CSV and standardize columns.

    FC25 uses 'Team', 'OVR', 'Age', 'Position' column names.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        DataFrame with standardized columns.
    """
    try:
        raw = pd.read_csv(csv_path, low_memory=False)
    except Exception as error:
        logger.warning(f"Could not read {csv_path}: {error}")
        return pd.DataFrame(columns=_STANDARD_COLUMNS)

    result = _remap_columns(raw, _FC25_COLUMN_MAP)
    result["potential"] = pd.NA
    result["season"] = "2425"

    _fill_missing_standard_columns(result)
    return result


def _fill_missing_standard_columns(df: pd.DataFrame) -> None:
    """Fill any missing standard columns with NaN in-place.

    Args:
        df: DataFrame to fill missing columns on.
    """
    for col in _STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_player_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize club names and add position group column.

    Args:
        df: DataFrame with club_name and player_positions columns.

    Returns:
        DataFrame with normalized club_name and position_group column.
    """
    result = df.copy()
    result["club_name"] = result["club_name"].apply(
        lambda name: normalize_team_name(name) if pd.notna(name) else name,
    )
    result["position_group"] = result["player_positions"].apply(
        classify_position_group,
    )
    return result


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _compute_positional_average(
    group: pd.DataFrame,
    position: str,
) -> float:
    """Compute mean overall for a position group within a squad.

    Args:
        group: Squad DataFrame (single team/season).
        position: Position group label ("GK", "DEF", "MID", "FWD").

    Returns:
        Mean overall rating, or NaN if no players in that position.
    """
    positional = group[group["position_group"] == position]
    if positional.empty:
        return float("nan")
    return positional["overall"].mean()


def _safe_column_mean(
    df: pd.DataFrame,
    column: str,
) -> float:
    """Compute mean of a column, returning NaN if column is missing.

    Args:
        df: Source DataFrame.
        column: Column name to compute mean of.

    Returns:
        Mean value or NaN.
    """
    if column not in df.columns:
        return float("nan")
    return df[column].mean()


def _safe_column_sum(
    df: pd.DataFrame,
    column: str,
) -> float:
    """Compute sum of a column, returning NaN if column is missing.

    Args:
        df: Source DataFrame.
        column: Column name to compute sum of.

    Returns:
        Sum value or NaN.
    """
    if column not in df.columns:
        return float("nan")
    return float(df[column].sum())


def _positional_column_mean(
    group: pd.DataFrame,
    position: str,
    column: str,
) -> float:
    """Compute mean of a column for a specific position group.

    Args:
        group: Squad DataFrame (single team/season).
        position: Position group label ("GK", "DEF", "MID", "FWD").
        column: Column name to average.

    Returns:
        Mean value or NaN.
    """
    positional = group[group["position_group"] == position]
    if positional.empty or column not in positional.columns:
        return float("nan")
    return positional[column].mean()


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _compute_all_positional_averages(
    players: pd.DataFrame,
) -> pd.DataFrame:
    """Compute positional average ratings for all teams.

    Args:
        players: Normalized player DataFrame.

    Returns:
        DataFrame with club_name, season, and avg_*_rating columns.
    """
    records: list[dict[str, object]] = []

    for (club, season), group in players.groupby(["club_name", "season"]):
        records.append({
            "club_name": club,
            "season": season,
            "avg_gk_rating": _compute_positional_average(group, "GK"),
            "avg_def_rating": _compute_positional_average(group, "DEF"),
            "avg_mid_rating": _compute_positional_average(group, "MID"),
            "avg_fwd_rating": _compute_positional_average(group, "FWD"),
        })

    return pd.DataFrame(records)


def _compute_extended_attributes(
    players: pd.DataFrame,
) -> pd.DataFrame:
    """Compute extended attribute averages per team-season.

    Args:
        players: Normalized player DataFrame.

    Returns:
        DataFrame with club_name, season, and extended feature columns.
    """
    records: list[dict[str, object]] = []

    for (club, season), group in players.groupby(["club_name", "season"]):
        record: dict[str, object] = {
            "club_name": club,
            "season": season,
        }
        _add_main_attribute_averages(record, group)
        _add_tactical_averages(record, group)
        _add_positional_skill_averages(record, group)
        _add_financial_totals(record, group)
        _add_meta_averages(record, group)
        records.append(record)

    return pd.DataFrame(records)


def _add_main_attribute_averages(
    record: dict[str, object],
    group: pd.DataFrame,
) -> None:
    """Add main 6-attribute averages to record dict.

    Args:
        record: Dict to add features to (mutated in-place).
        group: Squad DataFrame for one team-season.
    """
    for attr in _MAIN_ATTRIBUTE_COLUMNS:
        record[f"avg_{attr}"] = _safe_column_mean(group, attr)


def _add_tactical_averages(
    record: dict[str, object],
    group: pd.DataFrame,
) -> None:
    """Add tactical attribute averages to record dict.

    Args:
        record: Dict to add features to (mutated in-place).
        group: Squad DataFrame for one team-season.
    """
    record["avg_stamina"] = _safe_column_mean(group, "power_stamina")
    record["avg_sprint_speed"] = _safe_column_mean(
        group, "movement_sprint_speed",
    )
    record["avg_composure"] = _safe_column_mean(
        group, "mentality_composure",
    )
    record["avg_vision"] = _safe_column_mean(group, "mentality_vision")


def _add_positional_skill_averages(
    record: dict[str, object],
    group: pd.DataFrame,
) -> None:
    """Add position-specific skill averages to record dict.

    Args:
        record: Dict to add features to (mutated in-place).
        group: Squad DataFrame for one team-season.
    """
    record["avg_fwd_finishing"] = _positional_column_mean(
        group, "FWD", "attacking_finishing",
    )
    record["avg_def_standing_tackle"] = _positional_column_mean(
        group, "DEF", "defending_standing_tackle",
    )
    record["avg_gk_reflexes"] = _positional_column_mean(
        group, "GK", "goalkeeping_reflexes",
    )


def _add_financial_totals(
    record: dict[str, object],
    group: pd.DataFrame,
) -> None:
    """Add financial totals to record dict.

    Args:
        record: Dict to add features to (mutated in-place).
        group: Squad DataFrame for one team-season.
    """
    record["total_value_eur"] = _safe_column_sum(group, "value_eur")
    record["total_wage_eur"] = _safe_column_sum(group, "wage_eur")


def _add_meta_averages(
    record: dict[str, object],
    group: pd.DataFrame,
) -> None:
    """Add meta attribute averages to record dict.

    Args:
        record: Dict to add features to (mutated in-place).
        group: Squad DataFrame for one team-season.
    """
    record["avg_skill_moves"] = _safe_column_mean(group, "skill_moves")
    record["avg_weak_foot"] = _safe_column_mean(group, "weak_foot")
    record["avg_international_reputation"] = _safe_column_mean(
        group, "international_reputation",
    )


def aggregate_squad_features(players: pd.DataFrame) -> pd.DataFrame:
    """Aggregate player-level data into team-season features.

    Args:
        players: Normalized player DataFrame with club_name, season,
                 overall, potential, age, position_group columns.

    Returns:
        DataFrame with one row per team per season and feature columns.
    """
    grouped = players.groupby(["club_name", "season"], as_index=False)

    result = grouped.agg(
        avg_overall=("overall", "mean"),
        avg_potential=("potential", "mean"),
        avg_age=("age", "mean"),
        top_player_rating=("overall", "max"),
    )

    squad_depth = players[players["overall"] > _SQUAD_DEPTH_THRESHOLD].groupby(
        ["club_name", "season"], as_index=False,
    ).size().rename(columns={"size": "squad_depth"})

    result = result.merge(squad_depth, on=["club_name", "season"], how="left")
    result["squad_depth"] = result["squad_depth"].fillna(0).astype(int)

    positional = _compute_all_positional_averages(players)
    result = result.merge(positional, on=["club_name", "season"], how="left")

    extended = _compute_extended_attributes(players)
    result = result.merge(extended, on=["club_name", "season"], how="left")

    return result


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

_SOFIFA_VERSION_MAP: dict[str, int] = {
    "players_15.csv": 15,
    "players_16.csv": 16,
    "players_17.csv": 17,
    "players_18.csv": 18,
    "players_19.csv": 19,
    "players_20.csv": 20,
    "players_21.csv": 21,
    "players_22.csv": 22,
}


def _discover_csv_files(fifa_dir: Path) -> list[tuple[Path, int, str]]:
    """Discover all FIFA CSV files and their formats.

    Args:
        fifa_dir: Root directory for FIFA data.

    Returns:
        List of (path, fifa_version, format_type) tuples.
    """
    discovered: list[tuple[Path, int, str]] = []

    datasets_dir = fifa_dir / "fifa_2022_datasets"
    if datasets_dir.exists():
        for filename, version in _SOFIFA_VERSION_MAP.items():
            path = datasets_dir / filename
            if path.exists():
                discovered.append((path, version, "sofifa"))

    male_23 = fifa_dir / "male_players_23.csv"
    if male_23.exists():
        discovered.append((male_23, 23, "sofifa"))

    fc24_path = fifa_dir / "2024" / "male_players.csv"
    if fc24_path.exists():
        discovered.append((fc24_path, 24, "ea_fc24"))

    fc25_path = fifa_dir / "fc25" / "male_players.csv"
    if fc25_path.exists():
        discovered.append((fc25_path, 25, "ea_fc25"))

    fc26_candidates = list(fifa_dir.glob("FC26*.csv"))
    if fc26_candidates:
        discovered.append((fc26_candidates[0], 26, "sofifa"))

    logger.info(f"Discovered {len(discovered)} FIFA CSV files")
    return discovered


def _load_single_csv(
    path: Path,
    version: int,
    format_type: str,
) -> pd.DataFrame:
    """Load a single CSV file based on its format type.

    Args:
        path: Path to the CSV file.
        version: FIFA version number.
        format_type: One of "sofifa", "ea_fc24", "ea_fc25".

    Returns:
        Standardized DataFrame.
    """
    if format_type == "sofifa":
        return load_sofifa_csv(path, fifa_version=version)
    if format_type == "ea_fc24":
        return load_ea_fc24_csv(path)
    if format_type == "ea_fc25":
        return load_ea_fc25_csv(path)

    logger.warning(f"Unknown format type: {format_type}")
    return pd.DataFrame(columns=_STANDARD_COLUMNS)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def build_player_features(fifa_dir: Path) -> pd.DataFrame:
    """Build player features from all FIFA CSV files.

    Reads all available FIFA CSVs, normalizes club names, classifies
    positions, and aggregates per-team per-season features.

    Args:
        fifa_dir: Root directory containing FIFA data files.

    Returns:
        DataFrame with columns: club_name, season, avg_overall,
        avg_potential, squad_depth, top_player_rating, avg_age,
        avg_gk_rating, avg_def_rating, avg_mid_rating, avg_fwd_rating,
        plus extended attribute averages and financial totals.
    """
    if not fifa_dir.exists():
        logger.warning(f"FIFA directory not found: {fifa_dir}")
        return pd.DataFrame()

    csv_files = _discover_csv_files(fifa_dir)
    if not csv_files:
        logger.warning("No FIFA CSV files found")
        return pd.DataFrame()

    all_players: list[pd.DataFrame] = []
    for path, version, format_type in csv_files:
        loaded = _load_single_csv(path, version, format_type)
        if not loaded.empty:
            all_players.append(loaded)
            logger.info(
                f"Loaded {len(loaded)} players from {path.name} "
                f"(FIFA {version})"
            )

    if not all_players:
        return pd.DataFrame()

    combined = pd.concat(all_players, ignore_index=True)
    combined = combined.dropna(subset=["club_name", "overall"])
    normalized = normalize_player_dataframe(combined)
    features = aggregate_squad_features(normalized)

    logger.info(
        f"Built player features: {len(features)} team-season rows "
        f"from {len(combined)} players"
    )
    return features

"""Load Pinnacle closing odds from football-data.co.uk CSV files.

football-data.co.uk provides historical match results with closing odds
from multiple bookmakers including Pinnacle (columns PSH, PSD, PSA for
opening; PSCH, PSCD, PSCA for closing).

This module loads local CSVs and standardizes column names for downstream
CLV computation. It intentionally does NOT depend on the main
FootballDataExtractor in processing/extractors.py: that class downloads
on the fly and applies team-name normalization. Here we read pre-downloaded
files with a minimal, predictable schema so that odds data can be loaded
independently of the full pipeline.
"""

from pathlib import Path

import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

# Maps football-data.co.uk league codes to SportsLab canonical league names.
FOOTBALL_DATA_LEAGUE_MAP: dict[str, str] = {
    "E0": "ENG-Premier League",
    "SP1": "ESP-La Liga",
    "D1": "GER-Bundesliga",
    "I1": "ITA-Serie A",
    "F1": "FRA-Ligue 1",
    "E1": "ENG-Championship",
    "D2": "GER-Bundesliga 2",
    "I2": "ITA-Serie B",
    "N1": "NED-Eredivisie",
    "P1": "POR-Primeira Liga",
}

# Reverse map: SportsLab name -> football-data code.
_LEAGUE_TO_CODE: dict[str, str] = {v: k for k, v in FOOTBALL_DATA_LEAGUE_MAP.items()}

# Columns we extract from the CSV and their standardized names.
# Pinnacle closing 1X2 (preferred):
_PINNACLE_CLOSING_COLS: dict[str, str] = {
    "PSCH": "pinnacle_home",
    "PSCD": "pinnacle_draw",
    "PSCA": "pinnacle_away",
}

# Pinnacle opening 1X2 (fallback when closing is missing):
_PINNACLE_OPENING_COLS: dict[str, str] = {
    "PSH": "pinnacle_home",
    "PSD": "pinnacle_draw",
    "PSA": "pinnacle_away",
}

# Max market odds (fallback when Pinnacle is entirely absent):
_MAX_CLOSING_COLS: dict[str, str] = {
    "MaxCH": "max_home",
    "MaxCD": "max_draw",
    "MaxCA": "max_away",
}

_MAX_OPENING_COLS: dict[str, str] = {
    "MaxH": "max_home",
    "MaxD": "max_draw",
    "MaxA": "max_away",
}

# Legacy Betbrain max columns (older seasons):
_BETBRAIN_MAX_COLS: dict[str, str] = {
    "BbMxH": "max_home",
    "BbMxD": "max_draw",
    "BbMxA": "max_away",
}

# Over/Under 2.5 closing max:
_OU_CLOSING_COLS: dict[str, str] = {
    "MaxC>2.5": "max_over_25",
    "MaxC<2.5": "max_under_25",
}

_OU_OPENING_COLS: dict[str, str] = {
    "Max>2.5": "max_over_25",
    "Max<2.5": "max_under_25",
}

_OU_BETBRAIN_COLS: dict[str, str] = {
    "BbMx>2.5": "max_over_25",
    "BbMx<2.5": "max_under_25",
}

# Match metadata columns.
_META_COLS: dict[str, str] = {
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "FTHG": "home_goals",
    "FTAG": "away_goals",
}

_FOOTBALL_DATA_BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"


def load_football_data_csv(csv_path: Path) -> pd.DataFrame:
    """Load a single season CSV from football-data.co.uk.

    Parses the CSV and extracts match metadata, Pinnacle closing odds,
    max market odds, and over/under 2.5 odds.  When Pinnacle closing
    columns are missing, falls back to Pinnacle opening odds.  When
    Pinnacle is entirely absent, the pinnacle_* columns are NaN and
    max_* columns are populated from the aggregate max market columns.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        DataFrame with standardized columns: date, home_team, away_team,
        home_goals, away_goals, pinnacle_home, pinnacle_draw, pinnacle_away,
        max_home, max_draw, max_away, max_over_25, max_under_25.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If CSV lacks required match metadata columns
            (HomeTeam, AwayTeam).
    """
    raw = pd.read_csv(csv_path)

    required = {"HomeTeam", "AwayTeam"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(
            f"CSV missing required columns: {sorted(missing)}. Available: {sorted(raw.columns)}"
        )

    # Drop rows without teams (trailing garbage rows in some CSVs).
    raw = raw.dropna(subset=["HomeTeam", "AwayTeam"])

    result = pd.DataFrame()

    # Parse date — football-data.co.uk uses DD/MM/YYYY or DD/MM/YY.
    if "Date" in raw.columns:
        result["date"] = pd.to_datetime(
            raw["Date"],
            dayfirst=True,
        ).dt.strftime("%Y-%m-%d")
    else:
        result["date"] = pd.NaT

    # Match metadata.
    for src_col, dst_col in _META_COLS.items():
        if src_col in raw.columns:
            result[dst_col] = raw[src_col].values
        else:
            result[dst_col] = pd.NA

    # Pinnacle odds: prefer closing, then opening.
    _apply_odds_fallback(
        raw,
        result,
        preferred=_PINNACLE_CLOSING_COLS,
        fallbacks=[_PINNACLE_OPENING_COLS],
    )

    # Max market odds: prefer closing, then opening, then Betbrain legacy.
    _apply_odds_fallback(
        raw,
        result,
        preferred=_MAX_CLOSING_COLS,
        fallbacks=[_MAX_OPENING_COLS, _BETBRAIN_MAX_COLS],
    )

    # Over/Under 2.5: prefer closing, then opening, then Betbrain.
    _apply_odds_fallback(
        raw,
        result,
        preferred=_OU_CLOSING_COLS,
        fallbacks=[_OU_OPENING_COLS, _OU_BETBRAIN_COLS],
    )

    # Coerce odds columns to float (some CSVs have empty strings).
    odds_cols = [
        "pinnacle_home",
        "pinnacle_draw",
        "pinnacle_away",
        "max_home",
        "max_draw",
        "max_away",
        "max_over_25",
        "max_under_25",
    ]
    for col in odds_cols:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce")

    logger.info(
        "football_data_csv_loaded",
        path=str(csv_path),
        rows=len(result),
        has_pinnacle="pinnacle_home" in result.columns and result["pinnacle_home"].notna().any(),
    )

    return result


def _apply_odds_fallback(
    source: pd.DataFrame,
    target: pd.DataFrame,
    preferred: dict[str, str],
    fallbacks: list[dict[str, str]],
) -> None:
    """Copy odds columns from source to target with fallback chain.

    If the preferred source columns exist and have data, use them.
    Otherwise try each fallback mapping in order. Columns that cannot
    be found in any mapping are set to NaN.

    Args:
        source: Raw CSV DataFrame.
        target: Output DataFrame to populate.
        preferred: Primary column mapping (CSV name -> output name).
        fallbacks: Ordered list of alternative mappings.
    """
    # Try preferred mapping first.
    all_mappings = [preferred, *fallbacks]

    for mapping in all_mappings:
        available = {k: v for k, v in mapping.items() if k in source.columns}
        if available:
            for src_col, dst_col in available.items():
                if dst_col not in target.columns:
                    target[dst_col] = source[src_col].values
            # If we got at least one column from this mapping, stop.
            if len(available) == len(mapping):
                return

    # Ensure all expected output columns exist even if no source had them.
    for mapping in all_mappings:
        for dst_col in mapping.values():
            if dst_col not in target.columns:
                target[dst_col] = float("nan")


def load_pinnacle_odds(
    data_dir: Path,
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    """Load Pinnacle closing odds for multiple leagues/seasons.

    Discovers CSV files in data_dir following football-data.co.uk naming:
    ``data_dir/<league_code>/<season>.csv`` (e.g. ``data_dir/E0/2324.csv``).

    Alternatively, CSVs can be flat in data_dir named ``<code>_<season>.csv``
    (e.g. ``data_dir/E0_2324.csv``) for simpler layouts.

    Args:
        data_dir: Root directory with football-data.co.uk CSVs.
        leagues: Filter to these SportsLab league names
            (e.g. ``["ENG-Premier League"]``). ``None`` means all discovered.
        seasons: Filter to these season codes (e.g. ``["2324"]``).
            ``None`` means all discovered.

    Returns:
        DataFrame with closing odds per match, plus ``league`` and ``season``
        columns. Empty DataFrame (with correct columns) if no files found.
    """
    # Build set of allowed league codes.
    league_codes: set[str] | None = None
    if leagues is not None:
        league_codes = set()
        for league_name in leagues:
            code = _LEAGUE_TO_CODE.get(league_name)
            if code is not None:
                league_codes.add(code)
            else:
                logger.warning(
                    "unknown_league_name",
                    league=league_name,
                    known=sorted(_LEAGUE_TO_CODE.keys()),
                )

    frames: list[pd.DataFrame] = []

    for csv_path in sorted(data_dir.rglob("*.csv")):
        league_code, season_code = _parse_csv_location(csv_path, data_dir)
        if league_code is None or season_code is None:
            logger.debug(
                "skipping_unrecognized_csv",
                path=str(csv_path),
            )
            continue

        if league_codes is not None and league_code not in league_codes:
            continue
        if seasons is not None and season_code not in seasons:
            continue

        league_name = FOOTBALL_DATA_LEAGUE_MAP.get(league_code, league_code)

        try:
            frame = load_football_data_csv(csv_path)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning(
                "csv_load_failed",
                path=str(csv_path),
                error=str(exc),
            )
            continue

        frame["league"] = league_name
        frame["season"] = season_code
        frames.append(frame)

    if not frames:
        logger.info(
            "no_odds_files_found",
            data_dir=str(data_dir),
            leagues=leagues,
            seasons=seasons,
        )
        return pd.DataFrame(
            columns=[
                "date",
                "home_team",
                "away_team",
                "home_goals",
                "away_goals",
                "pinnacle_home",
                "pinnacle_draw",
                "pinnacle_away",
                "max_home",
                "max_draw",
                "max_away",
                "max_over_25",
                "max_under_25",
                "league",
                "season",
            ],
        )

    combined = pd.concat(frames, ignore_index=True)
    logger.info(
        "pinnacle_odds_loaded",
        total_matches=len(combined),
        leagues=combined["league"].nunique(),
        seasons=combined["season"].nunique(),
    )
    return combined


def _parse_csv_location(
    csv_path: Path,
    data_dir: Path,
) -> tuple[str | None, str | None]:
    """Extract league code and season from a CSV path.

    Supports two layouts:
    - Nested: ``data_dir/E0/2324.csv`` -> (``E0``, ``2324``)
    - Flat: ``data_dir/E0_2324.csv`` -> (``E0``, ``2324``)

    Args:
        csv_path: Absolute path to the CSV file.
        data_dir: Root data directory.

    Returns:
        Tuple of (league_code, season_code), or (None, None) if
        the path doesn't match any expected pattern.
    """
    try:
        relative = csv_path.relative_to(data_dir)
    except ValueError:
        return None, None

    parts = relative.parts

    # Nested layout: league_code/season.csv
    if len(parts) == 2:
        league_code = parts[0]
        season_code = parts[1].removesuffix(".csv")
        if league_code in FOOTBALL_DATA_LEAGUE_MAP:
            return league_code, season_code

    # Flat layout: league_code_season.csv (e.g. E0_2324.csv)
    if len(parts) == 1:
        stem = parts[0].removesuffix(".csv")
        for code in FOOTBALL_DATA_LEAGUE_MAP:
            prefix = f"{code}_"
            if stem.startswith(prefix):
                season_code = stem[len(prefix) :]
                return code, season_code

    return None, None


def download_season_csv(
    league_code: str,
    season: str,
    output_dir: Path,
) -> Path:
    """Download a single season CSV from football-data.co.uk.

    Fetches the CSV from the canonical URL and writes it to
    ``output_dir/<league_code>/<season>.csv``.

    Args:
        league_code: football-data.co.uk code (e.g. ``E0``).
        season: Season code (e.g. ``2324``).
        output_dir: Root directory to save files.

    Returns:
        Path to the downloaded CSV file.

    Raises:
        ValueError: If league_code is not in FOOTBALL_DATA_LEAGUE_MAP.
        RuntimeError: If the download fails.

    .. note::
        TODO(SPO-52): This function makes HTTP requests. Do not call
        in tests without mocking. Consider adding retry logic and
        rate limiting for bulk downloads.
    """
    if league_code not in FOOTBALL_DATA_LEAGUE_MAP:
        raise ValueError(
            f"Unknown league code: {league_code!r}. "
            f"Known: {sorted(FOOTBALL_DATA_LEAGUE_MAP.keys())}"
        )

    url = _FOOTBALL_DATA_BASE_URL.format(season=season, code=league_code)
    dest_dir = output_dir / league_code
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{season}.csv"

    # TODO(SPO-52): Add retry with exponential backoff, rate limiting,
    # and checksum validation. For now, a single request.
    import requests

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to download {url}: {exc}") from exc

    dest_path.write_bytes(response.content)
    logger.info(
        "season_csv_downloaded",
        url=url,
        dest=str(dest_path),
        size_bytes=len(response.content),
    )
    return dest_path

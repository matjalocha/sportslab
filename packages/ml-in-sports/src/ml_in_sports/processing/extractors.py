"""Data extractors wrapping soccerdata and external CSV sources.

Each extractor is immutable after __init__ and returns
Optional[pd.DataFrame] with standardized column names.
"""

import io
from pathlib import Path
from typing import Protocol

import pandas as pd
import requests
import soccerdata as sd  # type: ignore[import-untyped]  # no stubs available
import structlog
from tqdm import tqdm  # noqa: F401

from ml_in_sports.settings import get_settings
from ml_in_sports.utils.team_names import normalize_team_name

logger = structlog.get_logger(__name__)

LEAGUE_CONFIG: dict[str, dict[str, str]] = {
    "ENG-Premier League": {
        "football_data_code": "E0",
        "tm_competition_id": "GB1",
        "fifa_league_filter": "Premier League",
    },
    "ESP-La Liga": {
        "football_data_code": "SP1",
        "tm_competition_id": "ES1",
        "fifa_league_filter": "Spain Primera Division|La Liga|LALIGA",
    },
    "GER-Bundesliga": {
        "football_data_code": "D1",
        "tm_competition_id": "L1",
        "fifa_league_filter": "German 1. Bundesliga|^Bundesliga$",
    },
    "ITA-Serie A": {
        "football_data_code": "I1",
        "tm_competition_id": "IT1",
        "fifa_league_filter": "Italian Serie A|^Serie A",
    },
    "FRA-Ligue 1": {
        "football_data_code": "F1",
        "tm_competition_id": "FR1",
        "fifa_league_filter": "French Ligue 1|^Ligue 1",
    },
}

ALL_LEAGUES: list[str] = list(LEAGUE_CONFIG.keys())

def _fifa_data_dir() -> Path:
    """Resolve the FIFA data directory from settings at call time."""
    return get_settings().fifa_data_dir

_FIFA_COLUMN_MAP: dict[str, str] = {
    "short_name": "player_name",
    "long_name": "long_name",
    "age": "age",
    "nationality_name": "nationality",
    "club_name": "club_name",
    "league_name": "league_name",
    "overall": "overall",
    "potential": "potential",
    "value_eur": "value_eur",
    "wage_eur": "wage_eur",
    "preferred_foot": "preferred_foot",
    "height_cm": "height_cm",
    "weight_kg": "weight_kg",
    "player_positions": "positions",
    "pace": "pace",
    "shooting": "shooting",
    "passing": "passing",
    "dribbling": "dribbling",
    "defending": "defending",
    "physic": "physic",
    "skill_moves": "skill_moves",
    "weak_foot": "weak_foot",
}

_FC25_COLUMN_MAP: dict[str, str] = {
    "name": "player_name",
    "age": "age",
    "nation": "nationality",
    "club": "club_name",
    "league": "league_name",
    "overall": "overall",
    "preferred foot": "preferred_foot",
    "height": "height_cm",
    "weight": "weight_kg",
    "position": "positions",
    "PAC": "pace",
    "SHO": "shooting",
    "PAS": "passing",
    "DRI": "dribbling",
    "DEF": "defending",
    "PHY": "physic",
    "skill moves": "skill_moves",
    "weak foot": "weak_foot",
}

_FIFA_VERSION_TO_SEASON: dict[str, str] = {
    "15": "1415", "16": "1516", "17": "1617", "18": "1718",
    "19": "1819", "20": "1920", "21": "2021", "22": "2122",
    "23": "2223", "24": "2324", "25": "2425", "26": "2526",
}


class MatchExtractor(Protocol):
    """Protocol for extractors producing match-level data."""

    def extract_matches(
        self, league: str, season: str,
    ) -> pd.DataFrame | None: ...


class PlayerMatchExtractor(Protocol):
    """Protocol for extractors producing player-match data."""

    def extract_player_matches(
        self, league: str, season: str,
    ) -> pd.DataFrame | None: ...


class FifaRatingsExtractor:
    """Extracts FIFA/EA FC player ratings from local Kaggle CSVs.

    Supports three data formats:
    - stefanoleone992: combined male_players.csv (FIFA 15-24, sofifa format)
    - nyagami: FC 25 single file (easports.com format, Title Case columns)
    - rovnez: FC 26 single file (sofifa format)

    Download CSVs from Kaggle and place in data/fifa/.
    """

    def __init__(
        self,
        data_dir: Path | None = None,
        league_filters: list[str] | None = None,
    ) -> None:
        if data_dir is None:
            data_dir = _fifa_data_dir()
        if league_filters is None:
            league_filters = ["Premier League"]
        self._data_dir = data_dir
        self._league_filters = league_filters

    def _find_fifa_csv(self, fifa_version: str) -> list[Path]:
        """Find CSV file(s) matching a FIFA version number.

        Searches in order: filename match, recursive filename match,
        then directory-name match (e.g. '2024/male_players.csv').

        Args:
            fifa_version: Version number as string (e.g. "15", "24").

        Returns:
            List of matching Path objects (may be empty).
        """
        patterns = [
            f"*{fifa_version}*.csv",
            f"**/*{fifa_version}*.csv",
            f"*{fifa_version}*/*.csv",
        ]
        for pattern in patterns:
            matches = list(self._data_dir.glob(pattern))
            if matches:
                return matches
        return []

    def extract_ratings(
        self, fifa_version: str,
    ) -> pd.DataFrame | None:
        """Load FIFA ratings for a single version from a local CSV.

        Args:
            fifa_version: Version number as string (e.g. "15", "25").

        Returns:
            DataFrame with standardized columns, league-filtered, or None.
        """
        csv_files = self._find_fifa_csv(fifa_version)
        if not csv_files:
            logger.warning(
                f"No FIFA CSV found for {fifa_version} in {self._data_dir}"
            )
            return None

        try:
            df = pd.read_csv(csv_files[0], low_memory=False)
        except Exception as e:
            logger.warning(f"FIFA CSV read failed ({csv_files[0]}): {e}")
            return None

        return self._normalize_and_filter(df, fifa_version)

    def extract_combined_ratings(
        self,
    ) -> dict[str, pd.DataFrame]:
        """Load all FIFA versions from the combined stefanoleone992 file.

        Reads male_players.csv once and splits by fifa_version column.
        Keeps only the latest update per player per version.

        Returns:
            Dict of version string to league-filtered DataFrame.
        """
        combined_files = list(self._data_dir.glob("male_players*.csv"))
        if not combined_files:
            return {}

        usecols = [*_FIFA_COLUMN_MAP, "fifa_version", "fifa_update"]
        try:
            df = pd.read_csv(
                combined_files[0], usecols=usecols, low_memory=True,
            )
        except (ValueError, KeyError):
            try:
                df = pd.read_csv(combined_files[0], low_memory=True)
            except Exception as e:
                logger.warning(f"Combined FIFA CSV read failed: {e}")
                return {}
        except Exception as e:
            logger.warning(f"Combined FIFA CSV read failed: {e}")
            return {}

        if "fifa_version" not in df.columns:
            logger.warning("Combined CSV missing fifa_version column")
            return {}

        results: dict[str, pd.DataFrame] = {}
        for version_num in sorted(df["fifa_version"].dropna().unique()):
            version_str = str(int(version_num))
            chunk = df[df["fifa_version"] == version_num].copy()
            if "fifa_update" in chunk.columns:
                latest_update = chunk["fifa_update"].max()
                chunk = chunk[chunk["fifa_update"] == latest_update]
            normalized = self._normalize_and_filter(chunk, version_str)
            if normalized is not None and not normalized.empty:
                results[version_str] = normalized

        return results

    def _normalize_and_filter(
        self, df: pd.DataFrame, fifa_version: str,
    ) -> pd.DataFrame | None:
        """Normalize columns and filter to configured leagues.

        Args:
            df: Raw DataFrame from CSV.
            fifa_version: Version label for the output.

        Returns:
            League-filtered DataFrame with standard columns, or None.
        """
        column_map = self._detect_column_map(df)
        rename_map = {
            k: v for k, v in column_map.items() if k in df.columns
        }
        df = df.rename(columns=rename_map)

        if "league_name" not in df.columns:
            logger.warning(f"FIFA {fifa_version}: no league column found")
            return None

        pattern = "|".join(self._league_filters)
        league_mask = df["league_name"].str.contains(
            pattern, case=False, na=False,
        )
        filtered = df[league_mask].copy()
        filtered["fifa_version"] = fifa_version

        keep_cols = [*_FIFA_COLUMN_MAP.values(), "fifa_version"]
        available = [c for c in keep_cols if c in filtered.columns]
        filtered = filtered[available]

        logger.info(
            f"FIFA {fifa_version}: {len(filtered)} players "
            f"({len(self._league_filters)} leagues)"
        )
        return filtered

    def _detect_column_map(
        self, df: pd.DataFrame,
    ) -> dict[str, str]:
        """Detect which column format the CSV uses.

        Args:
            df: Raw DataFrame to inspect.

        Returns:
            Appropriate column rename mapping.
        """
        if "short_name" in df.columns:
            return _FIFA_COLUMN_MAP
        if "name" in df.columns and "PAC" in df.columns:
            return _FC25_COLUMN_MAP
        return _FIFA_COLUMN_MAP


class UnderstatExtractor:
    """Extracts xG data from Understat.

    Provides match-level and player-level data for top 5 European leagues.
    """

    def extract_matches(
        self, league: str, season: str,
    ) -> pd.DataFrame | None:
        """Extract match schedule + team stats from Understat.

        Args:
            league: League identifier (e.g. "ENG-Premier League").
            season: Season code (e.g. "2324").

        Returns:
            DataFrame indexed by [league, season, game] or None on error.
        """
        try:
            client = sd.Understat(leagues=league, seasons=season)
            schedule = client.read_schedule()
            team_stats = client.read_team_match_stats()
            return schedule.join(team_stats, rsuffix="_dup")  # type: ignore[no-any-return]  # soccerdata returns Any
        except Exception as e:
            logger.warning(f"Understat match extraction failed: {e}")
            return None

    def extract_player_season(
        self, league: str, season: str,
    ) -> pd.DataFrame | None:
        """Extract player season aggregates from Understat.

        Args:
            league: League identifier.
            season: Season code.

        Returns:
            DataFrame with player season stats or None.
        """
        try:
            client = sd.Understat(leagues=league, seasons=season)
            return client.read_player_season_stats()  # type: ignore[no-any-return]  # soccerdata returns Any
        except Exception as e:
            logger.warning(f"Understat player season failed: {e}")
            return None

    def extract_player_matches(
        self, league: str, season: str,
    ) -> pd.DataFrame | None:
        """Extract per-player per-match stats from Understat.

        Args:
            league: League identifier.
            season: Season code.

        Returns:
            DataFrame with player match stats or None.
        """
        try:
            client = sd.Understat(leagues=league, seasons=season)
            return client.read_player_match_stats()  # type: ignore[no-any-return]  # soccerdata returns Any
        except Exception as e:
            logger.warning(f"Understat player match failed: {e}")
            return None

    def extract_shots(
        self, league: str, season: str,
    ) -> pd.DataFrame | None:
        """Extract all shot events from Understat.

        Args:
            league: League identifier.
            season: Season code.

        Returns:
            DataFrame with shot events or None.
        """
        try:
            client = sd.Understat(leagues=league, seasons=season)
            return client.read_shot_events()  # type: ignore[no-any-return]  # soccerdata returns Any
        except Exception as e:
            logger.warning(f"Understat shots extraction failed: {e}")
            return None


class EspnExtractor:
    """Extracts match stats and lineups from ESPN.

    Provides possession, passes, tackles, shots, crosses,
    clearances at team level and per-player lineup stats.
    """

    def extract_matches(
        self,
        league: str,
        season: str,
        before_date: str | None = None,
    ) -> pd.DataFrame | None:
        """Extract match stats from ESPN (pivoted to one row per match).

        Args:
            league: League identifier.
            season: Season code.
            before_date: Only scrape matches before this date (YYYY-MM-DD).

        Returns:
            DataFrame indexed by [league, season, game] or None.
        """
        try:
            client = sd.ESPN(leagues=league, seasons=season)
            schedule = client.read_schedule()
            if before_date:
                cutoff = pd.Timestamp(before_date, tz="UTC")
                schedule = schedule[schedule["date"] < cutoff]
            game_ids = schedule["game_id"].tolist()
            logger.info(
                f"ESPN matchsheets: {len(game_ids)} matches"
                f"{f' (before {before_date})' if before_date else ''}",
            )

            all_sheets = client.read_matchsheet(match_id=game_ids)
            return _pivot_espn_matchsheet(all_sheets)
        except Exception as e:
            logger.warning(f"ESPN match extraction failed: {e}")
            return None

    def extract_player_matches(
        self,
        league: str,
        season: str,
        before_date: str | None = None,
    ) -> pd.DataFrame | None:
        """Extract per-player lineup stats from ESPN.

        Args:
            league: League identifier.
            season: Season code.
            before_date: Only scrape matches before this date (YYYY-MM-DD).

        Returns:
            DataFrame with player lineup stats or None.
        """
        try:
            client = sd.ESPN(leagues=league, seasons=season)
            schedule = client.read_schedule()
            if before_date:
                cutoff = pd.Timestamp(before_date, tz="UTC")
                schedule = schedule[schedule["date"] < cutoff]
            game_ids = schedule["game_id"].tolist()
            logger.info(
                f"ESPN lineups: {len(game_ids)} matches"
                f"{f' (before {before_date})' if before_date else ''}",
            )

            all_lineups = client.read_lineup(match_id=game_ids)
            return all_lineups  # type: ignore[no-any-return]  # soccerdata returns Any
        except Exception as e:
            logger.warning(f"ESPN player extraction failed: {e}")
            return None


class SofascoreExtractor:
    """Extracts schedule and league tables from Sofascore."""

    def extract_matches(
        self, league: str, season: str,
    ) -> pd.DataFrame | None:
        """Extract match schedule from Sofascore.

        Args:
            league: League identifier.
            season: Season code.

        Returns:
            DataFrame with schedule data or None.
        """
        try:
            client = sd.Sofascore(leagues=league, seasons=season)
            return client.read_schedule()  # type: ignore[no-any-return]  # soccerdata returns Any
        except Exception as e:
            logger.warning(f"Sofascore schedule failed: {e}")
            return None

    def extract_league_table(
        self, league: str, season: str,
    ) -> pd.DataFrame | None:
        """Extract league standings from Sofascore.

        Args:
            league: League identifier.
            season: Season code.

        Returns:
            DataFrame with league table or None.
        """
        try:
            client = sd.Sofascore(leagues=league, seasons=season)
            return client.read_league_table()  # type: ignore[no-any-return]  # soccerdata returns Any
        except Exception as e:
            logger.warning(f"Sofascore league table failed: {e}")
            return None


class ClubEloExtractor:
    """Extracts team Elo ratings from ClubElo."""

    def extract_ratings(self, date: str) -> pd.DataFrame | None:
        """Extract Elo ratings for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format.

        Returns:
            DataFrame indexed by team name or None.
        """
        try:
            client = sd.ClubElo()
            return client.read_by_date(date)  # type: ignore[no-any-return]  # soccerdata returns Any
        except Exception as e:
            logger.warning(f"ClubElo extraction failed: {e}")
            return None


_TM_BASE_URL = (
    "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"
)
_TM_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _download_tm_csv(table_name: str) -> pd.DataFrame | None:
    """Download a gzipped CSV from the Transfermarkt datasets CDN.

    Args:
        table_name: Name of the table (e.g. "players", "games").

    Returns:
        Parsed DataFrame or None on error.
    """
    url = f"{_TM_BASE_URL}/{table_name}.csv.gz"
    try:
        response = requests.get(url, headers=_TM_HEADERS, timeout=120)
        response.raise_for_status()
        return pd.read_csv(
            io.BytesIO(response.content), compression="gzip",
        )
    except Exception as e:
        logger.warning(f"Transfermarkt download failed ({table_name}): {e}")
        return None


class TransfermarktExtractor:
    """Extracts data from Transfermarkt pre-built CSV datasets.

    Args:
        competition_id: Transfermarkt competition ID to filter by.
    """

    def __init__(self, competition_id: str = "GB1") -> None:
        self._competition_id = competition_id

    def extract_players(self) -> pd.DataFrame | None:
        """Download player profiles for the configured competition.

        Returns:
            DataFrame with filtered players or None.
        """
        df = _download_tm_csv("players")
        if df is None:
            return None

        filtered = df[
            df["current_club_domestic_competition_id"]
            == self._competition_id
        ].copy()
        logger.info(
            f"Transfermarkt players ({self._competition_id}): "
            f"{len(filtered)} rows"
        )
        return filtered

    def extract_player_valuations(self) -> pd.DataFrame | None:
        """Download player market value history for the configured competition.

        Returns:
            DataFrame with filtered player valuations or None.
        """
        df = _download_tm_csv("player_valuations")
        if df is None:
            return None

        filtered = df[
            df["player_club_domestic_competition_id"]
            == self._competition_id
        ].copy()
        logger.info(
            f"Transfermarkt valuations ({self._competition_id}): "
            f"{len(filtered)} rows"
        )
        return filtered

    def extract_games(self) -> pd.DataFrame | None:
        """Download game data for the configured competition.

        Returns:
            DataFrame with filtered games or None.
        """
        df = _download_tm_csv("games")
        if df is None:
            return None

        filtered = df[
            df["competition_id"] == self._competition_id
        ].copy()
        logger.info(
            f"Transfermarkt games ({self._competition_id}): "
            f"{len(filtered)} rows"
        )
        return filtered


_FOOTBALL_DATA_COLUMN_MAP: dict[str, str] = {
    # Match info
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "FTHG": "ft_home_goals",
    "FTAG": "ft_away_goals",
    "FTR": "ft_result",
    "HTHG": "ht_home_goals",
    "HTAG": "ht_away_goals",
    "HTR": "ht_result",
    "Referee": "referee",
    # Match stats
    "HS": "home_shots",
    "AS": "away_shots",
    "HST": "home_shots_on_target",
    "AST": "away_shots_on_target",
    "HF": "home_fouls",
    "AF": "away_fouls",
    "HC": "home_corners",
    "AC": "away_corners",
    "HY": "home_yellow_cards",
    "AY": "away_yellow_cards",
    "HR": "home_red_cards",
    "AR": "away_red_cards",
    # Opening 1X2 odds
    "B365H": "b365_home",
    "B365D": "b365_draw",
    "B365A": "b365_away",
    "BWH": "bw_home",
    "BWD": "bw_draw",
    "BWA": "bw_away",
    "IWH": "iw_home",
    "IWD": "iw_draw",
    "IWA": "iw_away",
    "PSH": "ps_home",
    "PSD": "ps_draw",
    "PSA": "ps_away",
    "WHH": "wh_home",
    "WHD": "wh_draw",
    "WHA": "wh_away",
    "VCH": "vc_home",
    "VCD": "vc_draw",
    "VCA": "vc_away",
    # Aggregate opening odds (new format)
    "MaxH": "max_home",
    "MaxD": "max_draw",
    "MaxA": "max_away",
    "AvgH": "avg_home",
    "AvgD": "avg_draw",
    "AvgA": "avg_away",
    # Aggregate opening odds (old Betbrain format → same DB columns)
    "BbMxH": "max_home",
    "BbAvH": "avg_home",
    "BbMxD": "max_draw",
    "BbAvD": "avg_draw",
    "BbMxA": "max_away",
    "BbAvA": "avg_away",
    # Opening O/U 2.5
    "B365>2.5": "b365_over_25",
    "B365<2.5": "b365_under_25",
    "P>2.5": "ps_over_25",
    "P<2.5": "ps_under_25",
    "Max>2.5": "max_over_25",
    "Max<2.5": "max_under_25",
    "Avg>2.5": "avg_over_25",
    "Avg<2.5": "avg_under_25",
    "BbMx>2.5": "max_over_25",
    "BbAv>2.5": "avg_over_25",
    "BbMx<2.5": "max_under_25",
    "BbAv<2.5": "avg_under_25",
    # Opening Asian Handicap
    "AHh": "ah_handicap",
    "B365AHH": "b365_ah_home",
    "B365AHA": "b365_ah_away",
    "PAHH": "ps_ah_home",
    "PAHA": "ps_ah_away",
    "MaxAHH": "max_ah_home",
    "MaxAHA": "max_ah_away",
    "AvgAHH": "avg_ah_home",
    "AvgAHA": "avg_ah_away",
    "BbAHh": "ah_handicap",
    "BbMxAHH": "max_ah_home",
    "BbAvAHH": "avg_ah_home",
    "BbMxAHA": "max_ah_away",
    "BbAvAHA": "avg_ah_away",
    # Closing 1X2
    "B365CH": "b365c_home",
    "B365CD": "b365c_draw",
    "B365CA": "b365c_away",
    "BWCH": "bwc_home",
    "BWCD": "bwc_draw",
    "BWCA": "bwc_away",
    "IWCH": "iwc_home",
    "IWCD": "iwc_draw",
    "IWCA": "iwc_away",
    "PSCH": "psc_home",
    "PSCD": "psc_draw",
    "PSCA": "psc_away",
    "WHCH": "whc_home",
    "WHCD": "whc_draw",
    "WHCA": "whc_away",
    "VCCH": "vcc_home",
    "VCCD": "vcc_draw",
    "VCCA": "vcc_away",
    "MaxCH": "maxc_home",
    "MaxCD": "maxc_draw",
    "MaxCA": "maxc_away",
    "AvgCH": "avgc_home",
    "AvgCD": "avgc_draw",
    "AvgCA": "avgc_away",
    # Closing O/U 2.5
    "B365C>2.5": "b365c_over_25",
    "B365C<2.5": "b365c_under_25",
    "PC>2.5": "psc_over_25",
    "PC<2.5": "psc_under_25",
    "MaxC>2.5": "maxc_over_25",
    "MaxC<2.5": "maxc_under_25",
    "AvgC>2.5": "avgc_over_25",
    "AvgC<2.5": "avgc_under_25",
    # Closing Asian Handicap
    "AHCh": "ahc_handicap",
    "B365CAHH": "b365c_ah_home",
    "B365CAHA": "b365c_ah_away",
    "PCAHH": "psc_ah_home",
    "PCAHA": "psc_ah_away",
    "MaxCAHH": "maxc_ah_home",
    "MaxCAHA": "maxc_ah_away",
    "AvgCAHH": "avgc_ah_home",
    "AvgCAHA": "avgc_ah_away",
}

_SEASON_TO_FOOTBALL_DATA: dict[str, str] = {
    "1415": "1415", "1516": "1516", "1617": "1617",
    "1718": "1718", "1819": "1819", "1920": "1920",
    "2021": "2021", "2122": "2122", "2223": "2223",
    "2324": "2324", "2425": "2425", "2526": "2526",
}

_FOOTBALL_DATA_BASE_URL = (
    "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
)


class FootballDataExtractor:
    """Extracts betting odds from football-data.co.uk CSV files.

    Args:
        league: League identifier (e.g. "ENG-Premier League").
    """

    def __init__(self, league: str = "ENG-Premier League") -> None:
        self._league = league
        config = LEAGUE_CONFIG.get(league, {})
        self._code = config.get("football_data_code", "E0")

    def extract_odds(
        self, season: str,
    ) -> pd.DataFrame | None:
        """Download and parse betting odds CSV for a season.

        Args:
            season: Season code (e.g. "2324").

        Returns:
            DataFrame with standardized column names and game key,
            or None on error.
        """
        fd_season = _SEASON_TO_FOOTBALL_DATA.get(season, season)
        url = _FOOTBALL_DATA_BASE_URL.format(
            season=fd_season, code=self._code,
        )

        try:
            raw = pd.read_csv(url)
        except Exception as e:
            logger.warning(f"Football-data download failed ({url}): {e}")
            return None

        if raw.empty:
            logger.warning(f"Empty CSV from football-data ({season})")
            return None

        return _parse_football_data_csv(raw, season, self._league)


def _parse_football_data_csv(
    raw: pd.DataFrame,
    season: str,
    league: str = "ENG-Premier League",
) -> pd.DataFrame | None:
    """Parse and standardize a football-data.co.uk CSV.

    Args:
        raw: Raw DataFrame from CSV.
        season: Season code for metadata.
        league: League identifier for metadata.

    Returns:
        Cleaned DataFrame with game key, or None if parsing fails.
    """
    df = raw.dropna(subset=["HomeTeam", "AwayTeam"]).copy()
    if df.empty:
        return None

    rename_map = {
        k: v for k, v in _FOOTBALL_DATA_COLUMN_MAP.items()
        if k in df.columns
    }
    df = df.rename(columns=rename_map)

    drop_cols = [
        "Div", "Bb1X2", "BbOU", "BbAH", "Time",
        "Date", "LBH", "LBD", "LBA", "SJH", "SJD", "SJA",
    ]
    df = df.drop(
        columns=[c for c in drop_cols if c in df.columns],
    )

    df["date"] = pd.to_datetime(
        raw["Date"], dayfirst=True,
    ).dt.strftime("%Y-%m-%d")

    df["home_team"] = df["home_team"].map(normalize_team_name)
    df["away_team"] = df["away_team"].map(normalize_team_name)

    df["game"] = (
        df["date"] + " " + df["home_team"] + "-" + df["away_team"]
    )
    df["league"] = league
    df["season"] = season

    return df


def _pivot_espn_matchsheet(
    matchsheet: pd.DataFrame,
) -> pd.DataFrame:
    """Pivot ESPN matchsheet from team-level to match-level.

    Converts 2 rows per match (home/away) into 1 row with
    home_/away_ prefixed columns.

    Args:
        matchsheet: ESPN matchsheet with is_home column.

    Returns:
        DataFrame with one row per match.
    """
    home = matchsheet[matchsheet["is_home"]].copy()
    away = matchsheet[~matchsheet["is_home"]].copy()

    home = home.droplevel("team")
    away = away.droplevel("team")

    home.columns = [f"home_{c}" for c in home.columns]
    away.columns = [f"away_{c}" for c in away.columns]

    return home.join(away, how="outer")

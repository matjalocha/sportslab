"""Tests for the pipeline orchestration."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from ml_in_sports.processing.pipeline import (
    _add_elo_to_matches,
    _align_espn_dates,
    _build_fifa_league_filters,
    _build_fifa_scrape_label,
    _get_season_start,
    _normalize_game_key,
    _parse_game_key,
    backfill_elo_ratings,
    build_fifa_ratings,
    build_match_base,
    build_match_dataset,
    build_odds_dataset,
    build_player_base,
    build_player_dataset,
    build_shot_dataset,
    build_transfermarkt_datasets,
    enrich_matches_espn,
    enrich_players_espn,
)
from ml_in_sports.utils.database import FootballDatabase


@pytest.fixture
def mock_understat_matches() -> pd.DataFrame:
    """Fake merged Understat matches DataFrame."""
    index = pd.MultiIndex.from_tuples(
        [("ENG-Premier League", "2324", "2024-01-01 Arsenal-Chelsea")],
        names=["league", "season", "game"],
    )
    return pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "home_goals": [2],
            "away_goals": [1],
            "home_xg": [1.8],
            "away_xg": [0.9],
            "home_ppda": [10.5],
            "away_ppda": [8.3],
        },
        index=index,
    )


class TestGetSeasonStart:
    """Tests for season start date lookup."""

    def test_known_season(self) -> None:
        """Known season returns mapped date."""
        assert _get_season_start("2324") == "2023-08-01"

    def test_unknown_season_fallback(self) -> None:
        """Unknown season generates date from code."""
        assert _get_season_start("9900") == "2099-08-01"


class TestAddEloToMatches:
    """Tests for Elo enrichment."""

    def test_adds_elo_columns(self) -> None:
        """Adds home_elo and away_elo based on team names."""
        matches = pd.DataFrame({
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
        })
        elo_df = pd.DataFrame(
            {"elo": [1900.0, 1850.0]},
            index=pd.Index(["Arsenal", "Chelsea"], name="team"),
        )
        result = _add_elo_to_matches(matches, elo_df)
        assert result["home_elo"].iloc[0] == 1900.0
        assert result["away_elo"].iloc[0] == 1850.0

    def test_missing_team_gets_none(self) -> None:
        """Team not in Elo data gets None."""
        matches = pd.DataFrame({
            "home_team": ["Unknown FC"],
            "away_team": ["Chelsea"],
        })
        elo_df = pd.DataFrame(
            {"elo": [1850.0]},
            index=pd.Index(["Chelsea"], name="team"),
        )
        result = _add_elo_to_matches(matches, elo_df)
        assert pd.isna(result["home_elo"].iloc[0])
        assert result["away_elo"].iloc[0] == 1850.0

    def test_normalizes_clubelo_names(self) -> None:
        """ClubElo names like 'ManCity' map to canonical names."""
        matches = pd.DataFrame({
            "home_team": ["Manchester City"],
            "away_team": ["Manchester United"],
        })
        elo_df = pd.DataFrame(
            {"elo": [2050.0, 1900.0]},
            index=pd.Index(["ManCity", "ManUnited"], name="team"),
        )
        result = _add_elo_to_matches(matches, elo_df)
        assert result["home_elo"].iloc[0] == 2050.0
        assert result["away_elo"].iloc[0] == 1900.0

    def test_normalizes_multi_league_clubelo_names(self) -> None:
        """ClubElo names across leagues all resolve correctly."""
        matches = pd.DataFrame({
            "home_team": [
                "West Ham United",
                "Atletico Madrid",
                "Borussia Monchengladbach",
                "Paris Saint Germain",
            ],
            "away_team": [
                "Nottingham Forest",
                "Real Sociedad",
                "FC Koln",
                "Saint-Etienne",
            ],
        })
        elo_df = pd.DataFrame(
            {"elo": [
                1700.0, 1650.0, 1850.0, 1750.0,
                1680.0, 1550.0, 2100.0, 1500.0,
            ]},
            index=pd.Index([
                "WestHam", "NottmForest", "Atletico", "RealSociedad",
                "Gladbach", "Koeln", "PSG", "St-Etienne",
            ], name="team"),
        )
        result = _add_elo_to_matches(matches, elo_df)
        assert result["home_elo"].iloc[0] == 1700.0
        assert result["away_elo"].iloc[0] == 1650.0
        assert result["home_elo"].iloc[1] == 1850.0
        assert result["away_elo"].iloc[1] == 1750.0
        assert result["home_elo"].iloc[2] == 1680.0
        assert result["away_elo"].iloc[2] == 1550.0
        assert result["home_elo"].iloc[3] == 2100.0
        assert result["away_elo"].iloc[3] == 1500.0


class TestBackfillEloRatings:
    """Tests for backfill_elo_ratings."""

    def test_backfills_elo_from_db(self, db: FootballDatabase) -> None:
        """Backfill updates matches with Elo from elo_ratings table."""
        matches = pd.DataFrame({
            "league": ["ENG-Premier League"],
            "season": ["2324"],
            "game": ["2024-01-01 Arsenal-Chelsea"],
            "date": ["2024-01-01"],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "home_goals": [2],
            "away_goals": [1],
        })
        db.upsert_dataframe("matches", matches)

        elo = pd.DataFrame({
            "team": ["Arsenal", "Chelsea"],
            "date": ["2023-08-01", "2023-08-01"],
            "elo": [1900.0, 1850.0],
        })
        db.upsert_dataframe("elo_ratings", elo)

        backfill_elo_ratings(db=db)

        result = db.read_table("matches")
        assert result.iloc[0]["home_elo"] == 1900.0
        assert result.iloc[0]["away_elo"] == 1850.0

    def test_backfills_with_clubelo_names(
        self, db: FootballDatabase,
    ) -> None:
        """Backfill normalizes ClubElo names in elo_ratings table."""
        matches = pd.DataFrame({
            "league": ["ENG-Premier League"],
            "season": ["2324"],
            "game": ["2024-01-01 Manchester City-West Ham United"],
            "date": ["2024-01-01"],
            "home_team": ["Manchester City"],
            "away_team": ["West Ham United"],
            "home_goals": [3],
            "away_goals": [1],
        })
        db.upsert_dataframe("matches", matches)

        elo = pd.DataFrame({
            "team": ["ManCity", "WestHam"],
            "date": ["2023-08-01", "2023-08-01"],
            "elo": [2050.0, 1700.0],
        })
        db.upsert_dataframe("elo_ratings", elo)

        backfill_elo_ratings(db=db)

        result = db.read_table("matches")
        assert result.iloc[0]["home_elo"] == 2050.0
        assert result.iloc[0]["away_elo"] == 1700.0


class TestBuildMatchBase:
    """Tests for build_match_base (fast pass, no ESPN)."""

    @patch("ml_in_sports.processing.pipeline.ClubEloExtractor")
    @patch("ml_in_sports.processing.pipeline.SofascoreExtractor")
    @patch("ml_in_sports.processing.pipeline.UnderstatExtractor")
    def test_builds_base_from_understat(
        self,
        mock_understat_cls: MagicMock,
        mock_sofascore_cls: MagicMock,
        mock_elo_cls: MagicMock,
        mock_understat_matches: pd.DataFrame,
        db: FootballDatabase,
    ) -> None:
        """Builds base dataset without ESPN."""
        mock_understat = MagicMock()
        mock_understat.extract_matches.return_value = mock_understat_matches
        mock_understat_cls.return_value = mock_understat

        mock_sofascore = MagicMock()
        mock_sofascore.extract_matches.return_value = None
        mock_sofascore.extract_league_table.return_value = None
        mock_sofascore_cls.return_value = mock_sofascore

        mock_elo = MagicMock()
        mock_elo.extract_ratings.return_value = None
        mock_elo_cls.return_value = mock_elo

        result = build_match_base("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert len(result) == 1
        assert "home_xg" in result.columns
        assert "source_updated_at" in result.columns

    @patch("ml_in_sports.processing.pipeline.ClubEloExtractor")
    @patch("ml_in_sports.processing.pipeline.SofascoreExtractor")
    @patch("ml_in_sports.processing.pipeline.UnderstatExtractor")
    def test_stores_to_database(
        self,
        mock_understat_cls: MagicMock,
        mock_sofascore_cls: MagicMock,
        mock_elo_cls: MagicMock,
        mock_understat_matches: pd.DataFrame,
        db: FootballDatabase,
    ) -> None:
        """Stores result in the database."""
        mock_understat = MagicMock()
        mock_understat.extract_matches.return_value = mock_understat_matches
        mock_understat_cls.return_value = mock_understat

        mock_sofascore_cls.return_value = MagicMock(
            extract_matches=MagicMock(return_value=None),
            extract_league_table=MagicMock(return_value=None),
        )
        mock_elo_cls.return_value = MagicMock(
            extract_ratings=MagicMock(return_value=None),
        )

        build_match_base("ENG-Premier League", "2324", db=db)

        stored = db.read_table("matches")
        assert len(stored) == 1
        assert stored.iloc[0]["home_xg"] == 1.8

    @patch("ml_in_sports.processing.pipeline.ClubEloExtractor")
    @patch("ml_in_sports.processing.pipeline.SofascoreExtractor")
    @patch("ml_in_sports.processing.pipeline.UnderstatExtractor")
    def test_returns_cached_on_second_run(
        self,
        mock_understat_cls: MagicMock,
        mock_sofascore_cls: MagicMock,
        mock_elo_cls: MagicMock,
        mock_understat_matches: pd.DataFrame,
        db: FootballDatabase,
    ) -> None:
        """Second run loads from DB instead of re-scraping."""
        mock_understat = MagicMock()
        mock_understat.extract_matches.return_value = mock_understat_matches
        mock_understat_cls.return_value = mock_understat

        mock_sofascore_cls.return_value = MagicMock(
            extract_matches=MagicMock(return_value=None),
            extract_league_table=MagicMock(return_value=None),
        )
        mock_elo_cls.return_value = MagicMock(
            extract_ratings=MagicMock(return_value=None),
        )

        build_match_base("ENG-Premier League", "2324", db=db)
        result = build_match_base("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert len(result) == 1


class TestEnrichMatchesEspn:
    """Tests for enrich_matches_espn (slow pass)."""

    @patch("ml_in_sports.processing.pipeline.EspnExtractor")
    def test_enriches_existing_matches(
        self,
        mock_espn_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Merges ESPN data into existing match rows."""
        # Pre-populate DB with base match
        base = pd.DataFrame({
            "league": ["ENG-Premier League"],
            "season": ["2324"],
            "game": ["2024-01-01 Arsenal-Chelsea"],
            "date": ["2024-01-01"],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "home_xg": [1.8],
            "away_xg": [0.9],
        })
        db.upsert_dataframe("matches", base)

        # Mock ESPN data
        espn_index = pd.MultiIndex.from_tuples(
            [("ENG-Premier League", "2324", "2024-01-01 Arsenal-Chelsea")],
            names=["league", "season", "game"],
        )
        espn_df = pd.DataFrame(
            {"home_possession_pct": [62.0], "away_possession_pct": [38.0]},
            index=espn_index,
        )
        mock_espn = MagicMock()
        mock_espn.extract_matches.return_value = espn_df
        mock_espn_cls.return_value = mock_espn

        result = enrich_matches_espn("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert "home_possession" in result.columns
        assert result.iloc[0]["home_possession"] == 62.0

    @patch("ml_in_sports.processing.pipeline.EspnExtractor")
    def test_returns_none_when_no_base_data(
        self,
        mock_espn_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Returns None if no base matches exist in DB."""
        espn_index = pd.MultiIndex.from_tuples(
            [("ENG-Premier League", "2324", "2024-01-01 Arsenal-Chelsea")],
            names=["league", "season", "game"],
        )
        mock_espn = MagicMock()
        mock_espn.extract_matches.return_value = pd.DataFrame(
            {"home_possession_pct": [62.0]}, index=espn_index,
        )
        mock_espn_cls.return_value = mock_espn

        result = enrich_matches_espn("ENG-Premier League", "2324", db=db)
        assert result is None


class TestBuildMatchDataset:
    """Tests for build_match_dataset wrapper."""

    @patch("ml_in_sports.processing.pipeline.EspnExtractor")
    @patch("ml_in_sports.processing.pipeline.ClubEloExtractor")
    @patch("ml_in_sports.processing.pipeline.SofascoreExtractor")
    @patch("ml_in_sports.processing.pipeline.UnderstatExtractor")
    def test_wrapper_calls_base_and_espn(
        self,
        mock_understat_cls: MagicMock,
        mock_sofascore_cls: MagicMock,
        mock_elo_cls: MagicMock,
        mock_espn_cls: MagicMock,
        mock_understat_matches: pd.DataFrame,
        db: FootballDatabase,
    ) -> None:
        """Wrapper builds base + enriches with ESPN."""
        mock_understat = MagicMock()
        mock_understat.extract_matches.return_value = mock_understat_matches
        mock_understat_cls.return_value = mock_understat

        mock_sofascore_cls.return_value = MagicMock(
            extract_matches=MagicMock(return_value=None),
            extract_league_table=MagicMock(return_value=None),
        )
        mock_elo_cls.return_value = MagicMock(
            extract_ratings=MagicMock(return_value=None),
        )
        mock_espn_cls.return_value = MagicMock(
            extract_matches=MagicMock(return_value=None),
        )

        result = build_match_dataset("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert len(result) == 1
        assert "home_xg" in result.columns


class TestBuildPlayerBase:
    """Tests for build_player_base."""

    @patch("ml_in_sports.processing.pipeline.UnderstatExtractor")
    def test_builds_player_base(
        self,
        mock_understat_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Builds player base from Understat."""
        player_df = pd.DataFrame({
            "league": ["ENG-Premier League"],
            "season": ["2324"],
            "game": ["2024-01-01 Arsenal-Chelsea"],
            "team": ["Arsenal"],
            "player": ["Saka"],
            "minutes": [90],
            "goals": [1],
            "xg": [0.45],
        })
        player_df = player_df.set_index(["league", "season", "game"])

        mock_understat = MagicMock()
        mock_understat.extract_player_matches.return_value = player_df
        mock_understat_cls.return_value = mock_understat

        result = build_player_base("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert len(result) == 1

        stored = db.read_table("player_matches")
        assert len(stored) == 1


class TestEnrichPlayersEspn:
    """Tests for enrich_players_espn."""

    @patch("ml_in_sports.processing.pipeline.EspnExtractor")
    def test_enriches_existing_players(
        self,
        mock_espn_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Merges ESPN lineup data into existing player rows."""
        base = pd.DataFrame({
            "league": ["ENG-Premier League"],
            "season": ["2324"],
            "game": ["2024-01-01 Arsenal-Chelsea"],
            "team": ["Arsenal"],
            "player": ["Saka"],
            "minutes": [90],
            "xg": [0.45],
        })
        db.upsert_dataframe("player_matches", base)

        espn_index = pd.MultiIndex.from_tuples(
            [("ENG-Premier League", "2324",
              "2024-01-01 Arsenal-Chelsea", "Arsenal", "Saka")],
            names=["league", "season", "game", "team", "player"],
        )
        espn_df = pd.DataFrame(
            {"yellow_cards": [1], "goal_assists": [0], "is_home": [True]},
            index=espn_index,
        )
        mock_espn = MagicMock()
        mock_espn.extract_player_matches.return_value = espn_df
        mock_espn_cls.return_value = mock_espn

        result = enrich_players_espn("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert "yellow_cards" in result.columns


class TestBuildPlayerDataset:
    """Tests for build_player_dataset wrapper."""

    @patch("ml_in_sports.processing.pipeline.EspnExtractor")
    @patch("ml_in_sports.processing.pipeline.UnderstatExtractor")
    def test_builds_player_dataset(
        self,
        mock_understat_cls: MagicMock,
        mock_espn_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Wrapper builds base + enriches with ESPN."""
        player_df = pd.DataFrame({
            "league": ["ENG-Premier League"],
            "season": ["2324"],
            "game": ["2024-01-01 Arsenal-Chelsea"],
            "team": ["Arsenal"],
            "player": ["Saka"],
            "minutes": [90],
            "goals": [1],
            "xg": [0.45],
        })
        player_df = player_df.set_index(["league", "season", "game"])

        mock_understat = MagicMock()
        mock_understat.extract_player_matches.return_value = player_df
        mock_understat_cls.return_value = mock_understat

        mock_espn_cls.return_value = MagicMock(
            extract_player_matches=MagicMock(return_value=None),
        )

        result = build_player_dataset("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert len(result) == 1

        stored = db.read_table("player_matches")
        assert len(stored) == 1


class TestBuildShotDataset:
    """Tests for build_shot_dataset."""

    @pytest.fixture
    def mock_shot_df(self) -> pd.DataFrame:
        """Fake shot events DataFrame matching soccerdata output."""
        index = pd.MultiIndex.from_tuples(
            [
                ("ENG-Premier League", "2324",
                 "2024-01-01 Arsenal-Chelsea", "Arsenal", "Saka"),
                ("ENG-Premier League", "2324",
                 "2024-01-01 Arsenal-Chelsea", "Arsenal", "Saka"),
            ],
            names=["league", "season", "game", "team", "player"],
        )
        return pd.DataFrame(
            {
                "shot_id": [100001, 100002],
                "date": ["2024-01-01", "2024-01-01"],
                "xg": [0.12, 0.45],
                "location_x": [0.85, 0.92],
                "location_y": [0.45, 0.51],
                "minute": [23, 67],
                "body_part": ["Right Foot", "Left Foot"],
                "situation": ["Open Play", "Set Piece"],
                "result": ["Saved Shot", "Goal"],
                "assist_player": ["Odegaard", "Rice"],
                "player_id": [1234, 1234],
                "assist_player_id": [5678, 9012],
                "game_id": [22275, 22275],
                "team_id": [92, 92],
                "league_id": ["1", "1"],
                "season_id": [2023, 2023],
            },
            index=index,
        )

    @patch("ml_in_sports.processing.pipeline.UnderstatExtractor")
    def test_builds_shot_dataset(
        self,
        mock_understat_cls: MagicMock,
        mock_shot_df: pd.DataFrame,
        db: FootballDatabase,
    ) -> None:
        """Stores shot data in database."""
        mock_understat = MagicMock()
        mock_understat.extract_shots.return_value = mock_shot_df
        mock_understat_cls.return_value = mock_understat

        result = build_shot_dataset("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert len(result) == 2

        stored = db.read_table("shots")
        assert len(stored) == 2
        assert stored.iloc[0]["xg"] == 0.12
        assert stored.iloc[1]["result"] == "Goal"

    @patch("ml_in_sports.processing.pipeline.UnderstatExtractor")
    def test_returns_cached_on_second_run(
        self,
        mock_understat_cls: MagicMock,
        mock_shot_df: pd.DataFrame,
        db: FootballDatabase,
    ) -> None:
        """Second run loads from DB instead of re-scraping."""
        mock_understat = MagicMock()
        mock_understat.extract_shots.return_value = mock_shot_df
        mock_understat_cls.return_value = mock_understat

        build_shot_dataset("ENG-Premier League", "2324", db=db)
        result = build_shot_dataset("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert len(result) == 2

    @patch("ml_in_sports.processing.pipeline.UnderstatExtractor")
    def test_returns_none_on_failure(
        self,
        mock_understat_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Returns None when extraction fails and no cached data."""
        mock_understat = MagicMock()
        mock_understat.extract_shots.return_value = None
        mock_understat_cls.return_value = mock_understat

        result = build_shot_dataset("ENG-Premier League", "2324", db=db)
        assert result is None


class TestBuildOddsDataset:
    """Tests for build_odds_dataset."""

    @patch("ml_in_sports.processing.pipeline.FootballDataExtractor")
    def test_stores_odds_in_database(
        self,
        mock_fd_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Downloads and stores betting odds."""
        odds_df = pd.DataFrame({
            "league": ["ENG-Premier League"],
            "season": ["2324"],
            "game": ["2023-08-11 Manchester City-Burnley"],
            "date": ["2023-08-11"],
            "home_team": ["Manchester City"],
            "away_team": ["Burnley"],
            "ft_home_goals": [3],
            "ft_away_goals": [0],
            "ft_result": ["H"],
            "b365_home": [1.33],
            "b365_draw": [5.5],
            "b365_away": [8.0],
            "avg_home": [1.35],
            "avg_draw": [5.35],
            "avg_away": [9.02],
            "home_corners": [5],
            "away_corners": [6],
        })

        mock_fd = MagicMock()
        mock_fd.extract_odds.return_value = odds_df
        mock_fd_cls.return_value = mock_fd

        result = build_odds_dataset("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert len(result) == 1

        stored = db.read_table("match_odds")
        assert len(stored) == 1
        assert stored.iloc[0]["b365_home"] == 1.33
        assert stored.iloc[0]["home_corners"] == 5

    @patch("ml_in_sports.processing.pipeline.FootballDataExtractor")
    def test_returns_cached_on_second_run(
        self,
        mock_fd_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Second run loads from DB."""
        odds_df = pd.DataFrame({
            "league": ["ENG-Premier League"],
            "season": ["2324"],
            "game": ["2023-08-11 Manchester City-Burnley"],
            "date": ["2023-08-11"],
            "home_team": ["Manchester City"],
            "away_team": ["Burnley"],
            "b365_home": [1.33],
        })

        mock_fd = MagicMock()
        mock_fd.extract_odds.return_value = odds_df
        mock_fd_cls.return_value = mock_fd

        build_odds_dataset("ENG-Premier League", "2324", db=db)
        result = build_odds_dataset("ENG-Premier League", "2324", db=db)

        assert result is not None
        assert len(result) == 1


class TestBuildTransfermarktDatasets:
    """Tests for build_transfermarkt_datasets."""

    @patch("ml_in_sports.processing.pipeline.TransfermarktExtractor")
    def test_stores_all_three_tables(
        self,
        mock_tm_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Downloads and stores players, valuations, games."""
        mock_tm = MagicMock()
        mock_tm.extract_players.return_value = pd.DataFrame({
            "player_id": [12345],
            "name": ["Saka"],
            "position": ["Attack"],
            "foot": ["Left"],
            "height_in_cm": [178.0],
            "current_club_name": ["Arsenal"],
            "market_value_in_eur": [120000000],
        })
        mock_tm.extract_player_valuations.return_value = pd.DataFrame({
            "player_id": [12345],
            "date": ["2024-06-01"],
            "market_value_in_eur": [120000000],
            "current_club_name": ["Arsenal"],
        })
        mock_tm.extract_games.return_value = pd.DataFrame({
            "game_id": [99001],
            "competition_id": ["GB1"],
            "season": ["2023"],
            "date": ["2024-01-01"],
            "home_club_name": ["Arsenal"],
            "away_club_name": ["Chelsea"],
            "home_club_goals": [2],
            "away_club_goals": [1],
            "referee": ["M Oliver"],
            "home_club_formation": ["4-3-3"],
            "home_club_manager_name": ["M Arteta"],
        })
        mock_tm_cls.return_value = mock_tm

        results = build_transfermarkt_datasets(db=db)

        assert results["players"] is not None
        assert results["valuations"] is not None
        assert results["games"] is not None

        assert len(db.read_table("tm_players")) == 1
        assert len(db.read_table("tm_player_valuations")) == 1
        assert len(db.read_table("tm_games")) == 1

        players = db.read_table("tm_players")
        assert players.iloc[0]["name"] == "Saka"
        assert players.iloc[0]["market_value_in_eur"] == 120000000


class TestBuildFifaRatings:
    """Tests for build_fifa_ratings."""

    @patch("ml_in_sports.processing.pipeline.FifaRatingsExtractor")
    def test_stores_individual_version(
        self,
        mock_fifa_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Loads and stores a single FIFA version from individual file."""
        ratings_df = pd.DataFrame({
            "player_name": ["Saka"],
            "long_name": ["Bukayo Saka"],
            "age": [22],
            "nationality": ["England"],
            "club_name": ["Arsenal"],
            "league_name": ["Premier League"],
            "overall": [86],
            "potential": [92],
            "pace": [85],
            "shooting": [78],
            "passing": [80],
            "dribbling": [87],
            "defending": [55],
            "physic": [68],
            "fifa_version": ["25"],
        })

        mock_fifa = MagicMock()
        mock_fifa.extract_combined_ratings.return_value = {}
        mock_fifa.extract_ratings.return_value = ratings_df
        mock_fifa_cls.return_value = mock_fifa

        results = build_fifa_ratings(db=db, versions=["25"])

        assert results["25"] is not None
        assert len(results["25"]) == 1

        stored = db.read_table("fifa_ratings")
        assert len(stored) == 1
        assert stored.iloc[0]["player_name"] == "Saka"
        assert stored.iloc[0]["overall"] == 86

    @patch("ml_in_sports.processing.pipeline.FifaRatingsExtractor")
    def test_stores_combined_versions(
        self,
        mock_fifa_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Loads multiple versions from combined file."""
        mock_fifa = MagicMock()
        mock_fifa.extract_combined_ratings.return_value = {
            "23": pd.DataFrame({
                "player_name": ["Salah"],
                "club_name": ["Liverpool"],
                "league_name": ["Premier League"],
                "overall": [90],
                "fifa_version": ["23"],
            }),
            "24": pd.DataFrame({
                "player_name": ["Salah"],
                "club_name": ["Liverpool"],
                "league_name": ["Premier League"],
                "overall": [89],
                "fifa_version": ["24"],
            }),
        }
        mock_fifa.extract_ratings.return_value = None
        mock_fifa_cls.return_value = mock_fifa

        results = build_fifa_ratings(db=db, versions=["23", "24"])

        assert results["23"] is not None
        assert results["24"] is not None

        stored = db.read_table("fifa_ratings")
        assert len(stored) == 2


class TestBuildOddsDatasetMultiLeague:
    """Tests for build_odds_dataset with different leagues."""

    @patch("ml_in_sports.processing.pipeline.FootballDataExtractor")
    def test_la_liga_odds_use_correct_league(
        self,
        mock_fd_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """La Liga odds dataset uses ESP-La Liga label."""
        odds_df = pd.DataFrame({
            "league": ["ESP-La Liga"],
            "season": ["2324"],
            "game": ["2023-08-13 Barcelona-Getafe"],
            "date": ["2023-08-13"],
            "home_team": ["Barcelona"],
            "away_team": ["Getafe"],
            "b365_home": [1.22],
        })

        mock_fd = MagicMock()
        mock_fd.extract_odds.return_value = odds_df
        mock_fd_cls.return_value = mock_fd

        result = build_odds_dataset("ESP-La Liga", "2324", db=db)

        assert result is not None
        assert result.iloc[0]["league"] == "ESP-La Liga"
        mock_fd_cls.assert_called_once_with(league="ESP-La Liga")


class TestBuildTransfermarktMultiLeague:
    """Tests for build_transfermarkt_datasets with league parameter."""

    @patch("ml_in_sports.processing.pipeline.TransfermarktExtractor")
    def test_la_liga_uses_es1_competition_id(
        self,
        mock_tm_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """La Liga downloads use ES1 competition ID."""
        mock_tm = MagicMock()
        mock_tm.extract_players.return_value = pd.DataFrame({
            "player_id": [99],
            "name": ["Pedri"],
            "position": ["Midfield"],
        })
        mock_tm.extract_player_valuations.return_value = None
        mock_tm.extract_games.return_value = None
        mock_tm_cls.return_value = mock_tm

        results = build_transfermarkt_datasets(
            league="ESP-La Liga", db=db,
        )

        assert results["players"] is not None
        mock_tm_cls.assert_called_once_with(competition_id="ES1")

    @patch("ml_in_sports.processing.pipeline.TransfermarktExtractor")
    def test_default_league_is_epl(
        self,
        mock_tm_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Default league parameter is EPL."""
        mock_tm = MagicMock()
        mock_tm.extract_players.return_value = None
        mock_tm.extract_player_valuations.return_value = None
        mock_tm.extract_games.return_value = None
        mock_tm_cls.return_value = mock_tm

        build_transfermarkt_datasets(db=db)

        mock_tm_cls.assert_called_once_with(competition_id="GB1")


class TestBuildFifaRatingsMultiLeague:
    """Tests for build_fifa_ratings with multi-league support."""

    @patch("ml_in_sports.processing.pipeline.FifaRatingsExtractor")
    def test_multi_league_passes_filters(
        self,
        mock_fifa_cls: MagicMock,
        db: FootballDatabase,
    ) -> None:
        """Multiple leagues pass correct filters to extractor."""
        mock_fifa = MagicMock()
        mock_fifa.extract_combined_ratings.return_value = {}
        mock_fifa.extract_ratings.return_value = None
        mock_fifa_cls.return_value = mock_fifa

        build_fifa_ratings(
            db=db,
            versions=["25"],
            leagues=["ENG-Premier League", "ESP-La Liga"],
        )

        mock_fifa_cls.assert_called_once_with(
            league_filters=[
                "Premier League",
                "Spain Primera Division|La Liga|LALIGA",
            ],
        )


class TestBuildFifaLeagueFilters:
    """Tests for _build_fifa_league_filters helper."""

    def test_single_league(self) -> None:
        """Single league returns one filter."""
        result = _build_fifa_league_filters(["ENG-Premier League"])
        assert result == ["Premier League"]

    def test_multiple_leagues(self) -> None:
        """Multiple leagues return multiple filters."""
        result = _build_fifa_league_filters([
            "ENG-Premier League", "GER-Bundesliga",
        ])
        assert result == [
            "Premier League",
            "German 1. Bundesliga|^Bundesliga$",
        ]

    def test_unknown_league_skipped(self) -> None:
        """Unknown league identifier is skipped."""
        result = _build_fifa_league_filters(["UNKNOWN"])
        assert result == []


class TestBuildFifaScrapeLabel:
    """Tests for _build_fifa_scrape_label helper."""

    def test_epl_only(self) -> None:
        """EPL-only returns 'EPL'."""
        assert _build_fifa_scrape_label(["ENG-Premier League"]) == "EPL"

    def test_all_leagues(self) -> None:
        """All 5 leagues returns 'ALL'."""
        from ml_in_sports.processing.extractors import ALL_LEAGUES
        assert _build_fifa_scrape_label(list(ALL_LEAGUES)) == "ALL"

    def test_partial_leagues(self) -> None:
        """Partial league set returns sorted join."""
        result = _build_fifa_scrape_label([
            "ESP-La Liga", "ENG-Premier League",
        ])
        assert result == "ENG-Premier League+ESP-La Liga"


class TestParseGameKey:
    """Tests for _parse_game_key."""

    def test_valid_game_key(self) -> None:
        """Parse standard game key."""
        result = _parse_game_key("2024-01-15 Arsenal-Chelsea")
        assert result == ("2024-01-15", "Arsenal-Chelsea")

    def test_team_with_hyphen(self) -> None:
        """Parse game key where team has no hyphen ambiguity."""
        result = _parse_game_key("2024-01-15 West Ham-Liverpool")
        assert result == ("2024-01-15", "West Ham-Liverpool")

    def test_invalid_format(self) -> None:
        """Return None for non-matching format."""
        assert _parse_game_key("invalid") is None


class TestAlignEspnDates:
    """Tests for _align_espn_dates."""

    def test_exact_match_unchanged(self) -> None:
        """Dates that already match are not changed."""
        existing = pd.DataFrame({
            "game": ["2024-01-15 Arsenal-Chelsea"],
        })
        espn = pd.DataFrame({
            "game": ["2024-01-15 Arsenal-Chelsea"],
            "home_possession": [55.0],
        })
        result = _align_espn_dates(existing, espn)
        assert result["game"].iloc[0] == "2024-01-15 Arsenal-Chelsea"

    def test_date_plus_one_day(self) -> None:
        """ESPN date 1 day ahead is corrected."""
        existing = pd.DataFrame({
            "game": ["2024-01-15 Arsenal-Chelsea"],
        })
        espn = pd.DataFrame({
            "game": ["2024-01-16 Arsenal-Chelsea"],
            "home_possession": [55.0],
        })
        result = _align_espn_dates(existing, espn)
        assert result["game"].iloc[0] == "2024-01-15 Arsenal-Chelsea"

    def test_date_minus_one_day(self) -> None:
        """ESPN date 1 day behind is corrected."""
        existing = pd.DataFrame({
            "game": ["2024-01-15 Arsenal-Chelsea"],
        })
        espn = pd.DataFrame({
            "game": ["2024-01-14 Arsenal-Chelsea"],
            "home_possession": [55.0],
        })
        result = _align_espn_dates(existing, espn)
        assert result["game"].iloc[0] == "2024-01-15 Arsenal-Chelsea"

    def test_rescheduled_fixture_single_candidate(self) -> None:
        """ESPN date >1 day off with single candidate is corrected."""
        existing = pd.DataFrame({
            "game": ["2024-01-15 Arsenal-Chelsea"],
        })
        espn = pd.DataFrame({
            "game": ["2024-01-17 Arsenal-Chelsea"],
            "home_possession": [55.0],
        })
        result = _align_espn_dates(existing, espn)
        assert result["game"].iloc[0] == "2024-01-15 Arsenal-Chelsea"

    def test_rescheduled_fixture_ambiguous_not_fixed(self) -> None:
        """ESPN date >1 day off with 2 candidates is NOT corrected."""
        existing = pd.DataFrame({
            "game": [
                "2024-01-15 Arsenal-Chelsea",
                "2024-04-20 Arsenal-Chelsea",
            ],
        })
        espn = pd.DataFrame({
            "game": ["2024-01-17 Arsenal-Chelsea"],
            "home_possession": [55.0],
        })
        result = _align_espn_dates(existing, espn)
        assert result["game"].iloc[0] == "2024-01-17 Arsenal-Chelsea"

    def test_different_teams_not_matched(self) -> None:
        """Different team pairing is not cross-matched."""
        existing = pd.DataFrame({
            "game": ["2024-01-15 Arsenal-Chelsea"],
        })
        espn = pd.DataFrame({
            "game": ["2024-01-16 Arsenal-Liverpool"],
            "home_possession": [55.0],
        })
        result = _align_espn_dates(existing, espn)
        assert result["game"].iloc[0] == "2024-01-16 Arsenal-Liverpool"

    def test_does_not_mutate_input(self) -> None:
        """Input DataFrame is not modified."""
        existing = pd.DataFrame({
            "game": ["2024-01-15 Arsenal-Chelsea"],
        })
        espn = pd.DataFrame({
            "game": ["2024-01-16 Arsenal-Chelsea"],
            "home_possession": [55.0],
        })
        original_game = espn["game"].iloc[0]
        _align_espn_dates(existing, espn)
        assert espn["game"].iloc[0] == original_game


class TestNormalizeGameKey:
    """Tests for _normalize_game_key."""

    def test_simple_alias(self) -> None:
        """ESPN alias in away position is resolved."""
        result = _normalize_game_key(
            "2015-08-14 Bayern Munich-Hamburg SV",
        )
        assert result == "2015-08-14 Bayern Munich-Hamburger SV"

    def test_already_canonical(self) -> None:
        """Key with canonical names is unchanged."""
        key = "2024-01-15 Arsenal-Chelsea"
        assert _normalize_game_key(key) == key

    def test_hyphenated_away_team(self) -> None:
        """Away team with hyphen (Saint-Etienne) is handled."""
        result = _normalize_game_key(
            "2017-08-12 Lille-Saint-\u00c9tienne",
        )
        assert result == "2017-08-12 Lille-Saint-Etienne"

    def test_hyphenated_home_team(self) -> None:
        """Home team with hyphen is handled."""
        result = _normalize_game_key(
            "2017-08-12 Saint-\u00c9tienne-Lille",
        )
        assert result == "2017-08-12 Saint-Etienne-Lille"

    def test_psg_away(self) -> None:
        """PSG away (Paris Saint-Germain) is handled."""
        result = _normalize_game_key(
            "2017-08-12 Lyon-Paris Saint-Germain",
        )
        assert result == "2017-08-12 Lyon-Paris Saint Germain"

    def test_both_hyphenated(self) -> None:
        """Both teams have hyphens — best split wins."""
        result = _normalize_game_key(
            "2017-08-12 Saint-\u00c9tienne-Paris Saint-Germain",
        )
        assert "Saint-Etienne" in result
        assert "Paris Saint Germain" in result

    def test_no_hyphen(self) -> None:
        """Game key without hyphen separator is returned as-is."""
        key = "2024-01-15 Arsenal"
        assert _normalize_game_key(key) == key

    def test_invalid_format(self) -> None:
        """Non-matching key is returned as-is."""
        key = "not a game key"
        assert _normalize_game_key(key) == key

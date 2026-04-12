"""Tests for team name normalization."""

from ml_in_sports.utils.team_names import (
    ALL_KNOWN_TEAMS,
    find_unmapped_names,
    normalize_team_name,
)


class TestNormalizeTeamName:
    """Tests for normalize_team_name function."""

    def test_alias_maps_to_canonical(self) -> None:
        """Alias 'Bournemouth' maps to 'AFC Bournemouth'."""
        assert normalize_team_name("Bournemouth") == "AFC Bournemouth"

    def test_canonical_passes_through(self) -> None:
        """Canonical name 'Arsenal' returns unchanged."""
        assert normalize_team_name("Arsenal") == "Arsenal"

    def test_unknown_name_passes_through(self) -> None:
        """Unknown name returns unchanged."""
        assert normalize_team_name("Unknown FC") == "Unknown FC"

    def test_brighton_alias(self) -> None:
        """'Brighton' maps to 'Brighton & Hove Albion'."""
        assert normalize_team_name("Brighton") == "Brighton & Hove Albion"

    def test_luton_alias(self) -> None:
        """'Luton' maps to 'Luton Town'."""
        assert normalize_team_name("Luton") == "Luton Town"

    def test_tottenham_alias(self) -> None:
        """'Tottenham' maps to 'Tottenham Hotspur'."""
        assert normalize_team_name("Tottenham") == "Tottenham Hotspur"

    def test_west_ham_alias(self) -> None:
        """'West Ham' maps to 'West Ham United'."""
        assert normalize_team_name("West Ham") == "West Ham United"

    def test_wolverhampton_alias(self) -> None:
        """'Wolverhampton' maps to 'Wolverhampton Wanderers'."""
        result = normalize_team_name("Wolverhampton")
        assert result == "Wolverhampton Wanderers"


class TestAllKnownTeams:
    """Tests for ALL_KNOWN_TEAMS set."""

    def test_is_frozenset(self) -> None:
        """ALL_KNOWN_TEAMS is immutable."""
        assert isinstance(ALL_KNOWN_TEAMS, frozenset)

    def test_contains_epl_teams(self) -> None:
        """Contains standard EPL team names."""
        assert "Arsenal" in ALL_KNOWN_TEAMS
        assert "AFC Bournemouth" in ALL_KNOWN_TEAMS
        assert "Liverpool" in ALL_KNOWN_TEAMS


class TestFindUnmappedNames:
    """Tests for find_unmapped_names function."""

    def test_all_mapped_returns_empty(self) -> None:
        """Known names return empty list."""
        names = ["Arsenal", "AFC Bournemouth", "Brighton"]
        assert find_unmapped_names(names) == []

    def test_unknown_names_returned(self) -> None:
        """Unknown names are returned."""
        names = ["Arsenal", "Fake FC"]
        assert find_unmapped_names(names) == ["Fake FC"]

    def test_epl_understat_names_all_mapped(self) -> None:
        """Understat EPL names are all either known or aliased."""
        understat_names = [
            "Arsenal", "Aston Villa", "Bournemouth", "Brentford",
            "Brighton", "Burnley", "Chelsea", "Crystal Palace",
            "Everton", "Fulham", "Liverpool", "Luton",
            "Manchester City", "Manchester United", "Newcastle United",
            "Nottingham Forest", "Sheffield United", "Tottenham",
            "West Ham", "Wolverhampton Wanderers",
        ]
        assert find_unmapped_names(understat_names) == []


class TestClubEloTeamNames:
    """Tests for ClubElo team name normalization."""

    def test_epl_clubelo_names(self) -> None:
        """ClubElo EPL names map to canonical names."""
        assert normalize_team_name("ManCity") == "Manchester City"
        assert normalize_team_name("ManUnited") == "Manchester United"
        assert normalize_team_name("NottmForest") == "Nottingham Forest"
        assert normalize_team_name("SheffieldUnited") == "Sheffield United"
        assert normalize_team_name("WestHam") == "West Ham United"
        assert normalize_team_name("WestBrom") == "West Bromwich Albion"

    def test_la_liga_clubelo_names(self) -> None:
        """ClubElo La Liga names map to canonical names."""
        assert normalize_team_name("Atletico") == "Atletico Madrid"
        assert normalize_team_name("AthBilbao") == "Athletic Bilbao"
        assert normalize_team_name("RealSociedad") == "Real Sociedad"
        assert normalize_team_name("RealBetis") == "Betis"
        assert normalize_team_name("LasPalmas") == "Las Palmas"
        assert normalize_team_name("RayoVallecano") == "Rayo Vallecano"
        assert normalize_team_name("LaCoruna") == "Deportivo La Coruna"

    def test_bundesliga_clubelo_names(self) -> None:
        """ClubElo Bundesliga names map to canonical names."""
        assert normalize_team_name("Gladbach") == "Borussia Monchengladbach"
        assert normalize_team_name("Koeln") == "FC Koln"
        assert normalize_team_name("GreutherFuerth") == "Greuther Furth"
        assert normalize_team_name("StPauli") == "St Pauli"
        assert normalize_team_name("UnionBerlin") == "Union Berlin"
        assert normalize_team_name("Duesseldorf") == "Fortuna Dusseldorf"
        assert normalize_team_name("HerthaBSC") == "Hertha Berlin"

    def test_ligue_1_clubelo_names(self) -> None:
        """ClubElo Ligue 1 names map to canonical names."""
        assert normalize_team_name("PSG") == "Paris Saint Germain"
        assert normalize_team_name("St-Etienne") == "Saint-Etienne"
        assert normalize_team_name("LeHavre") == "Le Havre"


class TestMultiLeagueTeamNames:
    """Tests for team name normalization across 5 leagues."""

    def test_la_liga_aliases(self) -> None:
        """La Liga football-data.co.uk aliases map correctly."""
        assert normalize_team_name("Ath Madrid") == "Atletico Madrid"
        assert normalize_team_name("Ath Bilbao") == "Athletic Bilbao"
        assert normalize_team_name("Sociedad") == "Real Sociedad"
        assert normalize_team_name("Vallecano") == "Rayo Vallecano"

    def test_bundesliga_aliases(self) -> None:
        """Bundesliga football-data.co.uk aliases map correctly."""
        assert normalize_team_name("Bayern") == "Bayern Munich"
        assert normalize_team_name("Dortmund") == "Borussia Dortmund"
        assert normalize_team_name("Leverkusen") == "Bayer Leverkusen"
        assert normalize_team_name("M'gladbach") == "Borussia Monchengladbach"
        assert normalize_team_name("Ein Frankfurt") == "Eintracht Frankfurt"

    def test_serie_a_aliases(self) -> None:
        """Serie A football-data.co.uk aliases map correctly."""
        assert normalize_team_name("Milan") == "AC Milan"
        assert normalize_team_name("Inter Milan") == "Inter"
        assert normalize_team_name("Roma") == "AS Roma"
        assert normalize_team_name("Hellas Verona") == "Verona"

    def test_ligue_1_aliases(self) -> None:
        """Ligue 1 football-data.co.uk aliases map correctly."""
        assert normalize_team_name("Paris SG") == "Paris Saint Germain"
        assert normalize_team_name("St Etienne") == "Saint-Etienne"

    def test_la_liga_teams_in_known_set(self) -> None:
        """Major La Liga teams are in ALL_KNOWN_TEAMS."""
        la_liga_teams = [
            "Barcelona", "Real Madrid", "Atletico Madrid",
            "Sevilla", "Betis", "Real Sociedad", "Villarreal",
        ]
        for team in la_liga_teams:
            assert team in ALL_KNOWN_TEAMS, f"{team} not in ALL_KNOWN_TEAMS"

    def test_bundesliga_teams_in_known_set(self) -> None:
        """Major Bundesliga teams are in ALL_KNOWN_TEAMS."""
        bundesliga_teams = [
            "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen",
            "RB Leipzig", "Eintracht Frankfurt", "VfB Stuttgart",
        ]
        for team in bundesliga_teams:
            assert team in ALL_KNOWN_TEAMS, f"{team} not in ALL_KNOWN_TEAMS"

    def test_serie_a_teams_in_known_set(self) -> None:
        """Major Serie A teams are in ALL_KNOWN_TEAMS."""
        serie_a_teams = [
            "AC Milan", "Inter", "Juventus", "Napoli",
            "AS Roma", "Lazio", "Atalanta", "Fiorentina",
        ]
        for team in serie_a_teams:
            assert team in ALL_KNOWN_TEAMS, f"{team} not in ALL_KNOWN_TEAMS"

    def test_ligue_1_teams_in_known_set(self) -> None:
        """Major Ligue 1 teams are in ALL_KNOWN_TEAMS."""
        ligue_1_teams = [
            "Paris Saint Germain", "Lyon", "Marseille",
            "Monaco", "Lille", "Lens", "Nice",
        ]
        for team in ligue_1_teams:
            assert team in ALL_KNOWN_TEAMS, f"{team} not in ALL_KNOWN_TEAMS"


class TestExtendedLeagueTeamNames:
    """Tests for R5a league aliases."""

    def test_championship_aliases(self) -> None:
        """Championship football-data.co.uk aliases map correctly."""
        assert normalize_team_name("Leeds") == "Leeds United"
        assert normalize_team_name("Nott'm Forest") == "Nottingham Forest"
        assert normalize_team_name("Sheffield Utd") == "Sheffield United"
        assert normalize_team_name("West Brom") == "West Bromwich Albion"
        assert normalize_team_name("Middlesboro") == "Middlesbrough"
        assert normalize_team_name("QPR") == "Queens Park Rangers"

    def test_eredivisie_aliases(self) -> None:
        """Eredivisie aliases map correctly."""
        assert normalize_team_name("Ajax") == "Ajax Amsterdam"
        assert normalize_team_name("PSV") == "PSV Eindhoven"
        assert normalize_team_name("AZ") == "AZ Alkmaar"
        assert normalize_team_name("Den Haag") == "ADO Den Haag"

    def test_ekstraklasa_aliases(self) -> None:
        """Ekstraklasa aliases map correctly."""
        assert normalize_team_name("Legia") == "Legia Warszawa"
        assert normalize_team_name("Lech") == "Lech Poznan"
        assert normalize_team_name("Cracovia") == "MKS Cracovia"
        assert normalize_team_name("Piast") == "Piast Gliwice"
        assert normalize_team_name("Wisla") == "Wisla Krakow"
        assert normalize_team_name("Gornik") == "Gornik Zabrze"

    def test_other_r5a_aliases(self) -> None:
        """Popular aliases from other R5a leagues map correctly."""
        assert normalize_team_name("Sporting Lisbon") == "Sp Lisbon"
        assert normalize_team_name("Brugge") == "Club Brugge"
        assert normalize_team_name("Fenerbahçe") == "Fenerbahce"
        assert normalize_team_name("Sparta Praha") == "Sparta Prague"

    def test_extended_teams_in_known_set(self) -> None:
        """Major extended-league teams are in ALL_KNOWN_TEAMS."""
        teams = [
            "Ajax Amsterdam", "PSV Eindhoven", "Legia Warszawa",
            "Lech Poznan", "Sp Lisbon", "Club Brugge",
            "Galatasaray", "Sparta Prague",
        ]
        for team in teams:
            assert team in ALL_KNOWN_TEAMS, f"{team} not in ALL_KNOWN_TEAMS"

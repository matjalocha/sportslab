"""Team name normalization across data sources.

Canonical names follow the longest/most official form
(e.g. "AFC Bournemouth" not "Bournemouth") to match ESPN,
which is the most verbose source.

soccerdata handles Understat/ESPN/Sofascore alignment via
config/teamname_replacements.json. This module handles
ClubElo and other external sources.
"""

import json
from importlib.resources import files
from typing import cast

import structlog

logger = structlog.get_logger(__name__)


def _load_replacements() -> dict[str, list[str]]:
    """Load team name replacements from package-data JSON.

    Returns:
        Dict mapping canonical name to list of aliases.
    """
    try:
        with (files("ml_in_sports.utils") / "team_name_replacements.json").open(
            "r", encoding="utf-8"
        ) as f:
            return cast(dict[str, list[str]], json.load(f))
    except FileNotFoundError:
        logger.warning("Replacements file not found (package data missing)")
        return {}


def _build_reverse_mapping(
    replacements: dict[str, list[str]],
) -> dict[str, str]:
    """Build alias-to-canonical lookup from replacements dict.

    Args:
        replacements: Canonical name -> list of aliases.

    Returns:
        Dict mapping each alias to its canonical name.
    """
    reverse: dict[str, str] = {}
    for canonical, aliases in replacements.items():
        for alias in aliases:
            reverse[alias] = canonical
    return reverse


_REPLACEMENTS = _load_replacements()
_REVERSE_MAP = _build_reverse_mapping(_REPLACEMENTS)

ALL_KNOWN_TEAMS: frozenset[str] = frozenset({
    # EPL (14/15 - 25/26)
    "AFC Bournemouth", "Arsenal", "Aston Villa", "Brentford",
    "Brighton & Hove Albion", "Burnley", "Cardiff City", "Chelsea",
    "Crystal Palace", "Everton", "Fulham", "Hull City",
    "Ipswich Town", "Leeds United", "Leicester City", "Liverpool",
    "Luton Town", "Manchester City", "Manchester United",
    "Newcastle United", "Norwich City", "Nottingham Forest",
    "Queens Park Rangers", "Sheffield United", "Southampton",
    "Stoke City", "Sunderland", "Swansea City",
    "Tottenham Hotspur", "Watford", "West Bromwich Albion",
    "West Ham United", "Wolverhampton Wanderers",
    "Huddersfield Town", "Middlesbrough",
    # La Liga
    "Alaves", "Almeria", "Athletic Bilbao", "Atletico Madrid",
    "Barcelona", "Betis", "Cadiz", "Celta Vigo",
    "Deportivo La Coruna", "Eibar", "Elche", "Espanyol",
    "Getafe", "Girona", "Granada", "Huesca", "Las Palmas",
    "Leganes", "Levante", "Mallorca", "Osasuna",
    "Racing Santander", "Rayo Vallecano", "Real Madrid",
    "Real Sociedad", "Sevilla", "Valencia", "Valladolid",
    "Villarreal", "Real Oviedo", "Sporting Gijon",
    "Malaga", "Cordoba",
    # Bundesliga
    "Arminia Bielefeld", "Augsburg", "Bayer Leverkusen",
    "Bayern Munich", "Borussia Dortmund",
    "Borussia Monchengladbach", "Darmstadt",
    "Eintracht Frankfurt", "FC Koln", "Fortuna Dusseldorf",
    "Freiburg", "Greuther Furth", "Hamburger SV",
    "Hannover 96", "Heidenheim", "Hertha Berlin",
    "Hoffenheim", "Holstein Kiel", "Ingolstadt",
    "Mainz 05", "Paderborn", "RB Leipzig",
    "Schalke 04", "St Pauli", "Union Berlin",
    "VfB Stuttgart", "VfL Bochum", "VfL Wolfsburg",
    "Werder Bremen", "Nuernberg",
    # Serie A
    "AC Milan", "AS Roma", "Atalanta", "Benevento", "Bologna",
    "Cagliari", "Chievo", "Como", "Cremonese", "Empoli",
    "Fiorentina", "Frosinone", "Genoa", "Inter", "Juventus",
    "Lazio", "Lecce", "Monza", "Napoli", "Palermo", "Parma",
    "Salernitana", "Sampdoria", "Sassuolo", "SPAL", "Spezia",
    "Torino", "Udinese", "Venezia", "Verona",
    "Brescia", "Carpi", "Cesena", "Crotone", "Pescara", "Pisa",
    # Ligue 1
    "Ajaccio", "Amiens", "Angers", "Auxerre", "Bordeaux",
    "Brest", "Caen", "Clermont", "Dijon", "Guingamp",
    "Le Havre", "Lens", "Lille", "Lorient", "Lyon",
    "Marseille", "Metz", "Monaco", "Montpellier", "Nantes",
    "Nice", "Nimes", "Paris Saint Germain", "Reims", "Rennes",
    "Saint-Etienne", "Strasbourg", "Toulouse", "Troyes",
    "Bastia", "Evian Thonon Gaillard", "Nancy", "Paris FC",
    # R5a extended leagues
    "Ajax Amsterdam", "PSV Eindhoven", "AZ Alkmaar", "ADO Den Haag",
    "Feyenoord", "Twente", "Utrecht", "Vitesse", "Heerenveen",
    "Legia Warszawa", "Lech Poznan", "MKS Cracovia", "Piast Gliwice",
    "Wisla Krakow", "Gornik Zabrze", "Jagiellonia Bialystok",
    "Rakow Czestochowa", "Pogon Szczecin", "Slask Wroclaw",
    "Benfica", "Porto", "Sporting CP", "Braga", "Vitoria Guimaraes",
    "Club Brugge", "Anderlecht", "Genk", "Gent", "Standard Liege",
    "Antwerp", "Galatasaray", "Fenerbahce", "Besiktas", "Trabzonspor",
    "Istanbul Basaksehir", "Sparta Prague", "Slavia Prague",
    "Viktoria Plzen", "Banik Ostrava", "Slovan Liberec",
})


def normalize_team_name(name: str) -> str:
    """Normalize a team name to its canonical form.

    Args:
        name: Raw team name from any source.

    Returns:
        Canonical team name. Returns input unchanged if no mapping exists.
    """
    return _REVERSE_MAP.get(name, name)


def find_unmapped_names(names: list[str]) -> list[str]:
    """Find team names not recognized as canonical or aliased.

    Args:
        names: List of team names to check.

    Returns:
        List of names that are not in ALL_KNOWN_TEAMS and have no alias mapping.
    """
    return [
        name for name in names
        if name not in ALL_KNOWN_TEAMS and name not in _REVERSE_MAP
    ]

#!/usr/bin/env python3
"""Integrate FIFA/FC squad-level ratings into expansion league features.

Reads FIFA 15-26 CSV files, builds per-team per-season aggregate features
(avg_overall, avg_pace, squad_depth, etc.), and merges into the features
parquet as home_/away_ prefixed columns.

Top-5 leagues already have XI-level FIFA features from player_matches data.
This script adds SQUAD-level features for ALL leagues (expansion + top-5),
which are static per team per season and do not require match lineups.

Usage:
    uv run python scripts/integrate_fifa_ratings.py
    uv run python scripts/integrate_fifa_ratings.py --dry-run
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import structlog

# Add the research codebase to path for player_features module.
# The research repo uses "from src.features..." style imports, so we add
# the repo root (parent of src/) to sys.path.
_RESEARCH_ROOT = Path("c:/Users/Estera/Mateusz/ml_in_sports")
sys.path.insert(0, str(_RESEARCH_ROOT))

from src.features.player_features import (  # noqa: E402
    _STANDARD_COLUMNS,
    _discover_csv_files,
    _load_single_csv,
    aggregate_squad_features,
    normalize_player_dataframe,
)

logger = structlog.get_logger(__name__)

FIFA_DIR = Path("c:/Users/Estera/Mateusz/ml_in_sports/data/fifa")
PARQUET_PATH = Path("data/features/all_features.parquet")

# ---------------------------------------------------------------------------
# FIFA club name -> parquet canonical name mapping
# ---------------------------------------------------------------------------
# FIFA CSVs use verbose official club names. The parquet uses shorter canonical
# names. normalize_team_name() handles some cases, but many expansion league
# clubs need additional mapping. This dict maps the normalized FIFA name
# (after normalize_team_name()) to the parquet canonical name.
# ---------------------------------------------------------------------------

FIFA_TO_PARQUET_NAME: dict[str, str] = {
    # --- Belgian Jupiler Pro League ---
    "Club Brugge KV": "Club Brugge",
    "K Beerschot VA": "Beerschot VA",
    "KAA Gent": "Gent",
    "KAS Eupen": "Eupen",
    "KRC Genk": "Genk",
    "KSV Cercle Brugge": "Cercle Brugge",
    "KV Kortrijk": "Kortrijk",
    "KV Mechelen": "Mechelen",
    "KV Oostende": "Oostende",
    "KVC Westerlo": "Westerlo",
    "Lierse SK": "Lierse",
    "RSC Anderlecht": "Anderlecht",
    "Royal Antwerp FC": "Antwerp",
    "Royal Charleroi S.C.": "Charleroi",
    "Royal Excel Mouscron": "Mouscron",
    "Royale Union Saint-Gilloise": "St. Gilloise",
    "SV Zulte Waregem": "Waregem",
    "Sint-Truidense VV": "St Truiden",
    "Sporting Lokeren": "Lokeren",
    "Waasland-Beveren": "Waasland-Beveren",
    "Seraing": "Seraing",
    # Standard de Liege -> normalize_team_name doesn't handle it
    "Standard de Liege": "Standard Liege",

    # --- Holland Eredivisie ---
    "Ajax": "Ajax Amsterdam",
    "FC Groningen": "Groningen",
    "FC Twente": "Twente",
    "FC Utrecht": "Utrecht",
    "Heracles Almelo": "Heracles",
    "N.E.C. Nijmegen": "Nijmegen",
    "PEC Zwolle": "Zwolle",
    "PSV": "PSV Eindhoven",
    "RKC Waalwijk": "Waalwijk",
    "Roda JC Kerkrade": "Roda",
    "SC Cambuur": "Cambuur",
    "SC Heerenveen": "Heerenveen",
    "De Graafschap": "Graafschap",
    "VVV-Venlo": "VVV Venlo",
    "Willem II": "Willem II",
    "FC Dordrecht": "Dordrecht",
    "FC Emmen": "FC Emmen",
    "Go Ahead Eagles": "Go Ahead Eagles",
    "Excelsior": "Excelsior",
    "Vitesse": "Vitesse",
    "Sparta Rotterdam": "Sparta Rotterdam",
    "ADO Den Haag": "ADO Den Haag",
    "AZ Alkmaar": "AZ Alkmaar",
    "Feyenoord": "Feyenoord",
    "Fortuna Sittard": "For Sittard",
    "NAC Breda": "NAC Breda",
    "Almere City FC": "Almere City",
    "FC Volendam": "Volendam",

    # --- Portuguese Liga ZON SAGRES ---
    "FC Porto": "Porto",
    "SL Benfica": "Benfica",
    "Sporting CP": "Sp Lisbon",
    "SC Braga": "Sp Braga",
    "Boavista FC": "Boavista",
    "Gil Vicente FC": "Gil Vicente",
    "Moreirense FC": "Moreirense",
    "Rio Ave FC": "Rio Ave",
    "CD Nacional": "Nacional",
    "CD Tondela": "Tondela",
    "CD Feirense": "Feirense",
    "Estoril Praia": "Estoril",
    "FC Arouca": "Arouca",
    "FC Penafiel": "Penafiel",
    "FC Vizela": "Vizela",
    "GD Chaves": "Chaves",
    "Portimonense SC": "Portimonense",
    "Santa Clara": "Santa Clara",
    "SC Farense": "Farense",
    "Belenenses SAD": "Belenenses",
    "Desportivo das Aves": "Aves",
    "Futebol Clube de Famalicao": "Famalicao",
    "Clube Sport Maritimo": "Maritimo",
    "FC Pacos de Ferreira": "Pacos Ferreira",
    "Associacao Academica de Coimbra": "Academica",
    "Vitoria de Guimaraes": "Vitoria Guimaraes",
    "Vitoria de Setubal": "Setubal",
    "Uniao da Madeira": "Uniao Madeira",
    "Casa Pia AC": "Casa Pia",
    "AVS Futebol SAD": "AVS",
    "Estrela da Amadora": "Estrela",

    # --- Scottish Premiership ---
    "Rangers FC": "Rangers",
    "Celtic": "Celtic",
    "Aberdeen": "Aberdeen",
    "Heart of Midlothian": "Hearts",
    "Hibernian": "Hibernian",
    "Dundee FC": "Dundee",
    "Dundee United": "Dundee United",
    "Motherwell": "Motherwell",
    "Kilmarnock": "Kilmarnock",
    "Ross County FC": "Ross County",
    "Livingston FC": "Livingston",
    "St. Johnstone FC": "St Johnstone",
    "St. Mirren": "St Mirren",
    "Hamilton Academical FC": "Hamilton",
    "Partick Thistle FC": "Partick",
    "Inverness Caledonian Thistle": "Inverness C",

    # --- Greek Super League ---
    "AEK Athens": "AEK",
    "Olympiacos CFP": "Olympiakos",
    "Panathinaikos FC": "Panathinaikos",
    "PAOK": "PAOK",

    # --- Turkish Super Lig ---
    "Galatasaray SK": "Galatasaray",
    "Fenerbahce SK": "Fenerbahce",
    "Besiktas JK": "Besiktas",
    "Trabzonspor": "Trabzonspor",
    "Antalyaspor": "Antalyaspor",
    "Bursaspor": "Bursaspor",
    "Demir Grup Sivasspor": "Sivasspor",
    "Denizlispor": "Denizlispor",
    "Eskisehirspor": "Eskisehirspor",
    "Fatih Karagumruk S.K.": "Karagumruk",
    "GZT Giresunspor": "Giresunspor",
    "Gaziantepspor": "Gaziantepspor",
    "Gazisehir Gaziantep F.K.": "Gaziantep",
    "Genclerbirligi SK": "Genclerbirligi",
    "Goztepe SK": "Goztep",
    "Istanbul Basaksehir FK": "Buyuksehyr",
    "Ittifak Holding Konyaspor": "Konyaspor",
    "Kardemir Karabukspor": "Karabukspor",
    "Kasimpasa SK": "Kasimpasa",
    "Kayseri Erciyesspor": "Erciyesspor",
    "MKE Ankaragucu": "Ankaragucu",
    "Mersin Idman Yurdu": "Mersin Idman Yurdu",
    "Osmanlispor": "Osmanlispor",
    "Yeni Malatyaspor": "Yeni Malatyaspor",
    "Yukatel Kayserispor": "Kayserispor",
    "Caykur Rizespor": "Rizespor",
    "Adana Demirspor": "Ad. Demirspor",
    "Adanaspor": "Adanaspor",
    "Akhisar Belediyespor": "Akhisar Belediyespor",
    "Altay SK": "Altay",
    "Atakas Hatayspor": "Hatayspor",
    "Aytemiz Alanyaspor": "Alanyaspor",
    "BB Erzurumspor": "Erzurum BB",
    "Balikesirspor": "Balikesirspor",
    "Samsunspor": "Samsunspor",
    "Eyupspor": "Eyupspor",
    "Bodrumspor": "Bodrumspor",
    "Pendikspor": "Pendikspor",

    # --- FC24/FC25 abbreviated names (bypass normalize_team_name) ---
    "Newcastle Utd": "Newcastle United",
    "Sheffield Wed": "Sheffield Weds",
    "Rotherham Utd": "Rotherham",

    # --- English Championship ---
    "Birmingham City": "Birmingham",
    "Blackburn Rovers": "Blackburn",
    "Blackpool": "Blackpool",
    "Bolton Wanderers": "Bolton",
    "Bristol City": "Bristol City",
    "Burton Albion": "Burton",
    "Charlton Athletic": "Charlton",
    "Coventry City": "Coventry",
    "Derby County": "Derby",
    "Millwall": "Millwall",
    "Milton Keynes Dons": "Milton Keynes Dons",
    "Peterborough United": "Peterboro",
    "Preston North End": "Preston",
    "Reading": "Reading",
    "Rotherham United": "Rotherham",
    "Sheffield Wednesday": "Sheffield Weds",
    "Wigan Athletic": "Wigan",
    "Wycombe Wanderers": "Wycombe",
    "Barnsley": "Barnsley",
    "Brentford": "Brentford",
    "Plymouth Argyle": "Plymouth",
    "Oxford United": "Oxford",

    # --- German 2. Bundesliga ---
    "1. FC Kaiserslautern": "Kaiserslautern",
    "1. FC Koln": "FC Koln",
    "1. FC Magdeburg": "Magdeburg",
    "DSC Arminia Bielefeld": "Arminia Bielefeld",
    "Eintracht Braunschweig": "Braunschweig",
    "F.C. Hansa Rostock": "Hansa Rostock",
    "FC Erzgebirge Aue": "Erzgebirge Aue",
    "FC Schalke 04": "Schalke 04",
    "FC Wurzburger Kickers": "Wurzburger Kickers",
    "FSV Frankfurt": "Frankfurt FSV",
    "Karlsruher SC": "Karlsruhe",
    "MSV Duisburg": "Duisburg",
    "Nuernberg": "Nurnberg",
    "SG Dynamo Dresden": "Dresden",
    "SSV Jahn Regensburg": "Regensburg",
    "SV Sandhausen": "Sandhausen",
    "SV Wehen Wiesbaden": "Wehen",
    "SV Werder Bremen": "Werder Bremen",
    "Sport-Club Freiburg": "Freiburg",
    "TSV 1860 Munchen": "Munich 1860",
    "VfB Stuttgart": "VfB Stuttgart",
    "VfL Bochum 1848": "VfL Bochum",
    "VfL Osnabruck": "Osnabruck",
    "VfR Aalen": "Aalen",
    "SSV Ulm 1846": "Ulm",
    "SV Elversberg": "Elversberg",
    "SC Preussen Munster": "Preussen Munster",

    # --- Italian Serie B ---
    "Castellammare di Stabia": "Juve Stabia",
    "FC Pro Vercelli 1892": "Pro Vercelli",
    "Novara Calcio": "Novara",
    "SS Virtus Lanciano": "Virtus Lanciano",
    "Venezia FC": "Venezia",
    "Virtus Entella Chiavari": "Virtus Entella",
    "Ascoli": "Ascoli",
    "Avellino": "Avellino",
    "Bari": "Bari",
    "Brescia": "Brescia",
    "Catania": "Catania",
    "Cesena": "Cesena",
    "Cittadella": "Cittadella",
    "Cosenza": "Cosenza",
    "Foggia": "Foggia",
    "Latina": "Latina",
    "Livorno": "Livorno",
    "Modena": "Modena",
    "Padova": "Padova",
    "Perugia": "Perugia",
    "Pisa": "Pisa",
    "Pordenone": "Pordenone",
    "Ternana": "Ternana",
    "Trapani": "Trapani",
    "Varese": "Varese",
    "Vicenza": "Vicenza",
    "Reggina": "Reggina",
    "Reggiana": "Reggiana",
    "FeralpiSalo": "FeralpiSalo",
    "Sudtirol": "Sudtirol",
    "Catanzaro": "Catanzaro",
    "Carrarese": "Carrarese",

    # --- Spanish Segunda ---
    "AD Alcorcon": "Alcorcon",
    "Albacete BP": "Albacete",
    "Athletic Club de Bilbao B": "Ath Bilbao B",
    "Burgos CF": "Burgos",
    "C.D. Castellon": "Castellon",
    "CD Lugo": "Lugo",
    "CD Mirandes": "Mirandes",
    "CD Numancia": "Numancia",
    "CD Tenerife": "Tenerife",
    "CE Sabadell FC": "Sabadell",
    "CF Fuenlabrada": "Fuenlabrada",
    "CF Rayo Majadahonda": "Rayo Majadahonda",
    "CF Reus Deportiu": "Reus Deportiu",
    "Cultural Leonesa": "Leonesa",
    "Deportivo de La Coruna": "Deportivo La Coruna",
    "FC Barcelona B": "Barcelona B",
    "FC Cartagena": "Cartagena",
    "Gimnastic de Tarragona": "Gimnastic",
    "Levante Union Deportiva": "Levante",
    "Lorca FC": "Lorca",
    "RC Recreativo de Huelva": "Recreativo",
    "RCD Espanyol de Barcelona": "Espanyol",
    "Real Sporting de Gijon": "Sporting Gijon",
    "Real Valladolid CF": "Valladolid",
    "Real Zaragoza": "Zaragoza",
    "SD Eibar": "Eibar",
    "SD Amorebieta": "Amorebieta",
    "SD Ponferradina": "Ponferradina",
    "Sevilla Atletico": "Sevilla B",
    "UCAM Murcia CF": "UCAM Murcia",
    "UD Ibiza": "Ibiza",
    "UD Logrones": "Logrones",
    "UE Llagostera": "Llagostera",
    "Union Deportiva Almeria": "Almeria",
    "Union Deportiva Las Palmas": "Las Palmas",
    "Real Sociedad B": "Sociedad B",
    "Real Betis Balompie": "Betis",
    "Malaga CF": "Malaga",
    "Cadiz CF": "Cadiz",
    "Cordoba CF": "Cordoba",
    "Elche CF": "Elche",
    "Andorra CF": "Andorra",
    "SD Eldense": "Eldense",
    "Racing Ferrol": "Ferrol",

    # --- French Ligue 2 ---
    "Chamois Niortais Football Club": "Niort",
    "Clermont Foot 63": "Clermont",
    "En Avant de Guingamp": "Guingamp",
    "FC Chambly Oise": "Chambly",
    "FC Sochaux-Montbeliard": "Sochaux",
    "Football Bourg En Bresse Peronnas 01": "Bourg Peronnas",
    "Grenoble Foot 38": "Grenoble",
    "La Berrichonne de Chateauroux": "Chateauroux",
    "Le Mans FC": "Le Mans",
    "RC Strasbourg Alsace": "Strasbourg",
    "Racing Club de Lens": "Lens",
    "Red Star FC": "Red Star",
    "Rodez Aveyron Football": "Rodez",
    "Stade Lavallois Mayenne FC": "Laval",
    "Stade Malherbe Caen": "Caen",
    "Toulouse Football Club": "Toulouse",
    "Tours FC": "Tours",
    "US Creteil-Lusitanos": "Creteil",
    "US Orleans Loiret Football": "Orleans",
    "US Quevilly Rouen Metropole": "Quevilly Rouen",
    "USL Dunkerque": "Dunkerque",
    "Valenciennes FC": "Valenciennes",
    "Evian Thonon Gaillard FC": "Evian Thonon Gaillard",
    "AC Arles Avignon": "Arles",
    "AS Beziers": "Beziers",
    "Pau FC": "Pau FC",
    "Paris FC": "Paris FC",
    "AC Ajaccio GFCO": "Ajaccio GFCO",
    "SC Annecy": "Annecy",
    "Concarneau": "Concarneau",
}

# ---------------------------------------------------------------------------
# Parquet team name aliases
# ---------------------------------------------------------------------------
# Some teams appear under different names in different leagues within the
# same parquet (e.g. "Sporting Gijon" in La Liga, "Sp Gijon" in Segunda).
# FIFA maps to one canonical name. This dict maps the canonical name to its
# aliases so we can duplicate squad features for both.
# ---------------------------------------------------------------------------

PARQUET_ALIASES: dict[str, list[str]] = {
    "Sporting Gijon": ["Sp Gijon"],
    "Espanyol": ["Espanol"],
    "Nurnberg": ["Nuernberg"],
    "Roda": ["Roda JC"],
}


# Squad-level feature columns to merge (output of aggregate_squad_features)
SQUAD_FEATURE_COLUMNS: list[str] = [
    "avg_overall",
    "avg_potential",
    "avg_age",
    "top_player_rating",
    "squad_depth",
    "avg_gk_rating",
    "avg_def_rating",
    "avg_mid_rating",
    "avg_fwd_rating",
    "avg_pace",
    "avg_shooting",
    "avg_passing",
    "avg_dribbling",
    "avg_defending",
    "avg_physic",
    "avg_stamina",
    "avg_sprint_speed",
    "avg_composure",
    "avg_vision",
    "avg_fwd_finishing",
    "avg_def_standing_tackle",
    "avg_gk_reflexes",
    "avg_skill_moves",
    "avg_weak_foot",
    "avg_international_reputation",
    "total_value_eur",
    "total_wage_eur",
]


# ---------------------------------------------------------------------------
# FIFA 23 special loader (5.3 GB file, needs chunked reading)
# ---------------------------------------------------------------------------

def _load_fifa_23_base_roster(fifa_dir: Path) -> pd.DataFrame:
    """Load FIFA 23 base roster (update=1) via chunked reading.

    The male_players_23.csv is 5.3 GB with 64 roster updates.
    We only need the base roster (fifa_update=1) for season features.

    Args:
        fifa_dir: Root FIFA data directory.

    Returns:
        Standardized DataFrame with FIFA 23 players.
    """
    csv_path = fifa_dir / "male_players_23.csv"
    if not csv_path.exists():
        logger.warning("fifa_23_missing", path=str(csv_path))
        return pd.DataFrame(columns=_STANDARD_COLUMNS)

    # Columns needed for aggregation
    cols_to_read = [
        "club_name", "overall", "potential", "age", "player_positions",
        "pace", "shooting", "passing", "dribbling", "defending", "physic",
        "value_eur", "wage_eur", "international_reputation",
        "skill_moves", "weak_foot", "work_rate",
        "height_cm", "weight_kg", "preferred_foot",
        "attacking_crossing", "attacking_finishing",
        "attacking_heading_accuracy", "attacking_short_passing",
        "attacking_volleys",
        "skill_dribbling", "skill_curve", "skill_fk_accuracy",
        "skill_long_passing", "skill_ball_control",
        "movement_acceleration", "movement_sprint_speed",
        "movement_agility", "movement_reactions", "movement_balance",
        "power_shot_power", "power_jumping", "power_stamina",
        "power_strength", "power_long_shots",
        "mentality_aggression", "mentality_interceptions",
        "mentality_positioning", "mentality_vision",
        "mentality_penalties", "mentality_composure",
        "defending_marking_awareness", "defending_standing_tackle",
        "defending_sliding_tackle",
        "goalkeeping_diving", "goalkeeping_handling",
        "goalkeeping_kicking", "goalkeeping_positioning",
        "goalkeeping_reflexes",
        "fifa_update",
        "fifa_version",
    ]

    logger.info("loading_fifa_23", path=str(csv_path), method="chunked")

    filtered_chunks: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        csv_path,
        usecols=cols_to_read,
        chunksize=500_000,
        low_memory=False,
    ):
        # The file contains ALL historical versions (15-23) with multiple updates.
        # We only want fifa_version=23 with update=1 (base roster for season 2223).
        base = chunk[
            (chunk["fifa_version"] == 23) & (chunk["fifa_update"] == 1)
        ].drop(columns=["fifa_update", "fifa_version"])
        if not base.empty:
            filtered_chunks.append(base)

    if not filtered_chunks:
        logger.warning("fifa_23_no_base_roster")
        return pd.DataFrame(columns=_STANDARD_COLUMNS)

    result = pd.concat(filtered_chunks, ignore_index=True)
    result["season"] = "2223"

    # Fill any missing standard columns
    for col in _STANDARD_COLUMNS:
        if col not in result.columns:
            result[col] = pd.NA

    logger.info("fifa_23_loaded", players=len(result))
    return result


# ---------------------------------------------------------------------------
# Build all FIFA features with FIFA 23 fix
# ---------------------------------------------------------------------------

def build_all_fifa_features(fifa_dir: Path) -> pd.DataFrame:
    """Build squad features from all FIFA versions, including FIFA 23.

    Uses the research codebase's _discover_csv_files and _load_single_csv
    for versions 15-22, 24-26, plus a custom chunked loader for FIFA 23.

    Args:
        fifa_dir: Root FIFA data directory.

    Returns:
        DataFrame with squad-level features per team per season.
    """
    csv_files = _discover_csv_files(fifa_dir)

    all_players: list[pd.DataFrame] = []
    for path, version, format_type in csv_files:
        loaded = _load_single_csv(path, version, format_type)
        if not loaded.empty:
            all_players.append(loaded)
            logger.info(
                "loaded_csv",
                file=path.name,
                version=version,
                players=len(loaded),
            )

    # Load FIFA 23 separately with chunked reader
    fifa_23 = _load_fifa_23_base_roster(fifa_dir)
    if not fifa_23.empty:
        all_players.append(fifa_23)

    if not all_players:
        logger.error("no_fifa_data_found")
        return pd.DataFrame()

    combined = pd.concat(all_players, ignore_index=True)
    combined = combined.dropna(subset=["club_name", "overall"])

    logger.info("total_players_loaded", count=len(combined))

    normalized = normalize_player_dataframe(combined)
    features = aggregate_squad_features(normalized)

    logger.info(
        "squad_features_built",
        team_seasons=len(features),
        seasons=sorted(features["season"].unique()),
    )
    return features


# ---------------------------------------------------------------------------
# Name mapping
# ---------------------------------------------------------------------------

def _strip_diacritics_basic(text: str) -> str:
    """Strip common diacritics for matching purposes.

    Args:
        text: Input string.

    Returns:
        String with common accented characters replaced by ASCII equivalents.
    """
    replacements = {
        "\u00e9": "e", "\u00e8": "e", "\u00ea": "e", "\u00eb": "e",
        "\u00e0": "a", "\u00e1": "a", "\u00e2": "a", "\u00e3": "a", "\u00e4": "a",
        "\u00f2": "o", "\u00f3": "o", "\u00f4": "o", "\u00f5": "o", "\u00f6": "o",
        "\u00f9": "u", "\u00fa": "u", "\u00fb": "u", "\u00fc": "u",
        "\u00ed": "i", "\u00ee": "i", "\u00ef": "i", "\u00ec": "i",
        "\u00f1": "n",
        "\u00e7": "c",
        "\u0219": "s", "\u015f": "s",
        "\u00df": "ss",
        "\u00e6": "ae",
        "\u0131": "i",  # Turkish dotless i
        "\u011f": "g",  # Turkish g with breve
        "\u0130": "I",  # Turkish capital I with dot
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def map_fifa_name_to_parquet(
    fifa_name: str,
    parquet_teams: set[str],
) -> str:
    """Map a FIFA club name to the parquet canonical team name.

    Tries in order:
    1. Direct match (already in parquet)
    2. After normalize_team_name()
    3. Explicit FIFA_TO_PARQUET_NAME mapping
    4. Stripped diacritics match
    5. Returns original if no match found

    Args:
        fifa_name: Normalized FIFA club name (after normalize_team_name).
        parquet_teams: Set of all team names in the parquet.

    Returns:
        Parquet canonical team name, or original if unmapped.
    """
    # 1. Explicit mapping takes priority (handles ambiguous names like "Ajax")
    if fifa_name in FIFA_TO_PARQUET_NAME:
        return FIFA_TO_PARQUET_NAME[fifa_name]

    # 2. Strip diacritics and check explicit mapping
    stripped = _strip_diacritics_basic(fifa_name)
    if stripped in FIFA_TO_PARQUET_NAME:
        return FIFA_TO_PARQUET_NAME[stripped]

    # 3. Direct match in parquet teams
    if fifa_name in parquet_teams:
        return fifa_name

    # 4. Stripped diacritics direct match
    if stripped in parquet_teams:
        return stripped

    return fifa_name


# ---------------------------------------------------------------------------
# Parquet team name normalization (handle trailing spaces)
# ---------------------------------------------------------------------------

def _normalize_parquet_team_names(df: pd.DataFrame) -> pd.DataFrame:
    """Strip trailing spaces from team names in parquet.

    Some parquet team names have trailing spaces (e.g. "Ajax ").
    We normalize both home_team and away_team by stripping.

    Args:
        df: Features parquet DataFrame.

    Returns:
        DataFrame with stripped team names.
    """
    result = df.copy()
    result["home_team"] = result["home_team"].str.strip()
    result["away_team"] = result["away_team"].str.strip()
    return result


# ---------------------------------------------------------------------------
# Join squad features to match parquet
# ---------------------------------------------------------------------------

def join_squad_features_to_parquet(
    match_df: pd.DataFrame,
    squad_features: pd.DataFrame,
) -> pd.DataFrame:
    """Join squad-level FIFA features to match DataFrame.

    For each match, joins home_team -> squad features (prefixed home_)
    and away_team -> squad features (prefixed away_).

    Args:
        match_df: Match-level DataFrame with home_team, away_team, season.
        squad_features: Squad features with club_name, season columns.

    Returns:
        Match DataFrame with squad feature columns added.
    """
    result = match_df.copy()

    # Build rename mapping for home/away
    feature_cols = [
        c for c in SQUAD_FEATURE_COLUMNS
        if c in squad_features.columns
    ]

    original_row_count = len(result)

    for side in ["home", "away"]:
        team_col = f"{side}_team"

        # Prepare the squad features for joining
        join_df = squad_features[["club_name", "season", *feature_cols]].copy()
        rename_map = {col: f"{side}_{col}" for col in feature_cols}
        rename_map["club_name"] = team_col
        join_df = join_df.rename(columns=rename_map)

        # Assert no duplicate keys in join source (prevents fan-out)
        assert join_df.duplicated(subset=[team_col, "season"]).sum() == 0, (
            f"Duplicate team-season in squad features for {side} join"
        )

        result = result.merge(
            join_df,
            on=[team_col, "season"],
            how="left",
        )

    assert len(result) == original_row_count, (
        f"Row count changed: {original_row_count} -> {len(result)}. "
        "Likely duplicate team-season in squad features."
    )

    return result


# ---------------------------------------------------------------------------
# Main integration pipeline
# ---------------------------------------------------------------------------

def integrate_fifa_ratings(dry_run: bool = False) -> None:
    """Run the full FIFA rating integration pipeline.

    Steps:
    1. Load parquet
    2. Build squad features from all FIFA CSVs
    3. Map FIFA club names to parquet team names
    4. Join features to parquet
    5. Save updated parquet

    Args:
        dry_run: If True, compute and report but don't save.
    """
    logger.info("starting_fifa_integration", dry_run=dry_run)

    # 1. Load parquet
    if not PARQUET_PATH.exists():
        logger.error("parquet_not_found", path=str(PARQUET_PATH))
        return

    match_df = pd.read_parquet(PARQUET_PATH)
    original_cols = set(match_df.columns)
    logger.info("parquet_loaded", rows=len(match_df), cols=len(match_df.columns))

    # Normalize trailing spaces in team names
    match_df = _normalize_parquet_team_names(match_df)

    # Collect all parquet team names
    parquet_teams: set[str] = set(
        match_df["home_team"].unique()
    ) | set(
        match_df["away_team"].unique()
    )

    # 2. Build squad features
    squad_features = build_all_fifa_features(FIFA_DIR)
    if squad_features.empty:
        logger.error("no_squad_features_built")
        return

    logger.info(
        "squad_features_summary",
        team_seasons=len(squad_features),
        unique_clubs=squad_features["club_name"].nunique(),
        seasons=sorted(squad_features["season"].unique()),
    )

    # 3. Map FIFA club names to parquet names
    squad_features["club_name"] = squad_features["club_name"].apply(
        lambda name: map_fifa_name_to_parquet(name, parquet_teams),
    )

    # 3b. Duplicate features for known aliases
    alias_rows: list[pd.DataFrame] = []
    for canonical, aliases in PARQUET_ALIASES.items():
        for alias in aliases:
            if alias == canonical:
                continue
            canonical_features = squad_features[
                squad_features["club_name"] == canonical
            ].copy()
            if not canonical_features.empty:
                canonical_features["club_name"] = alias
                alias_rows.append(canonical_features)

    if alias_rows:
        squad_features = pd.concat(
            [squad_features, *alias_rows], ignore_index=True,
        )
        logger.info("alias_rows_added", count=sum(len(r) for r in alias_rows))

    # Report match rates
    mapped_clubs = set(squad_features["club_name"].unique())
    matched = mapped_clubs & parquet_teams
    unmatched_fifa = mapped_clubs - parquet_teams

    logger.info(
        "name_matching",
        fifa_clubs=len(mapped_clubs),
        parquet_teams=len(parquet_teams),
        matched=len(matched),
        unmatched_fifa=len(unmatched_fifa),
    )

    if unmatched_fifa:
        # Log only first 30 to avoid noise; ASCII-safe for Windows console
        sample = sorted(unmatched_fifa)[:30]
        safe_sample = [
            s.encode("ascii", errors="replace").decode("ascii")
            for s in sample
        ]
        logger.debug("unmatched_fifa_clubs", count=len(unmatched_fifa), sample=safe_sample)

    # 4. Drop any existing squad-level FIFA columns to avoid duplication
    existing_fifa_cols = [
        c for c in match_df.columns
        if any(
            c == f"{side}_{feat}"
            for side in ["home", "away"]
            for feat in SQUAD_FEATURE_COLUMNS
        )
    ]
    if existing_fifa_cols:
        logger.info("dropping_existing_fifa_cols", cols=existing_fifa_cols)
        match_df = match_df.drop(columns=existing_fifa_cols)

    # 5. Join
    result = join_squad_features_to_parquet(match_df, squad_features)

    # 6. Report coverage per league
    new_cols = sorted(set(result.columns) - original_cols)
    logger.info("new_columns_added", count=len(new_cols), columns=new_cols[:10])

    _report_coverage(result)

    # 7. Save
    if dry_run:
        logger.info("dry_run_complete", would_save_to=str(PARQUET_PATH))
    else:
        result.to_parquet(PARQUET_PATH, index=False)
        logger.info("parquet_saved", path=str(PARQUET_PATH), rows=len(result), cols=len(result.columns))


def _report_coverage(df: pd.DataFrame) -> None:
    """Report FIFA feature coverage per league.

    Args:
        df: DataFrame with FIFA features merged.
    """
    check_col = "home_avg_overall"
    if check_col not in df.columns:
        logger.warning("no_home_avg_overall_column")
        return

    for league in sorted(df["league"].unique()):
        sub = df[df["league"] == league]
        has_fifa = sub[check_col].notna().sum()
        total = len(sub)
        pct = has_fifa / total * 100 if total > 0 else 0
        logger.info(
            "league_coverage",
            league=league,
            matches_with_fifa=has_fifa,
            total_matches=total,
            coverage_pct=round(pct, 1),
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Integrate FIFA squad ratings into features parquet",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and report without saving",
    )
    args = parser.parse_args()

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )

    integrate_fifa_ratings(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

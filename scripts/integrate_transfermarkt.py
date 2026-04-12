#!/usr/bin/env python3
"""Integrate Transfermarkt formation and market value data into expansion leagues.

Downloads tm_games and tm_players from the Transfermarkt open-data CDN,
caches them locally, maps TM's verbose official names to our canonical
names, joins formations to the parquet by (home_team, away_team, date),
and runs add_formation_features() on each league.

Usage:
    uv run python scripts/integrate_transfermarkt.py
    uv run python scripts/integrate_transfermarkt.py --leagues NL1 BE1
    uv run python scripts/integrate_transfermarkt.py --dry-run

Rate limit: the CDN is free; we download two files (games.csv.gz, players.csv.gz)
once and cache locally. No repeated requests per league.
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import structlog

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent.parent
        / "packages"
        / "ml-in-sports"
        / "src"
    ),
)

from ml_in_sports.features.formation_features import add_formation_features
from ml_in_sports.processing.extractors import _download_tm_csv
from ml_in_sports.utils.team_names import normalize_team_name

logger = structlog.get_logger(__name__)

PARQUET_PATH = Path("data/features/all_features.parquet")
CACHE_DIR = Path("data/transfermarkt")

# Mapping: our canonical league name -> TM competition_id
LEAGUE_TO_TM_ID: dict[str, str] = {
    # Top-5
    "ENG-Premier League": "GB1",
    "ESP-La Liga": "ES1",
    "GER-Bundesliga": "L1",
    "ITA-Serie A": "IT1",
    "FRA-Ligue 1": "FR1",
    # Expansion leagues with TM data
    "NED-Eredivisie": "NL1",
    "POR-Primeira Liga": "PO1",
    "BEL-Jupiler Pro League": "BE1",
    "TUR-Süper Lig": "TR1",
    "GRE-Super League": "GR1",
    "SCO-Premiership": "SC1",
    # These second-tier leagues have NO games in TM CDN:
    # "ENG-Championship": "GB2",
    # "GER-Bundesliga 2": "L2",
    # "ITA-Serie B": "IT2",
    # "ESP-Segunda": "ES2",
    # "FRA-Ligue 2": "FR2",
}

# TM uses extremely verbose official club names.
# This maps them to our canonical names (from team_names.py / ALL_KNOWN_TEAMS).
# Built by inspecting every home_club_name in the TM games dataset.
TM_NAME_TO_CANONICAL: dict[str, str] = {
    # --- GB1 (Premier League) ---
    "Arsenal Football Club": "Arsenal",
    "Association Football Club Bournemouth": "AFC Bournemouth",
    "Aston Villa Football Club": "Aston Villa",
    "Brentford Football Club": "Brentford",
    "Brighton and Hove Albion Football Club": "Brighton & Hove Albion",
    "Burnley Football Club": "Burnley",
    "Cardiff City": "Cardiff City",
    "Chelsea Football Club": "Chelsea",
    "Crystal Palace Football Club": "Crystal Palace",
    "Everton Football Club": "Everton",
    "Fulham Football Club": "Fulham",
    "Huddersfield Town": "Huddersfield Town",
    "Hull City": "Hull City",
    "Ipswich Town": "Ipswich Town",
    "Leeds United Association Football Club": "Leeds United",
    "Leicester City": "Leicester City",
    "Liverpool Football Club": "Liverpool",
    "Luton Town": "Luton Town",
    "Manchester City Football Club": "Manchester City",
    "Manchester United Football Club": "Manchester United",
    "Middlesbrough FC": "Middlesbrough",
    "Newcastle United Football Club": "Newcastle United",
    "Norwich City": "Norwich City",
    "Nottingham Forest Football Club": "Nottingham Forest",
    "Queens Park Rangers": "Queens Park Rangers",
    "Reading FC": "Reading",
    "Sheffield United": "Sheffield United",
    "Southampton FC": "Southampton",
    "Stoke City": "Stoke City",
    "Sunderland Association Football Club": "Sunderland",
    "Swansea City": "Swansea City",
    "Tottenham Hotspur Football Club": "Tottenham Hotspur",
    "Watford FC": "Watford",
    "West Bromwich Albion": "West Bromwich Albion",
    "West Ham United Football Club": "West Ham United",
    "Wigan Athletic": "Wigan",
    "Wolverhampton Wanderers Football Club": "Wolverhampton Wanderers",
    # --- ES1 (La Liga) ---
    # TM uses multiple name variants across seasons
    "Athletic Club Bilbao": "Athletic Bilbao",
    "CD Leganés": "Leganes",
    "Club Atlético Osasuna": "Osasuna",
    "Club Atlético de Madrid S.A.D.": "Atletico Madrid",
    "Cádiz CF": "Cadiz",
    "Córdoba CF": "Cordoba",
    "Deportivo Alavés S. A. D.": "Alaves",
    "Deportivo de La Coruña": "Deportivo La Coruna",
    "Elche CF": "Elche",
    "Elche Club de Fútbol S.A.D.": "Elche",
    "FC Barcelona": "Barcelona",
    "Futbol Club Barcelona": "Barcelona",
    "Getafe Club de Fútbol S.A.D.": "Getafe",
    "Getafe Club de Fútbol S. A. D. Team Dubai": "Getafe",
    "Girona FC": "Girona",
    "Girona Fútbol Club S. A. D.": "Girona",
    "Granada CF": "Granada",
    "Granada Club de Fútbol": "Granada",
    "Levante Unión Deportiva": "Levante",
    "Levante Unión Deportiva S.A.D.": "Levante",
    "Málaga CF": "Malaga",
    "Málaga Club de Fútbol S.A.D.": "Malaga",
    "RC Celta de Vigo": "Celta Vigo",
    "RC Deportivo La Coruña": "Deportivo La Coruna",
    "RCD Espanyol de Barcelona": "Espanyol",
    "RCD Mallorca": "Mallorca",
    "Rayo Vallecano de Madrid S.A.D.": "Rayo Vallecano",
    "Rayo Vallecano de Madrid S. A. D.": "Rayo Vallecano",
    "Real Betis Balompié": "Betis",
    "Real Betis Balompié S.A.D.": "Betis",
    "Real Club Celta de Vigo S. A. D.": "Celta Vigo",
    "Real Club Deportivo Mallorca S.A.D.": "Mallorca",
    "Real Madrid Club de Fútbol": "Real Madrid",
    "Real Oviedo S.A.D.": "Real Oviedo",
    "Real Sociedad de Fútbol S.A.D.": "Real Sociedad",
    "Real Valladolid CF": "Valladolid",
    "Real Valladolid Club de Fútbol": "Valladolid",
    "Real Zaragoza": "Real Zaragoza",
    "Reial Club Deportiu Espanyol de Barcelona S.A.D.": "Espanyol",
    "SD Eibar": "Eibar",
    "SD Huesca": "Huesca",
    "Sevilla Fútbol Club S.A.D.": "Sevilla",
    "Sporting Gijón": "Sporting Gijon",
    "UD Almería": "Almeria",
    "UD Las Palmas": "Las Palmas",
    "Valencia Club de Fútbol": "Valencia",
    "Valencia Club de Fútbol S. A. D.": "Valencia",
    "Villarreal Club de Fútbol S.A.D.": "Villarreal",
    # --- L1 (Bundesliga) ---
    # TM uses different name variants across seasons
    "1. FC Heidenheim 1846": "Heidenheim",
    "1. FC Köln": "FC Koln",
    "1. FC Nürnberg": "Nuernberg",
    "1. FC Union Berlin": "Union Berlin",
    "1. FSV Mainz 05": "Mainz 05",
    "1. Fußball- und Sportverein Mainz 05": "Mainz 05",
    "1. Fußball-Club Köln": "FC Koln",
    "1. Fußballclub Heidenheim 1846": "Heidenheim",
    "1. Fußballclub Union Berlin": "Union Berlin",
    "1.FC Nuremberg": "Nuernberg",
    "Arminia Bielefeld": "Arminia Bielefeld",
    "Bayer 04 Leverkusen Fußball": "Bayer Leverkusen",
    "Bayer 04 Leverkusen Fußball GmbH": "Bayer Leverkusen",
    "Borussia Dortmund": "Borussia Dortmund",
    "Borussia Mönchengladbach": "Borussia Monchengladbach",
    "Borussia Verein für Leibesübungen 1900 Mönchengladbach": "Borussia Monchengladbach",
    "Borussia Verein für Leibesübungen 1900 e.V. Mönchengladbach": "Borussia Monchengladbach",
    "DSC Arminia Bielefeld": "Arminia Bielefeld",
    "Eintracht Braunschweig": "Eintracht Braunschweig",
    "Eintracht Frankfurt Fußball AG": "Eintracht Frankfurt",
    "FC Augsburg": "Augsburg",
    "FC Bayern München": "Bayern Munich",
    "FC Ingolstadt 04": "Ingolstadt",
    "FC Schalke 04": "Schalke 04",
    "Fortuna Düsseldorf": "Fortuna Dusseldorf",
    "Fußball-Club Augsburg 1907": "Augsburg",
    "Fußball-Club Augsburg 1907 GmbH & Co. KGaA": "Augsburg",
    "Fußball-Club Bayern München e. V.": "Bayern Munich",
    "Fußball-Club St. Pauli von 1910": "St Pauli",
    "Hamburger Sport Verein": "Hamburger SV",
    "Hamburger Sport-Verein e.V.": "Hamburger SV",
    "Hannover 96": "Hannover 96",
    "Hannover 96 GmbH & Co. KGaA": "Hannover 96",
    "Hertha BSC": "Hertha Berlin",
    "Holstein Kiel": "Holstein Kiel",
    "RasenBallsport Leipzig": "RB Leipzig",
    "RasenBallsport Leipzig e.V.": "RB Leipzig",
    "SC Freiburg": "Freiburg",
    "SC Paderborn 07": "Paderborn",
    "SV Darmstadt 98": "Darmstadt",
    "SpVgg Greuther Fürth": "Greuther Furth",
    "SpVgg Greuther Fürth 1903": "Greuther Furth",
    "Sport-Club Freiburg": "Freiburg",
    "Sport-Verein Darmstadt 1898 e.V.": "Darmstadt",
    "Sportverein Werder Bremen von 1899": "Werder Bremen",
    "Sportverein Werder Bremen von 1899 e.V.": "Werder Bremen",
    "TSG 1899 Hoffenheim Fußball-Spielbetriebs GmbH": "Hoffenheim",
    "Turn- und Sportgemeinschaft 1899 Hoffenheim Fußball-Spielbetriebs": "Hoffenheim",
    "Turn- und Sportgemeinschaft 1899 Hoffenheim e.V.": "Hoffenheim",
    "Verein für Bewegungsspiele Stuttgart 1893": "VfB Stuttgart",
    "VfB Stuttgart 1893 e.V.": "VfB Stuttgart",
    "VfL Bochum": "VfL Bochum",
    "VfL Bochum 1848 Fußballgemeinschaft e.V.": "VfL Bochum",
    "VfL Wolfsburg-Fußball GmbH": "VfL Wolfsburg",
    "Verein für Leibesübungen Wolfsburg": "VfL Wolfsburg",
    "FC St. Pauli von 1910 e.V.": "St Pauli",
    # --- IT1 (Serie A) ---
    # TM uses different name variants across seasons
    "AC Carpi": "Carpi",
    "AC Milan": "AC Milan",
    "AC Monza": "Monza",
    "AS Roma": "AS Roma",
    "ACF Fiorentina": "Fiorentina",
    "AC Chievo Verona": "Chievo",
    "Associazione Calcio Fiorentina": "Fiorentina",
    "Associazione Calcio Milan": "AC Milan",
    "Associazione Sportiva Roma": "AS Roma",
    "Atalanta Bergamasca Calcio": "Atalanta",
    "Atalanta Bergamasca Calcio S.p.a.": "Atalanta",
    "Benevento Calcio": "Benevento",
    "Bologna FC 1909": "Bologna",
    "Bologna Football Club 1909": "Bologna",
    "Brescia Calcio": "Brescia",
    "Cagliari Calcio": "Cagliari",
    "Calcio Como": "Como",
    "Carpi FC 1909": "Carpi",
    "Catania FC": "Catania",
    "Cesena FC": "Cesena",
    "ChievoVerona": "Chievo",
    "Chievo Verona": "Chievo",
    "Delfino Pescara 1936": "Pescara",
    "Empoli Football Club": "Empoli",
    "FC Crotone": "Crotone",
    "FC Empoli": "Empoli",
    "FC Internazionale Milano": "Inter",
    "Football Club Internazionale Milano S.p.A.": "Inter",
    "Frosinone Calcio": "Frosinone",
    "Genoa Cricket and Football Club": "Genoa",
    "Hellas Verona FC": "Verona",
    "Juventus Football Club": "Juventus",
    "Juventus Football Club S.p.A.": "Juventus",
    "Palermo FC": "Palermo",
    "Parma Calcio 1913": "Parma",
    "Pisa Sporting Club": "Pisa",
    "SPAL": "SPAL",
    "SPAL 2013 Ferrara": "SPAL",
    "Siena FC": "Siena",
    "Società Sportiva Calcio Napoli": "Napoli",
    "Società Sportiva Calcio Napoli S.p.A.": "Napoli",
    "Società Sportiva Lazio S.p.A.": "Lazio",
    "SS Lazio": "Lazio",
    "SSC Napoli": "Napoli",
    "Spezia Calcio": "Spezia",
    "Torino Calcio": "Torino",
    "Torino Football Club S.p.A.": "Torino",
    "U.C. Sampdoria": "Sampdoria",
    "UC Sampdoria": "Sampdoria",
    "US Cremonese": "Cremonese",
    "US Lecce": "Lecce",
    "US Livorno 1915": "Livorno",
    "US Palermo": "Palermo",
    "US Salernitana 1919": "Salernitana",
    "US Sassuolo Calcio": "Sassuolo",
    "Udinese Calcio": "Udinese",
    "Udinese Calcio S.p.A.": "Udinese",
    "Unione Sportiva Cremonese S.p.A.": "Cremonese",
    "Unione Sportiva Lecce": "Lecce",
    "Unione Sportiva Sassuolo Calcio": "Sassuolo",
    "Unione Venezia Football Club": "Venezia",
    "Venezia FC": "Venezia",
    "Verona Hellas Football Club": "Verona",
    "US Città di Palermo": "Palermo",
    # --- FR1 (Ligue 1) ---
    # TM uses different name variants across seasons
    "AC Ajaccio": "Ajaccio",
    "AJ Auxerre": "Auxerre",
    "AS Nancy-Lorraine": "Nancy",
    "AS Saint-Étienne": "Saint-Etienne",
    "Amiens SC": "Amiens",
    "Angers SCO": "Angers",
    "Angers Sporting Club de l'Ouest": "Angers",
    "AS Monaco FC": "Monaco",
    "Association de la Jeunesse auxerroise": "Auxerre",
    "Association sportive de Monaco Football Club": "Monaco",
    "Clermont Foot 63": "Clermont",
    "Dijon FCO": "Dijon",
    "Dijon Football Côte-d'Or": "Dijon",
    "EA Guingamp": "Guingamp",
    "ESTAC Troyes": "Troyes",
    "En Avant de Guingamp": "Guingamp",
    "FC Girondins Bordeaux": "Bordeaux",
    "FC Girondins de Bordeaux": "Bordeaux",
    "FC Lorient": "Lorient",
    "FC Metz": "Metz",
    "FC Nantes": "Nantes",
    "FC Sochaux-Montbéliard": "Sochaux",
    "Football Club Lorient-Bretagne Sud": "Lorient",
    "Football Club de Metz": "Metz",
    "Football Club de Nantes": "Nantes",
    "GFC Ajaccio": "Ajaccio",
    "Havre Athletic Club": "Le Havre",
    "Le Havre Athletic Club": "Le Havre",
    "LOSC Lille": "Lille",
    "Lille Olympique Sporting Club": "Lille",
    "Montpellier HSC": "Montpellier",
    "Nîmes Olympique": "Nimes",
    "OGC Nice": "Nice",
    "Olympique Gymnaste Club Nice Côte d'Azur": "Nice",
    "Olympique Lyonnais": "Lyon",
    "Olympique de Marseille": "Marseille",
    "Paris Football Club": "Paris FC",
    "Paris Saint-Germain Football Club": "Paris Saint Germain",
    "RC Lens": "Lens",
    "RC Strasbourg Alsace": "Strasbourg",
    "Racing Club de Lens": "Lens",
    "Racing Club de Strasbourg Alsace": "Strasbourg",
    "SC Bastia": "Bastia",
    "SM Caen": "Caen",
    "Stade Brestois 29": "Brest",
    "Stade Malherbe Caen": "Caen",
    "Stade Reims": "Reims",
    "Stade Rennais FC": "Rennes",
    "Stade Rennais Football Club": "Rennes",
    "Stade brestois 29": "Brest",
    "Stade de Reims": "Reims",
    "Thonon Évian Grand Genève FC": "Evian Thonon Gaillard",
    "Toulouse FC": "Toulouse",
    "Toulouse Football Club": "Toulouse",
    "Valenciennes FC": "Valenciennes",
    "Évian Thonon Gaillard FC": "Evian Thonon Gaillard",
    # --- NL1 (Eredivisie) ---
    # Parquet uses: Ajax Amsterdam, Feyenoord, Groningen, Nijmegen, Zwolle,
    # Waalwijk, Roda JC, VVV Venlo (no hyphen)
    "ADO Den Haag": "ADO Den Haag",
    "AFC Ajax Amsterdam": "Ajax Amsterdam",
    "Alkmaar Zaanstreek": "AZ Alkmaar",
    "Almere City FC": "Almere City",
    "De Graafschap Doetinchem": "Graafschap",
    "Eindhovense Voetbalvereniging Philips Sport Vereniging": "PSV Eindhoven",
    "Excelsior Rotterdam": "Excelsior",
    "FC Dordrecht": "Dordrecht",
    "FC Emmen": "FC Emmen",
    "Feyenoord Rotterdam": "Feyenoord",
    "Football Club Groningen": "Groningen",
    "Football Club Twente": "Twente",
    "Football Club Utrecht": "Utrecht",
    "Football Club Volendam": "Volendam",
    "Fortuna Sittardia Combinatie": "For Sittard",
    "Go Ahead Eagles": "Go Ahead Eagles",
    "Heracles Almelo": "Heracles",
    "Nijmegen Eendracht Combinatie": "Nijmegen",
    "Nooit Opgeven Altijd Doorzetten Aangenaam Door Vermaak En Nuttig Door Ontspanning Combinatie Breda": "NAC Breda",
    "Prins Hendrik Ende Desespereert Nimmer Combinatie Zwolle": "Zwolle",
    "RKC Waalwijk": "Waalwijk",
    "Roda JC Kerkrade": "Roda JC",
    "SC Cambuur Leeuwarden": "Cambuur",
    "Sparta Rotterdam": "Sparta Rotterdam",
    "Sportclub Heerenveen": "Heerenveen",
    "Sportclub Telstar": "Telstar",
    "VVV-Venlo": "VVV Venlo",
    "Vitesse Arnhem": "Vitesse",
    "Willem II Tilburg": "Willem II",
    # --- PO1 (Primeira Liga) ---
    # Parquet uses: Beira Mar (no hyphen), Aves (not Desportivo Aves),
    # Setubal (not Vitoria Setubal), Estrela (not Est Amadora for some)
    "AVS Futebol SAD": "AVS",
    "Académica Coimbra": "Academica",
    "B SAD": "Belenenses",
    "Boavista FC": "Boavista",
    "CD Feirense": "Feirense",
    "CF Os Belenenses": "Belenenses",
    "CF União Madeira (-2021)": "Uniao Madeira",
    "CS Marítimo": "Maritimo",
    "Casa Pia Atlético Clube": "Casa Pia",
    "Club Football Estrela da Amadora": "Est Amadora",
    "Clube Desportivo Nacional": "Nacional",
    "Clube Desportivo Santa Clara": "Santa Clara",
    "Clube Desportivo de Tondela": "Tondela",
    "Desportivo Aves (- 2020)": "Aves",
    "FC Paços de Ferreira": "Pacos Ferreira",
    "FC Penafiel": "Penafiel",
    "FC Vizela": "Vizela",
    "Futebol Clube de Alverca": "Alverca",
    "Futebol Clube de Arouca": "Arouca",
    "Futebol Clube de Famalicão": "Famalicao",
    "Futebol Clube do Porto": "Porto",
    "GD Chaves": "Chaves",
    "Gil Vicente Futebol Clube": "Gil Vicente",
    "Grupo Desportivo Estoril Praia": "Estoril",
    "Moreirense Futebol Clube": "Moreirense",
    "Portimonense SC": "Portimonense",
    "Rio Ave Futebol Clube": "Rio Ave",
    "SC Beira-Mar": "Beira Mar",
    "SC Farense": "Farense",
    "SC Olhanense": "Olhanense",
    "Sport Lisboa e Benfica": "Benfica",
    "Sporting Clube de Braga": "Sp Braga",
    "Sporting Clube de Portugal": "Sp Lisbon",
    "Vitória Setúbal FC": "Setubal",
    "Vitória Sport Clube": "Vitoria Guimaraes",
    # --- BE1 (Jupiler Pro League) ---
    # Parquet uses: Dender, Bergen, St Truiden, Waregem, Mechelen,
    # Louvieroise (for RAAL)
    "Beerschot AC": "Beerschot VA",
    "Beerschot VA": "Beerschot VA",
    "Cercle Brugge Koninklijke Sportvereniging": "Cercle Brugge",
    "Club Brugge Koninklijke Voetbalvereniging": "Club Brugge",
    "FC Verbroedering Denderhoutem Denderleeuw Eendracht Hekelgem": "Dender",
    "KAS Eupen": "Eupen",
    "KSC Lokeren (- 2020)": "Lokeren",
    "KV Kortrijk": "Kortrijk",
    "KV Oostende": "Oostende",
    "Koninklijke Atletiek Associatie Gent": "Gent",
    "Koninklijke Racing Club Genk": "Genk",
    "Koninklijke Sint-Truidense Voetbalvereniging": "St Truiden",
    "Koninklijke Voetbal Club Westerlo": "Westerlo",
    "Lierse SK (- 2018)": "Lierse",
    "Oud-Heverlee Leuven": "Oud-Heverlee Leuven",
    "RAAL La Louvière": "Louvieroise",
    "RAEC Mons (- 2015)": "Bergen",
    "RFC Seraing": "Seraing",
    "RWD Molenbeek": "RWD Molenbeek",
    "Royal Antwerp Football Club": "Antwerp",
    "Royal Charleroi Sporting Club": "Charleroi",
    "Royal Excel Mouscron (-2022)": "Mouscron",
    "Royal Sporting Club Anderlecht": "Anderlecht",
    "Royal Standard Club de Liège": "Standard Liege",
    "Royale Union Saint-Gilloise": "St. Gilloise",
    "SK Beveren": "Beveren",
    "Sportvereniging Zulte Waregem": "Waregem",
    "Yellow-Red Koninklijke Voetbalclub Mechelen": "Mechelen",
    # --- TR1 (Super Lig) ---
    "Adana Demirspor": "Ad. Demirspor",
    "Adanaspor": "Adanaspor",
    "Akhisarspor": "Akhisar Belediyespor",
    "Alanyaspor": "Alanyaspor",
    "Altay SK": "Altay",
    "Ankaraspor": "Ankaraspor",
    "Antalyaspor": "Antalyaspor",
    "Balikesirspor": "Balikesirspor",
    "Beşiktaş Jimnastik Kulübü": "Besiktas",
    "Bodrum FK": "Bodrumspor",
    "Bursaspor": "Bursaspor",
    "Denizlispor": "Denizlispor",
    "Elazigspor": "Elazigspor",
    "Erzurumspor FK": "Erzurum BB",
    "Eskisehirspor": "Eskisehirspor",
    "Eyüp Spor Kulübü": "Eyupspor",
    "Fatih Karagümrük Sportif Faaliyetler San. Tic. A.Ş.": "Karagumruk",
    "Fenerbahçe Spor Kulübü": "Fenerbahce",
    "Galatasaray Spor Kulübü": "Galatasaray",
    "Gaziantep Futbol Kulübü A.Ş.": "Gaziantep",
    "Gaziantepspor (- 2020)": "Gaziantepspor",
    "Gençlerbirliği Spor Kulübü": "Genclerbirligi",
    "Giresunspor": "Giresunspor",
    "Göztepe Sportif Yatırımlar A.Ş.": "Goztep",  # noqa: RUF001
    "Hatayspor": "Hatayspor",
    "Istanbulspor": "Istanbulspor",
    "Kardemir Karabükspor": "Karabukspor",
    "Kasımpaşa A.Ş.": "Kasimpasa",  # noqa: RUF001
    "Kayseri Erciyesspor": "Erciyesspor",
    "Kayserispor Kulübü": "Kayserispor",
    "Kocaelispor Kulübü": "Kocaelispor",
    "Konyaspor": "Konyaspor",
    "MKE Ankaragücü": "Ankaragucu",
    "Mersin Talimyurdu SK": "Mersin Idman Yurdu",
    "Orduspor": "Orduspor",
    "Pendikspor": "Pendikspor",
    "Samsunspor": "Samsunspor",
    "Sivasspor": "Sivasspor",
    "Trabzonspor Kulübü": "Trabzonspor",
    "Yeni Malatyaspor": "Yeni Malatyaspor",
    "Çaykur Rizespor Kulübü": "Rizespor",
    "Ümraniyespor": "Umraniyespor",
    "İstanbul Başakşehir Futbol Kulübü": "Buyuksehyr",
    # --- GR1 (Super League) ---
    # Parquet uses: AEK, Apollon, Giannina, Kallonis, Larisa,
    # Levadeiakos, OFI Crete
    "A.G.S Asteras Tripolis": "Asteras Tripolis",
    "AEL Kalloni": "Kallonis",
    "AO Platanias": "Platanias",
    "AO Xanthi": "Xanthi",
    "AOK Kerkyra": "Kerkyra",
    "APO Levadiakos Football Club": "Levadeiakos",
    "APS Atromitos Athinon": "Atromitos",
    "Apollon Smyrnis": "Apollon",
    "Aris Thessalonikis": "Aris",
    "Athens Kallithea": "Athens Kallithea",
    "Athlitiki Enosi Kifisias": "AEK",
    "Athlitiki Enosi Konstantinoupoleos": "AEK",
    "Athlitiki Enosi Larisas": "Larisa",
    "GS Ergotelis": "Ergotelis",
    "Ionikos Nikeas": "Ionikos",
    "Iraklis Thessaloniki": "Iraklis",
    "Niki Volou": "Niki Volos",
    "Olympiakos Syndesmos Filathlon Peiraios": "Olympiakos",
    "Omilos Filathlon Irakliou FC": "OFI Crete",
    "PAS Giannina": "Giannina",
    "PAS Lamia 1964": "Lamia",
    "Panathinaikos Athlitikos Omilos": "Panathinaikos",
    "Panetolikos Agrinio": "Panetolikos",
    "Panionios Athens": "Panionios",
    "Panserraikos Serres": "Panserraikos",
    "Panthessalonikios Athlitikos Omilos Konstantinoupoliton": "PAOK",
    "Panthrakikos Komotini": "Panthrakikos",
    "Veria NPS": "Veria",
    "Volou Neos Podosferikos Syllogos": "Volos NFC",
    # --- SC1 (Scottish Premiership) ---
    # Parquet uses: Inverness C, Partick, St Johnstone, St Mirren
    "Aberdeen Football Club": "Aberdeen",
    "Dundee Football Club": "Dundee",
    "Dundee United Football Club": "Dundee United",
    "Falkirk Football & Athletic Club": "Falkirk",
    "Hamilton Academical FC": "Hamilton",
    "Heart of Midlothian Football Club": "Hearts",
    "Hibernian Football Club": "Hibernian",
    "Inverness Caledonian Thistle FC": "Inverness C",
    "Kilmarnock Football Club": "Kilmarnock",
    "Livingston Football Club": "Livingston",
    "Motherwell Football Club": "Motherwell",
    "Partick Thistle FC": "Partick",
    "Rangers Football Club": "Rangers",
    "Ross County FC": "Ross County",
    "Saint Mirren Football Club": "St Mirren",
    "St. Johnstone FC": "St Johnstone",
    "The Celtic Football Club": "Celtic",
}


def _normalize_tm_name(name: str) -> str:
    """Map a TM official name to canonical, then run normalize_team_name.

    Two-stage resolution:
    1. TM_NAME_TO_CANONICAL for verbose TM -> short canonical
    2. normalize_team_name for any remaining alias resolution
    """
    mapped = TM_NAME_TO_CANONICAL.get(name, name)
    return normalize_team_name(mapped)


def _tm_season_to_ours(tm_season: int) -> str:
    """Convert TM season (calendar year of start) to our YYMM format.

    TM season 2023 means 2023/24, which we encode as '2324'.
    """
    start_yy = tm_season % 100
    end_yy = (tm_season + 1) % 100
    return f"{start_yy:02d}{end_yy:02d}"


def download_and_cache_tm_games() -> pd.DataFrame:
    """Download tm_games from CDN or load from local cache.

    Returns:
        Full games DataFrame from Transfermarkt CDN.
    """
    cache_path = CACHE_DIR / "games.parquet"
    if cache_path.exists():
        logger.info("loading_cached_tm_games", path=str(cache_path))
        return pd.read_parquet(cache_path)

    logger.info("downloading_tm_games_from_cdn")
    df = _download_tm_csv("games")
    if df is None:
        logger.error("tm_games_download_failed")
        return pd.DataFrame()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    logger.info("cached_tm_games", rows=len(df), path=str(cache_path))
    return df


def download_and_cache_tm_players() -> pd.DataFrame:
    """Download tm_players from CDN or load from local cache.

    Returns:
        Full players DataFrame from Transfermarkt CDN.
    """
    cache_path = CACHE_DIR / "players.parquet"
    if cache_path.exists():
        logger.info("loading_cached_tm_players", path=str(cache_path))
        return pd.read_parquet(cache_path)

    logger.info("downloading_tm_players_from_cdn")
    # Rate limit: wait 5 seconds between CDN requests
    time.sleep(5)
    df = _download_tm_csv("players")
    if df is None:
        logger.error("tm_players_download_failed")
        return pd.DataFrame()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    logger.info("cached_tm_players", rows=len(df), path=str(cache_path))
    return df


def filter_tm_games_for_league(
    all_games: pd.DataFrame,
    tm_competition_id: str,
) -> pd.DataFrame:
    """Filter TM games to a single competition and normalize names.

    Args:
        all_games: Full TM games DataFrame.
        tm_competition_id: TM competition ID (e.g. 'NL1').

    Returns:
        Filtered DataFrame with normalized team names and our season format.
    """
    league_games = all_games[
        all_games["competition_id"] == tm_competition_id
    ].copy()

    if league_games.empty:
        return league_games

    league_games["home_club_name_orig"] = league_games["home_club_name"]
    league_games["away_club_name_orig"] = league_games["away_club_name"]
    league_games["home_club_name"] = league_games["home_club_name"].apply(
        _normalize_tm_name
    )
    league_games["away_club_name"] = league_games["away_club_name"].apply(
        _normalize_tm_name
    )

    league_games["our_season"] = league_games["season"].apply(
        _tm_season_to_ours
    )
    league_games["date"] = pd.to_datetime(league_games["date"])

    return league_games


def compute_match_rate_for_league(
    parquet_league: pd.DataFrame,
    tm_league: pd.DataFrame,
) -> dict[str, int]:
    """Compute join statistics between parquet matches and TM games.

    Args:
        parquet_league: Matches from the parquet for one league.
        tm_league: TM games for the same league (normalized names).

    Returns:
        Dict with total_parquet, total_tm, matched, unmatched counts.
    """
    parquet_dates = pd.to_datetime(parquet_league["date"]).dt.strftime(
        "%Y-%m-%d"
    )
    parquet_keys = set(
        zip(
            parquet_dates,
            parquet_league["home_team"],
            parquet_league["away_team"],
            strict=True,
        )
    )

    tm_dates = tm_league["date"].dt.strftime("%Y-%m-%d")
    tm_keys = set(
        zip(
            tm_dates,
            tm_league["home_club_name"],
            tm_league["away_club_name"],
            strict=True,
        )
    )

    matched = parquet_keys & tm_keys
    return {
        "total_parquet": len(parquet_keys),
        "total_tm": len(tm_keys),
        "matched": len(matched),
        "unmatched_parquet": len(parquet_keys - tm_keys),
    }


def find_unmapped_tm_names(
    tm_league: pd.DataFrame,
    parquet_league: pd.DataFrame,
) -> set[str]:
    """Find TM team names that have no match in the parquet.

    Useful for diagnosing name mapping gaps.

    Args:
        tm_league: TM games with normalized names.
        parquet_league: Parquet matches for the league.

    Returns:
        Set of TM normalized names not found in parquet teams.
    """
    parquet_teams = set(parquet_league["home_team"].unique()) | set(
        parquet_league["away_team"].unique()
    )
    tm_teams = set(tm_league["home_club_name"].unique()) | set(
        tm_league["away_club_name"].unique()
    )
    return tm_teams - parquet_teams


def integrate_formations_for_league(
    df_league: pd.DataFrame,
    tm_league_games: pd.DataFrame,
) -> pd.DataFrame:
    """Run add_formation_features on a single league's data.

    Passes the TM games directly via tm_games_df parameter,
    avoiding any database dependency.

    Args:
        df_league: Parquet rows for one league.
        tm_league_games: TM games for the same league (normalized).

    Returns:
        DataFrame with formation features populated.
    """
    if df_league.empty or tm_league_games.empty:
        return df_league.copy()

    result = add_formation_features(
        df=df_league,
        db=None,
        tm_games_df=tm_league_games,
    )
    return result


def integrate_market_values(
    df_league: pd.DataFrame,
    tm_players: pd.DataFrame,
    tm_competition_id: str,
) -> pd.DataFrame:
    """Add aggregate market value features per team per match.

    Computes squad_market_value_home and squad_market_value_away
    by summing current_club player market values at the time of
    the match (latest valuation before match date).

    Args:
        df_league: Parquet rows for one league.
        tm_players: Full TM players DataFrame.
        tm_competition_id: Competition ID for filtering.

    Returns:
        DataFrame with market value columns added.
    """
    result = df_league.copy()

    league_players = tm_players[
        tm_players["current_club_domestic_competition_id"] == tm_competition_id
    ].copy()

    if league_players.empty or "market_value_in_eur" not in league_players.columns:
        result["home_squad_market_value"] = np.nan
        result["away_squad_market_value"] = np.nan
        result["market_value_ratio"] = np.nan
        return result

    league_players["club_norm"] = league_players["current_club_name"].apply(
        _normalize_tm_name
    )

    squad_values = (
        league_players.groupby("club_norm")["market_value_in_eur"]
        .sum()
        .to_dict()
    )

    result["home_squad_market_value"] = result["home_team"].map(squad_values)
    result["away_squad_market_value"] = result["away_team"].map(squad_values)
    result["market_value_ratio"] = (
        result["home_squad_market_value"]
        / result["away_squad_market_value"].replace(0, np.nan)
    )

    return result


def _safe_print(text: str) -> None:
    """Print text with fallback for non-UTF8 consoles (Windows cp1250)."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def main() -> None:
    """Main entry point for Transfermarkt integration."""
    parser = argparse.ArgumentParser(
        description="Integrate Transfermarkt data into expansion leagues"
    )
    parser.add_argument(
        "--leagues",
        nargs="*",
        help="TM competition IDs to process (default: all expansion)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute stats but don't write parquet",
    )
    parser.add_argument(
        "--include-top5",
        action="store_true",
        help="Also re-process top-5 leagues (they have sparse formation data)",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Force re-download from CDN (ignore local cache)",
    )
    args = parser.parse_args()

    if not PARQUET_PATH.exists():
        print(f"ERROR: Parquet not found at {PARQUET_PATH}")
        sys.exit(1)

    # Determine which leagues to process
    expansion_leagues = {
        k: v
        for k, v in LEAGUE_TO_TM_ID.items()
        if k
        not in {
            "ENG-Premier League",
            "ESP-La Liga",
            "GER-Bundesliga",
            "ITA-Serie A",
            "FRA-Ligue 1",
        }
    }

    target_leagues = (
        dict(LEAGUE_TO_TM_ID) if args.include_top5 else dict(expansion_leagues)
    )

    if args.leagues:
        target_leagues = {
            k: v for k, v in target_leagues.items() if v in args.leagues
        }

    if not target_leagues:
        print("No target leagues matched. Available TM IDs:")
        for name, tid in LEAGUE_TO_TM_ID.items():
            print(f"  {tid} -> {name}")
        sys.exit(1)

    # Handle cache refresh
    if args.refresh_cache:
        for cached_file in CACHE_DIR.glob("*.parquet"):
            cached_file.unlink()
            print(f"Removed cache: {cached_file}")

    # Download data
    print("=" * 70)
    print("Step 1: Download Transfermarkt data")
    print("=" * 70)
    all_tm_games = download_and_cache_tm_games()
    all_tm_players = download_and_cache_tm_players()

    if all_tm_games.empty:
        print("FATAL: Could not download TM games data")
        sys.exit(1)

    # Load parquet
    print("\n" + "=" * 70)
    print("Step 2: Load parquet and process leagues")
    print("=" * 70)
    df = pd.read_parquet(PARQUET_PATH)
    original_shape = df.shape
    print(f"Loaded parquet: {df.shape[0]} rows, {df.shape[1]} columns")

    # Formation columns that add_formation_features produces
    formation_feature_cols = [
        "home_formation",
        "away_formation",
        "home_num_defenders",
        "home_num_midfielders",
        "home_num_forwards",
        "home_formation_group",
        "away_num_defenders",
        "away_num_midfielders",
        "away_num_forwards",
        "away_formation_group",
        "home_formation_stability_5",
        "home_formation_stability_10",
        "home_win_rate_current_formation_std",
        "away_formation_stability_5",
        "away_formation_stability_10",
        "away_win_rate_current_formation_std",
        "defender_mismatch",
        "midfield_dominance",
    ]

    # Additional columns we check for from the rolling nback features
    nback_cols = [
        "home_win_rate_vs_3back_std",
        "home_win_rate_vs_4back_std",
        "home_win_rate_vs_5back_std",
        "away_win_rate_vs_3back_std",
        "away_win_rate_vs_4back_std",
        "away_win_rate_vs_5back_std",
        "home_goals_scored_vs_3back_std",
        "home_goals_scored_vs_4back_std",
        "home_goals_scored_vs_5back_std",
        "away_goals_scored_vs_3back_std",
        "away_goals_scored_vs_4back_std",
        "away_goals_scored_vs_5back_std",
    ]

    market_value_cols = [
        "home_squad_market_value",
        "away_squad_market_value",
        "market_value_ratio",
    ]

    # Ensure all target columns exist in the master DataFrame
    all_new_cols = formation_feature_cols + nback_cols + market_value_cols
    for col in all_new_cols:
        if col not in df.columns:
            df[col] = np.nan

    report: list[dict[str, object]] = []

    for league_name, tm_id in target_leagues.items():
        _safe_print(f"\n--- {league_name} ({tm_id}) ---")

        league_mask = df["league"] == league_name
        df_league = df[league_mask].copy()

        if df_league.empty:
            print(f"  SKIP: No matches in parquet for {league_name}")
            report.append(
                {
                    "league": league_name,
                    "tm_id": tm_id,
                    "parquet_matches": 0,
                    "tm_games": 0,
                    "matched": 0,
                    "formation_coverage": 0.0,
                    "status": "NO_PARQUET_DATA",
                }
            )
            continue

        # Filter TM games for this league
        tm_league = filter_tm_games_for_league(all_tm_games, tm_id)
        print(
            f"  TM games: {len(tm_league)}, "
            f"with formations: {tm_league['home_club_formation'].notna().sum()}"
        )

        # Compute match rate
        match_stats = compute_match_rate_for_league(df_league, tm_league)
        print(
            f"  Match rate: {match_stats['matched']}/{match_stats['total_parquet']} "
            f"parquet matches found in TM ({match_stats['matched']/max(match_stats['total_parquet'],1)*100:.1f}%)"
        )

        # Report unmapped names
        unmapped = find_unmapped_tm_names(tm_league, df_league)
        if unmapped:
            print(f"  WARNING: {len(unmapped)} unmapped TM team names:")
            for name in sorted(unmapped):
                _safe_print(f"    - {name}")

        # Run formation features
        print("  Computing formation features...")
        enriched = integrate_formations_for_league(df_league, tm_league)

        # Count formation coverage after enrichment
        home_formation_filled = enriched["home_formation"].notna().sum()
        total_rows = len(enriched)
        coverage_pct = home_formation_filled / max(total_rows, 1) * 100

        print(
            f"  Formation coverage: {home_formation_filled}/{total_rows} "
            f"({coverage_pct:.1f}%)"
        )

        # Add market values
        if not all_tm_players.empty:
            print("  Adding market value features...")
            enriched = integrate_market_values(
                enriched, all_tm_players, tm_id
            )
            mv_filled = enriched["home_squad_market_value"].notna().sum()
            print(
                f"  Market value coverage: {mv_filled}/{total_rows} "
                f"({mv_filled/max(total_rows,1)*100:.1f}%)"
            )

        report.append(
            {
                "league": league_name,
                "tm_id": tm_id,
                "parquet_matches": match_stats["total_parquet"],
                "tm_games": match_stats["total_tm"],
                "matched": match_stats["matched"],
                "formation_coverage": coverage_pct,
                "unmapped_names": len(unmapped),
                "status": "OK",
            }
        )

        if not args.dry_run:
            # Write enriched columns back into the master DataFrame
            # Must align indexes to avoid positional mismatch
            enriched.index = df.loc[league_mask].index
            for col in enriched.columns:
                if col not in df.columns:
                    df[col] = np.nan
                df.loc[league_mask, col] = enriched[col].values

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(
        f"{'League':<30} {'Parquet':>8} {'TM':>8} {'Matched':>8} "
        f"{'Fmtn%':>8} {'Unmapped':>8} {'Status':>12}"
    )
    print("-" * 90)
    for r in report:
        print(
            f"{r['league']:<30} {r['parquet_matches']:>8} "
            f"{r.get('tm_games', 0):>8} {r['matched']:>8} "
            f"{r['formation_coverage']:>7.1f}% "
            f"{r.get('unmapped_names', 0):>8} {r['status']:>12}"
        )

    if not args.dry_run:
        # Save
        print(f"\nSaving updated parquet to {PARQUET_PATH}...")
        # Backup original
        backup_path = PARQUET_PATH.with_suffix(".parquet.bak")
        if not backup_path.exists():
            import shutil

            shutil.copy2(PARQUET_PATH, backup_path)
            print(f"  Backup saved to {backup_path}")

        df.to_parquet(PARQUET_PATH, index=False)
        print(
            f"  Saved: {df.shape[0]} rows, {df.shape[1]} columns "
            f"(was {original_shape[0]} rows, {original_shape[1]} columns)"
        )
    else:
        print("\n[DRY RUN] No changes written to parquet.")


if __name__ == "__main__":
    main()

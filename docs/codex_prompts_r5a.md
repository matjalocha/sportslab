# Codex Prompts — R5a More Leagues

> Realizuj sekwencyjnie. Testy RAZ na końcu.
> Po zakończeniu zapisz status w `docs/codex_status_r5a.md`.

---

## TASK-R5a-01: League registry + football-data.co.uk downloader

```
Stwórz centralny rejestr lig i downloader danych z football-data.co.uk.

Pliki do stworzenia:
- packages/ml-in-sports/src/ml_in_sports/processing/leagues.py
- packages/ml-in-sports/src/ml_in_sports/cli/download_leagues_cmd.py
- packages/ml-in-sports/tests/processing/test_leagues.py

leagues.py:
```python
"""League registry and football-data.co.uk data management."""

from dataclasses import dataclass

@dataclass(frozen=True)
class LeagueInfo:
    canonical_name: str      # "ENG-Premier League"
    football_data_code: str  # "E0"
    country: str             # "England"
    tier: int                # 1 = top flight, 2 = second division
    has_xg: bool             # Understat coverage
    has_sofascore: bool      # Sofascore coverage

LEAGUE_REGISTRY: dict[str, LeagueInfo] = {
    "ENG-Premier League": LeagueInfo("ENG-Premier League", "E0", "England", 1, True, True),
    "ESP-La Liga": LeagueInfo("ESP-La Liga", "SP1", "Spain", 1, True, True),
    "GER-Bundesliga": LeagueInfo("GER-Bundesliga", "D1", "Germany", 1, True, True),
    "ITA-Serie A": LeagueInfo("ITA-Serie A", "I1", "Italy", 1, True, True),
    "FRA-Ligue 1": LeagueInfo("FRA-Ligue 1", "F1", "France", 1, True, True),
    "ENG-Championship": LeagueInfo("ENG-Championship", "E1", "England", 2, False, True),
    "NED-Eredivisie": LeagueInfo("NED-Eredivisie", "N1", "Netherlands", 1, False, True),
    "POL-Ekstraklasa": LeagueInfo("POL-Ekstraklasa", "EC", "Poland", 1, False, True),
    "GER-Bundesliga 2": LeagueInfo("GER-Bundesliga 2", "D2", "Germany", 2, False, True),
    "ITA-Serie B": LeagueInfo("ITA-Serie B", "I2", "Italy", 2, False, True),
    "POR-Primeira Liga": LeagueInfo("POR-Primeira Liga", "P1", "Portugal", 1, False, True),
    "BEL-Jupiler Pro League": LeagueInfo("BEL-Jupiler Pro League", "B1", "Belgium", 1, False, True),
    "TUR-Süper Lig": LeagueInfo("TUR-Süper Lig", "T1", "Turkey", 1, False, True),
    "CZE-Fortuna Liga": LeagueInfo("CZE-Fortuna Liga", "CZ", "Czech Republic", 1, False, True),
}

def get_league(name: str) -> LeagueInfo | None:
    return LEAGUE_REGISTRY.get(name)

def get_all_leagues(tier: int | None = None) -> list[LeagueInfo]:
    leagues = list(LEAGUE_REGISTRY.values())
    if tier is not None:
        leagues = [l for l in leagues if l.tier == tier]
    return leagues
```

CLI: `sl download-leagues --leagues "ENG-Championship" "NED-Eredivisie" --seasons 2223 2324 2425`
Downloads football-data.co.uk CSVs to data/odds/{code}/{season}.csv.
Uses existing download_season_csv() from processing/odds/pinnacle.py.

Testy:
- LEAGUE_REGISTRY has all 14 leagues
- get_league returns correct LeagueInfo
- get_all_leagues tier filter works
```

---

## TASK-R5a-02: Team name normalization per new league

```
Rozszerz team_name_replacements.json o nowe ligi.

Pliki do modyfikacji:
- packages/ml-in-sports/src/ml_in_sports/utils/team_name_replacements.json

Dodaj mapowania dla nowych lig. Football-data.co.uk używa skróconych nazw.
Przykłady do dodania:

Championship:
  "Leeds": "Leeds United", "Nott'm Forest": "Nottingham Forest",
  "Sheffield Utd": "Sheffield United", "West Brom": "West Bromwich Albion",
  "Middlesboro": "Middlesbrough", "QPR": "Queens Park Rangers"

Eredivisie:
  "Ajax": "Ajax Amsterdam", "PSV": "PSV Eindhoven",
  "AZ": "AZ Alkmaar", "Den Haag": "ADO Den Haag"

Ekstraklasa:
  "Legia": "Legia Warszawa", "Lech": "Lech Poznań",
  "Cracovia": "MKS Cracovia", "Piast": "Piast Gliwice",
  "Wisla": "Wisła Kraków", "Gornik": "Górnik Zabrze"

Pozostałe ligi: dodaj popularne skróty/aliasy.

Testy: rozszerz test_team_names.py o nowe mapowania.
```

---

## TASK-R5a-03: Feature pipeline for leagues without xG

```
Ligi bez Understat (Championship, Eredivisie, Ekstraklasa, itd.) nie mają xG.
Stwórz fallback feature pipeline.

Pliki do stworzenia:
- packages/ml-in-sports/src/ml_in_sports/features/basic_features.py
- packages/ml-in-sports/tests/features/test_basic_features.py

basic_features.py:
```python
"""Basic feature pipeline for leagues without xG data.

Uses only stats available from football-data.co.uk:
goals, shots, corners, fouls, cards, odds.
Provides rolling averages and form features.
"""

def build_basic_features(df: pd.DataFrame, windows: list[int] = [3, 5, 10]) -> pd.DataFrame:
    """Build features from basic match stats (no xG required).
    
    Features:
    - Rolling goals scored/conceded (home/away)
    - Rolling shots on target
    - Rolling corners
    - Form: W/D/L last N
    - Goal difference rolling
    - Odds-implied features (from avg_home/draw/away)
    - Home advantage (rolling home win rate)
    - League table position (if available)
    
    All use shift(1) to prevent lookahead.
    """
```

Testy:
- Test z syntetycznym DataFrame (no xG columns)
- Test shift(1) prevents lookahead
- Test rolling windows
```

---

## TASK-R5a-04: Multi-league backtest config + experiment

```
Stwórz experiment configs dla nowych lig.

Pliki do stworzenia:
- experiments/championship.yaml
- experiments/eredivisie.yaml
- experiments/ekstraklasa.yaml
- experiments/all_14_leagues.yaml

championship.yaml:
```yaml
name: "ENG-Championship Backtest"
data:
  leagues: ["ENG-Championship"]
  seasons: ["2223", "2324", "2425"]
  markets: ["1x2"]
models:
  - name: lightgbm
    type: lightgbm
    params: {n_estimators: 200, learning_rate: 0.05}
  - name: xgboost
    type: xgboost
    params: {n_estimators: 200}
calibration:
  methods: [temperature, platt, isotonic]
evaluation:
  walk_forward: {train_seasons: 2, test_seasons: 1}
```

all_14_leagues.yaml — all 14 leagues, 3 seasons, LGB + XGB.

Aktualizuj BacktestDataLoader żeby obsługiwał ligi spoza Top-5
(może wymagać rozszerzenia parquet albo ładowania z football-data.co.uk CSVs).
```

---

## TASK-R5a-05: Data ingestion for new leagues (football-data.co.uk → parquet)

```
Stwórz pipeline: download CSV → parse → merge z istniejącym features parquet.

Pliki do stworzenia:
- packages/ml-in-sports/src/ml_in_sports/processing/league_ingestion.py
- packages/ml-in-sports/src/ml_in_sports/cli/ingest_cmd.py

league_ingestion.py:
```python
"""Ingest new league data from football-data.co.uk into features parquet."""

def ingest_league(
    league: str,
    seasons: list[str],
    odds_dir: Path = Path("data/odds"),
    output_parquet: Path = Path("data/features/all_features.parquet"),
) -> int:
    """Download, parse, compute basic features, append to parquet.
    
    1. Download CSVs via download_season_csv()
    2. Parse via load_football_data_csv()  
    3. Compute basic features via build_basic_features()
    4. Append to existing parquet (or create new)
    
    Returns number of matches added.
    """
```

CLI: `sl ingest --league "ENG-Championship" --seasons 2223 2324 2425`

Testy: test z mock CSV data → parquet output.

Po zakończeniu WSZYSTKICH tasków R5a, uruchom:
```bash
uv run ruff check packages/ml-in-sports --fix
uv run mypy packages
uv run pytest packages/ml-in-sports -q
```

Zapisz wynik w docs/codex_status_r5a.md.
```

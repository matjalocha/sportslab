# Codex Tasks — SportsLab

> Taski gotowe do realizacji przez Codex. Każdy jest samodzielny.
> Repo: `c:/Users/Estera/Mateusz/sportslab`
> Stan: 1128 testów, ruff clean, mypy 0 source errors
> 
> Po każdym tasku uruchom:
> ```bash
> uv run ruff check packages/ml-in-sports --fix
> uv run mypy packages
> uv run pytest packages/ml-in-sports -q
> ```

---

## R2 — Remaining Tasks

### TASK-01: SPO-55 — Report faza 2: Calibration Curves + ECE Heatmap (Sekcja C)

**Cel:** Dodać do HTML raportu backtestowego sekcję C z reliability diagram i ECE heatmap.

**Pliki do modyfikacji:**
- `packages/ml-in-sports/src/ml_in_sports/backtesting/report/html.py` — dodać sekcję C w template HTML
- `packages/ml-in-sports/src/ml_in_sports/backtesting/report/charts.py` — dodać `build_reliability_diagram()` i `build_ece_heatmap()`
- `packages/ml-in-sports/src/ml_in_sports/backtesting/report/generator.py` — dodać `calibration_data` i `ece_per_league_season` do `ReportData`

**Pliki do przeczytania (kontekst):**
- `docs/design/backtest_report_spec.md` — sekcja C specyfikacja
- `packages/ml-in-sports/src/ml_in_sports/backtesting/runner.py` — FoldResult ma `predictions` i `actuals`

**Co zaimplementować:**

1. W `charts.py` dodaj:
```python
def build_reliability_diagram(fold_results: list[FoldResult]) -> dict[str, list[tuple[float, float]]]:
    """Per-model calibration curve data: list of (predicted_prob_bin, actual_frequency) tuples.
    
    Bin predictions into 10 equal-width bins. For each bin compute:
    - mean predicted probability
    - actual frequency (fraction of positive outcomes)
    
    For multiclass (1X2): do per-class (home/draw/away) and average.
    """

def build_ece_heatmap(fold_results: list[FoldResult]) -> list[dict]:
    """ECE per (league, season) combination.
    
    Returns list of dicts: {league, season, ece, n_matches}
    Use compute_ece from backtesting.metrics.
    """
```

2. W `generator.py` dodaj pola do `ReportData`:
```python
@dataclass
class ReportData:
    ...
    reliability_data: dict[str, list[tuple[float, float]]]  # model -> [(pred, actual)]
    ece_heatmap: list[dict]  # [{league, season, ece, n_matches}]
```

3. W `html.py` dodaj sekcję C w template (po sekcji B, przed sekcją D):
- Reliability diagram: Plotly scatter + line chart. X = predicted prob, Y = actual frequency. Diagonal dashed line = perfect calibration. One line per model.
- ECE heatmap: Plotly heatmap. X = season, Y = league. Color: green < 1.5% → white 2% → red > 3%.
- Use colors from design spec: LGB=#2D7DD2, XGB=#E36209, TabPFN=#8250DF, Hybrid=#1B2A4A.

**Acceptance criteria:**
- `uv run sl backtest run experiments/hybrid_v1.yaml --synthetic` generates report with Calibration section
- Reliability diagram shows model lines + diagonal
- ECE heatmap shows league × season grid
- All tests pass, ruff clean, mypy clean

---

### TASK-02: SPO-55 — Report faza 2: Kelly Distribution + Edge Violin (Sekcja F)

**Cel:** Dodać sekcję F (stakes & betting activity) do HTML raportu.

**Pliki do modyfikacji:**
- `packages/ml-in-sports/src/ml_in_sports/backtesting/report/html.py` — dodać sekcję F w template
- `packages/ml-in-sports/src/ml_in_sports/backtesting/report/charts.py` — dodać chart builders
- `packages/ml-in-sports/src/ml_in_sports/backtesting/report/generator.py` — dodać dane do ReportData

**Co zaimplementować:**

1. W `charts.py`:
```python
def build_kelly_distribution_chart(fold_results: list[FoldResult]) -> str:
    """Plotly histogram of recommended Kelly fractions.
    
    X = Kelly fraction (%), Y = count.
    Annotation: mean, median, % capped at max_exposure.
    """

def build_edge_per_market_chart(fold_results: list[FoldResult]) -> str:
    """Plotly box plot (or violin) of edge per market type.
    
    X = market (1X2_H, 1X2_D, 1X2_A, OU_Over, OU_Under, BTTS_Y, BTTS_N)
    Y = edge (model_prob - implied_prob) in %
    """

def build_bets_heatmap(fold_results: list[FoldResult]) -> str:
    """Plotly heatmap of bet count per (league, season).
    
    X = season, Y = league. Values = count of bets.
    """
```

2. W `generator.py` dodaj: `kelly_fractions: list[float]`, `edges_per_market: dict[str, list[float]]`, `bets_per_league_season: list[dict]`

3. W `html.py` dodaj sekcję F po sekcji E, przed footer:
- Layout: 3 charts w grid 4col + 4col + 4col

**Acceptance criteria:**
- Report shows Kelly histogram, edge box plot, bets heatmap
- All tests pass

---

### TASK-03: SPO-55 — Report faza 2: Model Comparison Radar + Pairwise Matrix (Sekcja H)

**Cel:** Dodać sekcję H do HTML raportu.

**Pliki do modyfikacji:**
- `packages/ml-in-sports/src/ml_in_sports/backtesting/report/html.py`
- `packages/ml-in-sports/src/ml_in_sports/backtesting/report/charts.py`
- `packages/ml-in-sports/src/ml_in_sports/backtesting/report/generator.py`

**Co zaimplementować:**

1. W `charts.py`:
```python
def build_radar_chart(model_comparison: list[ModelComparisonRow]) -> str:
    """Plotly radar/polar chart comparing models across 6 dimensions.
    
    Dimensions: Log Loss (inverted), ECE (inverted), CLV, ROI, Sharpe, Hit Rate.
    Normalize each to 0-1 percentile rank within available models.
    One line per model, colors from design spec.
    """

def build_pairwise_matrix(aggregate_metrics: dict[str, dict[str, float]]) -> str:
    """Plotly heatmap (triangular) showing log loss difference between model pairs.
    
    Green = row model better, red = column model better.
    """
```

2. W `generator.py`: dane już dostępne w `model_comparison` — wystarczy dodać `radar_data` i `pairwise_data`.

3. W `html.py`: sekcja H po sekcji F. Layout: radar (6col) + pairwise (6col).

**Acceptance criteria:**
- Radar chart visible with model lines
- Pairwise matrix shows model × model grid
- All tests pass

---

## R3 — Bet Slip Implementation

### TASK-04: Daily Bet Slip — Data Layer + CLI

**Cel:** Stworzyć pipeline: load model → predict upcoming matches → compute Kelly stakes → output bet slip.

**Pliki do stworzenia:**
- `packages/ml-in-sports/src/ml_in_sports/prediction/__init__.py`
- `packages/ml-in-sports/src/ml_in_sports/prediction/daily.py`
- `packages/ml-in-sports/src/ml_in_sports/cli/predict_cmd.py`
- `packages/ml-in-sports/tests/prediction/__init__.py`
- `packages/ml-in-sports/tests/prediction/test_daily.py`

**Co zaimplementować:**

`prediction/daily.py`:
```python
@dataclass(frozen=True)
class BetRecommendation:
    """Single bet recommendation for today."""
    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff: datetime
    market: str  # "1x2_home", "1x2_draw", "1x2_away", "over_25", "under_25", "btts_yes", "btts_no"
    model_prob: float
    bookmaker_prob: float
    edge: float  # model_prob - bookmaker_prob
    min_odds: float  # 1 / model_prob
    kelly_fraction: float
    stake_eur: float
    model_agreement: int  # 1-3 (how many models agree)
    best_bookmaker: str
    best_odds: float


class DailyPredictor:
    """Generate today's value bet recommendations.
    
    Uses trained models from last backtest run (saved as pickle).
    Loads upcoming matches from database.
    Computes predictions, calibrates, applies Kelly.
    """
    
    def __init__(
        self,
        model_dir: Path = Path("models/latest"),
        bankroll: float = 5000.0,
        kelly_fraction: float = 0.25,
        min_edge: float = 0.02,
    ) -> None: ...
    
    def predict(self, date: date | None = None) -> list[BetRecommendation]:
        """Generate bet recommendations for a given date.
        
        Args:
            date: Target date. None = today.
        
        Returns:
            List of BetRecommendation sorted by edge descending.
        """
    
    def save_predictions(self, predictions: list[BetRecommendation], output_dir: Path) -> Path:
        """Save predictions as JSON for later results tracking."""
```

CLI `sl predict run`:
```python
@predict_app.command("run")
def run(
    date: str = typer.Option(None, help="Date YYYY-MM-DD, default today"),
    bankroll: float = typer.Option(5000.0),
    kelly_fraction: float = typer.Option(0.25),
    min_edge: float = typer.Option(0.02),
) -> None:
    """Generate today's bet recommendations."""
```

**Note:** For MVP, the predictor can use a synthetic/mock data source (upcoming matches hardcoded or from parquet future rows where result_1x2 is NaN). Real odds scraping comes in TASK-06.

**Testy:**
- Test BetRecommendation creation
- Test DailyPredictor with mock model (returns fixed probs)
- Test filtering by min_edge
- Test Kelly stake computation
- Test sorting by edge
- Test JSON save/load roundtrip
- Test CLI --help works

**Acceptance criteria:**
- `uv run sl predict run --date 2026-04-06` prints bet recommendations
- JSON saved to `predictions/`
- All tests pass

---

### TASK-05: Daily Bet Slip — HTML + Terminal + Telegram Report

**Cel:** Render bet slip w 3 formatach.

**Pliki do stworzenia:**
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/__init__.py`
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/html.py`
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/terminal.py`
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/telegram.py`
- `packages/ml-in-sports/tests/prediction/test_report.py`

**Kontekst designu:** `docs/design/bet_slip_report_spec.md`

**Co zaimplementować:**

`report/html.py`:
- Self-contained HTML (Jinja2 + CSS inline, same design system as backtest report)
- Summary card: N bets, total stake, EV
- Table: match, league, kickoff, market, model P, book P, edge, Kelly %, stake EUR, agreement, bookmaker
- Glossary section with metric descriptions
- Colors: Inter + JetBrains Mono, brand palette

`report/terminal.py`:
- Rich table with color-coded edge and agreement columns
- Summary line at top

`report/telegram.py`:
- Plain text markdown, max 4096 chars
- 3 lines per bet: match | market + edge + Kelly + stake | bookmaker + odds + agreement

**Testy:**
- HTML contains required sections (summary, table, glossary)
- Terminal output is non-empty string
- Telegram output < 4096 chars
- Empty bets → proper empty state message
- 30 bets → telegram truncates to top 15

**Acceptance criteria:**
- `uv run sl predict run --date 2026-04-06` generates HTML + terminal + Telegram output
- HTML opens in browser correctly
- All tests pass

---

### TASK-06: Daily Results Tracker — Data Layer + CLI

**Cel:** After matches complete, log results and compute CLV per bet.

**Pliki do stworzenia:**
- `packages/ml-in-sports/src/ml_in_sports/prediction/results.py`
- `packages/ml-in-sports/src/ml_in_sports/cli/results_cmd.py`
- `packages/ml-in-sports/tests/prediction/test_results.py`

**Co zaimplementować:**

`prediction/results.py`:
```python
@dataclass(frozen=True)
class BetResult:
    """Result of a single bet."""
    recommendation: BetRecommendation
    actual_score: str  # "2-1"
    actual_result: str  # "home", "draw", "away"
    hit: bool
    closing_odds: float | None
    clv: float | None
    pnl: float  # in EUR
    bankroll_after: float


class ResultsTracker:
    """Track bet results and compute daily P&L.
    
    Loads today's predictions JSON, matches with actual results from database,
    computes CLV against Pinnacle closing odds.
    """
    
    def __init__(self, predictions_dir: Path = Path("predictions")) -> None: ...
    
    def process_day(self, date: date) -> list[BetResult]:
        """Process results for a given date."""
    
    def running_totals(self) -> dict[str, float]:
        """Compute running totals across all tracked days.
        
        Returns: {total_bets, hit_rate, roi, mean_clv, current_bankroll, 
                  max_drawdown, current_streak}
        """
```

CLI `sl results run`:
```python
@results_app.command("run")
def run(date: str = typer.Option(None, help="Date YYYY-MM-DD, default yesterday")) -> None:
    """Process results and generate report."""
```

**Note:** For MVP, results can be manually entered or loaded from the features parquet (historical matches with known outcomes). Real-time score scraping is a later task.

**Testy:**
- Test BetResult creation from recommendation + actual result
- Test CLV computation with mock closing odds
- Test running_totals accumulation
- Test JSON persistence (load predictions, match with results)
- Test edge cases: no predictions for date, partial results

**Acceptance criteria:**
- `uv run sl results run --date 2026-04-05` prints results
- Running totals computed correctly
- All tests pass

---

### TASK-07: Daily Results — HTML + Terminal + Telegram Report

**Cel:** Render daily results w 3 formatach.

**Pliki do stworzenia:**
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/results_html.py`
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/results_terminal.py`
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/results_telegram.py`
- `packages/ml-in-sports/tests/prediction/test_results_report.py`

**Kontekst designu:** `docs/design/bet_slip_report_spec.md` — sekcja 2 (Daily Results Tracker)

**Co zaimplementować:**
- HTML: Summary card (W/L, P&L, CLV, bankroll) + results table (kolorowane WIN/MISS) + running totals
- Terminal: Rich table, color-coded outcomes
- Telegram: TRAFIONE/PUDŁA grouping, summary line

**Same design system** as bet slip (Inter + JetBrains Mono, brand colors).

**Acceptance criteria:**
- Report shows per-bet results with P&L and CLV
- Running totals visible
- All 3 formats work
- All tests pass

---

### TASK-08: Weekly Performance Report — Data + HTML + Terminal + Telegram

**Cel:** Weekly summary combining all daily results.

**Pliki do stworzenia:**
- `packages/ml-in-sports/src/ml_in_sports/prediction/weekly.py`
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/weekly_html.py`
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/weekly_terminal.py`
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/weekly_telegram.py`
- `packages/ml-in-sports/src/ml_in_sports/cli/weekly_cmd.py`
- `packages/ml-in-sports/tests/prediction/test_weekly.py`

**Kontekst designu:** `docs/design/bet_slip_report_spec.md` — sekcja 3 (Weekly Performance Report)

**Co zaimplementować:**
- Weekly summary card: bets, P&L, bankroll change, CLV 7d, ROI 7d
- Daily P&L bar chart (Plotly, 7 bars mon-sun)
- Cumulative bankroll chart (Plotly line, week view)
- Per-league breakdown table
- Per-market breakdown table
- Kelly vs flat comparison
- Best/worst 3 bets

CLI `sl weekly run`:
```python
@weekly_app.command("run")
def run(week: str = typer.Option(None, help="Week start date, default last Monday")) -> None:
```

**Acceptance criteria:**
- `uv run sl weekly run` generates weekly report
- Charts visible in HTML
- Telegram < 4096 chars
- All tests pass

---

### TASK-09: Telegram Bot Integration

**Cel:** Telegram bot that pushes daily bet slips and responds to commands.

**Pliki do stworzenia:**
- `packages/ml-in-sports/src/ml_in_sports/notification/__init__.py`
- `packages/ml-in-sports/src/ml_in_sports/notification/telegram.py`
- `packages/ml-in-sports/tests/notification/test_telegram.py`

**Co zaimplementować:**
```python
class TelegramNotifier:
    """Send messages to a Telegram chat via Bot API.
    
    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in env vars.
    """
    
    def __init__(self) -> None: ...
    def send_message(self, text: str) -> bool: ...
    def send_bet_slip(self, recommendations: list[BetRecommendation]) -> bool: ...
    def send_results(self, results: list[BetResult]) -> bool: ...
    def send_weekly(self, weekly_data: WeeklyData) -> bool: ...
```

Add to settings.py:
```python
telegram_bot_token: str = ""
telegram_chat_id: str = ""
```

CLI `sl notify`:
```python
@notify_app.command("bet-slip")
def bet_slip(date: str = typer.Option(None)) -> None:
    """Send today's bet slip via Telegram."""
```

**Testy (mock, no real API calls):**
- Test message formatting (< 4096 chars)
- Test send_message with mock httpx
- Test graceful failure when token not configured

**Acceptance criteria:**
- `TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=yyy uv run sl notify bet-slip` sends message
- Without token → graceful error message
- All tests pass

---

### TASK-10: Live Odds Scraper (STS)

**Cel:** Scrape current odds from STS.pl for upcoming matches.

**Pliki do stworzenia:**
- `packages/ml-in-sports/src/ml_in_sports/processing/scrapers/__init__.py`
- `packages/ml-in-sports/src/ml_in_sports/processing/scrapers/sts.py`
- `packages/ml-in-sports/tests/processing/scrapers/test_sts.py`

**Co zaimplementować:**
```python
@dataclass(frozen=True)
class OddsSnapshot:
    """Current odds from a bookmaker."""
    bookmaker: str
    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff: datetime
    market: str
    odds: float
    scraped_at: datetime

class StsScraper:
    """Scrape odds from STS.pl website.
    
    Uses requests + BeautifulSoup (no Selenium for MVP).
    Implements rate limiting (1 request per 3 seconds).
    """
    
    def scrape_upcoming(self, leagues: list[str] | None = None) -> list[OddsSnapshot]: ...
```

**Note:** STS.pl structure may change. Include robust error handling and fallback. Tests should use saved HTML fixtures (not live requests).

**Testy:**
- Test HTML parsing with saved fixture
- Test rate limiting
- Test error handling (404, timeout, changed HTML)
- Test OddsSnapshot creation

**Acceptance criteria:**
- `uv run python -c "from ml_in_sports.processing.scrapers.sts import StsScraper"` imports
- Tests pass with fixtures
- No live HTTP calls in tests

---

## General Tasks

### TASK-11: Git Commit All R2 Work

**Cel:** Commit everything done in R1+R2 to git.

**Komendy:**
```bash
cd c:/Users/Estera/Mateusz/sportslab
git add -A
git status  # review what's being committed
# Commit with message:
git commit -m "feat: R1 complete + R2 backtest framework, calibration, Kelly, ensemble, reports

R1 (Clean Code):
- 22 modules migrated from research codebase
- structlog, pydantic-settings, Typer CLI, Alembic
- pre-commit, GitHub Actions CI

R2 (Better Models):
- Backtest framework: YAML config → walk-forward → HTML report
- Calibration: Temperature, Platt, Isotonic + auto-selector
- Portfolio Kelly with constraints + shrinkage
- Model registry: LightGBM, XGBoost, TabPFN (optional)
- Stacking ensemble with OOF predictions
- Pinnacle CLV loader (football-data.co.uk)
- Drift detection (PSI) + ECE monitoring
- Leakage detection module (4 strategies)
- 1128 tests, 87.5% coverage, mypy strict clean

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

**Nie pushuj** — tylko local commit.

---

### TASK-12: Generate Fresh Report with All Improvements

**Cel:** Re-generate backtest report z wszystkimi poprawkami (kalibracja, Kelly equity, leakage cleanup).

**Komendy:**
```bash
cd c:/Users/Estera/Mateusz/sportslab
uv run sl backtest run experiments/hybrid_v1.yaml --output-dir reports
# Also quick test:
uv run sl backtest run experiments/quick_test.yaml --output-dir reports
```

**Acceptance criteria:**
- HTML reports generated with:
  - Plotly charts visible (not escaped)
  - Glossary section with metric descriptions
  - Per-season breakdown table
  - 3 equity curve lines (flat, quarter-Kelly, half-Kelly)
  - Calibration methods logged in terminal output

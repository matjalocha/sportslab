# Specyfikacja projektowa raportu backtestowego SportsLab

> **Autor:** Designer + MLEng + Lead
> **Data:** 2026-04-06
> **Status:** Zatwierdzony, gotowy do implementacji
> **Decyzje:** Plotly interactive (nie matplotlib), HTML + terminal (nie PDF), inkrementalne wdrożenie

---

## 0. Kontekst

Raport backtestowy to główny output frameworka R2. Odpowiada na pytanie: **"Czy model bije rynek?"**

**Odbiorcy:**
1. Solo founder (ML/data background) — potrzebuje głębokości i drill-down
2. Potencjalni klienci B2B (tipsterzy, fundusze) — potrzebują profesjonalnego wrażenia i szybkiego werdyktu

**Uruchomienie:**
```bash
sl backtest --config experiments/hybrid_v1.yaml
# Output: raport HTML + terminal summary
```

---

## 1. Sekcje raportu (HTML)

Organizacja w logice **odwróconej piramidy**: werdykt → pogłębienie → dane surowe.

### Sekcja A — Nagłówek i metadane

- Nazwa eksperymentu (z YAML config)
- Data i czas generacji
- Wersja frameworku (git hash)
- Parametry konfiguracji (zwijany blok)
- Czas trwania backtesta

**Layout:** Pełna szerokość, kompaktowy header. Logo po lewej, metadata po prawej.

### Sekcja B — Werdykt (Executive Summary)

**Najważniejsza sekcja.** Odpowiada na "czy to działa?" w 5 sekund.

1. **Semafor werdyktu** — trzy ikony z kolorami:
   - CLV: zielony (> 0) / żółty (-1 do 0%) / czerwony (< -1%)
   - ECE: zielony (< 1.5%) / żółty (1.5-3%) / czerwony (> 3%)
   - ROI: zielony (> 2%) / żółty (-2 do 2%) / czerwony (< -2%)

2. **Hero metrics** — siatka 2x4:
   - CLV (mean), ROI, Sharpe Ratio, ECE (aggregate)
   - Log Loss, Brier Score, N betów, Max Drawdown

3. **Auto-werdykt tekstowy** — generowany na podstawie semafor, np.:
   > "Model osiąga pozytywny ROI (+3.2%), ale CLV jest negatywny (-1.38%),
   > co sugeruje że zysk może wynikać z wariancji, nie z trwałej przewagi."

**Wizualnie:** Każda metryka to mini-karta z nazwą, wartością (duża czcionka JetBrains Mono),
kolorową obwódką (zielona/żółta/czerwona). Click na kartę → scroll do odpowiedniej sekcji.

### Sekcja C — Calibration & Model Quality

**C1. Reliability Diagram (Calibration Curve)**
- Plotly scatter + line, diagonala = perfect calibration
- Osobna linia per model (LGB, XGB, TabPFN, Hybrid)
- Hover: bin range, n_samples, predicted mean, actual freq

**C2. ECE Heatmap — Liga × Sezon**
- Plotly heatmap, skala divergująca (zielony < 1.5% → biały 2% → czerwony > 3%)
- Hover: ECE, Brier, n_matches

**C3. Tabela porównawcza modeli**
- Kolumny: Model | Log Loss | Brier | ECE | Delta vs baseline | 95% CI
- Najlepszy model bold + zielone tło, baseline (market) szary

**C4. Log Loss per sezon (sparklines)**
- Small multiples per model × sezon (styl Tufte)

### Sekcja D — Closing Line Value (CLV)

**D1. Cumulative CLV Chart**
- Plotly line z area fill, osobna linia per model
- Range slider na osi X
- Hover: data meczu, liga, edge, odds, CLV

**D2. CLV Distribution**
- Plotly histogram + KDE overlay
- Adnotacja: mean, median, % positive, SE

**D3. CLV by Edge Bucket**
- Plotly bar (grouped): 0-2%, 2-5%, 5-10%, 10%+
- Zielony jeśli mean CLV > 0, czerwony jeśli < 0

**D4. CLV Tabela per Liga**
- Kolumny: Liga | N bets | Mean CLV | Median CLV | % Positive | SE | 95% CI

### Sekcja E — P&L / ROI Performance

**E1. Equity Curve (Bankroll Growth)**
- Plotly line z area fill
- Linie per strategia Kelly (quarter, half, flat unit)
- Shaded drawdown region
- Dropdown selector dla strategii

**E2. Drawdown Chart (Underwater Plot)**
- Plotly area (odwrócony), gradient czerwony
- Adnotacja: max drawdown value + data

**E3. P&L by League (Stacked Bar)**
- Plotly stacked bar: X = sezon, Y = profit/loss, kolory per liga

**E4. Monthly Returns Heatmap**
- Plotly heatmap (styl kalendarza): X = miesiąc, Y = rok
- Zielony > 0, czerwony < 0

**E5. Tabela podsumowująca**
- Strategie | ROI | Yield | Sharpe | Max DD | Max Losing Streak | Hit Rate | N Bets

### Sekcja F — Stake Distribution & Betting Activity

**F1. Kelly Fraction Distribution** — histogram
**F2. Bets per Liga/Sezon** — heatmap
**F3. Edge Distribution per Market** — violin plot (1X2, OU, BTTS)

### Sekcja G — Feature Importance

**G1. Top 20 Features** — Plotly horizontal bar
**G2. SHAP Beeswarm** — opcjonalny (jeśli SHAP dostępny w runtime)

### Sekcja H — Model Comparison Matrix

**H1. Radar Chart** — 6-8 wymiarów (LL inv, ECE inv, CLV, ROI, Sharpe, Hit Rate)
**H2. Pairwise Win Matrix** — heatmap trójkątna z p-value lub delta LL

### Sekcja I — Walk-Forward Fold Details (zwijalna)

**I1. Tabela foldów** — Fold | Train range | Test range | LL | ECE | CLV | ROI
**I2. Small multiples** — reliability diagram per fold

### Sekcja J — Config & Reproducibility (zwijalna)

- Pełny YAML config
- Git hash, branch, wersje bibliotek
- Random seeds, ścieżki artefaktów, checksums

---

## 2. Paleta kolorów

### Brand

| Token | Hex | Zastosowanie |
|-------|-----|-------------|
| `--color-brand-primary` | `#1B2A4A` | Nagłówki, primary text |
| `--color-brand-accent` | `#2D7DD2` | Linki, CTA |
| `--color-brand-surface` | `#F7F8FA` | Tło strony |
| `--color-brand-surface-raised` | `#FFFFFF` | Karty |
| `--color-brand-border` | `#E2E5EA` | Obramowania |

### Semantyczne

| Token | Hex | Zastosowanie |
|-------|-----|-------------|
| `--color-positive` | `#1A7F37` | Profit, positive CLV |
| `--color-negative` | `#CF222E` | Loss, negative CLV |
| `--color-neutral` | `#9A6700` | Break-even, warning |
| `--color-muted` | `#656D76` | Secondary text |

### Modele (deuteranopia-safe)

| Model | Hex |
|-------|-----|
| LightGBM | `#2D7DD2` (niebieski) |
| XGBoost | `#E36209` (pomarańczowy) |
| TabPFN | `#8250DF` (fioletowy) |
| Hybrid ENS | `#1B2A4A` (ciemny granat) |
| Baseline (market) | `#AFB8C1` (szary) |

### Ligi

| Liga | Hex |
|------|-----|
| EPL | `#3D0B5B` |
| La Liga | `#CF222E` |
| Bundesliga | `#1A7F37` |
| Serie A | `#2D7DD2` |
| Ligue 1 | `#1B2A4A` |

### Skale divergujące (heatmapy)

ECE/P&L: `#1A7F37` (dobry) → `#FFFFFF` (neutralny) → `#CF222E` (zły)

Wszystkie kolory spełniają WCAG AA 4.5:1 na białym tle.

---

## 3. Typografia

| Poziom | Font | Waga | Rozmiar | Zastosowanie |
|--------|------|------|---------|-------------|
| H1 | Inter | 700 | 28px | Tytuł raportu |
| H2 | Inter | 600 | 22px | Sekcje A-J |
| H3 | Inter | 600 | 18px | Podsekcje |
| Body | Inter | 400 | 14px | Tekst opisowy |
| Caption | Inter | 400 | 12px | Opisy wykresów |
| **Data** | **JetBrains Mono** | **500** | **16px/13px** | **Wartości liczbowe** |
| Code | JetBrains Mono | 400 | 13px | YAML, git hash |

**Fallback:** `Inter, -apple-system, 'Segoe UI', sans-serif` / `'JetBrains Mono', 'Fira Code', monospace`

---

## 4. Layout HTML

- **Max width:** 1200px centered
- **Grid:** CSS Grid 12 kolumn, 24px gutter
- **Sticky sidebar** (left, 200px) z nawigacją sekcji A-J
- **Responsive:** desktop-first, 900px → single column
- **Self-contained:** single HTML file, Plotly JS z CDN, fonty z Google Fonts CDN

### Siatka sekcji

```
[A] Header (full width)
[B] Executive Summary — 2x4 grid of metric cards + verdict
[C] Calibration — C1 (8col) + C2 (4col) | C3 table | C4 sparklines
[D] CLV — D1 (full) | D2 (6col) + D3 (6col) | D4 table
[E] P&L — E1 (full) | E2 (full, short) | E3 (6col) + E4 (6col) | E5 table
[F] Stakes — F1 (4col) + F2 (4col) + F3 (4col)
[G] Features — G1 (6col) + G2 (6col, optional)
[H] Comparison — H1 (6col) + H2 (6col)
[I] Walk-Forward (collapsible)
[J] Config (collapsible)
[Footer]
```

---

## 5. Interaktywność (Plotly)

Wszystkie wykresy:
- Hover tooltips z pełnym kontekstem
- Legenda toggle (click = show/hide)
- Zoom (box select)
- Download PNG (toolbar)
- Reset axes

Dodatkowe:
- Sekcja B: click na kartę → scroll do sekcji
- D1: range slider
- E1: dropdown selector strategii Kelly

**Performance:** Przy > 2000 betów — downsample do 500 punktów z zachowaniem min/max.

---

## 6. Wersja terminalowa (Rich)

Kompaktowe podsumowanie (~25 linii), nie konkuruje z HTML:

```
SPORTSLAB BACKTEST REPORT
Experiment: hybrid_ens4_5leagues | 2026-04-05 14:32

VERDICT: [red]MODEL DOES NOT BEAT CLOSING LINE (CLV -1.38%)[/red]

HERO METRICS
  CLV      -1.38% [X]  |  ROI       +3.2% [OK]
  Sharpe    0.87        |  ECE       1.98% [~]
  Log Loss  0.9359      |  Brier     0.198
  N Bets    4,964       |  Max DD   -12.4%

MODEL COMPARISON
  Model       LL      ECE     CLV      ROI     N Bets
  Hybrid ENS  0.9359  1.98%  -1.38%   +3.2%   4,964
  LightGBM    0.9402  2.14%  -1.52%   +2.8%   4,120
  XGBoost     0.9418  2.31%  -1.67%   +1.9%   3,890
  TabPFN      0.9440  2.45%  -0.98%   +4.1%   2,340

CLV PER LEAGUE
  Liga        N Bets  Mean CLV  % Pos   ROI
  EPL         1,102   -0.82%    43.2%   +5.1%
  La Liga       987   -1.54%    40.8%   +2.3%
  ...

Full report: reports/backtest_2026-04-05_hybrid_ens4.html
```

Implementacja: `rich.console.Console`, `rich.table.Table`, `rich.panel.Panel`.

---

## 7. Empty states i edge cases

| Sytuacja | Komunikat |
|----------|-----------|
| 0 betów | "Żaden zakład nie spełnił kryteriów. Sprawdź config." |
| Brak Pinnacle | "CLV niedostępny. Sekcja D pominięta." |
| Brak SHAP | "SHAP niedostępny. Feature importance z LightGBM." |
| Tylko 1 model | Sekcje H pomijane |
| < 100 betów | Żółty banner: "Próba < 100. Wyniki niewiarygodne statystycznie." |
| Bootstrap CI brak | Kolumna CI z kreską i "[TODO]" |

---

## 8. Zasady data viz

1. Osie od zera dla bar/histogram, auto-range z 10% marginesem dla line
2. Gridlines subtelne (`#E2E5EA`, 0.5px)
3. Linia referencyjna: przerywana, czarna, opacity 0.5
4. Legenda: na górze wykresu, horyzontalna
5. Fonty: Inter 12px osie, JetBrains Mono 12px tooltips
6. Brak 3D, brak pie charts
7. Kolory z palety (nigdy defaulty Plotly)
8. Adnotacje na key values (max drawdown, CLV peak)
9. Aspect ratio ~1.618:1 (golden ratio)

---

## 9. Plan wdrożenia (inkrementalny)

### Faza 1 (80% wartości):
- Sekcja A (header)
- Sekcja B (werdykt + hero metrics)
- Sekcja D (CLV — cumulative, distribution, per liga)
- Sekcja E (equity curve, drawdown, P&L summary)
- Terminal output (Rich)

### Faza 2:
- Sekcja C (calibration curves, ECE heatmap)
- Sekcja F (stake distribution)
- Sekcja H (model comparison radar + pairwise)

### Faza 3:
- Sekcja G (feature importance, SHAP)
- Sekcja I (walk-forward details)
- Sekcja J (config dump)
- Sidebar nawigacja
- Print CSS

---

## 10. Inspiracje

| Źródło | Co pożyczamy |
|--------|-------------|
| **Quantopian pyfolio** | Struktura: equity curve + drawdown + monthly heatmap |
| **Bloomberg Terminal** | Mono font na danych, gęstość informacji |
| **Stripe Dashboard** | Hero metric cards, typografia Inter |
| **Statsbomb IQ** | Minimalizm, kolor tylko semantycznie |
| **Evidently AI** | HTML report z sekcjami + Plotly + werdykt |
| **Edward Tufte** | Data-ink ratio, sparklines, small multiples |

---

## 11. Zależności techniczne

```toml
"plotly>=5.0,<6.0"
"jinja2>=3.1,<4.0"
"rich>=13.0,<14.0"
```

Template HTML: single-file z embedded CSS. Plotly JS z CDN (v1), embedded (v2 offline).
Fonty: Google Fonts CDN.

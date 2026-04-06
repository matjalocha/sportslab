# Tech-debt Audit: `ml_in_sports` Research Codebase

> **Zadanie:** P0.19 z `ideas/phase_0_foundations/tasks.md`
> **Linear issue:** [SPO-19](https://linear.app/sportslab/issue/SPO-19/p019-audyt-dlugu-technicznego-obecnego-repo)
> **Audytowany kod:** `c:/Users/Estera/Mateusz/ml_in_sports/`
> **Data audytu:** 2026-04-05
> **Audytor:** Claude Code (Explore subagent) — do weryfikacji przez MLEng/Lead
> **Cel:** Baseline przed migracją do `packages/ml-in-sports/` w Phase 1 (Code Cleanup)

---

## 1. Executive Summary

**Skala repo:** ~11,400 LOC Pythona w `src/`, 22 pliki testowe (40+ testów passing), 18 notebooków (5.1 MB), 47 scriptów (~25k LOC), 5.5 GB danych (głównie FIFA CSV + parquety). 10 modułów feature engineering (1.2k–40 funkcji, średnio 29 LOC/func).

**Ogólna ocena:** **Research-grade, zbliża się do production.** Mocna architektura (warstwy: extractors → pipeline → features → models), dobre pokrycie testami (pytest + fixtures), immutable extractors, type hinty wszędzie, czysty styl (zero `print()`, zero `import *`, zero bare `except:`, zero hardcoded paths). **Jednak:** 15 plików >300 linii (max 1.2k), klasa bazodanowa to monolit 569 LOC, pliki feature mogłyby być rozbite na mniejsze jednostki.

**Top-3 największe problemy:**
1. **Monolityczne pliki feature** — 9 plików 700-941 linii, funkcje średnio 28-34 LOC, graniczna granica czytelności.
2. **Klasa `FootballDatabase` za duża** — 569 LOC, brak separacji domen (schema DDL, CRUD, walidacja w jednym miejscu).
3. **Chaos w `scripts/`** — 47 ad-hoc scriptów, wiele >300 LOC, duplikacja logiki (np. 5 wariantów `run_tabpfn_r32_vN.py`), brak frameworku CLI.

**Top-3 największe zalety:**
1. **Dyscyplina Clean Code** — zero `print()`, logging przez `logger`, type hints ~95%+, Google-style docstrings konsekwentnie.
2. **Test-driven** — 22 moduły testowe z fixtures, `conftest.py`, 40+ testów passing, separacja test-per-module.
3. **Warstwowanie danych** — extractors immutable, pipeline orkiestruje, features modularne, models lekkie (Kelly stake = 68 LOC).

**Rekomendacja dla P1 (Code Cleanup):** **Umiarkowany refaktor**, nie full rewrite. Realistycznie 3-4 tygodnie (dolna granica widełek 4-8 tyg. z `phase_transitions.md`). Główna praca: rozbicie plików feature, ekstrakcja schema do Alembic migrations, konsolidacja scriptów do CLI. Bezpiecznie migrować w obecnym kształcie, wymaga polishingu przed produkcją.

---

## 2. Struktura Repo

```
ml_in_sports/
├── src/                          [11.4k LOC, 5 pod-katalogów]
│   ├── processing/               [2.0k LOC: extractors.py (875), pipeline.py (1.2k)]
│   ├── utils/                    [787 LOC: database.py (569), team_names.py (135), seasons.py (83)]
│   ├── models/                   [157 LOC: value_betting.py (67), schemas.py (frozen dataclasses)]
│   ├── features/                 [8.5k LOC: 10 modułów, 100-941 linii każdy]
│   └── db/                       [.db storage, poprawnie gitignored]
├── tests/                        [1.5 MB: 22 plików testowych, pytest + fixtures]
├── notebooks/                    [5.1 MB: 18 notebooków, research-grade (01-14 + 3 warianty)]
├── scripts/                      [1.3 MB: 47 scriptów, wiele >300 LOC, subfolder _archive/]
├── data/                         [5.5 GB: fifa/ (3 GB CSV), features/ (parquety), artifacts/]
├── config/                       [teamname_replacements.json]
├── pyproject.toml                [Poetry, Python 3.11+, 12 głównych deps, pytest/cov w dev]
└── .gitignore                    [podstawowy: *.db, __pycache__, .coverage]
```

**Struktura `src/` — Dobra separacja warstw:**
- `processing/`: Extractors (wrappery soccerdata) → Pipeline (orkiestracja)
- `utils/`: Database (SQLite CRUD), normalizacja nazw, sezony
- `models/`: Value betting math, schemas (frozen dataclasses)
- `features/`: 10 wyspecjalizowanych modułów (form, rolling, tactical, player, etc.)

**Dead code / archiwum:** TAK — `scripts/_archive/` zawiera 18 starych scriptów generacyjnych (`_gen_nb03.py`, `_patch_nb07_*.py`, itp.). Powinny być przeniesione do osobnej gałęzi albo skasowane.

**Organizacja scriptów:** **Monolityczna** — `run_nb*.py`, `scrape_*.py`, `materialize_*.py` rozrzucone, wiele z duplikatami logiki (np. 5 scriptów dla TabPFN predictions). Brak frameworku CLI (click/typer), `argparse` użyty tylko w 1 pliku (`run_pipeline.py`).

---

## 3. Jakość Kodu Python

**Type hints:** ~95% pokrycia. Wszystkie sygnatury funkcji w `src/` mają return types.
- `src/processing/pipeline.py:52` — `def _parse_game_key(game: str) -> tuple[str, str] | None:`
- `src/features/form_features.py:27` — `def _build_streak_histories(df: pd.DataFrame) -> pd.DataFrame:`
- Drobne: kilka `Optional[]` zamiast `X | None`, minimalny impact.

**Docstrings:** Google-style, ~100% na publicznych funkcjach. Przykład:
```python
def compute_kelly_stake(
    p_model: float, odds: float, ece: float, bankroll: float,
) -> tuple[float, float, float]:
    """Compute variance-constrained fractional Kelly stake.
    Args: ... Returns: ...
    """
```

**Rozmiar plików:**

| Plik | LOC | Funkcje | Uwagi |
|---|---:|---:|---|
| `src/processing/pipeline.py` | 1,187 | 31 | Orkiestrator, avg 38 LOC/func |
| `src/features/form_features.py` | 941 | 32 | Form / streaks / timing / discipline |
| `src/processing/extractors.py` | 875 | 3 gł. | Wrappery soccerdata, metody 100-200 LOC |
| `src/features/player_features.py` | 820 | 24 | Player ratings, Transfermarkt |
| + 11 innych plików | 300-800 | — | Głównie `src/features/*.py` |

**Rozmiar funkcji:** Dobra dyscyplina. Średnio **26-34 LOC/func** w modułach feature. Kilka outlierów:
- `src/processing/pipeline.py:_extract_source()` — ~40 LOC (OK, orchestrator)
- `src/features/form_features.py:_compute_timing_goals()` — ~60 LOC (graniczny, złożona logika feature)

**Logging vs print:**
- Zero `print()` w `src/` — 100% używa `logger = logging.getLogger(__name__)`
- `BasicConfig` w `scripts/run_pipeline.py:19-23` ustawia logging do stdout

**Hardcoded paths:**
- Zero `C:\Users\Estera\...` w kodzie
- `pathlib.Path` wszędzie: `src/processing/extractors.py:51` — `_FIFA_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "fifa"`
- Database path: `src/utils/database.py:17` — `DEFAULT_DB_PATH = Path(__file__).parent.parent / "db" / "football.db"`

**Naruszenia importów:** Zero `import *`.

**Commented-out code:** Minimum, głównie czyste docstrings dla wyłączonej logiki.

**`Any` types:** Zero (ścisłe typowanie).

**Problematyczne wzorce:**
- Zero bare `except:`
- Jeden `except Exception` w `src/features/form_features.py:908` (akceptowalny — fallback bazy danych)

---

## 4. Testy

**Framework:** pytest

**Struktura:** `/tests/` — 22 pliki testowe, jeden per moduł `src/`:
- `test_extractors.py`, `test_pipeline.py`, `test_database.py`
- `test_form_features.py`, `test_rolling_features.py`, ... (10 plików feature)
- `test_value_betting.py`, `test_team_names.py`, `test_seasons.py`

**Fixtures:** Doskonałe. `/tests/conftest.py` definiuje reużywalne fixtures:
```python
@pytest.fixture
def understat_schedule() -> pd.DataFrame:
    """Fake Understat schedule DataFrame."""
```

**Typy testów:** Mix unit + integration. `test_pipeline.py` (39 KB):
- Unit: test scrape_log skipping, parsing kluczy gier
- Integration: mock extractors + db inserts

**Coverage:** Plik `.coverage` obecny (SQLite format). Wg SUMMARY.md: "40 tests, all passing". Szacunkowo **~70-80%**.

**Problemy:**
- Brak explicit coverage target w CI (powinno być ≥ 80%)
- Niektóre testy integration hardcodują sezon `"2324"`, ligę `"ENG-Premier League"` (kruche)

---

## 5. Dependencies i Tooling

**pyproject.toml** (Poetry):
- Python: `>=3.11,<3.14`
- Główne deps: `soccerdata >=1.8.8`, `pandas`, `tqdm`, `lightgbm`, `xgboost`, `catboost`, `optuna >=4.0`, `shap`, `seaborn`, `matplotlib`
- Dev: `pytest >=8.3`, `pytest-cov >=7.0`

**Tooling status:**

| Narzędzie | Status | Komentarz |
|---|---|---|
| ruff | ✅ Skonfigurowane | line-length=100, target=py313, lint select E/F/I/UP |
| mypy | ❌ Brak | Brak sekcji `[tool.mypy]` w pyproject |
| black | ❌ Brak | Nie używane (ruff format wystarczy) |
| pre-commit | ❌ Brak | Brak `.pre-commit-config.yaml` |
| CI/CD | ❌ Brak | Brak `.github/workflows/` |
| poetry.lock | ✅ | Reprodukowalność |

**Obawy:**
- Brak mypy strict (wymóg P1)
- Brak pre-commit (kod może driftować)
- Brak CI/CD

**Konflikty wersji:** Brak oczywistych. Ograniczenia rozsądne (luźne major, tight minor).

---

## 6. Data & DB

**Bazy danych:**
- `./src/db/football.db` (główna, gitignored)
- `./data/football.db` (kopia, też gitignored)

**Schema:** 11 tabel tworzonych w `src/utils/database.py`:
- `matches` (380/sezon × 12 sezonów = 4,560 rows, 55 kolumn)
- `player_matches` (11k+ rows, 27 kolumn)
- `elo_ratings`, `league_tables`, `scrape_log`
- `fifa_ratings`, `tm_players`, `tm_player_valuations`, `tm_games`
- `match_odds` (betting data)
- `shots`

**Migracje:** **BRAK Alembic**. Schema DDL zaszyta jako stringi w `src/utils/database.py:19-400`. **RED FLAG dla produkcji** — brak version control, brak rollbacku. Kryterium wyjścia z P1 wymaga Alembic migrations (reversible).

**Connection strings:** Brak hardcoded secrets. Ścieżka DB relatywna (via `pathlib`).

**Dane w repo:** TAK, **5.5 GB**:
- `data/fifa/` — FIFA/FC CSV datasety (~3 GB, z Kaggle)
- `data/features/` — pliki parquet (cache feature)
- `data/artifacts/` — artefakty bukmacherskie (raporty markdown)

**Obawa:** FIFA CSV powinny być `.gitignored` lub przeniesione do external storage (DVC / Backblaze B2 / S3). 3 GB jest za duże dla git.

---

## 7. Notebooki

**Liczba:** 18 notebooków w `/notebooks/`, 5.1 MB total.

**Klasyfikacja:**
- Research: `01_feature_quality_eda.ipynb`, `02_baseline_model.ipynb`, `03_model_comparison.ipynb`, ..., `14_model_comparison.ipynb`
- Utilities: `database_explorer.ipynb`, `soccerdata_exploration.ipynb`
- Anomalia: `build_nb08v2.py` (plik `.py` w `notebooks/`)

**Rozmiar:** Największy ~500 KB (nie duży). Brak `*-Copy1.ipynb` / duplikatów (nazewnictwo czyste: `01`, `02`, ..., `14`, z wariantami `08_btts_v2.ipynb`).

**Obawy:**
- Notebooki są w `/notebooks/`, NIE w ścieżce production
- Rozmiar rozsądny
- `build_nb08v2.py` powinien być w `scripts/`, nie `notebooks/`

---

## 8. Scripts

**Liczba:** 47 plików Python w `/scripts/`, 1.3 MB, ~25k LOC total.

**Organizacja:**
- Subfolder `_archive/`: 18 starych scriptów (sprzed obecnej architektury pipeline)
- Root: 29 aktywnych scriptów

**Monolity (>300 LOC):**

| Script | LOC |
|---|---:|
| `run_nb21_form_model.py` | 977 |
| `run_shrinkage_r32.py` | 866 |
| `run_nb15.py` | 820 |
| `run_nb26_predictions.py` | 816 |
| + 12 innych | 300-800 |

**Gotowość CLI:**
- `run_pipeline.py` używa `argparse` z subcommands (dobre)
- Większość innych: brak frameworku CLI, hardcoded parametry na górze lub `if __name__ == "__main__"`

**Duplikacja:** Duża. Przykład: 5 scriptów dla TabPFN predictions:
- `run_tabpfn_r31_retro.py`
- `run_tabpfn_r32_v2.py`, `_v3.py`, `_v4.py`, `_v5.py`

Każdy kopiuje ~70% logiki.

---

## 9. Modele i ML Artifacts

**Folder models:** `/src/models/`:
- `schemas.py` — frozen dataclasses (immutable, dobre dla type safety)
- `value_betting.py` — 67 LOC, dwie funkcje: `compute_kelly_stake()`, `scale_to_budget()`

**ML artifacts:** **Brak w repo** (poprawnie). Żadne `.pkl`, `.joblib`, `.pt`, `.onnx` nie są trackowane.

**MLflow/MLruns:** Brak folderów `/mlruns/`, `/mlflow/`.

**Obawa:** Predykcje generowane na runtime (notebooki liczą modele on-the-fly), nie zapisywane. OK dla research; dla produkcji potrzeba versioning modeli (MLflow registry, decyzja z `ideas/tech_stack.md`).

---

## 10. Problemy Krytyczne (MUST-FIX w P1)

**Zero kritycznych bugów.** Kod jest czysty. Jednak są krytyczne problemy strukturalne:

| Problem | Plik | Linie | Typ | Opis |
|---|---|---|---|---|
| Monolityczna klasa DB | `src/utils/database.py` | 1-569 | Architektura | 569 LOC, miesza schema DDL, CRUD, walidację, logging. Wymaga splitu. |
| Pliki feature >700 LOC | `src/features/form_features.py` | 1-941 | Style | 32 funkcje w 941 LOC; split na 2-3 moduły. |
| Pliki feature >700 LOC | `src/features/player_features.py` | 1-820 | Style | Ten sam problem; rozważyć submoduł. |
| + 8 innych plików feature | `src/features/*.py` | (różne) | Style | 700-800 LOC każdy. |
| Brak migracji | `src/utils/database.py` | 19-400 | Production | Schema w hardcoded stringach; brak version control / rollback. **Blokuje wyjście z P1.** |
| Chaos w scripts | `scripts/` | (all) | Maintenance | 47 ad-hoc scriptów, duplikacja, brak CLI. |
| Nieusunięty archive | `scripts/_archive/` | 18 plików | Maintenance | Stare scripty w repo; przenieść do gałęzi `archive/pre-cleanup`. |
| Za dużo danych | `data/fifa/` | 3 GB | Repo bloat | FIFA CSV powinny być gitignored / external (DVC/S3). |
| Brak mypy/pre-commit | `pyproject.toml` | — | CI/CD | Brakuje strict type checking, hooks. |
| Plik .py w notebooks/ | `notebooks/build_nb08v2.py` | 1 | Organizacja | Powinien być w `scripts/`. |

**TODO/FIXME count:** 0 (dobra dyscyplina).

---

## 11. Problemy SHOULD-FIX

| Problem | Uwagi |
|---|---|
| Niespójność naming prywatnych funkcji | Niektóre zaczynają się od `_`, inne nie; ujednolicić. |
| Naruszenia DRY w scripts | `run_nb21_form_model.py`, `run_nb26_predictions.py` kopiują 80% logiki; ekstrahować base class / factory. |
| Kruche testy integration | Hardcoded sezon `"2324"`, liga `"ENG-Premier League"`; użyć parametrization. |
| Kohezja modułów feature | `form_features.py` obsługuje streaks, timing, discipline, xG chain, corners — rozważyć 2-3 submoduły. |
| Interface `database.read_table()` | Przyjmuje filtry `league=`, `season=`, SQL injection safe; ale warto query builder (sqlalchemy). |

---

## 12. NICE-TO-HAVE

- Sphinx docstrings → auto-generated docs
- `__all__` exports w `__init__.py` (obecnie puste)
- Pydantic models dla extractors (type safety + walidacja)
- Async extractors (ESPN jest wolny; można parallelizować)
- Data versioning (DVC) dla CSV
- Notebook → script export (jupytext)

---

## 13. Mapa Migracji do P1 Monorepo

| Obecna lokalizacja | Docelowa (w `packages/ml-in-sports/`) | Uwagi |
|---|---|---|
| `src/processing/` | `src/ml_in_sports/processing/` | Direct copy. |
| `src/utils/` | `src/ml_in_sports/utils/` | Direct copy, ale split `database.py`. |
| `src/models/` | `src/ml_in_sports/models/` | Direct copy. |
| `src/features/` | `src/ml_in_sports/features/` | Split dużych plików (`form_features` → `form/*`, etc.). |
| `tests/` | `packages/ml-in-sports/tests/` | Restruktura wg nowego layoutu src. |
| `config/` | `packages/ml-in-sports/config/` | Copy. |
| `notebooks/` | `research/ml_in_sports/` | Przenieść do research (non-production). |
| `scripts/` | Deprecate → CLI commands | Przepisać jako `ml-in-sports` CLI (click/typer). |
| `data/` | External (DVC/S3) lub `data/ml_in_sports/` | Nie commitować CSV; użyć referencji. |
| `pyproject.toml` | Merge do monorepo `packages/ml-in-sports/pyproject.toml` | Update paths. |
| `scripts/_archive/` | Delete (archiwum w git history) | Nie potrzebne w monorepo. |

---

## 14. Ocena Końcowa (1-5, gdzie 5 = production-ready)

| Obszar | Ocena | Komentarz |
|---|---:|---|
| **Structure** | 4/5 | Dobre warstwowanie. Minor: monolityczna DB, dense feature files. |
| **Code Quality** | 4/5 | Clean (no print, type hints, logging). Minor: tylko ruff, brak mypy/pre-commit. |
| **Tests** | 4/5 | pytest + fixtures, 40 testów passing. Minor: brak coverage target, kruche integration tests. |
| **Documentation** | 4/5 | Google-style docstrings, SUMMARY.md świetny. Brak: architecture diagram, API docs. |
| **Dependencies/Tooling** | 3/5 | Poetry dobrze, ruff skonfigurowane. Brak: mypy strict, pre-commit, CI/CD. |
| **Data Management** | 2/5 | **Brak migracji** (schema jako stringi), 5.5 GB CSV w repo (powinny być external). |
| **Observability** | 3/5 | Logging przez logger, scrape_log table. Brak: error tracking, metrics. |
| **Overall** | **3.5/5** | **Research-grade, gotowe do P1 cleanup.** Nie production-ready ale niskie ryzyko migracji. |

---

## 15. Rekomendacja na P1 (Code Cleanup)

**Timeline:** **3-4 tygodnie** (dolna granica widełek 4-8 tyg. z `phase_transitions.md`, dzięki czystemu punktowi startowemu).

**Breakdown:**

| Tydzień | Scope | Czas |
|---|---|---|
| W1 | Split `database.py` (schema → Alembic, CRUD → class methods) | ~2 dni |
| W1 | Split top-5 plików feature | ~3 dni |
| W2 | Konsolidacja scriptów → CLI (click/typer) | ~4 dni |
| W2 | Przeniesienie notebooków do `research/` | ~1 dzień |
| W3 | mypy strict + pre-commit + usprawnienia testów | ~3 dni |
| W3 | Code review + fixes | ~2 dni |
| (W4) | Bufor na nieprzewidziane | ~5 dni |

**Największe ryzyka:**
1. **Interdependencje plików feature** — ostrożny refaktor, testy po każdym splicie
2. **Konsolidacja scriptów** — duplikatowa logika może ukrywać edge cases, wymaga manualnej deduplikacji
3. **Migracja schema → Alembic** — zachować backward compatibility z istniejącą `.db`

**Można robić równolegle:**
- Dodanie CI/CD (`.github/workflows/`) — niezależne
- Migracja danych do DVC/S3 — niezależne
- Upgrade do Python 3.12 — test najpierw osobno

**Rekomendacja końcowa:** **Procedować z P1.** Kod jest production-adjacent; cleanup jest prosty. **Brak red flagów architektonicznych.** Focus na refaktor (split monoliths), nie rewrite.

---

## Artefakty powiązane

- [ideas/phase_0_foundations/tasks.md](../ideas/phase_0_foundations/tasks.md) — zadanie P0.19
- [ideas/phase_1_code_cleanup/](../ideas/phase_1_code_cleanup/) — target layout i plan P1
- [ideas/phase_transitions.md](../ideas/phase_transitions.md) — kryteria wyjścia z P1
- [ideas/phase_0_foundations/repo_strategy.md](../ideas/phase_0_foundations/repo_strategy.md) — struktura monorepo docelowego

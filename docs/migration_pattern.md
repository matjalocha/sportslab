# P1 Migration Pattern Playbook

> Established across SPO-30, SPO-33, SPO-35, SPO-37, SPO-38.  
> Use this as the canonical reference when migrating any module from
> `c:/Users/Estera/Mateusz/ml_in_sports/src/` →
> `packages/ml-in-sports/src/ml_in_sports/`.

---

## 1. Pre-migration checklist

Before touching any file:

1. Read the source module fully — understand imports, external deps, hardcoded paths, data files.
2. Read the existing tests in `ml_in_sports/tests/test_<module>.py`.
3. Identify which Linear issue tracks this migration (create one if missing, assign `type:refactor`).
4. Move the Linear issue to **In Progress** immediately.

---

## 2. Import path rewrite

The research codebase uses a flat `src/` layout without a package name:

```python
# OLD (research)
from src.utils.database import FootballDatabase
from src.utils.seasons import season_code
from src.features._shared import compute_match_points

# NEW (production)
from ml_in_sports.utils.database import FootballDatabase
from ml_in_sports.utils.seasons import season_code
from ml_in_sports.features._shared import compute_match_points
```

Replace globally across the source file **and** its test file.  
`sed -i 's/from src\./from ml_in_sports./g'` works but prefer explicit review.

---

## 3. Hardcoded paths → env var shims

The research codebase uses `Path(__file__).parent` navigation to reach `data/`:

```python
# OLD
_FIFA_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "fifa"
_DB_PATH = Path(__file__).parent.parent.parent / "data" / "football.db"

# NEW — env var shim (no default that works in production; test via env var)
import os
_FIFA_DATA_DIR = Path(os.environ.get("ML_IN_SPORTS_FIFA_DATA_DIR", "data/fifa"))
_DB_PATH = Path(os.environ.get("ML_IN_SPORTS_DB_PATH", "data/football.db"))
```

**Why shim instead of config class?** A full `pydantic-settings` config class is deferred to P3
(config package). The shim is a one-liner that unblocks migration without a new dependency.

---

## 4. Package data (JSON / CSV config files)

When a module reads a JSON file that ships with the package (e.g. `team_name_replacements.json`):

```python
# OLD
_REPLACEMENTS_PATH = Path(__file__).parent / "team_name_replacements.json"

# NEW — importlib.resources (stdlib, Python 3.9+)
import importlib.resources
_REPLACEMENTS_PATH = importlib.resources.files("ml_in_sports.utils") / "team_name_replacements.json"
```

Also add the file to `[tool.hatch.build.targets.wheel]` if it's not a `.py` file:

```toml
# packages/ml-in-sports/pyproject.toml
[tool.hatch.build.targets.wheel]
packages = ["src/ml_in_sports"]
# hatchling includes all non-.py files inside packages by default — no extra config needed
# for JSON files that live inside src/ml_in_sports/**
```

---

## 5. `ruff --fix` — expected automatic rewrites

Run `uv run ruff check packages/ml-in-sports --fix` after copying. Expect these auto-rewrites:

| Rule | Transformation | Notes |
|------|----------------|-------|
| `UP045` | `Optional[X]` → `X \| None` | ~100+ instances in larger files |
| `UP007` | `Union[X, Y]` → `X \| Y` | less common |
| `F401` | unused import removed | review — sometimes needed at runtime |
| `B007` | unused loop var → `_` prefix | `for x in ...` → `for _x in ...` |
| `RUF005` | `[*a] + b` → `[*a, *b]` | list concat style |
| `SIM118` | `x in dict.keys()` → `x in dict` | |

**After `--fix`, always verify** with `uv run ruff check packages/ml-in-sports` (zero errors expected).

---

## 6. mypy — type-ignore rules

| Library | Stubs available? | Directive |
|---------|-----------------|-----------|
| `pandas` | `pandas-stubs` (deferred to SPO-36) | `# type: ignore[import-untyped]` |
| `numpy` | bundled stubs (numpy 1.24+) | **no ignore needed** |
| `requests` | `types-requests` (deferred to SPO-36) | `# type: ignore[import-untyped]` |
| `tqdm` | `types-tqdm` (deferred to SPO-36) | `# type: ignore[import-untyped]` |
| `soccerdata` | none, no plans | `# type: ignore[import-untyped]` (permanent) |

Always add a comment explaining why the ignore is there:

```python
import pandas as pd  # type: ignore[import-untyped]  # pandas-stubs deferred to SPO-36
```

Verify clean with `uv run mypy packages` (zero errors on production source; test files may have
`tests.*` module pattern overrides in `pyproject.toml`).

---

## 7. Adding new external dependencies

When the module being migrated introduces a new third-party import:

**Step 1** — Add to the package `pyproject.toml`:
```toml
# packages/ml-in-sports/pyproject.toml
[project]
dependencies = [
    "numpy>=1.24,<3.0",
    "pandas>=2.0,<3.0",
    "your-new-dep>=X.Y,<Z.0",  # added in SPO-NNN (<module>.py)
]
```

**Step 2** — The root `pyproject.toml` does NOT need a new entry for the dep itself, only for
new workspace members (see ADR-0001). Run `uv sync --all-extras --dev` to pick up the dep.

**Step 3** — Add a `# type: ignore[import-untyped]` if the library has no stubs (check PyPI for
`types-<name>` or `<name>-stubs`).

---

## 8. pyproject.toml — new workspace member

When adding a **new package** (not a new dep inside an existing package):

```toml
# root pyproject.toml
[project]
dependencies = [
    "ml-in-sports",          # existing
    "new-package",           # new — ADR-0001 Option A
]

[tool.uv.sources]
ml-in-sports = { workspace = true }
new-package = { workspace = true }
```

Then `uv sync --all-extras --dev` picks up the new member automatically (it's declared in
`pnpm-workspace.yaml` equivalent via `[tool.uv.workspace] members = ["packages/*", "apps/*"]`).

---

## 9. Test layout

Tests mirror the source layout:

```
packages/ml-in-sports/
├── src/ml_in_sports/
│   ├── features/
│   │   └── rolling_features.py     ← source
│   └── processing/
│       └── extractors.py
└── tests/
    ├── conftest.py                  ← shared fixtures
    ├── features/
    │   └── test_rolling_features.py ← mirrors src layout
    └── processing/
        └── test_extractors.py
```

Port tests from `ml_in_sports/tests/test_<module>.py` with:

1. Import path rewrite (`from src.X` → `from ml_in_sports.X`)
2. Shared fixtures moved to `tests/conftest.py` (don't duplicate per test file)
3. Naming: `test_<function>_<scenario>` — keep existing names, only rewrite if they violate convention

---

## 10. Hatchling `ignore-vcs = true`

The root `.gitignore` historically had recursive patterns that blocked package source (SPO-33
`models/` bug). Defense-in-depth: every `packages/*/pyproject.toml` must have:

```toml
[tool.hatch.build]
ignore-vcs = true
```

This tells hatchling to collect package files directly, ignoring `.gitignore` rules.

---

## 11. Verification sequence (always run in this order)

```bash
# 1. Ruff lint + autofix
uv run ruff check packages/ml-in-sports --fix
uv run ruff check packages/ml-in-sports        # must be clean

# 2. Mypy strict
uv run mypy packages                           # zero errors

# 3. Tests
uv run pytest packages/ml-in-sports -v        # all pass

# 4. Quick sanity — import works from a fresh interpreter
uv run python -c "from ml_in_sports.<module> import <MainClass>; print('ok')"
```

---

## 12. Linear done comment template

```
✅ Migration complete — <module(s)>

DoD checklist:
✅ Source file(s) at packages/ml-in-sports/src/ml_in_sports/<path>
✅ Import paths rewritten (src.X → ml_in_sports.X)
✅ Hardcoded paths → env var shims (if any)
✅ Tests ported to packages/ml-in-sports/tests/<path>
✅ ruff clean (0 errors)
✅ mypy clean (0 errors on production source)
✅ <N> tests passing (was <M> before)
✅ pyproject.toml updated with new deps (if any)

Caveats / deferred:
- <any known limitations>
```

---

## 13. Common pitfalls

| Pitfall | Fix |
|---------|-----|
| `models/` in `.gitignore` shadows source | Never add bare `models/`; extension patterns cover artifacts |
| `uv sync` doesn't install new member | Root `[project].dependencies` must list member (ADR-0001) |
| `hatchling` misses package data | `ignore-vcs = true` + confirm JSON inside `src/ml_in_sports/` |
| `:memory:` breaks `DEFAULT_DB_PATH.parent.mkdir()` | Known limitation in FootballDatabase — deferred to split task |
| Parallel agents edit same file | Split scope cleanly by module; no file shared across agents |
| mypy `tests.*` override | Root `pyproject.toml` `[[tool.mypy.overrides]]` covers test discovery |

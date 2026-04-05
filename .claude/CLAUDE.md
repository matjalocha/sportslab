# Working Rules

## Core Philosophy

- **Clean Code First**: Prioritize readability and maintainability over speed.
- **Human-in-the-loop**: Review all code changes carefully.
- **Surgical Changes**: Only modify code directly related to the task. Avoid unnecessary refactoring.

## Clean Code Rules

### 1. Meaningful Naming
- Avoid abbreviations (`data`, `info`, `manager`).
- Ensure names are pronounceable and searchable.
- Use descriptive names that explain intent.

### 2. Functions & Components
- **Single Responsibility**: Each function/class should do one thing only.
- **Size**: Keep functions small (< 20 lines).
- **Arguments**: Limit to 0-2 (max 3). Avoid flag arguments.
- **No Side Effects**: Methods should not change state unless clearly named to do so.

### 3. Comments & Documentation
- **Self-explanatory code**: If it needs a comment, refactor it.
- **Allowed Comments**: Docstrings for public APIs, legal info, TODOs.
- **Forbidden**: Commented-out code (use git history).

### 4. Formatting & Style
- **File Structure**: Keep files focused and small.
- **Consistency**: Match existing style, even if you dislike it.
- **Line Length**: 80-120 characters.

### 5. Type Safety
- **Always use type hints**: For all function parameters and return values.
- **NO `Any` types**: If `Any` is necessary, pause and ask for user approval.

### 6. [FORBIDDEN PATTERNS]
- No premature optimization.
- No "just in case" features (YAGNI - You Ain't Gonna Need It).
- No duplicated code (DRY - Don't Repeat Yourself).

## Project Workflow

- **Test First**: Write or update tests before writing implementation code.
- **Plan First**: Ask for a detailed plan before editing files.
- **Verify**: Run tests after changes to ensure nothing broke.

## Coding Conventions

### Python Style
- **Type hints**: Always use type hints for parameters and return values
- **Docstrings**: Google Style format for all public functions/classes
- **Line length**: Maximum 100 characters
- **Imports**: Group by: stdlib → third-party → local
- **Naming**:
  - Classes: `PascalCase`
  - Functions/variables: `snake_case`
  - Private: `_leading_underscore`

### Project Structure
```
ml_in_sports/src/
├── models/          # Dataclasses + Interfaces
├── processing/      # Extractors (implement interfaces)
└── utils/          # Helper functions
```

## Git Workflow

### Commit Format
```
[Type] Short description TICKET-NUMBER

Type: Add, Fix, Update, Refactor, Remove
Example: [Add] ImageExtractor with FeatureExtractor interface AIML-47
```

### Branching
- `main` - production ready
- `feature/feature-name` - new features
- `fix/fix-name` - bug fixes

## Data Extraction Rules

### Validation
- ✅ Always validate data before saving
- ✅ Return `Optional[T]` when data might not exist
- ✅ Log warnings for problematic data, don't crash

### Error Handling
```python
# ✅ GOOD - graceful degradation
try:
    data = extract_something(page)
except Exception as e:
    logger.warning(f"Could not extract: {e}")
    data = None

# ❌ BAD - let it crash
data = extract_something(page)  # can crash
```

### Extractors
- Each extractor must be **tested** with fixtures
- Extractors are **immutable** - don't modify state after __init__
- Progress tracking: use `tqdm` for long operations

## What NOT to Do

### ❌ Forbidden Practices
- Don't use `print()` - **always use logging**
- Don't commit `*tmp*`, `*temp*`, `output/` files
- Don't hardcode paths - **use Path**
- Don't ignore errors - **log + return None/empty**
- Don't use `import *`

### ❌ Bad Patterns
```python
# ❌ BAD
def extract(pdf_path="/path/to/file.pdf"):  # hardcoded path
    with open(pdf_path) as f:  # can crash
        data = f.read()
    print(data)  # print instead of logging
    return data

# ✅ GOOD
def extract(pdf_path: Path) -> Optional[str]:
    """Extract data from PDF."""
    try:
        with open(pdf_path, 'r') as f:
            data = f.read()
        logger.info(f"Extracted {len(data)} bytes from {pdf_path}")
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {pdf_path}")
        return None
```

## Testing

### Requirements
- **Framework**: Use **pytest** for all tests
- **Coverage**: Minimum 80% for new code
- **Fixtures**: Use pytest fixtures for test PDFs
- **Naming**: `test_<function_name>_<scenario>`

### Test Structure
```python
def test_extract_product_name_valid_page():
    """Test extraction with valid product page."""
    # Arrange
    page = create_test_page(...)

    # Act
    result = extract_product_name(page)

    # Assert
    assert result == "ICEROSS SEAL-IN X"
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=catalog_scrapper --cov-report=html

# Run specific test file
pytest tests/test_extractors.py

# Run specific test
pytest tests/test_extractors.py::test_extract_product_name_valid_page

# Verbose output
pytest -v
```

## Documentation

### Docstrings (Google Style)
```python
def extract(self, page) -> List[ComponentImage]:
    """Extract images from a single PDF page.

    Args:
        page: pdfplumber page object

    Returns:
        List of ComponentImage objects

    Raises:
        ValueError: If page is invalid
    """
```

### Documentation Updates
- New functionality: **update README.md**
- API changes: **update CLAUDE.md**
- Breaking changes: **version bump + migration guide**

## Plan Mode

- Make the plan extremely concise. Sacrifice grammar for the sake of concision.
- At the end of each plan, give me a list of unresolved questions to answer, if any.
- Focus on what needs to be done, not how long it will take.

## Priorities

### High Priority (Do first)
1. K-level extraction (activity icons)
2. Multi-page product merging
3. Export functions (JSON/CSV)
4. Unit tests with pytest

### Medium Priority
5. Materials extraction
6. Data normalization
7. CLI interface

### Low Priority
8. Performance optimization
9. Caching

## Key Commands

```bash
# Testing
pytest                          # Run all tests
pytest --cov                    # Run with coverage
pytest -v                       # Verbose output

# Linting
ruff check src/ scripts/        # Lint
ruff format src/ scripts/       # Auto-format

# Jupyter
jupyter notebook notebooks/
```

## Review Process

**Team:** Architect, Code Architect, Senior ML Engineer, Reviewer — see `.claude/agents/`

**Phase 1 — Harsh (3 iter):** "Find every problem." Classify: MUST-FIX (bugs/crashes) / SHOULD-FIX (naming/edge-cases) / NICE-TO-HAVE (style).
**Phase 2 — Acceptance (2 iter):** Only block on MUST-FIX. Zero MUST-FIX + tests pass + ruff clean → approved.

## Research & Strategy Team

Expert agents for deep analysis — see `.claude/agents/`:

| Agent | File | Specialty |
|-------|------|-----------|
| Dr. Krzysztof | `ml-engineer-agent.md` | Models, features, calibration, stacking |
| Dr. Anna | `strategy-agent.md` | Betting strategy, markets, Kelly, CLV, scaling |
| Dr. Marek | `infra-agent.md` | Pipeline, automation, data engineering |
| Architect | `architect-agent.md` | System design, task breakdown, coordination |
| Code Architect | `code-architect.md` | Architecture review, coupling, DRY |
| Senior ML Eng | `senior-ml-engineer.md` | Code review, refactoring, quality |
| Reviewer | `reviewer-agent.md` | Final QA, tests, ruff, acceptance |
| Data Research | `data-research-agent.md` | Data sources, scraping, validation |
| Report | `report-agent.md` | Betting slips, analysis reports, MD output |

## Research Artifacts

- `data/artifacts/research/expert_models_report.md` — ML models deep analysis
- `data/artifacts/research/expert_strategy_report.md` — betting strategy analysis
- `data/artifacts/research/expert_infra_report.md` — infrastructure analysis
- `data/artifacts/research/synthesis_plan.md` — cross-validated plan (CRO)
- `data/artifacts/research/tasks.md` — 38 actionable tasks (F0-F3)
- `data/artifacts/research/refactor_tasks.md` — refactoring backlog
- `rozwoj.md` — high-level development roadmap

## Questions?

If something is unclear:
1. Check CLAUDE.md
2. Check examples in notebooks/
3. Check `data/artifacts/research/tasks.md` for implementation plan
4. Ask before implementation

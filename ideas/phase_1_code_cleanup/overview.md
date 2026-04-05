# Phase 1 — Code Cleanup

**Widełki:** 4-8 tygodni
**Cel:** Przekształcenie obecnego research repo w **production-grade codebase** gotowy do rozwoju przez 6-osobowy zespół.
**Przejście do P2:** Patrz [phase_transitions.md](../phase_transitions.md#p1--p2--code-cleanup--new-features)

## Dlaczego ta faza jest krytyczna

Obecny stan (audyt z P0.19):
- **45 skryptów** w `scripts/` — każdy z inną konwencją, brak wspólnej CLI
- **18 notebooków** w `notebooks/` — eksperymentalny kod często importowany do skryptów (anti-pattern)
- **17 plików w `scripts/_archive/`** — martwy kod, confusing dla nowych członków
- **Brak CI/CD** — żadnego zielonego światełka
- **Brak mypy strict** — typy są, ale nie wymuszone
- **SQLite schema in-code** — brak migracji, trudno modyfikować
- **`print()` w wielu miejscach** — zamiast strukturalnego logowania
- **Hardcoded paths** (Windows specific) — brak portowalności
- **Pokrycie testami** — 21 plików testów, ale pokrycie nieznane (prawdopodobnie <60%)

Bez P1:
- P2 (nowe features) będzie budowane na długach technicznych
- Nowi członkowie zespołu nie będą umieli kontrybuować
- Debugowanie produkcji (P5+) będzie koszmarem

## Główne outputy

- Monorepo zrestrukturyzowane według `phase_0_foundations/repo_strategy.md`
- GitHub Actions CI: lint + test + typecheck + build zielone na każdym PR
- Pokrycie testami ≥ 80% na `src/ml_in_sports/`
- ruff strict + mypy strict bez warnings
- Wszystkie skrypty skonsolidowane do CLI entry points
- Notebooki przeniesione do `research/`, odłączone od produkcji
- SQLite schema w Alembic migrations
- Logging strukturalny (structlog)
- Pydantic-settings jako config layer
- `CONTRIBUTING.md` + setup instructions dla nowych devów

## Zadania

Szczegóły → [tasks.md](tasks.md)

## Wspierające dokumenty

- [target_repo_layout.md](target_repo_layout.md) — dokładna struktura katalogów docelowa

## Ryzyka w P1

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|---|---|---|---|
| Refaktor zepsuje coś co obecnie działa | Wysokie | Wysoki | Testy przed refaktorem, mały PRs, code review |
| Zespół się nudzi / traci motywację podczas sprzątania | Średnie | Średni | Równoległa praca: DrMat pracuje nad `ip_moat.md` (P2 preview), reszta sprząta |
| Zbytnia perfekcja — "bikeshedding" | Średnie | Średni | Lead pilnuje, że cleanup ma DoD, nie jest nieskończony |
| Mypy strict wykrywa setki błędów | Wysokie | Niski | Stopniowo włączamy strict per moduł, nie wszystko na raz |
| Migracja SQLite → Alembic zepsuje istniejące dane | Średnie | Wysoki | Backup DB, testy migracji na kopii, dopiero potem production |

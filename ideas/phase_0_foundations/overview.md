# Phase 0 — Foundations

**Widełki:** 2-4 tygodnie
**Cel:** Ukonstytuowanie zespołu, narzędzi, procesów i formalności **przed** jakąkolwiek pracą kodową.
**Przejście do P1:** Patrz [phase_transitions.md](../phase_transitions.md#p0--p1--foundations--code-cleanup)

## Dlaczego ta faza istnieje

Obecny projekt to **solo research repo**. Żeby przekształcić go w biznes z 6-osobowym zespołem, musimy:
1. Ustawić formalności (firma, umowy, konta bukmacherskie)
2. Ustawić narzędzia (Linear, GitHub, secrets, komunikacja)
3. Ustawić proces (rytm tygodniowy, przeglądy, decyzje)
4. Zrobić audyt długu technicznego **przed** zaczęciem refaktoru

Pominięcie P0 = chaos w P1+.

## Główne outputy

- Firma założona (forma prawna wybrana, konto bankowe)
- Konta bukmacherskie u 5 operatorów (STS ✅, LVBet, Superbet, Fortuna, Betclic)
- Linear workspace + GitHub organization gotowe
- Audyt długu technicznego napisany przez MLEng/DataEng/SWE
- Weekly rhythm ustalony i przetestowany przez min. 1 cykl
- Budżet 3-6 miesięcy operacyjny zapewniony

## Zadania

Szczegóły → [tasks.md](tasks.md)

## Wspierające dokumenty

- [repo_strategy.md](repo_strategy.md) — monorepo vs polyrepo + decyzja
- [tooling.md](tooling.md) — Linear, GitHub, 1Password, komunikacja

## Ryzyka w P0

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|---|---|---|---|
| Długie procesy KYC u bukmacherów (2+ tyg.) | Wysokie | Średnie | Start KYC w tygodniu 1 równolegle z innymi zadaniami |
| Brak zgody zespołu na formę prawną | Średnie | Średnie | Lead podejmuje decyzję po 1 dniu debaty, reszta nie blokuje |
| Narzędzia (Linear paid plan) zbyt drogie | Niskie | Niskie | Start na free tier, upgrade gdy > 5 osób aktywnych |
| Zespół nie może się synchronizować time-zone | Średnie | Wysokie | Core hours ustalone w P0.1 (np. 10:00-14:00 CET) |

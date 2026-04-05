# Phase 4 — More Sports

**Widełki łącznie:** 20-32 tygodnie (3 pod-fazy sekwencyjne z wspólnym szkieletem)
**Cel:** Rozszerzenie platformy z piłki nożnej na **3 dodatkowe dyscypliny**: tenis, koszykówka, hokej. Pierwsza pokazuje że abstract framework działa; kolejne idą szybciej.
**Przejście do P5:** Patrz [phase_transitions.md](../phase_transitions.md#p4--p5--more-sports--automation)

## Kontekst

Po P3 mamy 10 lig piłki nożnej w produkcji. To jest dobre dla **jednej niszy**. Ale:
- Jeden sport = wąski B2B market (tylko piłkarscy klienci)
- Multi-sport = **szeroka baza klientów** (tipsterzy, kluby tenisa, koszykarskie akademie, NHL fantasy apps)
- Wiele rynków = **dywersyfikacja edge'u** (piłka może być efektywna, tenis nie)
- Tech credibility = pokazujemy że mamy sport-agnostic platformę, a nie tylko "football model"

## Strategia: 3 sporty, abstract framework

**Nie budujemy 3 osobnych systemów.** Budujemy **jeden sport-agnostic framework** (`src/ml_in_sports/sports/`) z abstract interfaces, i dla każdego sportu robimy implementację.

### Abstract architecture

```python
# src/ml_in_sports/sports/base.py

class SportAdapter(ABC):
    """Każdy sport implementuje ten interface."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_extractors(self) -> list[BaseExtractor]: ...

    @abstractmethod
    def get_feature_builders(self) -> list[BaseFeatureBuilder]: ...

    @abstractmethod
    def get_default_model(self) -> BaseModel: ...

    @abstractmethod
    def get_markets(self) -> list[str]:
        """np. ['1X2', 'OU2.5', 'BTTS'] dla football;
               ['match_winner', 'set_betting', 'games_ou'] dla tennis"""
        ...

    @abstractmethod
    def get_schema(self) -> dict:
        """Match schema specific to this sport."""
        ...
```

Benefity:
- **Testy kontraktowe** — każdy nowy sport przechodzi te same integration testy
- **Shared logic** — calibration, portfolio Kelly, drift detection działają identycznie
- **Szybkie dodawanie** — 4-ty sport zajmie 4-6 tygodni zamiast 20 (szkielet gotowy)
- **Frontend agnostic** — dashboardy w P6 używają schema-driven rendering

## Pod-fazy i kolejność

### P4.1 — Tenis (primary, pierwszy non-football)
**Widełki:** 6-10 tygodni

Tenis jest **najłatwiejszy** do dodania jako pierwszy sport:
- Jeff Sackmann ma kompletne historical ATP/WTA (2014-present, darmowe)
- 1v1 vs 11v11 — prostszy model (mniej noise)
- Brak kontuzji drużynowych (tylko retire/walkover)
- Surface-specific (clay/hard/grass/indoor) = ciekawy feature engineering
- Rynki bukmacherskie płynne u wszystkich (match winner, set betting, games handicap)

**Główne outputy:**
- Abstract framework (`src/ml_in_sports/sports/`) gotowy i przetestowany
- Tennis module w `sports/tennis/`
- Tennis model (LGB/LogReg hybrid) z positive ROI na walk-forward 2020-2025
- Backtest raport

### P4.2 — Koszykówka (NBA + EuroLeague)
**Widełki:** 8-12 tygodni

Koszykówka jest **największym rynkiem** obok piłki:
- NBA Stats API oficjalne, darmowe, bogate
- Pace-adjusted metrics są standardem
- Długa regular season + playoffs = dużo danych
- EuroLeague jako bonus (trudniejsze scraping, ale mniej konkurencji)
- Szybkie tempo = codzienne pipeline'y

**Wyzwania:**
- 10-15 meczów dziennie (vs 3-5 w piłce) — obciążenie pipeline
- Player availability (load management, restricting stars) wpływa na wyniki — trzeba scrape'ować injury reports
- Player props jako separate model (feasibility study)

### P4.3 — Hokej (NHL + SHL)
**Widełki:** 6-10 tygodni

Hokej jest **niszą o potencjalnie wyższym edge**:
- Mniej tipsterów analizuje → rynek mniej efektywny
- NHL API darmowe + Natural Stat Trick / Moneypuck dla advanced
- SHL scraping (szwedzka) jako secondary — jeszcze mniej konkurencji
- Goalie jako single biggest factor — unusual feature structure

**Wyzwania:**
- Overtime/shootout adds variance (regulation vs full-time rynki)
- Small team pool = overfitting risk (32 NHL teams)
- Special teams (PP/PK%) critical, less obvious

## Główne outputy (łączne dla P4)

- **Abstract sport framework** (`src/ml_in_sports/sports/`) — tested, documented, extensible
- **3 sporty w produkcji**: tenis, koszykówka, hokej
- **3 modele** z positive ROI walk-forward (> 5% każdy)
- **Testy kontraktowe** — każdy sport przechodzi te same integration testy
- **Multi-sport DB schema** (sport-agnostic base + sport-specific extensions)
- **Dokumentacja per sport** w `docs/sports/`
- **3 artykuły / case studies** na blog (dla P6 marketingu): "How we modeled tennis", "Basketball pace adjustment", "Hockey goalie impact"

## Zadania

Szczegóły → [tasks.md](tasks.md)

## Wspierające dokumenty

- [sport_prioritization.md](sport_prioritization.md) — scoring matrix (data × market × edge) + future sports roadmap

## Ryzyka w P4

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|---|---|---|---|
| Abstract framework overengineered (zaczyna dominować nad simple implementation) | Wysokie | Średni | YAGNI — zaczynamy minimal, rozszerzamy z potrzebą; tennis jako proof |
| Tennis model nie bije ELO baseline (w tenisie ELO jest bardzo silne) | Średnie | Wysoki | Focus na surface-specific + form features; target marginal improvement |
| NBA Stats API ma rate limity blokujące daily pipeline | Średnie | Wysoki | Caching, batched requests, fallback na Basketball-Reference |
| NHL data jest tylko dla NA season (pol-mar) → przerwa w pipeline | Wysokie | Niski | Accepted, dodajemy SHL lub inne ligi europejskie |
| Multi-sport w jednym DB rośnie zbyt szybko (performance) | Średnie | Średni | Partitioning (Postgres w P5), schema optimization w P4.1 |
| Zespół rozcieńczony między sportami — nikt nie jest ekspertem | Wysokie | Średni | 1 osoba = sport owner; DrMat rotuje jako shared domain expert |
| Bukmacherzy różnie oferują markety per sport | Wysokie | Niski | Dokumentacja per sport × bookmaker, fallbacks |

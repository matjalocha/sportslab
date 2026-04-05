# Phase 3 — More Leagues

**Widełki:** 6-10 tygodni
**Cel:** Rozszerzenie pokrycia z 5 do 10 lig piłki nożnej, z pełnym feature parity i positive walk-forward ROI na każdej.
**Przejście do P4:** Patrz [phase_transitions.md](../phase_transitions.md#p3--p4--more-leagues--more-sports)

## Kontekst

Obecnie mamy 5 lig: EPL, La Liga, Bundesliga, Serie A, Ligue 1. To jest solidna baza, ale z punktu widzenia produktu B2B (P6) i skali biznesu potrzebujemy **więcej terytoriów** żeby:
- Zaoferować subskrypcje klubom z niższych europejskich lig
- Zmniejszyć ryzyko "jeden rynek zaczyna nas znać" (bukmacherzy limitują konta)
- Uzyskać network effects (kluby z tej samej ligi = lepszy kontekst)
- Dostarczyć więcej material'u do trenowania modeli (więcej meczów = lepsza kalibracja)

## Wybór 5 nowych lig

Priorytety oparte na 4 kryteriach:
1. **Data availability** — czy Understat/soccerdata/ESPN/FBref mają coverage
2. **Market size** — czy bukmacherzy oferują dużo rynków (1X2, AH, O/U, BTTS)
3. **Client demand** — czy potencjalni klienci (kluby, tipsterzy) będą zainteresowani
4. **Edge potential** — czy ligi są mniej "efektywne" (mniej analizowane = większy edge)

Propozycja (finalna decyzja w P3.0 po data audit):

| # | Liga | Kraj | Data availability | Market size | Edge potential | Priorytet |
|---|------|------|---|---|---|---|
| 1 | **Eredivisie** | 🇳🇱 NL | ⭐⭐⭐ Understat, Sofascore | ⭐⭐⭐ | ⭐⭐ | High |
| 2 | **Primeira Liga** | 🇵🇹 PT | ⭐⭐ soccerdata, FBref | ⭐⭐⭐ | ⭐⭐⭐ | High |
| 3 | **Championship (EFL)** | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 EN | ⭐⭐⭐ FBref, Sofascore | ⭐⭐⭐⭐ | ⭐⭐⭐ | **Very High** |
| 4 | **MLS** | 🇺🇸 US | ⭐⭐⭐ FBref, MLS Stats | ⭐⭐⭐ | ⭐⭐⭐ | High |
| 5 | **Brasileirão Série A** | 🇧🇷 BR | ⭐⭐ FBref, soccerway | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **Very High** |

Alternative (jeśli któraś z powyższych odpadnie):
- **Liga MX** (🇲🇽, podobnie do MLS, duży rynek US)
- **Scottish Premiership** (🏴󠁧󠁢󠁳󠁣󠁴󠁿, Celtic dominuje, małe)
- **Süper Lig** (🇹🇷, duży rynek bukmacherski europejski, ale volatile)
- **Pro League** (🇧🇪, znany z overperformance Belgian talents)
- **Ekstraklasa** (🇵🇱, polski rynek — strategiczne dla klientów PL)

## Co musi zadziałać per liga

- Scraper z Understat / FBref / soccerdata działa, dane się zapisują
- Team name normalization (aliases) kompletne — team z alternatywnymi pisowniami (akcenty, prefiksy klubowe)
- Feature engineering (rolling, elo, form, table) daje non-NaN values
- Model trening działa na tej lidze
- Backtest walk-forward: **ROI > 5%** na ostatnich 2 sezonach
- Bukmacher odds dostępne (STS, Fortuna, Betclic mają) — przynajmniej 1X2, O/U 2.5, BTTS

## Główne outputy

- **5 nowych lig w production DB**, kompletne historical (min. 3 sezony)
- **Team name normalization** rozszerzone — nowe aliases, edge cases udokumentowane
- **Feature parity check** — każda nowa liga ma wszystkie features co obecne top-5
- **Backtest per liga** — raport w `docs/leagues/<liga>.md`
- **Decision log** — które ligi zatrzymujemy, które porzucamy (gdy ROI < 3%)
- **Odds coverage** — mapa bukmacher × liga × rynek
- **Cost estimate** per liga — scraping time, infra, complexity

## Zadania

Szczegóły → [tasks.md](tasks.md)

## Wspierające dokumenty

- [data_source_matrix.md](data_source_matrix.md) — mapa źródeł danych per liga, coverage, jakość

## Ryzyka w P3

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|---|---|---|---|
| Brak dobrych danych xG dla Brasileirão / MLS | Wysokie | Wysoki | Fallback: modelowanie bez xG, accept gorszego ECE, lub dedicated scraping |
| Bukmacherzy banują scraping (za duża aktywność) | Średnie | Wysoki | Rotation proxies, retry, multi-source odds |
| Team name chaos (akcenty, przydomki) | Wysokie | Średni | Dedykowane issues per liga, test cases per team |
| Model nie osiąga 5% ROI na którejś lidze | Średnie | Średni | Accept — zamkaj tę ligę w decision log, focus na pozostałych |
| Prefect flows rosną zbyt szybko (10 lig × 5 sources = 50 jobs) | Średnie | Średni | Modularna orchestracja, parametryzowane flows |
| Sezon 2026/27 startuje w trakcie P3 → chaos | Niskie | Wysoki | Planowanie: P3 kończymy przed startem sezonu lub po mocnym 1 okienku |

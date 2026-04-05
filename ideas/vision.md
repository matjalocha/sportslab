# Vision — ML-in-Sports jako biznes

## Problem

Rynek danych i analityki sportowej jest rozdrobniony:

- **Kluby piłkarskie** poniżej Top-5 lig (Ekstraklasa, Championship, Eredivisie, kluby szkoleniowe) nie mają dostępu do narzędzi jakości Statsbomb/Opta/Wyscout (koszt: €50-200k/rok).
- **Tipsterzy i serwisy bukmacherskie** kopiują dane z darmowych źródeł, ale nie mają modeli ML ani probabilistyki.
- **Fantasy apps, symulatory, niezależni researcherzy** potrzebują jednego miejsca do pobrania enriched danych — obecnie kleją je z 5+ źródeł.
- **Trenerzy tenisowi, koszykarscy, hokejowi** (szczególnie szkoleniowcy indywidualni, małe akademie) nie mają narzędzi do scoutingu przeciwnika i analizy H2H.
- **Bettorzy indywidualni i fundusze sportowe** nie mają sposobu na backtestowanie własnych strategii z jakościowymi features.

## Misja

> **Zbudować "Bloomberg dla sportów"** — jedno miejsce, gdzie dane, modele prognostyczne i narzędzia analityczne są dostępne w abonamencie dla różnych odbiorców: od klubów, przez trenerów, po tipsterów i fundusze sportowe.

Produkt nie ogranicza się do typów bukmacherskich. Typy są **dowodem skuteczności modelu** — jednak prawdziwą wartością jest **infrastruktura danych + ML** skonsumowana jako API, dashboardy i raporty.

## Propozycja wartości (per segment)

### Segment 1 — Kluby piłkarskie (niższe ligi, akademie)
- **Ich ból**: Nie stać ich na Statsbomba. Scoutują przeciwników ręcznie, z YouTube.
- **Co dostają**: Dashboard z opponent scoutingiem (1-click PDF), xG breakdown, formacje rywala, feature radar. Cena: €500-3000/m-c vs €50k Statsbomb.

### Segment 2 — Tipsterzy / serwisy bukmacherskie
- **Ich ból**: Potrzebują predykcji, nie chcą budować własnego ML zespołu.
- **Co dostają**: Value feed API z 5+ bukmacherów × 3+ sportów. Realtime probabilistyka. Cena: €200-2000/m-c.

### Segment 3 — Fantasy apps / research / inne ML teamy
- **Ich ból**: Dane są rozproszone. Scrapują tygodniami, potem tygodniami czyszczą.
- **Co dostają**: Data Lake access z enriched danymi (SQL/API/Parquet). Cena: per GB + flat fee.

### Segment 4 — Trenerzy multi-sport
- **Ich ból**: Brak narzędzi do H2H analizy dla tenisistów amatorskich/juniorów, trenerów koszykarskich w niższych ligach.
- **Co dostają**: Coach analytics dashboard z H2H deep dive, słabościami rywala, przygotowaniem taktycznym. Cena: €200-1000/m-c.

### Segment 5 — Bettorzy / fundusze
- **Ich ból**: Ich własne strategie są testowane na kiepskich danych.
- **Co dostają**: Backtest-as-a-service — upload strategii, raport walk-forward na naszych features. Cena: pay-per-run + subscription.

### Segment 6 — Agencje, sponsorzy, kluby big
- **Ich ból**: Potrzebują jednorazowych analiz (wyceny graczy, market studies).
- **Co dostają**: Custom research / consulting. Cena: €5-50k per projekt.

## Dlaczego teraz

1. **TabPFN i nowe architektury transformer** dają ML bez potrzeby milionów sampli — można zacząć od niszy (ligi, sportów), gdzie Opta nie działa.
2. **Regulacje hazardu w UE** wypychają B2C z Polski, ale **B2B data play jest legalne** i niskoryzykowe.
3. **Kluby niższych lig** zaczynają wymagać analityki, bo Ekstraklasa, Championship, Eredivisie inwestują w ML.
4. **Infrastructure commoditizowana** (Hetzner, Cloudflare, Supabase) — można uruchomić maszynkę za €50-100/m-c, co było niemożliwe 5 lat temu.

## Co nie robimy

- **Nie jesteśmy bukmacherem.** Nie przyjmujemy zakładów.
- **Nie jesteśmy B2C tipster-service z Telegramu** na początku. To opcja w P6 jako sekundarny kanał — ale primary = B2B.
- **Nie robimy grywalizacji / social / community** — to inny biznes.
- **Nie budujemy własnego data labeling od zera** — wykorzystujemy darmowe źródła (Understat, soccerdata, Sackmann, NBA Stats, NHL API) i enrichujemy.

## Metryki sukcesu (w kolejności)

1. **Techniczne (P1-P2)**: CI zielone, ECE <2%, CLV >0 vs Pinnacle closing — dowód że model jest prawdziwy
2. **Operacyjne (P5)**: Maszynka działa codziennie bez manual intervention przez 30 dni
3. **Komercyjne (P6)**: ≥1 płacący klient B2B, MRR > koszty infra
4. **Skalowalne (P6+)**: 10+ klientów B2B, 3 sporty, 10+ lig, MRR €5k+

## Ryzyka

| Ryzyko | Mitigation |
|---|---|
| Model przestaje bić rynek (edge rośnie zamkniętnie) | Dywersyfikacja produktów — nie zależymy tylko od tipów |
| Bukmacherzy limitują konta | B2B fokus — nie potrzebujemy gra graves grubej ryby |
| Regulacje GDPR / hazard w UE | Prawnik w P0, compliance-by-design |
| Scraping bany / zmiany API | Redundancja źródeł, cache strategia, fallbacks |
| Zespół się rozsypie | Linear + GitHub + dokumentacja; wszystko reproducible |
| Konkurencja (Stats Perform, Opta) obniża ceny | My targetujemy dolny segment — oni nie zejdą pod €10k/m-c |

## TL;DR dla zewnętrznego słuchacza

> "Budujemy infrastrukturę danych i modeli ML dla sportu. Pierwszymi produktami są API z prognozami (dla tipsterów) i dashboardy analityczne (dla klubów i trenerów). Zaczynamy od piłki nożnej w 5 największych ligach, potem rozszerzamy do 10 lig + 3 sportów (tenis, koszykówka, hokej). Monetizacja: B2B subscription + pay-per-use + consulting. Zespół: 6 osób, wszyscy senior. Target: pierwsze MRR w 9-12 miesięcy od startu."

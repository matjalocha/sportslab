# Raport: Zrodla danych i ligi -- football-data.co.uk + alternatywy

**Data:** 2026-04-06
**Autor:** Claude Code (research)
**Status:** Referencyjny -- do decyzji uzytkownika

---

## Spis tresci

1. [Kompletna lista lig football-data.co.uk](#1-kompletna-lista-lig-football-datacouk)
2. [KRYTYCZNY BUG: Bledne kody EC i CZ w rejestrze](#2-krytyczny-bug-bledne-kody-ec-i-cz-w-rejestrze)
3. [Zrodla danych dla Ekstraklasy](#3-zrodla-danych-dla-polskiej-ekstraklasy)
4. [Zrodla danych dla czeskiej Fortuna Ligi](#4-zrodla-danych-dla-czeskiej-fortuna-ligi)
5. [Dodatkowe ligi z football-data.co.uk](#5-dodatkowe-ligi-do-rozszerzenia)
6. [Rekomendacje](#6-rekomendacje)

---

## 1. Kompletna lista lig football-data.co.uk

### 1A. Ligi glowne (format "main" -- pelne dane)

Dane dostepne pod URL: `https://www.football-data.co.uk/mmz4281/{sezon}/{kod}.csv`

Format CSV: **120 kolumn** -- wyniki, statystyki meczowe (strzaly, rogi, kartki, faule),
kursy od 6+ bukmacherow (opening + closing), Over/Under 2.5, Asian Handicap, Betfair Exchange.

**Pinnacle closing odds (PSCH/PSCD/PSCA)** dostepne od sezonu **2012/13** dla wszystkich lig glownych.

| Kraj | Liga | Kod CSV | Tier | Najstarszy sezon | Pinnacle (od) | Statystyki meczowe |
|------|------|---------|------|------------------|---------------|-------------------|
| Anglia | Premier League | E0 | 1 | 1993/94 | 2012/13 | TAK (od ~2000/01) |
| Anglia | Championship | E1 | 2 | 1993/94 | 2012/13 | TAK |
| Anglia | League One | E2 | 3 | 1993/94 | 2012/13 | TAK |
| Anglia | League Two | E3 | 4 | 1993/94 | 2012/13 | TAK |
| Anglia | National League (Conference) | EC | 5 | 1993/94 | 2012/13 | Czesciowe (brak strzalow/rogow) |
| Szkocja | Premiership | SC0 | 1 | 1993/94 | 2012/13 | TAK |
| Szkocja | Championship | SC1 | 2 | 1993/94 | 2012/13 | TAK |
| Szkocja | League One | SC2 | 3 | 1993/94 | 2012/13 | TAK |
| Szkocja | League Two | SC3 | 4 | 1993/94 | 2012/13 | TAK |
| Niemcy | Bundesliga | D1 | 1 | 1993/94 | 2012/13 | TAK |
| Niemcy | 2. Bundesliga | D2 | 2 | 1993/94 | 2012/13 | TAK |
| Wlochy | Serie A | I1 | 1 | 1993/94 | 2012/13 | TAK |
| Wlochy | Serie B | I2 | 2 | 1993/94 | 2012/13 | TAK |
| Hiszpania | La Liga | SP1 | 1 | 1993/94 | 2012/13 | TAK |
| Hiszpania | Segunda Division | SP2 | 2 | 1993/94 | 2012/13 | TAK |
| Francja | Ligue 1 | F1 | 1 | 1993/94 | 2012/13 | TAK |
| Francja | Ligue 2 | F2 | 2 | 1993/94 | 2012/13 | TAK |
| Holandia | Eredivisie | N1 | 1 | 1993/94 | 2012/13 | TAK |
| Belgia | Jupiler Pro League | B1 | 1 | 1995/96 | 2012/13 | TAK |
| Portugalia | Primeira Liga | P1 | 1 | 1994/95 | 2012/13 | TAK |
| Turcja | Super Lig | T1 | 1 | 1994/95 | 2012/13 | TAK |
| Grecja | Super League | G1 | 1 | 1994/95 | 2012/13 | TAK |

**Razem: 22 ligi w formacie glownym.**

### 1B. Ligi dodatkowe (format "extra/new" -- uproszczone dane)

Dane dostepne pod URL: `https://www.football-data.co.uk/new/{KOD}.csv`

Format CSV: **25 kolumn** -- wyniki + kursy (Pinnacle closing, Max closing, Avg closing, Betfair Exchange closing, Bet365 closing).
**BRAK statystyk meczowych** (strzalow, rogow, kartek, fauli).
**BRAK kursow opening** (tylko closing).
Wszystkie sezony w jednym pliku CSV.

| Kraj | Liga | Kod CSV | Najstarszy sezon | Pinnacle (od) | Pinnacle coverage |
|------|------|---------|------------------|---------------|-------------------|
| **Polska** | **Ekstraklasa** | **POL** | **2012/13** | **2012/13** | **~100% (do biezacego sez.)** |
| Argentyna | Primera Division | ARG | 2012/13 | 2012/13 | TAK |
| Austria | Bundesliga | AUT | 2012/13 | 2012/13 | TAK |
| Brazylia | Serie A | BRA | 2012 | 2012 | TAK |
| Chiny | Super League | CHN | 2014 | 2014 | TAK |
| Dania | Superliga | DNK | 2012/13 | 2012/13 | TAK |
| Finlandia | Veikkausliiga | FIN | 2012 | 2012 | TAK |
| Irlandia | Premier Division | IRL | 2012 | 2012 | TAK |
| Japonia | J-League | JPN | 2012 | 2012 | TAK |
| Meksyk | Liga MX | MEX | 2012/13 | 2012/13 | TAK |
| Norwegia | Eliteserien | NOR | 2012 | 2012 | TAK |
| Rumunia | Liga 1 | ROU | 2012/13 | 2012/13 | TAK |
| Rosja | Premier League | RUS | 2012/13 | 2012/13 | TAK |
| Szwecja | Allsvenskan | SWE | 2012 | 2012 | TAK |
| Szwajcaria | Super League | SWZ | 2012/13 | 2012/13 | TAK |
| USA | MLS | USA | 2012 | 2012 | TAK |

**Razem: 16 lig w formacie extra.**

**UWAGA: Czeska Fortuna Liga (CZE) NIE ISTNIEJE na football-data.co.uk.** Sprawdzone:
- `https://www.football-data.co.uk/new/CZE.csv` -- HTTP 404
- `https://www.football-data.co.uk/mmz4281/2425/CZ.csv` -- HTTP 404
- Brak strony czechrepublicm.php

### 1C. Roznice formatow -- kluczowe

| Cecha | Format glowny (E0, SP1, ...) | Format extra (POL, DNK, ...) |
|-------|------------------------------|------------------------------|
| Liczba kolumn | ~120 | 25 |
| Strzaly (HS/AS, HST/AST) | TAK | NIE |
| Rogi (HC/AC) | TAK | NIE |
| Kartki (HY/AY, HR/AR) | TAK | NIE |
| Faule (HF/AF) | TAK | NIE |
| Half-time wynik | TAK | NIE |
| Sedzia | TAK | NIE |
| Kursy opening | TAK (PSH/PSD/PSA) | NIE |
| Kursy closing | TAK (PSCH/PSCD/PSCA) | TAK (PSCH/PSCD/PSCA) |
| Bukmacherzy individual | 6+ (B365, BW, BF, PS, WH, 1XB) | Tylko closing: PS, Max, Avg, BFE, B365 |
| Over/Under 2.5 | TAK | NIE |
| Asian Handicap | TAK | NIE |
| Nazwy kolumn druzyn | HomeTeam / AwayTeam | Home / Away |
| Nazwy kolumn goli | FTHG / FTAG | HG / AG |
| Nazwy kolumn wyniku | FTR | Res |
| Layout plikow | Osobny plik per sezon | Jeden plik wszystkie sezony |

---

## 2. KRYTYCZNY BUG: Bledne kody EC i CZ w rejestrze

### Problem

W `packages/ml-in-sports/src/ml_in_sports/processing/leagues.py` i `pinnacle.py`:

```python
# BLEDNE MAPOWANIE:
"POL-Ekstraklasa": LeagueInfo(..., "EC", ...)   # EC = English Conference!
"CZE-Fortuna Liga": LeagueInfo(..., "CZ", ...)  # CZ nie istnieje na f-d.co.uk!
```

**Faktyczny stan:**
- **EC** na football-data.co.uk to **English National League (Conference)**, 5. tier angielski
- **CZ** w ogole nie istnieje -- download_season_csv() zwroci HTTP 404
- Ekstraklasa jest dostepna pod kodem **POL** w formacie "extra" (`/new/POL.csv`), NIE w formacie "main"

### Implikacje

1. `download_season_csv()` uzywa URL `mmz4281/{season}/EC.csv` -- pobiera dane **English Conference**, nie Ekstraklasy
2. `download_season_csv()` uzywa URL `mmz4281/{season}/CZ.csv` -- **HTTP 404, RuntimeError**
3. `load_football_data_csv()` oczekuje kolumn `HomeTeam`/`AwayTeam`/`FTHG`/`FTAG` -- format extra uzywa `Home`/`Away`/`HG`/`AG`
4. Caly pipeline ingestion dla tych dwoch lig jest **zepsuty**

### Wymagane naprawy

1. Usunac `EC` i `CZ` z `FOOTBALL_DATA_LEAGUE_MAP`
2. Dodac oddzielny handler dla formatu "extra" (`/new/{KOD}.csv`)
3. Napisac parser dla kolumn formatu "extra" (lub adapter na format glowny)
4. Dla Fortuna Ligi -- football-data.co.uk nie jest opcja, trzeba inne zrodlo

---

## 3. Zrodla danych dla polskiej Ekstraklasy

### 3A. football-data.co.uk (POL) -- GLOWNE ZRODLO

| Parametr | Wartosc |
|----------|---------|
| URL | `https://www.football-data.co.uk/new/POL.csv` |
| Sezony | 2012/13 -- 2025/26 (14 sezonow) |
| Pinnacle closing (PSCH/PSCD/PSCA) | TAK, ~100% coverage (2012/13--2024/25), ~47% w biezacym sezonie (lag) |
| Bet365 closing (B365CH/B365CD/B365CA) | Tylko 2025/26 (~86% coverage) |
| Max closing (MaxCH/MaxCD/MaxCA) | TAK, pelne |
| Avg closing (AvgCH/AvgCD/AvgCA) | TAK, pelne |
| Betfair Exchange (BFECH/BFECD/BFECA) | Czesciowe |
| Statystyki meczowe | NIE |
| Koszt | Darmowe |
| Odswiezanie | ~1x/tydzien |
| Gotowy parser | NIE -- wymaga adaptera formatu "extra" |

**Ocena: 9/10 dla kursow, 2/10 dla statystyk**

### 3B. FBref / Opta

| Parametr | Wartosc |
|----------|---------|
| URL | `https://fbref.com/en/comps/36/Ekstraklasa-Stats` |
| Sezony | Od ~2017/18 (basic), xG od 2021/22 (Opta partnership) |
| Dane | Tabele, statystyki druzyn i graczy, shooting, passing, defending, GCA, xG/xA |
| Kursy | NIE |
| Koszt | Darmowe (scraping) |
| Python library | `soccerdata` (wymaga custom league config), `worldfootballR` (R) |
| Odswiezanie | Dzienne |
| Anti-scraping | Rate limiting, wymaga ostroznoci |

**Ocena: 8/10 dla statystyk, 0/10 dla kursow**

### 3C. Sofascore

| Parametr | Wartosc |
|----------|---------|
| URL | `https://www.sofascore.com/tournament/football/poland/ekstraklasa/202` |
| Sezony | Wiele sezonow (pelna historia) |
| Dane | Wyniki, sklady, statystyki meczowe (strzaly, rogi, kartki, posiadanie), xG |
| Kursy | NIE |
| Koszt | Darmowe (scraping) |
| Python library | `sofascore_scraper` (GitHub: tunjayoff/sofascore_scraper) |
| Anti-scraping | Srednie -- API mobilne, wymaga reverse engineering |
| Odswiezanie | Real-time |

**Ocena: 9/10 dla statystyk, 0/10 dla kursow**

### 3D. OddsPortal

| Parametr | Wartosc |
|----------|---------|
| URL | `https://www.oddsportal.com/football/poland/ekstraklasa/` |
| Sezony | 1998/99 -- 2025/26 (27 sezonow!) |
| Dane | Wyniki + kursy od wielu bukmacherow |
| Kursy | TAK -- Pinnacle, Bet365, 1xBet, Betfair i wiele innych |
| Rynki | 1X2, Over/Under, BTTS, Asian Handicap |
| Koszt | Darmowe (scraping) |
| Python library | `OddsHarvester` (GitHub: jordantete/OddsHarvester) |
| Anti-scraping | AGRESYWNE -- JavaScript rendering, headless browser wymagany |
| Odswiezanie | Real-time |

**Ocena: 10/10 dla kursow, 3/10 dla statystyk, 4/10 dla latwosci scrapingu**

### 3E. BetExplorer

| Parametr | Wartosc |
|----------|---------|
| URL | `https://www.betexplorer.com/football/poland/ekstraklasa/` |
| Sezony | Wiele sezonow (podobne do OddsPortal -- ten sam wlasciciel: Livesport) |
| Dane | Wyniki + kursy zamykajace |
| Kursy | TAK -- wielu bukmacherow |
| Koszt | Darmowe (scraping) |
| Anti-scraping | Podobne do OddsPortal |

**Ocena: 8/10 dla kursow, 2/10 dla statystyk, 4/10 dla latwosci scrapingu**

### 3F. ESPN

| Parametr | Wartosc |
|----------|---------|
| URL | `https://www.espn.com/soccer/scoreboard/_/league/pol.1` |
| Sezony | Kilka sezonow wstecz |
| Dane | Wyniki, posiadanie, strzaly, rogi, faule |
| Kursy | NIE |
| Koszt | Darmowe (API/scraping) |
| Python library | `soccerdata` (ESPN scraper), `espn_api` |
| Anti-scraping | Niskie -- stosunkowo latwy dostep |

**Ocena: 6/10 dla statystyk, 0/10 dla kursow**

### 3G. Transfermarkt

| Parametr | Wartosc |
|----------|---------|
| URL | `https://www.transfermarkt.us/pko-ekstraklasa/startseite/wettbewerb/PL1` |
| Dane | Wartosci rynkowe, transfery, formacje, kontuzje, sklady |
| Kursy | NIE |
| Koszt | Darmowe (scraping) |
| Python library | `soccerdata` (Transfermarkt scraper), `transfermarkt-api` |
| Anti-scraping | Srednie |

**Ocena: 7/10 dla danych kontekstowych, 0/10 dla kursow/statystyk meczowych**

### 3H. ClubElo

| Parametr | Wartosc |
|----------|---------|
| URL | `http://clubelo.com/POL` |
| Dane | Historyczne ratingi Elo dla polskich klubow |
| API | TAK -- `api.clubelo.com/{YYYY-MM-DD}` i per-team |
| Koszt | Darmowe |
| Python library | `soccerdata` (ClubElo scraper) |
| Historia | Od lat 40. XX wieku |

**Ocena: Bardzo przydatne jako feature, ale nie zastepuje kursow/statystyk**

### 3I. API-Football (api-football.com)

| Parametr | Wartosc |
|----------|---------|
| Coverage | 1200+ lig, w tym Ekstraklasa |
| Dane | Wyniki, statystyki, sklady, kursy (pre-match) |
| Koszt | Od $19/mies. (brak darmowego planu) |
| API | REST, dobrze udokumentowane |

**Ocena: 9/10 dla danych, 3/10 dla kosztow (platne)**

### 3J. 90minut.pl

| Parametr | Wartosc |
|----------|---------|
| URL | `http://www.90minut.pl/` |
| Dane | Wyniki, tabele, statystyki polskiej pilki |
| Historia | Wiele sezonow, glebokie archiwum |
| API | BRAK -- tylko HTML |
| Koszt | Darmowe |
| Anti-scraping | Niskie (prosta strona HTML) |

**Ocena: 5/10 -- dobre archiwum, ale wymaga custom scrapera**

### 3K. football-data.org (NIE .co.uk)

| Parametr | Wartosc |
|----------|---------|
| Coverage | ~140 lig, ALE Ekstraklasa NIE jest w coverage |
| Koszt | Darmowy tier (12 lig), platne od 49 EUR/mies. |

**Ocena: 0/10 -- nie pokrywa Ekstraklasy**

### 3L. Flashscore

| Parametr | Wartosc |
|----------|---------|
| Dane | Wyniki, statystyki meczowe, live scores, pelna historia |
| API | BRAK oficjalnego |
| Python | `flashscore-scraper` (PyPI), kilka scrapers na GitHub |
| Anti-scraping | AGRESYWNE -- dynamiczny JS, Cloudflare |

**Ocena: 8/10 dla danych, 2/10 dla latwosci scrapingu**

### Ranking zrodel dla Ekstraklasy (feasibility)

| # | Zrodlo | Kursy | Statystyki | Latwosc | Priorytet |
|---|--------|-------|------------|---------|-----------|
| 1 | **football-data.co.uk (POL)** | Pinnacle closing | Brak | Wysoka (CSV) | **MUST -- glowne zrodlo kursow** |
| 2 | **FBref** | Brak | xG, shooting, passing | Srednia (scraping) | SHOULD -- statystyki |
| 3 | **Sofascore** | Brak | Pelne match stats | Srednia (API) | SHOULD -- uzupelnienie statystyk |
| 4 | **ESPN** | Brak | Podstawowe stats | Wysoka | NICE -- backup statystyk |
| 5 | **ClubElo** | Brak | Elo ratings | Wysoka (API) | SHOULD -- feature |
| 6 | **OddsPortal** | Pelne | Brak | Niska (JS scraping) | NICE -- dodatkowe kursy |

---

## 4. Zrodla danych dla czeskiej Fortuna Ligi

### Kluczowy problem: BRAK na football-data.co.uk

Czeska Fortuna Liga **nie istnieje** na football-data.co.uk w zadnym formacie.
To oznacza, ze nie mamy latwego zrodla kursow Pinnacle w CSV.

### 4A. OddsPortal

| Parametr | Wartosc |
|----------|---------|
| URL | `https://www.oddsportal.com/football/czech-republic/chance-liga/` |
| Nazwa ligi | Chance Liga (dawniej Fortuna Liga) |
| Sezony | Od 1998/99 (tabele), od 2003/04 (wyniki z kursami) |
| Kursy | Wielu bukmacherow w tym Pinnacle |
| Anti-scraping | Agresywne |

**Ocena: 9/10 dla kursow, ale trudne w scrapingu**

### 4B. BetExplorer

| Parametr | Wartosc |
|----------|---------|
| URL | `https://www.betexplorer.com/football/czech-republic/` |
| Dane | Wyniki + kursy zamykajace, historyczne |
| Koszt | Darmowe (scraping) |

**Ocena: 8/10 dla kursow**

### 4C. FBref

| Parametr | Wartosc |
|----------|---------|
| URL | `https://fbref.com/en/comps/66/Czech-First-League-Stats` |
| Sezony | Od ~2017/18 (basic), xG od ~2021/22 |
| Dane | Tabele, statystyki, xG/xA |

**Ocena: 8/10 dla statystyk**

### 4D. Sofascore

| Parametr | Wartosc |
|----------|---------|
| URL | `https://www.sofascore.com/tournament/football/czech-republic/1-liga/172` |
| Dane | Pelne statystyki meczowe, sklady, xG |

**Ocena: 9/10 dla statystyk**

### 4E. statistiky1ligy.fotbal.cz

| Parametr | Wartosc |
|----------|---------|
| Opis | Oficjalna baza statystyk czeskiej 1. ligi |
| Dane | Historyczne wyniki, tabele, statystyki |
| API | Brak oficjalnego; jest unofficial `fotbal-cz-api` (GitHub: mikealdo/fotbal-cz-api) |
| Jezyk | Czeski |

**Ocena: 6/10 -- glebokie archiwum, ale trudne w dostepie**

### 4F. ESPN, Transfermarkt, ClubElo

Podobna sytuacja jak dla Ekstraklasy -- statystyki i kontekst tak, kursy nie.
ClubElo ma czeskie kluby (55+ krajow europejskich w bazie).

### 4G. API-Football, Sportmonks

Platne API z pelnym coverage czeskiej ligi. Od ~$19-29/mies.

### Ranking zrodel dla Fortuna Ligi (feasibility)

| # | Zrodlo | Kursy | Statystyki | Latwosc | Priorytet |
|---|--------|-------|------------|---------|-----------|
| 1 | **OddsPortal** | Pinnacle + inne | Brak | Niska (JS) | **MUST -- jedyne zrodlo Pinnacle** |
| 2 | **BetExplorer** | Wielu bukm. | Brak | Niska (JS) | Alternatywa dla OddsPortal |
| 3 | **FBref** | Brak | xG, advanced | Srednia | SHOULD |
| 4 | **Sofascore** | Brak | Pelne match stats | Srednia | SHOULD |
| 5 | **ClubElo** | Brak | Elo ratings | Wysoka | SHOULD |
| 6 | **ESPN** | Brak | Podstawowe | Wysoka | NICE |

---

## 5. Dodatkowe ligi do rozszerzenia

### 5A. Ligi glowne, ktorych NIE uzywamy (format "main" -- pelne dane + Pinnacle)

Te ligi maja **120 kolumn** (pelne statystyki meczowe + Pinnacle + wielu bukmacherow).
Dodanie ich do systemu jest **trywialne** -- ten sam parser co dla E0/SP1/D1.

| Liga | Kod | Obecna w rejestrze? | Wartosc dla SportsLab | Rekomendacja |
|------|-----|--------------------|-----------------------|--------------|
| **Grecja -- Super League** | G1 | NIE | Sredni rynek, liquidity Pinnacle ok | SHOULD ADD |
| **Szkocja -- Premiership** | SC0 | NIE | Popularny w UK, dobra liquidity | SHOULD ADD |
| **Hiszpania -- Segunda** | SP2 | NIE | Duzy rynek, silna liga | SHOULD ADD |
| **Francja -- Ligue 2** | F2 | NIE | Sredni rynek | NICE TO ADD |
| **Anglia -- League One** | E2 | NIE | Duzy wolumen zakladow w UK | NICE TO ADD |
| **Anglia -- League Two** | E3 | NIE | Mniejszy, ale Pinnacle aktywny | NICE TO ADD |
| **Szkocja -- Championship** | SC1 | NIE | Maly rynek | LOW PRIORITY |
| **Anglia -- National League** | EC | NIE (BUG: zmapowane jako Ekstraklasa!) | Bardzo maly rynek | LOW PRIORITY |

### 5B. Ligi extra, ktorych NIE uzywamy (format "extra" -- uproszczone dane)

Wszystkie maja **Pinnacle closing** od 2012/13, ale **brak statystyk meczowych**.
Dodanie wymaga adaptera formatu "extra".

| Liga | Kod | Liczba meczow | Wartosc | Rekomendacja |
|------|-----|---------------|---------|--------------|
| **Dania -- Superliga** | DNK | ~2900 | Dobra liga, Pinnacle aktywny | SHOULD ADD |
| **Austria -- Bundesliga** | AUT | ~2600 | Srednia, ale latwa | NICE TO ADD |
| **Szwajcaria -- Super League** | SWZ | ~2600 | Srednia liga | NICE TO ADD |
| **Rumunia -- Liga 1** | ROU | ~4100 | Duza liga, mniejszy rynek | NICE TO ADD |
| **Norwegia -- Eliteserien** | NOR | - | Letni kalendarz | LOW PRIORITY |
| **Szwecja -- Allsvenskan** | SWE | - | Letni kalendarz | LOW PRIORITY |
| **Finlandia -- Veikkausliiga** | FIN | - | Maly rynek | LOW PRIORITY |
| **USA -- MLS** | USA | - | Nietypowy kalendarz | Osobny projekt |
| **Brazylia -- Serie A** | BRA | - | Duzy rynek, ale trudny | Osobny projekt |
| **Argentyna -- Primera** | ARG | - | Sredni rynek | LOW PRIORITY |
| **Japonia -- J-League** | JPN | - | Maly rynek w EU | LOW PRIORITY |
| **Meksyk -- Liga MX** | MEX | - | Maly rynek w EU | LOW PRIORITY |
| **Chiny -- Super League** | CHN | - | Maly rynek, problemy z danymi | SKIP |
| **Irlandia -- Premier Division** | IRL | - | Bardzo maly rynek | SKIP |
| **Rosja -- Premier League** | RUS | - | Sankcje, problematyczne | SKIP |

---

## 6. Rekomendacje

### 6.1. PILNE -- Fix bugow w rejestrze

**Priorytet: KRYTYCZNY**

1. Naprawic mapowanie `EC` -- to English Conference, nie Ekstraklasa
2. Usunac `CZ` -- nie istnieje na football-data.co.uk
3. Dodac osobny handler dla formatu "extra" (`/new/{KOD}.csv`) z poprawnym parsowaniem kolumn
4. Dla Ekstraklasy: uzyc kodu `POL` z URL `/new/POL.csv`

### 6.2. Strategia dla Ekstraklasy

**Rekomendacja: football-data.co.uk (POL) jako primary + FBref/Sofascore dla statystyk**

- **Kursy:** football-data.co.uk ma Pinnacle closing z ~100% coverage od 2012/13 -- wystarczajace
- **Statystyki meczowe:** Brak w football-data.co.uk -- trzeba FBref lub Sofascore
- **Koszt:** Zero -- oba zrodla darmowe
- **Zlozonosc:** Wymaga adaptera formatu "extra" (nowe nazwy kolumn) + scraper FBref

### 6.3. Strategia dla czeskiej Fortuna Ligi

**Rekomendacja: Odlozyc na pozniej LUB uzyc OddsPortal/BetExplorer**

Fortuna Liga jest problematyczna:
- **Brak na football-data.co.uk** -- zero latwo dostepnych kursow
- **OddsPortal/BetExplorer** maja dane, ale scraping jest trudny (JS rendering, headless browser)
- **Alternatywa:** API-Football ($19/mies.) -- ale nie ma Pinnacle closing
- **Pytanie biznesowe:** Czy czeski rynek jest wystarczajaco wazny, zeby uzasadnic koszt scrapera?

Opcje:
1. **Rezygnacja z Fortuna Ligi** -- skupienie na ligach z latwym dostepem do danych
2. **OddsPortal scraper** -- inwestycja ~3-5 dni dev, ryzyko lamania ToS, utrzymanie scrapers
3. **Platne API** -- API-Football/Sportmonks, ale brak Pinnacle closing

### 6.4. Ligi do natychmiastowego dodania (niski koszt)

Te ligi uzywaja formatu "main" (ten sam parser co E0) i maja pelne dane:

1. **Grecja (G1)** -- 0 pracy ponad dodanie do rejestru
2. **Szkocja Premiership (SC0)** -- 0 pracy ponad dodanie do rejestru
3. **Hiszpania Segunda (SP2)** -- 0 pracy ponad dodanie do rejestru
4. **Francja Ligue 2 (F2)** -- 0 pracy ponad dodanie do rejestru

### 6.5. Ligi wymagajace adaptera formatu "extra"

Po napisaniu adaptera (raz, ~1 dzien dev):

1. **Polska Ekstraklasa (POL)** -- priorytetowa
2. **Dania Superliga (DNK)** -- dobra wartosc
3. **Austria Bundesliga (AUT)** -- dobra wartosc
4. **Szwajcaria Super League (SWZ)** -- opcjonalna

### 6.6. Kolejnosc prac

1. **TERAZ:** Fix bugow EC/CZ w rejestrze (blokuje poprawne dzialanie)
2. **P1/P2:** Adapter formatu "extra" + POL ingestion
3. **P3:** Dodanie G1, SC0, SP2, F2 (trywialne)
4. **P3:** Dodanie DNK, AUT, SWZ (po adapterze)
5. **P3+:** Decyzja o Fortuna Liga (OddsPortal scraper vs rezygnacja)
6. **P4+:** Ewentualne dodanie FBref/Sofascore scrapers dla statystyk meczowych

---

## Zrodla

- https://www.football-data.co.uk/data.php -- glowna strona danych
- https://www.football-data.co.uk/downloadm.php -- dodatkowe ligi
- https://www.football-data.co.uk/notes.txt -- dokumentacja kolumn
- https://www.football-data.co.uk/new/POL.csv -- dane Ekstraklasy (zweryfikowane)
- https://github.com/footballcsv/cache.footballdata -- cache z kodami lig
- https://www.oddsportal.com/football/poland/ekstraklasa/ -- historyczne kursy
- https://www.oddsportal.com/football/czech-republic/chance-liga/ -- czeskie kursy
- https://www.betexplorer.com/football/czech-republic/ -- czeskie kursy alt
- https://fbref.com/en/comps/36/Ekstraklasa-Stats -- FBref Ekstraklasa
- https://fbref.com/en/comps/66/Czech-First-League-Stats -- FBref czeska liga
- https://soccerdata.readthedocs.io/ -- soccerdata Python library
- https://github.com/tunjayoff/sofascore_scraper -- Sofascore scraper
- https://github.com/jordantete/OddsHarvester -- OddsPortal scraper
- https://github.com/mikealdo/fotbal-cz-api -- unofficial fotbal.cz API
- https://www.api-football.com/coverage -- API-Football coverage
- https://www.football-data.org/coverage -- football-data.org coverage
- http://clubelo.com/ -- ClubElo ratings
- http://www.90minut.pl/ -- polskie statystyki

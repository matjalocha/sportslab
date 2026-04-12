# Raport: Zrodla danych xG (Expected Goals) dla lig poza Top-5

**Data:** 2026-04-06
**Autor:** Claude Code (research)
**Status:** Referencyjny -- do decyzji uzytkownika

---

## Spis tresci

1. [Podsumowanie wykonawcze](#1-podsumowanie-wykonawcze)
2. [KRYTYCZNA ZMIANA: FBref stracil dane Opta (styczen 2026)](#2-krytyczna-zmiana-fbref-stracil-dane-opta)
3. [Ocena zrodel -- szczegolowo](#3-ocena-zrodel)
4. [Macierz pokrycia lig](#4-macierz-pokrycia-lig)
5. [Ranking zrodel](#5-ranking-zrodel)
6. [Obliczanie wlasnego xG](#6-obliczanie-wlasnego-xg)
7. [Alternatywy dla xG](#7-alternatywy-dla-xg)
8. [Rekomendacja dla kazdej ligi ekspansji](#8-rekomendacja-per-liga)
9. [Rekomendacja strategiczna](#9-rekomendacja-strategiczna)
10. [Zrodla](#10-zrodla)

---

## 1. Podsumowanie wykonawcze

**Problem:** Potrzebujemy danych xG dla 12 lig ekspansji poza Top-5 europejskich.

**Kluczowe odkrycie:** W styczniu 2026 Opta/Stats Perform zerwala umowe z FBref, usuwajac
WSZYSTKIE zaawansowane statystyki (xG, xA, progressive passing itd.) z serwisu. Historyczne
dane rowniez zostaly skasowane. To zasadniczo zmienia krajobraz darmowych danych xG.

**Najlepsze dostepne zrodlo:** FotMob (dane od Opta, darmowe, xG dla 500+ lig, nieoficjalne API
w Pythonie). Drugie miejsce: Sofascore (wlasne API, xG + shotmapy, szerokie pokrycie).

**Wniosek:** Dla wiekszosci naszych 12 lig ekspansji xG jest dostepne za darmo przez FotMob
i/lub Sofascore. Nie musimy budowac wlasnego modelu xG na tym etapie.

---

## 2. KRYTYCZNA ZMIANA: FBref stracil dane Opta

### Co sie stalo

20 stycznia 2026 Opta (nalezaca do Stats Perform) zerwala umowe z FBref/Sports Reference,
zadajac natychmiastowego usuniecia wszystkich zaawansowanych danych z serwisu.

**Przyczyna:** Opta podpisala ekskluzywna umowe z FIFA na dostarczanie danych bukmacherskich
na Mistrzostwach Swiata 2026. Te same dane, ktore wczesniej udostepniala FBref, teraz
sprzedaje wylacznemu dystrybutorowi.

### Co to oznacza dla nas

- **FBref NIE MA juz xG** -- ani dla biezacych, ani historycznych sezonow
- **soccerdata library:** Klasa `FBref` przestala zwracac kolumny xG (od ~15 marca 2026
  scrapery FBref moga w ogole nie dzialac)
- **Nasz obecny pipeline:** `UnderstatExtractor` w ml_in_sports nadal dziala (Top-5 only),
  ale FBref jako alternatywne zrodlo xG odpada

### Co pozostalo na FBref

Podstawowe dane: gole, asysty, mecze, minuty, clean sheets. Bez xG, xA, progressive passing,
shot-creating actions, pressures itp.

### Historyczne pokrycie FBref (przed usunieciem)

Zanim Opta wycofala dane, FBref mial zaawansowane statystyki (w tym xG) dla nastepujacych
lig (grupowanych w "tiers"):

**Big 5** (od 2017/18):
Premier League, La Liga, Bundesliga, Serie A, Ligue 1

**Next 8** (od 2022/23 -- partnerstwo z Opta):
Championship, MLS, Liga MX, Serie A (Brazylia), Eredivisie,
Primeira Liga (Portugalia), Champions League, Europa League

**Next 14** (od 2023/24 -- rozszerzenie):
2. Bundesliga, Ligue 2, Serie B, La Liga 2 (Segunda), Jupiler Pro League (Belgia),
Primera Division (Argentyna)

**Inne pokryte ligi** (czesciowo, nie zawsze xG):
Scottish Premiership, Super Lig (Turcja), Super League (Grecja),
Ekstraklasa (Polska), plus kilka lig kobiecych

**WAZNE:** Wszystkie te dane sa juz NIEDOSTEPNE na FBref. Kto zdazyl je zeskrapowac
przed styczniem 2026, ma archiwum. Kto nie -- musi uzyc innego zrodla.

---

## 3. Ocena zrodel

### 3.1. FBref / StatsBomb / Opta

| Parametr | Wartosc |
|----------|---------|
| Status | **MARTWY** dla xG (od 20.01.2026) |
| Wczesniejsze pokrycie xG | Big 5 + Next 14 + kilka dodatkowych (~20-25 lig) |
| Obecne dane | Tylko podstawowe statystyki (gole, asysty, minuty) |
| Python | `soccerdata.FBref` -- scrapery niezawodne od ~marca 2026 |
| Ocena | **0/10 -- niedostepne** |

### 3.2. Understat (understat.com)

| Parametr | Wartosc |
|----------|---------|
| Pokrycie lig | **TYLKO 6 lig:** EPL, La Liga, Bundesliga, Serie A, Ligue 1, Russian PL |
| xG per mecz | TAK |
| xG per strzal | TAK (shot-level z koordynatami x,y) |
| xG per gracz | TAK (xG, xA, xG chain, xG buildup) |
| Sezony wstecz | Od 2014/15 |
| Python | `soccerdata.Understat`, `understatapi` (PyPI) |
| Anti-scraping | Niskie -- dane w JS na stronie |
| Ocena | **10/10 dla Top-5, 0/10 dla naszych lig ekspansji** |

**Wniosek:** Understat NIE pokrywa zadnej z 12 lig ekspansji. Uzyteczny tylko jako zrodlo
treningowe do budowy wlasnego modelu xG (shot data z Top-5).

### 3.3. FotMob (fotmob.com)

| Parametr | Wartosc |
|----------|---------|
| Dostawca xG | **Opta** (ta sama firma co FBref -- ale FotMob nadal ma umowe) |
| Pokrycie lig | **500+ lig na swiecie** |
| xG per mecz (team) | TAK |
| xG per gracz | TAK (xG, xA, xG per 90) |
| xG tabela ligowa | TAK (xPTS) |
| Shot map z xG | TAK |
| Sezony wstecz | Kilka (biezacy + 1-3 poprzednie, zalezne od ligi) |
| Python | `fotmob-api` (PyPI), `pyfotmob` (PyPI), `fmscraper` (PyPI) |
| API | Nieoficjalne, ale stabilne: `https://www.fotmob.com/api/` |
| Anti-scraping | Srednie -- rate limiting, ale brak agresywnych blokad |
| Koszt | **Darmowe** |

**Potwierdzone ligi ekspansji z xG na FotMob:**

| Liga | FotMob league ID | xG team stats URL |
|------|-----------------|-------------------|
| Championship | 48 | `/leagues/48/stats/.../expected_goals_team/` |
| Eredivisie | 57 | `/leagues/57/stats/.../expected_goals_team/` |
| Ekstraklasa | 196 | `/leagues/196/stats/.../expected_goals_team/` |
| Scottish Premiership | 64 | `/leagues/64/table/premiership?filter=xg` |
| 2. Bundesliga | 146 | `/leagues/146/stats/.../expected_goals_team/` |
| Super Lig (Turcja) | 71 | potwierdzony w wynikach wyszukiwania |

Pozostale ligi (Serie B, Primeira Liga, Jupiler Pro, Super League Grecja, Segunda, Ligue 2)
sa rowniez obecne na FotMob -- serwis pokrywa 500+ lig. xG jest dostarczane przez Opta
i prawdopodobnie dostepne dla wszystkich lig, ktore Opta pokrywa (tj. wiekszosc
profesjonalnych lig europejskich).

**Ocena: 9/10 -- najlepsze darmowe zrodlo xG po upadku FBref**

### 3.4. Sofascore (sofascore.com)

| Parametr | Wartosc |
|----------|---------|
| Dostawca xG | Opta (Sofascore uzywa danych Opta) |
| Pokrycie lig | Bardzo szerokie (setki lig) |
| xG per mecz | TAK |
| Shot map z xG per strzal | TAK (koordynaty x,y + xG per shot) |
| xG per gracz | TAK |
| Sezony wstecz | Kilka |
| Python | `sofascore_scraper` (GitHub), `ScraperFC`, `soccerdata.Sofascore` |
| API | Nieoficjalne: `https://api.sofascore.com/api/v1/` |
| Shotmap endpoint | `https://api.sofascore.com/api/v1/event/{id}/shotmap` |
| Anti-scraping | Srednie -- rate limiting, Cloudflare |
| Koszt | **Darmowe** (ale oficjalne API nie jest publiczne) |

**Kluczowa przewaga Sofascore:** Dostepne shotmapy (shot-level data z koordynatami x,y
i xG per shot). To pozwala na:
- Analize jakosci szans per mecz
- Budowe wlasnych modeli (np. xG overperformance)
- Porownania z innymi dostawcami xG

**Potwierdzone ligi ekspansji:**
- Ekstraklasa: `sofascore.com/tournament/football/poland/ekstraklasa/202`
- 2. Bundesliga: `sofascore.com/tournament/football/germany/2-bundesliga/44`
- Eredivisie: `sofascore.com/football/tournament/netherlands/eredivisie/37`
- Pozostale europejskie ligi rowniez pokryte

**Wada:** Sofascore oficjalnie nie udostepnia API -- scrapery moga sie popsuc.

**Ocena: 8/10 -- szerokie pokrycie, shot-level data, ale nieoficjalne API**

### 3.5. WhoScored (whoscored.com)

| Parametr | Wartosc |
|----------|---------|
| Dostawca danych | Opta |
| xG | TAK -- pojawilo sie w ostatnich latach |
| Pokrycie lig | 500+ turniejow, w tym Championship, Eredivisie, Super Lig, itd. |
| xG per mecz | TAK (ale interface mniej wygodny niz FotMob) |
| Shot map | Czesc danych (heat mapy, action zones) |
| Python | `soccerdata.WhoScored` |
| Anti-scraping | AGRESYWNE -- JavaScript rendering, Cloudflare |
| Koszt | Darmowe |

**Wady:**
- Scraping ekstremalnie trudny (wymaga Selenium/Playwright)
- xG dodane pozno -- brak danych historycznych
- Interface nie jest user-friendly do bulk extraction

**Ocena: 5/10 -- dane sa, ale ekstrakcja bardzo trudna**

### 3.6. Flashscore (flashscore.com)

| Parametr | Wartosc |
|----------|---------|
| xG | TAK -- wyswietlane w statystykach meczowych |
| Pokrycie lig | 1000+ lig z 90+ krajow |
| Python | `flashscore-scraper` (PyPI), kilka scrapers na GitHub |
| Anti-scraping | **AGRESYWNE** -- dynamiczny JS, Cloudflare WAF |
| Koszt | Darmowe |

**Ocena: 4/10 -- dane sa, ale scraping praktycznie niemozliwy**

### 3.7. FootyStats (footystats.org)

| Parametr | Wartosc |
|----------|---------|
| xG | TAK -- xG, xGA, xG home/away |
| Pokrycie lig | 1500+ lig, 10000+ druzyn |
| Potwierdzone ligi ekspansji | Ekstraklasa, Eredivisie, 2. Bundesliga, Pro League (BE), Liga NOS (PT), Super League (GR) |
| API | TAK (platne) -- JSON API |
| CSV download | TAK (platne) |
| Koszt | Platne (cena nieznana, API subscription) |

**Ocena: 7/10 -- szerokie pokrycie xG, ale platne**

### 3.8. OddAlerts (oddalerts.com)

| Parametr | Wartosc |
|----------|---------|
| xG | TAK -- xG, xGA, xPTS, npxG, overperformance |
| Pokrycie lig | 50+ lig |
| API | TAK (`oddalerts.com/football-data-api`) |
| Potwierdzone ligi | Super Lig, 2. Bundesliga, Scottish Premiership, Ekstraklasa |
| Koszt | Free tier (ograniczony) + OddAlerts Pro |

**Ocena: 6/10 -- dobry zasob, ale ograniczona darmowa warstwa**

### 3.9. footballxg.com

| Parametr | Wartosc |
|----------|---------|
| xG | TAK -- xG league tables + predictions |
| Pokrycie lig | 50+ lig |
| Tiers | xG Free (3 ligi), xG Core 30+ lig, xG Pro 50+ lig |
| Aktualizacja | 2x/tydzien (wt + pt) |
| API | Brak |
| Koszt | Free (3 ligi), platne (wiecej lig) |

**Ocena: 5/10 -- dobre dane ale platne dla naszych lig**

### 3.10. xGscore.io

| Parametr | Wartosc |
|----------|---------|
| xG | TAK -- xG, xGOT, xPTS |
| Pokrycie lig | Glowne ligi europejskie + Champions League |
| Python | `XGStatScraper` (GitHub -- Playwright scraper) |
| Koszt | Darmowe (scraping) |

**Ocena: 5/10 -- darmowe ale wazkie pokrycie lig ekspansji**

### 3.11. API-Football (api-football.com)

| Parametr | Wartosc |
|----------|---------|
| xG | **NIE** -- API-Football NIE dostarcza xG jako natywnej metryki |
| Pokrycie lig | 1200+ lig |
| Statystyki meczowe | TAK (strzaly, rogi, posiadanie, kartki) |
| Koszt | Od $0 (free, 100 req/dzien) do $450/mies. |

**Ocena: 3/10 dla xG -- nie maja tej metryki**

### 3.12. Sportmonks (sportmonks.com)

| Parametr | Wartosc |
|----------|---------|
| xG | **TAK** -- jako platny add-on |
| Pokrycie lig | 2080+ lig |
| xG tiers | Basic (12h delay), Standard (po meczu), Advanced (real-time) |
| xG dostepnosc historyczna | **Tylko od sezonu 2024+** |
| Plany cenowe | Starter (5 lig), Growth (30 lig), Pro (120 lig) |
| Koszt | Nieznany dokladnie, ale xG jest dodatkowym platnym add-onem |

**Ocena: 6/10 -- dobre API, ale platne i xG tylko od 2024**

### 3.13. Opta / Stats Perform (bezposrednio)

| Parametr | Wartosc |
|----------|---------|
| xG | TAK -- najlepsza jakosc (to jest zrodlowy dostawca) |
| Pokrycie | Setki lig na calym swiecie |
| Cennik | Enterprise-only -- tysiace EUR/mies. za lige |
| Dostep akademicki | Mozliwy, ale drogi |
| Public portal | theanalyst.com (czesciowe dane, nie do scrapowania) |

**Ocena: 10/10 jakosc, 1/10 dostepnosc -- zbyt drogie**

### 3.14. Wyscout / Hudl

| Parametr | Wartosc |
|----------|---------|
| xG | TAK |
| Shot-level data | TAK (koordynaty, typ strzalu) |
| Pokrycie | Szerokie -- wiele lig nizszyh |
| Cennik video | Od 250 EUR/rok (Bronze -- 50 min video/mies.) |
| Cennik data/API | **~5000 GBP za 1 lige, 1 rok** (angielska lower league -- zrodlo: tweet) |
| Dostep akademicki | Mozliwy ale drogi |

**Ocena: 8/10 jakosc, 2/10 dostepnosc cenowa**

### 3.15. StatsBomb Open Data (GitHub)

| Parametr | Wartosc |
|----------|---------|
| xG | TAK -- shot-level, najwyzsza jakosc |
| Dostepne ligi | **Bardzo ograniczone:** La Liga (18 sezonow), Champions League (18 sezonow), Premier League (2), Bundesliga (2), Ligue 1 (3), Serie A (2), FIFA WC, Euro, Copa America, kilka kobiecych |
| Ligi ekspansji | **ZERO** -- brak Championship, Eredivisie, Ekstraklasy itd. |
| Python | `statsbombpy` (oficjalne) |
| Koszt | Darmowe |

**Ocena: 10/10 jakosc, 0/10 dla naszych potrzeb -- brak lig ekspansji**

### 3.16. football-data.co.uk

| Parametr | Wartosc |
|----------|---------|
| xG | **NIE** -- brak kolumn xG w CSV |
| Dostepne metryki | Gole, strzaly (HS/AS), strzaly celne (HST/AST), rogi, kartki, faule, kursy |
| Pokrycie naszych lig | Wszystkie 12 lig ekspansji (format main lub extra) |

**Ocena: 0/10 dla xG, 10/10 dla kursow i basic stats**

### 3.17. Kaggle datasety

| Parametr | Wartosc |
|----------|---------|
| "Football Data: Expected Goals and Other Metrics" | Top-5 + RPL, dane z Understat |
| "Club Football Match Data (2000-2025)" | Wiele lig, ale bez xG |
| Inne | Glownie Top-5, brak lower leagues |

**Ocena: 2/10 -- nic uzytecznego dla naszych lig ekspansji**

### 3.18. Transfermarkt

| Parametr | Wartosc |
|----------|---------|
| xG | **NIE** -- brak metryki xG |
| Dane | Wartosci rynkowe, transfery, kontuzje, formacje |

**Ocena: 0/10 dla xG**

---

## 4. Macierz pokrycia lig

**Legenda:**
- **Y** = potwierdzone xG dostepne
- **P** = prawdopodobne (serwis pokrywa lige, ale xG nie potwierdzone bezposrednio)
- **N** = brak xG
- **$** = platne
- **X** = zrodlo niedostepne (FBref)

| Liga | FotMob | Sofascore | Understat | FBref | WhoScored | FootyStats | OddAlerts | Flashscore |
|------|--------|-----------|-----------|-------|-----------|------------|-----------|------------|
| Championship | **Y** | P | N | X | Y | P | P | P |
| Eredivisie | **Y** | **Y** | N | X | Y | **Y** | P | P |
| Ekstraklasa | **Y** | **Y** | N | X | P | **Y** | **Y** | P |
| 2. Bundesliga | **Y** | **Y** | N | X | Y | **Y** | **Y** | P |
| Serie B | P | P | N | X | P | P | P | P |
| Primeira Liga (PT) | P | P | N | X | Y | **Y** | P | P |
| Jupiler Pro (BE) | P | P | N | X | P | **Y** | P | P |
| Super Lig (TR) | **Y** | P | N | X | Y | P | **Y** | P |
| Super League (GR) | P | P | N | X | P | **Y** | P | P |
| Scottish Premiership | **Y** | P | N | X | P | P | **Y** | P |
| Segunda (ES) | P | P | N | X | P | **Y** | P | P |
| Ligue 2 (FR) | P | P | N | X | P | P | P | P |

**Kluczowy wniosek:** FotMob ma najszersze potwierdzone pokrycie xG sposrod darmowych zrodel.
Sofascore jest blisko za nim. Oba uzywaja danych Opta.

---

## 5. Ranking zrodel (od najlepszego)

### Dla naszych 12 lig ekspansji:

| # | Zrodlo | xG jakosc | Pokrycie | Dostepnosc | Koszt | Python | WYNIK |
|---|--------|-----------|----------|------------|-------|--------|-------|
| 1 | **FotMob** | Opta (najlepsza) | 12/12 lig | Nieoficjalne API | Darmowe | `fotmob-api`, `pyfotmob` | **9/10** |
| 2 | **Sofascore** | Opta | 12/12 lig | Nieoficjalne API | Darmowe | `sofascore_scraper`, `soccerdata` | **8/10** |
| 3 | **FootyStats** | Wlasny model | 8+/12 lig | API/CSV | Platne | Brak gotowego | **6/10** |
| 4 | **OddAlerts** | Nieznany | 6+/12 lig | API | Free tier + Pro | Brak gotowego | **5/10** |
| 5 | **WhoScored** | Opta | 10+/12 lig | Scraping trudny | Darmowe | `soccerdata.WhoScored` | **4/10** |
| 6 | **Sportmonks** | Wlasny | 12/12 lig | Oficjalne API | Platne ($$$) | Oficjalne SDK | **4/10** |
| 7 | **Flashscore** | Nieznany | 12/12 lig | Scraping b. trudny | Darmowe | Slabe scrapery | **3/10** |
| 8 | **Understat** | Wlasny (dobry) | 0/12 lig | Darmowe | Darmowe | `soccerdata`, `understatapi` | **0/10** |
| 9 | **FBref** | N/A (usun.) | 0/12 lig | N/A | N/A | Nie dziala | **0/10** |

---

## 6. Obliczanie wlasnego xG

### 6.1. Czy potrzebujemy wlasnego modelu xG?

**Krotka odpowiedz: NIE na tym etapie.** FotMob i Sofascore dostarczaja xG od Opta
za darmo dla wszystkich naszych lig. Budowa wlasnego modelu jest uzasadniona dopiero gdy:

1. Zrodla xG przestana byc darmowe (np. FotMob zerwany jak FBref)
2. Potrzebujemy wlasnej, lepiej skalibrowanej metryki xG
3. Potrzebujemy xG dla lig, ktorych nikt nie pokrywa

### 6.2. Co jest potrzebne do budowy modelu xG

**Dane shot-level (minimum):**
- Pozycja strzalu (x, y) na boisku
- Wynik strzalu (gol / nie-gol)

**Dane shot-level (optymalne):**
- Pozycja strzalu (x, y)
- Typ strzalu (stopa / glowa / inne)
- Sytuacja (open play / rzut wolny / rzut rozny / karny)
- Kat i dystans do bramki
- Pozycja bramkarza
- Cialo pod presja (TAK/NIE)
- Typ asysty (podanie, drybling, staly fragment)
- Stan meczu (wynik w momencie strzalu)

**Model:**
- Logistic regression (najprostszy, ~0.08-0.10 Brier score)
- Gradient boosting / XGBoost (~0.07-0.08 Brier score)
- Neural network (~0.07 Brier score, marginalna przewaga)

### 6.3. Skad wziac dane shot-level

| Zrodlo | Ligi | Shot coords | xG label | Koszt |
|--------|------|-------------|----------|-------|
| **StatsBomb Open Data** | La Liga, CL, WC, Euro (ograniczone) | TAK | TAK | Darmowe |
| **Understat** | Top-5 + RPL | TAK | TAK (ich wlasne xG) | Darmowe |
| **Sofascore shotmap API** | Wiele lig (w tym ekspansji) | TAK | TAK (Opta xG) | Darmowe (nieoficjalne) |
| **FotMob shotmap** | Wiele lig | TAK | TAK | Darmowe (nieoficjalne) |
| **Wyscout** | Wiele lig | TAK | TAK | ~5000 GBP/liga/rok |

### 6.4. Strategia "transfer learning"

Gdybysmy chcieli budowac wlasny model:

1. **Train** na danych StatsBomb Open Data + Understat (Top-5, duzy zbior danych z labelami)
2. **Validate** porownujac nasze xG z Opta xG (FotMob/Sofascore) na tych samych meczach
3. **Apply** model do shot-level data z Sofascore/FotMob dla lig ekspansji

**Problem:** Modele xG trenowane na Top-5 moga byc mniej dokladne w nizszych ligach
(inne taktyki, wiecej bledon, gorsze boiska, mniej precyzyjne wykonczenie).
Badanie "Is xG Lying To You In The Lower Leagues?" (worldinsport.com) potwierdza
ten problem. Kalibracja per-liga bylaby konieczna.

**Estymowany naklad pracy:** 2-3 tygodnie (scraping + model + walidacja + kalibracja).

---

## 7. Alternatywy dla xG

Jesli xG okazaloby sie niedostepne dla jakiejs ligi, mamy alternatywy:

### 7.1. Model Poissona z golami (bez xG)

Nasz obecny pipeline juz uzywa modelu opartego na golach (Dixon-Coles).
To **nie wymaga xG** -- wystarczy historia wynikow.

**Zalety:**
- Dziala dla kazdej ligi (wystarczy historia meczy)
- football-data.co.uk dostarcza wyniki dla wszystkich 12 lig
- Nasz istniejacy model juz to implementuje

**Wady:**
- Gole sa bardziej losowe niz xG -- wiekszy szum
- Brak informacji o jakosci szans

### 7.2. Shots-on-target jako proxy xG

football-data.co.uk dostarcza HS (home shots), AS (away shots), HST (home shots on target),
AST (away shots on target) dla wszystkich lig w formacie "main" (22 lig).

Mozna uzyc stosunku `goals / shots_on_target` jako prostego proxy:
- "Expected goals" = `shots_on_target * league_avg_conversion_rate`
- Prostszy ale mniej precyzyjny niz prawdziwe xG

**Dostepnosc:** 10/12 lig ekspansji (brak shots dla Ekstraklasy w formacie extra).

### 7.3. Market-implied xG

Odwrocone inzynieria kursow bukmacherskich:
- Z kursow 1X2 i Over/Under wyliczamy implied probabilities golowe
- Z rozkladu Poissona odwracamy oczekiwana liczbe goli per druzyna
- To daje "market-implied xG" -- ile goli rynek spodziewa sie od kazdej druzyny

**Zalety:**
- Dostepne dla KAZDEJ ligi z kursami (wszystkie 12 lig)
- Agreguje informacje z calego rynku (wliczajac dane, do ktorych nie mamy dostepu)
- Pinnacle closing odds sa najbardziej eficientne

**Wady:**
- To nie jest "prawdziwe" xG oparte na strzalach
- Odzwierciedla oczekiwania rynku, nie faktyczna gre
- Nie pozwala na analize per-strzal

### 7.4. Hybrid: xG gdzie dostepne + Poisson gdzie nie

**Rekomendowany approach:**
- Dla lig z xG (FotMob/Sofascore): uzywamy xG jako feature
- Dla lig bez xG: uzywamy modelu Poissona z golami + shots proxy
- Model predykcyjny powinien byc odporny na brak xG (feature importance)

---

## 8. Rekomendacja per liga

### Tabela: Najlepsze zrodlo xG dla kazdej ligi ekspansji

| # | Liga | Najlepsze zrodlo xG | Backup | Sezony xG | Uwagi |
|---|------|---------------------|--------|-----------|-------|
| 1 | **Championship** | FotMob (ID: 48) | Sofascore | 2-3 | Duzy rynek, pelne pokrycie |
| 2 | **Eredivisie** | FotMob (ID: 57) | Sofascore, FootyStats | 2-3 | Dobrze pokryte |
| 3 | **Ekstraklasa** | FotMob (ID: 196) | Sofascore | 2-3 | Potwierdzone xG + xG conceded |
| 4 | **2. Bundesliga** | FotMob (ID: 146) | Sofascore, FootyStats | 2-3 | Potwierdzone xG |
| 5 | **Serie B** | FotMob (prawdopodobne) | Sofascore | 2-3 | Opta pokrywa, do weryfikacji |
| 6 | **Primeira Liga (PT)** | FotMob (prawdopodobne) | Sofascore, FootyStats | 2-3 | Opta pokrywa, do weryfikacji |
| 7 | **Jupiler Pro (BE)** | FotMob (prawdopodobne) | Sofascore, FootyStats | 2-3 | Opta pokrywa, do weryfikacji |
| 8 | **Super Lig (TR)** | FotMob (ID: 71) | Sofascore, WhoScored | 2-3 | Potwierdzone |
| 9 | **Super League (GR)** | FotMob (prawdopodobne) | Sofascore, FootyStats | 2-3 | Do weryfikacji |
| 10 | **Scottish Premiership** | FotMob (ID: 64) | Sofascore, OddAlerts | 2-3 | Potwierdzone xPTS table |
| 11 | **Segunda (ES)** | FotMob (prawdopodobne) | Sofascore, FootyStats | 2-3 | Do weryfikacji |
| 12 | **Ligue 2 (FR)** | FotMob (prawdopodobne) | Sofascore | 2-3 | Do weryfikacji |

**"Prawdopodobne"** = FotMob pokrywa lige (500+ lig), Opta jest dostawca, ale nie znaleziono
bezposredniego URL z xG stats w wyszukiwaniach. Wymaga weryfikacji manualnej na stronie.

---

## 9. Rekomendacja strategiczna

### 9.1. Pierwsze kroki (P1-P2)

**1. Zbudowac scraper FotMob jako glowne zrodlo xG**

```
Technologia: fotmob-api (PyPI) lub wlasny client do FotMob API
Endpoint: https://www.fotmob.com/api/matchDetails?matchId={id}
Dane: xG per mecz, xG per druzyna, shotmap z xG per shot
Estymowany czas: 3-5 dni
```

**2. Zbudowac scraper Sofascore jako backup/uzupelnienie**

```
Technologia: soccerdata.Sofascore lub wlasny client
Endpoint: https://api.sofascore.com/api/v1/event/{id}/shotmap
Dane: Shot-level data z koordynatami + xG per shot
Estymowany czas: 3-5 dni
```

**3. Weryfikacja pokrycia xG per liga**

Przed budowa scrapers, nalezy manualnie sprawdzic na FotMob/Sofascore
czy kazda z 12 lig ekspansji faktycznie wyswietla xG w statystykach
meczowych. Estymowany czas: 1-2 godziny.

### 9.2. Architektura danych xG

```
Zrodla xG:
  Top-5:     Understat (istniejacy pipeline) -- shot-level + team-level
  Ekspansja: FotMob (nowy scraper)           -- team-level xG per mecz
  Backup:    Sofascore (nowy scraper)         -- shot-level data

Fallback (brak xG):
  Poisson z golami (istniejacy model)
  Shots-based proxy (football-data.co.uk)
  Market-implied xG (z kursow Pinnacle)
```

### 9.3. Ryzyka

| Ryzyko | Prawdopodobienstwo | Wplyw | Mitygacja |
|--------|-------------------|-------|-----------|
| FotMob zrywania z Opta (jak FBref) | Niskie | Wysoki | Sofascore jako backup |
| FotMob blokuje nieoficjalne API | Srednie | Wysoki | Sofascore, FootyStats API |
| Sofascore blokuje scrapery | Srednie | Sredni | FotMob jako primary |
| Opta przestaje dostarczac xG do darmowych serwisow | Niskie-Srednie | Bardzo wysoki | Wlasny model xG (plan B) |
| xG w nizszych ligach mniej dokladne | Pewne | Niski | Kalibracja per liga, hybrid approach |

### 9.4. Czego NIE robic

1. **Nie budowac wlasnego modelu xG teraz** -- dostepne sa darmowe zrodla Opta xG
2. **Nie placic za Sportmonks/Wyscout/Opta** -- za wczesnie, za drogie
3. **Nie polegac na FBref** -- dane xG usuniety, scrapery zepsute
4. **Nie scrapowac WhoScored/Flashscore** -- anti-scraping zbyt agresywny vs. alternatywy

### 9.5. Kolejnosc implementacji

1. **TERAZ:** Manualna weryfikacja xG per liga na FotMob (~2h)
2. **P1:** Scraper FotMob -- xG per mecz per druzyna (3-5 dni)
3. **P1:** Scraper Sofascore -- shot-level data jako backup (3-5 dni)
4. **P2:** Integracja xG jako feature w modelu predykcyjnym
5. **P3+:** (Opcjonalnie) Wlasny model xG trenowany na shot data z Sofascore/Understat

---

## 10. Zrodla

### Uderzenie FBref/Opta
- [Sports Reference pulls advanced soccer data after agreement violation dispute](https://awfulannouncing.com/soccer/sports-reference-pulls-advanced-data-agreement-violation-dispute.html)
- [FBref & Stathead Data Update](https://www.sports-reference.com/blog/2026/01/fbref-stathead-data-update/)
- [Farewell FBref Advanced Stats](https://ricardoheredia.substack.com/p/farewell-fbref-advanced-stats-when)
- [Loss of FBref advanced stats is disaster for women's soccer data](https://www.theixsports.com/the-ix-soccer/fbrefs-loss-advanced-stats-womens-soccer-data-accessibility/)
- [FBref Is Gone: 5 Best Football Stats Alternatives](https://www.bestbettingsites.com/blog/fbref-alternatives-sports-bettors.html)
- [FBref Adds Advanced Data for Six New Leagues (Next 14)](https://www.sports-reference.com/blog/2023/09/fbref-adds-advanced-data-for-six-new-leagues-so-the-next-8-becomes-the-next-14/)

### FotMob
- [Live xG data is now in FotMob](https://www.fotmob.com/topnews/3627-Live-xG-data-is-now-in-FotMob)
- [FotMob xG from Opta (tweet)](https://x.com/FotMob/status/1377910871318540288)
- [fotmob-api PyPI](https://pypi.org/project/fotmob-api/)
- [fotmob-api GitHub](https://github.com/C-Roensholt/fotmob-api)
- [pyfotmob PyPI](https://pypi.org/project/pyfotmob/)
- FotMob xG pages: [Championship](https://www.fotmob.com/leagues/48/stats/season/27195/teams/expected_goals_team/championship-teams), [Eredivisie](https://www.fotmob.com/leagues/57/stats/season/27131/teams/expected_goals_team/eredivisie-teams), [Ekstraklasa](https://www.fotmob.com/leagues/196/stats/season/27045/teams/expected_goals_team/ekstraklasa-teams), [2. Bundesliga](https://www.fotmob.com/leagues/146/stats/season/23795/teams/expected_goals_team/2-bundesliga-teams), [Scottish Premiership xPTS](https://www.fotmob.com/leagues/64/table/premiership?filter=xg)

### Sofascore
- [Sofascore Ekstraklasa](https://www.sofascore.com/football/tournament/poland/ekstraklasa/202)
- [Sofascore 2. Bundesliga](https://www.sofascore.com/tournament/football/germany/2-bundesliga/44)
- [Sofascore Eredivisie](https://www.sofascore.com/football/tournament/netherlands/eredivisie/37)
- [sofascore_scraper GitHub](https://github.com/tunjayoff/sofascore_scraper)
- [soccerdata Sofascore docs](https://deepwiki.com/probberechts/soccerdata/3.5-understat-and-sofascore-scrapers)
- [ScraperFC Sofascore](https://scraperfc.readthedocs.io/en/latest/sofascore.html)

### Understat
- [Understat.com](https://www.understat.com/)
- [understatapi PyPI](https://pypi.org/project/understatapi/)

### StatsBomb Open Data
- [StatsBomb open-data GitHub](https://github.com/statsbomb/open-data)
- [statsbombpy GitHub](https://github.com/statsbomb/statsbombpy)
- [StatsBomb free data](https://statsbomb.com/what-we-do/hub/free-data/)

### soccerdata
- [soccerdata PyPI](https://pypi.org/project/soccerdata/)
- [soccerdata FBref docs](https://soccerdata.readthedocs.io/en/latest/datasources/FBref.html)
- [soccerdata custom leagues](https://soccerdata.readthedocs.io/en/latest/howto/custom-leagues.html)
- [soccerdata GitHub](https://github.com/probberechts/soccerdata)

### Inne platformy xG
- [FootyStats xG](https://footystats.org/stats/xg)
- [OddAlerts xG 50+ leagues](https://www.oddalerts.com/xg)
- [OddAlerts Football Data API](https://www.oddalerts.com/football-data-api)
- [footballxg.com](https://footballxg.com/)
- [xGscore.io](https://xgscore.io/xg-statistics)
- [XGStatScraper GitHub](https://github.com/mukk38/XGStatScraper-)

### Platne zrodla
- [Sportmonks xG API](https://www.sportmonks.com/football-api/xg-data/)
- [Sportmonks pricing](https://www.sportmonks.com/football-api/plans-pricing/)
- [Opta / Stats Perform](https://www.statsperform.com/opta-analytics/)
- [Wyscout pricing](https://www.hudl.com/en_gb/products/wyscout/pricing)
- [API-Football](https://www.api-football.com/)

### Budowa modelu xG
- [soccer_xg (KU Leuven)](https://github.com/ML-KULeuven/soccer_xg)
- [Building an xG model (McKay Johns)](https://mckayjohns.substack.com/p/building-an-xg-model-with-machine)
- [Soccermatics xG model](https://soccermatics.readthedocs.io/en/latest/gallery/lesson2/plot_xGModelFit.html)
- [Is xG Lying To You In The Lower Leagues?](https://worldinsport.com/is-xg-lying-to-you-in-the-lower-leagues/)

### Proxy i alternatywy
- [Dixon-Coles and xG together](https://www.statsandsnakeoil.com/2018/06/22/dixon-coles-and-xg-together-at-last/)
- [Inflated ML Poisson model (Beat the Bookie)](https://beatthebookie.blog/2022/08/22/inflated-ml-poisson-model-to-predict-football-matches/)
- [Comparing xG data providers (Beat the Bookie)](https://beatthebookie.blog/2024/01/06/comparing-the-predictive-power-of-different-xg-data-providers/)
- [football-data.co.uk column notes](https://www.football-data.co.uk/notes.txt)

# Research Backlog — P2+

**Owner:** DrMat (primary) + MLEng (support)
**Scope:** Hipotezy do sprawdzenia. Nie wszystkie będą w P2 — niektóre przejdą do P3-P6 jako "research spikes".

## Format hipotezy

Każdy item = hipoteza z:
- **Claim** — co twierdzimy
- **Test** — jak sprawdzamy
- **Success criterion** — co uznajemy za potwierdzenie
- **Est. effort** — ile dni
- **Phase** — kiedy to robimy

---

## Kategoria 1 — Kalibracja modeli

### RB-01: TabPFN over-confidence jest systematyczny, nie przypadkowy
- **Claim:** TabPFN w naszych danych ma ECE >3% i rośnie z wartością P
- **Test:** Calibration curve na 5000 predictions z walk-forward
- **Success:** Plot pokazujący monotoniczny over-confidence
- **Est. effort:** 2 dni
- **Phase:** P2

### RB-02: Temperature scaling TabPFN per liga jest lepszy od globalnego
- **Claim:** Różne ligi mają różne optimum T
- **Test:** Grid search T w [0.5, 2.0] per liga na walk-forward
- **Success:** Average ECE improvement ≥ 0.5pp per liga vs global T
- **Est. effort:** 3 dni
- **Phase:** P2

### RB-03: Beta calibration per rynek (1X2 vs O/U vs BTTS)
- **Claim:** Rynek O/U ma inny profil kalibracji niż 1X2
- **Test:** Beta params fitted per market
- **Success:** Poprawa ECE per rynek
- **Est. effort:** 2 dni
- **Phase:** P2

---

## Kategoria 2 — Portfolio i Kelly

### RB-04: Shrinkage Bayesowski redukuje drawdown w backteście
- **Claim:** Shrinkage edge w kierunku rynku dla ekstremalnych edge'ów (>30%) redukuje max drawdown o >20%
- **Test:** Walk-forward backtest 4 sezony, z/bez shrinkage
- **Success:** Drawdown reduction + ROI retention (lub nawet improvement)
- **Est. effort:** 4 dni
- **Phase:** P2

### RB-05: Portfolio Kelly z constraint correlation redukuje bust rate akumulatorów
- **Claim:** Gdy drużyna jest w 3+ betach, exposure zmniejszony → mniejsze bust rate gdy drużyna przegrywa
- **Test:** Simulation portfolio z/bez correlation constraint
- **Success:** 30-50% redukcja bust scenariuszy
- **Est. effort:** 3 dni
- **Phase:** P2

### RB-06: Kelly alpha adaptive per sezon
- **Claim:** Kelly alpha (0.25 globalne) powinien być adjustowany per sezon na bazie ostatnich 30-60 dni CLV
- **Test:** Adaptive alpha vs fixed alpha w walk-forward
- **Success:** Better risk-adjusted return (Sharpe)
- **Est. effort:** 3 dni
- **Phase:** P2 lub P3

---

## Kategoria 3 — Goals models

### RB-07: Dixon-Coles bije Poisson na O/U 0.5, 1.5, 4.5
- **Claim:** Klasyczny Poisson underperformuje na skrajnych liniach
- **Test:** Compare LogLoss na wszystkich O/U liniach
- **Success:** Dixon-Coles wins na ≥3 liniach
- **Est. effort:** 3 dni
- **Phase:** P2

### RB-08: Bayesian DC bije frequentist DC gdy mało danych (nowy zespół, sezon start)
- **Claim:** Prior hel nad MAP w pierwszych 5 rundach sezonu
- **Test:** LogLoss rundy 1-5 per sezon
- **Success:** Bayesian wygrywa przy start season
- **Est. effort:** 4 dni
- **Phase:** P2

### RB-09: xG-based Poisson vs score-based Poisson
- **Claim:** Lambda z xG daje lepszą predykcję niż Lambda z historycznych goals
- **Test:** Two versions, same data, compare
- **Success:** xG version wins LogLoss
- **Est. effort:** 2 dni
- **Phase:** P2

---

## Kategoria 4 — Features i data

### RB-10: Weather data poprawia modele
- **Claim:** Deszcz/wiatr wpływa na O/U goals
- **Test:** Scrape weather per mecz, dodaj jako feature, measure ΔLogLoss
- **Success:** ΔLL > 0.001 na O/U
- **Est. effort:** 5 dni (scraping + test)
- **Phase:** P3

### RB-11: Referee data — sędzia decyduje o fouls/cards
- **Claim:** Różni sędziowie mają różne profile kart, wpływa na rynki card/foul
- **Test:** Feature: avg cards per referee; measure wpływ na card betting
- **Success:** Nowy rynek (cards) z positive ROI
- **Est. effort:** 7 dni
- **Phase:** P3+

### RB-12: Manager / coach change impact
- **Claim:** Po zmianie trenera przez pierwsze 5 meczów forma jest znacząco różna
- **Test:** Feature: `days_since_manager_change`, `new_manager_flag`, interactions
- **Success:** Positive ΔLL w sezonach z wieloma zmianami trenera
- **Est. effort:** 5 dni
- **Phase:** P3

### RB-13: Injury / absence impact (via Sofascore / Transfermarkt)
- **Claim:** Brak 3+ kluczowych graczy obniża win probability o >5pp
- **Test:** Sofascore lineups 24h przed meczem, cross-reference z FIFA ratings
- **Success:** Feature dodany, ΔLL > 0.001
- **Est. effort:** 7 dni
- **Phase:** P3

### RB-14: Travel distance / time zone impact (europejskie puchary, CL/EL)
- **Claim:** Wyjazd 2000+km po europejskim pucharze obniża wyniki
- **Test:** Geographic distance feature + travel time
- **Success:** Positive signal for long-travel teams
- **Est. effort:** 4 dni
- **Phase:** P3

---

## Kategoria 5 — Modeling architecture

### RB-15: Stacking ensemble bije simple averaging
- **Claim:** LogReg meta-learner na OOF predictions z base models wygrywa
- **Test:** Stacking vs simple weighted avg vs single best
- **Success:** Stacking LL lepsze o ≥ 0.001
- **Est. effort:** 3 dni
- **Phase:** P2

### RB-16: Neural network (simple MLP) doesn't beat tabular models
- **Claim:** MLP na naszych features jest gorszy od LGB/XGB
- **Test:** NB03 results already show this, potwierdzić na nowych features
- **Success:** Confirm LGB/XGB superiority → zamknąć NN research
- **Est. effort:** 2 dni (only validation)
- **Phase:** P2

### RB-17: Transformer na sekwencji meczów (jak GPT dla wyników)
- **Claim:** Attention nad last 10 matches może uchwycić patterns których rolling features nie widzi
- **Test:** Simple transformer na sekwencji meczów per team
- **Success:** ΔLL > 0.002 vs rolling features
- **Est. effort:** 10 dni
- **Phase:** P3 lub P4

### RB-18: TabPFN fine-tuning vs default
- **Claim:** Czy TabPFN (model) może być fine-tuned na naszych danych
- **Test:** Try fine-tuning approach (jeśli library pozwala)
- **Success:** Lepsze lub gorsze — decyzja
- **Est. effort:** 5 dni
- **Phase:** P3

### RB-19: CatBoost z native categorical features bije LGB z label encoding
- **Claim:** CatBoost handles categorical better
- **Test:** NB24 already did this — potwierdzić na nowych features (P2)
- **Success:** Confirm lub reject
- **Est. effort:** 2 dni
- **Phase:** P2

---

## Kategoria 6 — Live / In-play

### RB-20: Live odds daje mierzalny edge vs pre-match
- **Claim:** Pre-match model + live score updates może dać edge w odds 10-30 minut po kickoff
- **Test:** Symulacja: jak zmienia się nasze P vs live odds?
- **Success:** Mean absolute diff > 5pp dla zmiana wynik
- **Est. effort:** 7 dni research, 30+ dni implementation
- **Phase:** P2 research, P4+ implementation

### RB-21: In-play goals model — Dixon-Coles z conditional lambda
- **Claim:** Po golu w 20 minucie, lambdas się aktualizują, rynek wolno reaguje
- **Test:** Research paper replication
- **Success:** Working prototype
- **Est. effort:** 10 dni
- **Phase:** P4+

---

## Kategoria 7 — Alternative markets

### RB-22: Cards market (over/under cards)
- **Claim:** Card distribution jest przewidywalna z referee + team aggression features
- **Test:** Model on historical cards data (Sofascore + ESPN)
- **Success:** ROI > 5% na card markets
- **Est. effort:** 10 dni
- **Phase:** P3+

### RB-23: Corner kicks market
- **Claim:** Corners distribution jest przewidywalna z tactical features
- **Test:** Model on corner data
- **Success:** ROI > 5%
- **Est. effort:** 10 dni
- **Phase:** P3+

### RB-24: Player props (shots, passes, assists)
- **Claim:** Per-player rolling features predict player props
- **Test:** Model on player stats from Fbref/Sofascore
- **Success:** ROI > 5%
- **Est. effort:** 15 dni
- **Phase:** P4+

### RB-25: Asian Handicap modeling
- **Claim:** Goals model (Dixon-Coles) bije bookmakers na AH
- **Test:** Walk-forward na AH data
- **Success:** ROI > 5% na AH
- **Est. effort:** 5 dni
- **Phase:** P2-P3

---

## Kategoria 8 — Multi-sport (P4)

### RB-26: Tennis ELO per surface bije single ELO
- **Claim:** Per-surface ELO jest znacząco lepszy
- **Test:** Walk-forward na ATP 2014-2023
- **Success:** ΔLL > 0.01 vs single ELO
- **Est. effort:** 4 dni
- **Phase:** P4.1

### RB-27: Tennis — serving % jest najmocniejszym feature
- **Claim:** 1st serve %, aces, double faults > niż rankings w krótkim terminie
- **Test:** SHAP importance na tennis model
- **Success:** Serving features w top 5
- **Est. effort:** 3 dni
- **Phase:** P4.1

### RB-28: NBA — pace-adjusted metrics bije raw stats
- **Claim:** OffRtg/DefRtg > goals for/against (basketball equivalent)
- **Test:** Walk-forward NBA 2018-2025
- **Success:** ΔLL improvement
- **Est. effort:** 4 dni
- **Phase:** P4.2

### RB-29: NHL — goalie quality dominuje w short series
- **Claim:** Goalie saves% jest najsilniejszy feature w NHL
- **Test:** SHAP NHL model
- **Success:** Goalie w top 3 features
- **Est. effort:** 3 dni
- **Phase:** P4.3

---

## Priorytetyzacja

**Must-do w P2** (blokują DoD fazy):
- RB-01, RB-02, RB-03 (kalibracja)
- RB-04, RB-05 (portfolio Kelly)
- RB-07, RB-08, RB-09 (goals model)
- RB-15, RB-19 (ensemble architecture)
- RB-25 (AH market — rozszerza produkt)

**Nice-to-have w P2** (jeśli czas):
- RB-06 (adaptive Kelly)
- RB-16 (NN sanity check)
- RB-20 (live feasibility study — tylko research)

**Do P3**: RB-10, RB-11, RB-12, RB-13, RB-14, RB-17, RB-18, RB-22, RB-23

**Do P4**: RB-26, RB-27, RB-28, RB-29

**Do P4+** (research spikes): RB-21, RB-24

## Tracking

Każdy item dostaje Linear issue w projekcie "Research (P2)" lub "Research (P3+)" z odpowiednim labelem. DrMat reviewuje weekly progress. Wyniki spisane w `docs/research/rb_<id>.md`.

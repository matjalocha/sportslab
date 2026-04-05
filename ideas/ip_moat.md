# IP Moat — Autorskie podejście

**Owner:** DrMat (primary) + MLEng (implementacja)
**Status:** Do rozpisania i udokumentowania w Fazie 2

Ten dokument opisuje **przewagę konkurencyjną projektu** — co odróżnia nas od darmowych modeli (FiveThirtyEight SPI, ClubElo) i od drogich rozwiązań (Stats Perform, Opta).

## Zasada: trzy warstwy różnicowania

1. **Dane** — kombinacja źródeł, której konkurencja nie ma w jednym miejscu
2. **Modele** — hybrydowa architektura + kalibracja + portfolio Kelly
3. **Produkt** — targetowanie niszy (kluby niższych lig, trenerzy multi-sport) niedostępnej dla gigantów

## 1. Warstwa danych (Data Moat)

### Unikalne cechy naszego data lake'u

- **Top-5 lig + Top-10 lig (po P3)** z pełnym historical (2014/15–present) zenrichowane:
  - Understat xG (shot-by-shot)
  - ClubElo dynamic rating
  - FIFA ratings per sezon per gracz
  - ESPN possession, fouls, pace metrics
  - Sofascore rounds + lineups
  - Transfermarkt market values + transfers
  - Pinnacle closing odds (gold standard)
  - STS / LVBet / Superbet / Fortuna / Betclic opening/closing (after P0 + P5)
- **Tenis** — Jeff Sackmann historical + ELO per surface + live ATP rankings + nasze feature engineering (forma, zmęczenie, H2H deep)
- **Koszykówka** — NBA Stats API + EuroLeague + pace-adjusted metrics + player availability
- **Hokej** — NHL API + Natural Stat Trick + SHL scraping

### Czemu to IP

Żadna darmowa platforma nie łączy tych źródeł w jedną, **kalibrowaną, kompletną, kwerenonalną bazę**. Konkurencja płatna (Opta, Stats Perform) ma własne dane, ale:
- Licencjonują je dopiero od €10k/m-c
- Nie dają dostępu SQL/API do raw danych
- Nie enrichują xG z 5 źródeł (tylko swoje)

## 2. Warstwa modeli (Model Moat)

### Autorska architektura — **"Hybrid Calibrated Portfolio"**

**Motywacja:** Pojedyncze modele (LGB, XGB, TabPFN) są dobre, ale:
- LGB/XGB overfitują na małych seasonal shiftach
- TabPFN jest magicznie silny, ale **notorycznie overconfident** (ECE może być wysokie)
- Poisson/Dixon-Coles jest stabilny, ale słabszy na 1X2
- Żaden z nich nie radzi sobie dobrze z **portfolio optimization** (korelacje między betami w akumulatorach, jedna runda)

### Komponenty hybrydy

**A. Model Layer (ensemble z różnorodnością)**

1. **LGB Tuned** (baseline 100 features + 45 new features z NB13)
2. **XGBoost Tuned** (różne hiperparametry, różnica w sposobie splittingu)
3. **TabPFN** (10k recent samples, n_estimators=8) — uśrednione z ECE-aware shrinkingiem
4. **Bayesian Dixon-Coles** (goals model, dla AH, O/U, Correct Score) — **IP DrMat**
5. **Logistic Regression stacking** (meta-learner) z OOF predictions z 1-4

**B. Calibration Layer**

- Platt + Isotonic tested per liga per sezon (wybór best w walk-forward)
- **Beta calibration per market** (1X2, O/U, BTTS) — ważne, bo różne rynki mają różne base rates
- **Temperature scaling** dla TabPFN — korekta overconfident predictions
- **Monitoring ECE online** — jeśli ECE przekroczy próg, model się re-kalibruje

**C. Portfolio Layer — "Shrunken Bayesian Kelly"** — **IP DrMat + MLEng**

Zamiast niezależnego Kelly per bet:

```
stake_i = alpha * kelly_i * shrink(p_i, odds_i, volume_i) * position_limit(i, portfolio)
```

gdzie:
- `kelly_i` — klasyczny fractional Kelly na danym becie
- `alpha` — globalny parameter (0.1-0.5), optymalizowany per strategia
- `shrink(p_i, odds_i, volume_i)` — shrinkage w kierunku rynku gdy:
  - nasz edge jest zbyt duży (outlier, wiarygodność spadkiem)
  - odds są ekstremalne (>5.00 lub <1.20)
  - rynek jest mało płynny (volume niski, spread szeroki)
- `position_limit(i, portfolio)` — ograniczenia na:
  - max exposure per match (default 3%)
  - max exposure per runda (default 15%)
  - max exposure per liga (default 20%)
  - max exposure na pojedyncze team (gdy team jest w 3+ betach jednocześnie)
  - maksymalna korelacja między akumulatorami (unikanie duplikatów nóg)

**D. Drift Detection Layer**

- Feature drift — PSI (Population Stability Index) na key features rolling 30 dni
- Label drift — rozkład W/D/L vs expected
- Odds drift — nasza implied vs rynek implied, alerty gdy divergence >3σ
- **Auto-retraining trigger** gdy driftów przekroczą próg

### Czemu to IP

- **Portfolio Kelly z shrinkage'em** jest opisany w akademikach, ale **nikt tego nie ma jako production pipeline**
- **Temperature scaling TabPFN per liga per sezon** — nowa konfiguracja, brak benchmarków w literaturze
- **Combined drift detection → retraining** — standard w MLOps finansowym, rzadkość w sports betting

## 3. Warstwa produktu (Product Moat)

### Nisza niedostępna dla gigantów

- **Stats Perform / Opta** kosztują €50k+/rok. Kluby Ekstraklasy, I ligi, Championship niższego środka, wszystkie akademie — **nie stać ich**.
- **Darmowe** (FiveThirtyEight, ClubElo) — są **nieprecyzyjne** i bez custom analiz.
- **My** targetujemy lukę: **€500-3000/m-c** z dashboardem jakości Opta dla małych klubów i trenerów.

### Mechanizmy lock-in

1. **Historical data** — klient importuje nasze dane do swoich raportów, nie chce stracić historii
2. **Custom models per klub** — stopniowo trenujemy model tuned pod ich specyficzny kontekst (ich liga, ich przeciwnicy)
3. **API rate + volume discounts** — im więcej używają, tym taniej per call
4. **White-label** — ich branding, nie chcą migrować

### Network effects (długoterminowo)

- Klub 1 używa naszego dashboardu → generuje notyfikacje o trendach w lidze
- Klub 2 z tej samej ligi dostaje lepszy kontekst (bo mamy więcej lineupów, formacji, danych pozycyjnych)
- Compounding value dla kolejnych klubów w tej samej lidze

## 4. Dokumentacja IP

### Do wykonania w P2

- [ ] White paper "Hybrid Calibrated Portfolio Kelly" — 15-20 stron, publikowane na arXiv jako credibility boost
- [ ] Patent research — czy warto zgłaszać patenty na metody? (W PL trudne, w US łatwiejsze)
- [ ] Branded naming — "SportsLab Platform", "EdgeML", "PitchIntel"... decyzja brandingowa w P0
- [ ] Open-source vs closed-source strategy — core IP zamknięte, helper utilities open-source (marketing)

### Etyka i transparentność

- **Nie publikujemy daily value betów publicznie** — to hurtownia dla klientów B2B.
- **Transparentność metodologii** — opisujemy co robimy (jak FiveThirtyEight), nie podajemy exact hyperparametrów.
- **Odpowiedzialna gra** — w landing page + onboarding komunikujemy że typy są statystyką, nie gwarancją.

## 5. Benchmark vs konkurencja

| Cecha | Nasza platforma | Stats Perform | Opta | FiveThirtyEight | ClubElo | Statsbomb |
|---|---|---|---|---|---|---|
| Cena wejściowa | €200-500/m-c | €10k+/m-c | €10k+/m-c | darmo | darmo | €50k+/rok |
| API dostęp | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Raw data download | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ✅ |
| Modele ML | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ (SPI) | ❌ |
| Custom dashboards | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Backtest as service | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Multi-sport | ✅ (3) | ✅ (wiele) | ✅ (wiele) | ❌ (tylko piłka) | ❌ | ❌ |
| Lower league coverage | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ⚠️ |
| Self-serve onboarding | ✅ | ❌ | ❌ | N/A | N/A | ❌ |

**Legenda:** ✅ = silne, ⚠️ = częściowe, ❌ = brak.

## 6. Gdy IP przestanie być wyjątkowe (plan awaryjny)

- Gdy ktoś skopiuje portfolio Kelly → skupiamy się na **customer relationships** (kluby nie chcą zmieniać vendora)
- Gdy TabPFN stanie się commodity → przechodzimy na jeszcze nowsze architektury (in-context learning dalsze ewolucje)
- Gdy ligi otworzą API → przesuwamy się w stronę **insights layer** (nie dane, tylko interpretacja)

## 7. Pierwsze kroki (actionable w P2)

1. DrMat spisuje formalnie metodologię "Hybrid Calibrated Portfolio Kelly" w `ip_moat.md` (rozszerzenie tego pliku)
2. MLEng implementuje prototype w `src/ml_in_sports/models/portfolio_kelly.py`
3. Backtest na pełnym historical (5 lig × 10 sezonów)
4. Porównanie z obecnym ensemble (NB14) i TabPFN
5. Publikacja whitepaper (arXiv) — credibility boost dla P6

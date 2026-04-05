# Sport Prioritization — Scoring Matrix

**Cel:** Usystematyzowane podejście do wyboru sportów w P4 i P4+ (po P4 może być apetyt na kolejne).
**Scoring:** Każdy sport oceniany na 4 wymiarach (1-5), waga sumowana.

## Wymiary oceny

### 1. Data Availability (waga: 30%)
- Czy mamy darmowe historical
- Czy API jest stabilne
- Czy coverage jest kompletny
- Czy jakość danych jest wysoka (mało braków, mało błędów)

### 2. Market Size (waga: 25%)
- Ile bukmacherów oferuje rynki
- Jaki jest volume na rynkach
- Ile typów rynków (1X2, O/U, spread, props, futures)
- Czy rynek jest europejski (dla nas priorytet)

### 3. Edge Potential (waga: 25%)
- Czy rynek jest "mądry" (Top-5 liga piłki = tak) czy "naiwny" (SHL = nie)
- Czy bukmacherzy mają asymetrię informacji (np. rzadkie ligi)
- Czy nasza metoda (ML) jest w stanie wykorzystać tę asymetrię

### 4. Client Demand (waga: 20%)
- Czy istnieje potencjalny B2B klient dla tego sportu
- Czy nasi obecni kontakci (tipsterzy, kluby) są zainteresowani
- Czy jest to sport, do którego łatwo przyciągać inbound leads

## Scoring matrix (P4 + future sports)

### 1-5 scale

| Sport | Data | Market | Edge | Client | **Total** | Priorytet |
|---|---|---|---|---|---|---|
| **Piłka top-5** (obecne) | 5 | 5 | 3 | 5 | **4.55** | Core |
| **Piłka lower (P3)** | 4 | 4 | 4 | 4 | **4.00** | High (P3) |
| **Tennis ATP/WTA** | 5 | 5 | 3 | 4 | **4.30** | **Very High (P4.1)** |
| **Basketball NBA** | 5 | 5 | 3 | 4 | **4.30** | **Very High (P4.2)** |
| **Basketball EuroLeague** | 3 | 3 | 4 | 3 | **3.20** | Medium (P4.2 bonus) |
| **Hockey NHL** | 5 | 4 | 4 | 3 | **4.05** | **High (P4.3)** |
| **Hockey SHL** | 3 | 2 | 5 | 2 | **3.05** | Low (P4.3 bonus) |
| **Football MLS** | 4 | 4 | 4 | 3 | **3.85** | P3 |
| **Football Brasileirão** | 3 | 4 | 5 | 3 | **3.85** | P3 |
| **Baseball MLB** | 5 | 4 | 2 | 2 | **3.35** | P5+ (US focus) |
| **American Football NFL** | 4 | 5 | 2 | 2 | **3.35** | P5+ |
| **Cricket (T20, Test)** | 3 | 5 | 4 | 3 | **3.85** | P5+ (high volume Asia) |
| **Rugby (Six Nations, Premiership)** | 3 | 3 | 3 | 3 | **3.00** | P5+ |
| **E-sport (CS:GO, Dota, LoL)** | 4 | 4 | 3 | 4 | **3.80** | P5+ (trend) |
| **Handball** | 2 | 2 | 5 | 2 | **2.70** | P6+ |
| **Volleyball** | 2 | 2 | 4 | 2 | **2.40** | P6+ |
| **Darts** | 2 | 3 | 3 | 2 | **2.55** | P6+ (UK market) |
| **Formuła 1** | 4 | 3 | 2 | 4 | **3.25** | P5+ (brand value) |
| **Boks/MMA (UFC)** | 3 | 4 | 3 | 3 | **3.25** | P6+ |

### Waga detail:

```
Total = 0.30 * Data + 0.25 * Market + 0.25 * Edge + 0.20 * Client
```

## Analiza Top 3 wyborów dla P4

### #1 — Tennis (score 4.30)

**Strengths:**
- Jeff Sackmann ma kompletne, darmowe dane ATP i WTA z feature'ami jakich nie mają w piłce (pełne serving stats per mecz, H2H deep)
- 1v1 vs 11v11 = prostsze modelowanie, mniej zmiennych, mniej noise
- Surface effects (clay/hard/grass/indoor) = unikalny i ważny feature engineering
- Rynki bukmacherskie płynne globalnie (nie tylko europejskie)
- **Klienci**: trenerzy tenisowi na różnych poziomach (ATP challenger, ITF, akademie juniorskie)

**Weaknesses:**
- ELO w tenisie jest bardzo silne — trudno pobić baseline
- Walkovers, retirements add noise
- Sezon ciągły (tylko przerwa grudzień) = mniej "pauzy" na retraining

**Start reason:** Najłatwiejszy onboarding, dobry proof że abstract framework działa.

### #2 — Basketball (score 4.30, tied)

**Strengths:**
- NBA jest globalnym sportem #2 — market size ogromny (US + Europe + Asia)
- NBA Stats API jest **oficjalne, darmowe, bogate** (wszystko co potrzeba i więcej)
- Pace-adjusted metrics są standardem — nasz edge w dokładnej ich kalkulacji
- 82 regular season games + playoffs = dużo danych
- Player availability (load management) jest kluczowe i niedocenianie — nasz potencjalny edge
- **Klienci**: NBA fantasy apps (duży rynek), koszykarskie akademie, tipsterzy NBA

**Weaknesses:**
- Wysokie tempo (10-15 meczów dziennie) = obciążenie pipeline'u
- Star player impact jest gigantyczny → injuries są wybiórcze i hard to predict
- Rynek jest "mądry" — dużo tipsterów i profesjonalnych modeli

**Kolejność:** Po tenisie, gdy framework już pokazał że działa.

### #3 — Hockey NHL (score 4.05)

**Strengths:**
- NHL API darmowe, bogate
- Mniej konkurencji tipsterów = **potencjalnie wyższy edge**
- Natural Stat Trick / Moneypuck dają advanced xG-equivalent metrics
- Goalie jako single biggest factor = unusual feature structure, uniquely modelable

**Weaknesses:**
- Overtime / shootout adds variance (trzeba mieć regulation + full-time osobne modele)
- Small team pool (32 teams) = overfitting risk
- Krótki sezon (październik-kwiecień) = przerwa w pipeline latem

**Kolejność:** Trzeci, gdy tennis i NBA stabilne. Niszowy, ale uczy innego podejścia (goalie-centric).

## Sporty odrzucone dla P4 (z uzasadnieniem)

### Baseball (MLB)
- **Score:** 3.35
- **Powód odrzucenia:** US-focused, market size duża ale nasz target jest europejski. Bardzo statystyczny sport (już zakopany przez analityków). Wysoki barrier to entry.
- **Future:** P5+ jeśli zdobywamy US klientów.

### American Football (NFL)
- **Score:** 3.35
- **Powód odrzucenia:** Tylko 17 regular season games × 32 teams = mało danych dla ML. US-focused. Handicap market dominuje (wymagałby osobnej specialization).
- **Future:** P5+ jako niche addition.

### Cricket
- **Score:** 3.85 (high!)
- **Powód odrzucenia:** Asia-focused, culturowo odległe dla zespołu. Wysoka złożoność (T20 vs ODI vs Test są różnymi sportami).
- **Future:** P5+ jako big expansion, wymagałoby domain expert.

### E-sport
- **Score:** 3.80
- **Powód odrzucenia:** Dane są, ale fundamentalne different (meta changes, patch dependencies, roster rotacje miesięcznie). Wymagałby dedicated research phase.
- **Future:** P5+ jako trend-following, high growth market.

### Formuła 1
- **Score:** 3.25
- **Powód odrzucenia:** Tylko 23 wyścigi w sezonie, bardzo deterministyczny top-3 (Verstappen dominuje), mały edge.
- **Future:** P6+ jako brand-building (każdy zna F1), ale nie jako core.

### Handball, Volleyball, Darts
- **Score:** 2.40-2.70
- **Powód odrzucenia:** Małe rynki, słabe dane, niszowe.
- **Future:** Być może P6+ jako "European niche package" dla lokalnych klientów.

## Roadmap sportów long-term

```
P0-P3: Piłka nożna (5 lig → 10 lig)
P4.1: Tennis ATP/WTA                  [4.30]
P4.2: Basketball NBA + EuroLeague     [4.30 + 3.20]
P4.3: Hockey NHL + SHL                [4.05 + 3.05]

── Gate: P4 complete, 3 sports live ──

P5+: Może dodać jeden z:
      - NFL (jeśli mamy US klientów)    [3.35]
      - MLB (jeśli mamy US klientów)    [3.35]
      - Cricket (jeśli mamy Asia outreach) [3.85]
      - E-sport (jeśli trend wspiera)   [3.80]

P6+: Niche European additions:
      - Handball, Volleyball, Darts dla lokalnych klientów
      - F1 jako brand marketing play
```

## Decision criteria dla P5+ sportów

Dodajemy nowy sport tylko gdy:
1. **Abstract framework z P4 dowiódł że działa** (P4.X.1 contract tests zielone)
2. **Istnieje potwierdzony klient** który zapłaci za ten sport
3. **ROI analysis** pokazuje że koszt implementacji < expected revenue 12 mies.
4. **Ktoś z zespołu (lub konsultant)** ma domain knowledge

Nie dodajemy "bo można" — każdy sport = ongoing maintenance cost.

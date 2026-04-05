# Data Source Matrix — Per liga

**Cel:** Mapa które źródła mają co dla której ligi + jakość coverage + koszt scrapingu.
**Aktualizowane:** w P3.0 (audit) i potem per liga.

## Legenda

- ⭐⭐⭐⭐⭐ — Pełne, wysokiej jakości, darmowe
- ⭐⭐⭐⭐ — Prawie pełne, darmowe lub tanie
- ⭐⭐⭐ — Częściowe, wymaga scrapingu
- ⭐⭐ — Minimalne, trudne
- ⭐ — Brak lub nie nadaje się
- ❌ — Nie wspierane

## Źródła danych — co oferują

| Źródło | Typ | Piłka top-5 | Piłka lower | Tenis | NBA | NHL |
|---|---|---|---|---|---|---|
| **Understat** | xG shot-by-shot | ⭐⭐⭐⭐⭐ | ⭐⭐ (EN Championship) | ❌ | ❌ | ❌ |
| **FBref / StatsBomb** | Advanced stats | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ❌ | ❌ |
| **soccerdata (Python)** | Aggregator | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ❌ | ❌ |
| **Sofascore** | Rounds, lineups, scores | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **ESPN** | Stats, possession, fouls | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **ClubElo** | Dynamic ELO | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ❌ | ❌ |
| **football-data.co.uk** | Odds, scores | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ❌ | ❌ |
| **Transfermarkt** | Market values, formations | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ❌ | ❌ |
| **FIFA ratings (CSV)** | Player ratings | ⭐⭐⭐⭐ | ⭐⭐ | ❌ | ❌ | ❌ |
| **Pinnacle** | Closing odds | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **STS / LVBet / Fortuna / Betclic / Superbet** | Local odds | ⭐⭐⭐⭐ (PL market) | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Jeff Sackmann GitHub** | Tennis historical | ❌ | ❌ | ⭐⭐⭐⭐⭐ | ❌ | ❌ |
| **NBA Stats API** | NBA official | ❌ | ❌ | ❌ | ⭐⭐⭐⭐⭐ | ❌ |
| **NHL Stats API** | NHL official | ❌ | ❌ | ❌ | ❌ | ⭐⭐⭐⭐⭐ |
| **Natural Stat Trick / Moneypuck** | NHL advanced | ❌ | ❌ | ❌ | ❌ | ⭐⭐⭐⭐⭐ |
| **HLTV / Liquipedia** | E-sport | ❌ | ❌ | ❌ | ❌ | ❌ |

## Per liga — coverage matrix (football P3)

### Obecne (baseline)

| Liga | Understat | FBref | Sofascore | ESPN | ClubElo | TM | FIFA | Odds | Coverage |
|---|---|---|---|---|---|---|---|---|---|
| **EPL** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **100%** |
| **La Liga** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **100%** |
| **Bundesliga** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **100%** |
| **Serie A** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **100%** |
| **Ligue 1** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **100%** |

### Nowe (P3)

| Liga | Understat | FBref | Sofascore | ESPN | ClubElo | TM | FIFA | Odds | Est. Coverage |
|---|---|---|---|---|---|---|---|---|---|
| **Eredivisie** 🇳🇱 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ~85% |
| **Primeira Liga** 🇵🇹 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ~75% |
| **Championship** 🏴󠁧󠁢󠁥󠁮󠁧󠁿 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ~85% |
| **MLS** 🇺🇸 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ~75% |
| **Brasileirão** 🇧🇷 | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ~65% |

**Observation:**
- **Championship** jest największym winnerem — FBref ma pełny coverage, Sofascore excellent, ClubElo obejmuje, soccerdata wspiera. **Najniższy risk.**
- **Eredivisie** solidne, ale może mieć issues z xG (Understat nie pokrywa tak dobrze jak top-5).
- **Brasileirão** ma najsłabsze xG, ale największe market size i potencjalny edge. Requires custom scraping.
- **MLS** ma dobry ESPN coverage (US-focused), ale różny kalendarz sezonu (marzec-listopad).

## Kolejność wykonania w P3

1. **Championship first** — najniższy risk, najlepsze dane
2. **Eredivisie second** — stabilne źródła
3. **MLS third** — challenge z sezonem, ale ESPN pomaga
4. **Primeira Liga fourth** — mniejszy rynek, mniej urgent
5. **Brasileirão last** — highest risk, potentially highest reward

## Custom scraping decyzje

Dla Brasileirão i częściowo Primeira Liga może być potrzebne **dedicated scraping** z:
- **Soccerway** (European sites — więcej coverage)
- **Flashscore** (ostrożnie — aggressive anti-scraping)
- **SofaScore mobile API** (via reverse engineering — risk)
- **Globo Esporte** (Brasileirão specific)

Decyzja w P3.0 audit.

## Odds coverage — per bukmacher × liga

Do wypełnienia w P3.0 i P3.13.

| Bukmacher | EPL | Eredivisie | Primeira | Championship | MLS | Brasileirão |
|---|---|---|---|---|---|---|
| STS (PL) | ✅ | ✅ | ⚠️ limited | ✅ | ⚠️ | ❌ |
| LVBet (PL) | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ |
| Fortuna (CZ/PL) | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ |
| Betclic (FR/PT/PL) | ✅ | ⚠️ | **✅** | ✅ | ⚠️ | ✅ |
| Superbet (PL/RO) | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ |
| Pinnacle (global) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Betfair Exchange | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Key finding:** Pinnacle + Betfair Exchange są jedynymi z pełnym coverage dla wszystkich 10 lig. Lokalni bukmacherzy pokrywają top-5 i selective lower leagues.

**Implications dla produktu:**
- Value feed API musi integrować >=2 globalnych bukmacherów (Pinnacle/Betfair) + selected PL/UK/FR
- CLV tracking primary vs Pinnacle dla lower leagues
- Lokalni bukmacherzy są bonus, nie core

## Scraping strategia per liga (P3)

| Liga | Primary source | Secondary | Scraping complexity | Est. time setup | Est. maintenance/m-c |
|---|---|---|---|---|---|
| Eredivisie | soccerdata | FBref, Sofascore | Low | 3 dni | 2h |
| Primeira Liga | soccerdata | FBref, Sofascore | Medium | 4 dni | 3h |
| Championship | FBref | Sofascore, soccerdata | Low | 2 dni | 2h |
| MLS | ESPN + FBref | Sofascore | Medium (kalendarz) | 5 dni | 4h |
| Brasileirão | FBref + custom | Sofascore, Globo | High | 8 dni | 6h |

**Total setup:** ~22 developer-days
**Total maintenance:** ~17h/miesiąc ongoing

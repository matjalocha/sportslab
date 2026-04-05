# Bookmaker Accounts

**Owner:** Lead (primary), DataEng (integration)
**Status:** P0 task — zakładanie kont.

## Dlaczego potrzebujemy wielu bukmacherów

1. **Lepsze value bety** — różni bukmacherzy mają różne linie, szukamy arbitrów edge'owych
2. **Redundancja** — gdy jeden banuje konto, inny dostarcza odds
3. **Coverage per liga** — nie wszyscy oferują wszystkie ligi
4. **CLV tracking** — Pinnacle jako gold standard (closing odds)
5. **Produktowa wartość** — Value Feed API (SKU 1) musi agregować min. 5+ źródeł

## Lista bukmacherów

### Podstawowi (P0 — konta osobiste + firmowe)

| # | Bukmacher | Kraj | Dostęp | Status | Coverage | Priorytet |
|---|-----------|------|--------|--------|----------|---|
| 1 | **STS** | 🇵🇱 PL | Scraping | ✅ Już mamy | Top-5 liga PL | High |
| 2 | **LVBet** | 🇵🇱 PL | Scraping/API | P0 | Top-5 liga PL | High |
| 3 | **Superbet** | 🇵🇱 PL | Scraping | P0 | Top-5 liga PL | High |
| 4 | **Fortuna** | 🇨🇿 CZ/PL | Scraping | P0 | Top-5 liga EU | High |
| 5 | **Betclic** | 🇫🇷 FR/PT/PL | Scraping | P0 | Top-5 liga EU | High |

### Globalni (P0-P3 — dla CLV i coverage)

| # | Bukmacher | Kraj | Dostęp | Status | Coverage | Priorytet |
|---|-----------|------|--------|--------|----------|---|
| 6 | **Pinnacle** | 🇲🇹 MT | Account (via VPN, nie PL) | P0 | Global, gold standard | **Very High** |
| 7 | **Betfair Exchange** | 🇬🇧 UK | API | P2-P3 | Global | High |
| 8 | **Bet365** | 🇬🇧 UK | Scraping (trudne) | Opcjonalne | Global | Medium |
| 9 | **Marathonbet** | 🇷🇺/cypr | Account | Opcjonalne | Duże markety | Low |

### Regionalni (P3+ — dla lig lower)

| # | Bukmacher | Specjalizacja | Priorytet |
|---|-----------|---|---|
| 10 | **SBK** / **Smarkets** | UK exchange | Medium |
| 11 | **William Hill** | UK football lower leagues | Medium |
| 12 | **Unibet** | Scandinavian sports | Medium |
| 13 | **Kindred Group brands** | Europa | Low |

## KYC strategia

### Konta **firmowe** (po P0.2 rejestracja sp. z o.o.)

**Problem:** Jeśli jako osoba prywatna wygrasz zbyt dużo, bukmacherzy limitują konto ("gruba ryba"). Firma = inny profil klienta + limit exposure osobistej.

**Rozwiązanie:**
1. Konto firmowe jako **primary** (wszystkie zakłady + scraping)
2. Konta osobiste jako **testowe** (mały bankroll, testowanie nowych strategii)
3. Konto **partnera** (freelance DataEng/SWE) jako **backup** gdy firma zostanie zlimitowana

### KYC wymagania (per bukmacher)

| Bukmacher | KYC time | Wymagane dokumenty |
|---|---|---|
| STS | 1-3 dni | Dowód osobisty, potwierdzenie adresu |
| LVBet | 1-3 dni | j.w. |
| Superbet | 1-5 dni | j.w. |
| Fortuna | 1-3 dni | j.w. |
| Betclic | 1-7 dni | j.w. + potwierdzenie źródła środków |
| Pinnacle | **VPN needed, PL nie dostępne**, Malta licence | Paszport + utility bill + bank statement |
| Betfair | **PL nieregulowane** | j.w. |

**Pinnacle / Betfair note:** Polska nie jest w dostępnych rynkach (ustawa hazardowa). Potrzeba:
- Maltese / offshore company (opcja kompleksowa, P3+)
- Partnership z brokerem betting (np. BetInAsia, Sportmarket)
- API access via data partner (bez placing bets, tylko odds) — **rekomendacja**

## Integration strategy per bukmacher

### Scraping vs API

**Scraping (primary dla lokalnych PL):**
- STS, LVBet, Superbet, Fortuna, Betclic — Selenium/Playwright, anti-detect
- Rate limiting (12s między requestami min.)
- Rotacja user agents + proxies
- Retry logic, resume from failures

**API (primary dla globalnych):**
- **Pinnacle** — oficjalne API, wymaga odpowiedniej licencji dostępu
- **Betfair Exchange** — oficjalne API (app key + cert)
- **Odds API** (third-party aggregator) — https://the-odds-api.com, backup

### Data to scrape per source (odds types)

Minimum dla value feed:
- 1X2 (match winner)
- Over/Under 2.5 goals
- BTTS (both teams to score)

Nice to have (P2+):
- Asian Handicap (AH -1.5, -1, 0, +1, +1.5)
- Over/Under 0.5, 1.5, 3.5, 4.5
- Correct Score top-15
- Double Chance
- Draw No Bet

Advanced (P4+):
- Player props (goals, assists, shots on target)
- Cards total
- Corners total
- Half time / Full time
- First goal scorer

## Anti-detection + account health

### Anti-detection (scraping)
- User agent rotation
- Proxy rotation (residential > datacenter)
- Randomized delays (8-15s)
- Cookie management per session
- Captcha solving service (2captcha, jeśli potrzebne)
- Headless detection avoidance (stealth plugins)

### Account health (betting)
- **Nie betujemy wszystkich edge'ów** — bukmacherzy widzą "sharp" behavior
- **Mieszanina**: duże bety na low edge + małe na high edge (disguise)
- **Rotacja drużyn** — nie zawsze EPL, różne ligi
- **Normal distribution staking** — nie zawsze round numbers (zamiast 50 PLN stawiać 47 PLN)
- **Time distribution** — nie tylko pre-match, czasem mid-day
- **Account cooling periods** — po wygranej serii, zmniejszamy aktywność

### Limit management
Gdy konto limited:
1. Log w `bookmaker_limits.md` z datą
2. Identyfikacja co spowodowało (high win rate, specific markets?)
3. Przeprowadzenie się na drugie konto
4. Info do zespołu (aby inni nie popełnili tego samego błędu)

## Scraping monitoring

Per bukmacher metrics:
- Requests successful / failed (rate)
- Average response time
- Coverage (% meczów z odds)
- Freshness (ile minut temu ostatnie odds)
- Bans / blocks (captcha frequency)

Alerty:
- Coverage < 80% przez 1h → warning
- Captcha rate > 20% → block detection → switch proxy
- Complete failure > 10 min → critical → notify DataEng

## Cost estimation

### Początkowy koszt (P0)
- Deposit na każde konto: €100-500 (KYC + test betów)
- **Razem 5 kont polskich:** ~€1,500 bankroll testowy
- **Razem 1 konto globalne (Pinnacle via partner):** €500 setup + €500 bankroll

### Miesięczny koszt (P5+)
- Proxies (residential rotating): €50-100/m-c
- 2captcha (gdy wymagane): €10-30/m-c
- Odds API backup: €49-149/m-c
- Partner CLV Pinnacle data: €100-300/m-c
- **Razem:** ~€200-600/m-c

### Bankroll tradingowy (oddzielny od infra)
- **Początek:** €2,000 per bookmaker = €10,000 total
- **Po P2 (confirmed edge):** skalowanie gdy portfolio Kelly pokazuje positive
- **Uwaga:** Bankroll tradingowy **NIE** jest infrastruktury firmowej. To osobny księgowy bucket.

## Compliance

- **PL regulacje hazardowe:** STS, LVBet, Superbet, Fortuna, Betclic PL są licencjonowane w PL. Legalnie betujemy.
- **Cross-border betting:** Pinnacle, Betfair — **technicznie nielegalne z PL**, ale traktowane jako "data source" (bez placing bets) jest OK. Placing bets wymagałoby offshore company.
- **Podatki od wygranych:** w PL 10% podatku od wygranych z nielicencjonowanych bukmacherów, **0% od licencjonowanych PL**. To dodatkowy powód fokusu na PL-licensed dla placing bets.
- **Księgowość bankrolla:** wszystkie depozyty, withdrawals, net P/L muszą być zaraportowane. Zlecić księgowemu dedykowany księgowy bucket.

## Action items (P0)

1. **Lead:** Założ konta osobiste u STS (jeśli nie), LVBet, Superbet, Fortuna, Betclic
2. **Lead:** Decyzja o Pinnacle/Betfair approach (partner vs offshore)
3. **Lead:** Po P0.2 (firma) — przejście na konta firmowe gdzie możliwe
4. **DataEng:** Setup proxy infrastructure dla scraping
5. **DataEng:** Pierwsze scraping tests na wszystkich 5 polskich bukmacherach
6. **DataEng:** Storage credentials w Doppler, nigdy w kodzie

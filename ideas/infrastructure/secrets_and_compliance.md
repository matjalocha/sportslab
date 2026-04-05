# Secrets & Compliance

**Owner:** SWE (secrets), Lead (compliance), Prawnik (legal review)
**Status:** P0 — kluczowe decyzje muszą być podjęte przed rozpoczęciem pracy nad aplikacją komercyjną.

## Secrets management

### Co jest sekretem
- API keys bukmacherów (STS, LVBet, Superbet, Fortuna, Betclic, Pinnacle)
- Database credentials
- JWT signing keys
- OAuth client secrets
- Stripe API keys (live + test)
- Email provider keys (Resend)
- Cloud provider credentials (Hetzner, B2, Cloudflare)
- SSH keys
- Webhook secrets
- Third-party API keys (soccerdata, NBA Stats, Jeff Sackmann GitHub tokens)

### Gdzie przechowujemy

#### P0-P4 (small team)
- **1Password Teams** — human access (zespół), secrets shared w vaults
- **Doppler** — machine access (CI, apps), secrets injected at runtime
- **Vault structure w 1Password:**
  - `Engineering` — infra, Github, Docker registry
  - `Bookmakers` — wszystkie credentials scraping
  - `Cloud` — Hetzner, B2, Cloudflare
  - `Marketing` — Stripe, analytics
  - `Personal` — per osoba (ich własne)

#### P5+ (production)
- **Doppler Teams** — primary dla production + CI/CD
- **1Password Connect** — alternatywa jeśli Doppler jest za drogi
- **Secrets rotation** — automatic tam gdzie możliwe (Doppler managed rotations)

### Rules
1. **Zero hardcoded secrets** w kodzie, config files, git
2. **Pre-commit hooks** sprawdzają `detect-secrets` przed commitem
3. **GitHub Actions** używa GitHub Secrets (mapped z Doppler)
4. **Rotation cadence:**
   - JWT keys: co 90 dni
   - API keys bukmacherów: po każdym incydencie bezpieczeństwa
   - Database passwords: co 180 dni
   - OAuth secrets: co 180 dni
5. **Access control:**
   - Production secrets: tylko SWE + DataEng + Lead
   - Bookmaker credentials: tylko DataEng + Lead
   - Stripe live: tylko Lead + SWE

## Compliance

### 1. GDPR (RODO) — od P0 planowanie, od P6 enforcement

#### Jakie dane osobowe zbieramy
- **Players (zawodnicy) w sporcie:** Imię, nazwisko, data urodzenia, narodowość, pozycja, klub, wartość rynkowa
  - **Basis:** Publicznie dostępne dane, uzasadniony interes
  - **No PII sensitive** (medical, political, religious)
- **Nasi klienci (B2B w P6):** Imię, nazwisko, email, firma, VAT number, adres rozliczeniowy, usage data
  - **Basis:** Umowa (wykonanie kontraktu)
- **Użytkownicy landing page (P6):** IP, browser fingerprint (via PostHog), email jeśli zapisali się do waitlist
  - **Basis:** Legitimate interest + explicit consent (cookies banner)

#### Obowiązki
- [ ] **Privacy Policy** opublikowana (P6.0.7)
- [ ] **Cookie consent banner** (P6 landing)
- [ ] **Data Processing Agreement** (DPA) dla klientów B2B (P6.0.7)
- [ ] **Right to access** — endpoint API zwracający user data
- [ ] **Right to deletion** — endpoint DELETE usuwający user
- [ ] **Right to portability** — export user data jako JSON
- [ ] **Data Protection Officer** (DPO) — jeśli przetwarzamy systematically > 5000 osób (prawdopodobnie nie wcześniej niż P6+)
- [ ] **Breach notification** — procedura (72h do GIODO)
- [ ] **Processor register** — lista wszystkich processors (Stripe, Clerk, Hetzner, B2, PostHog)

#### Obowiązek EOD
- Prawnik review (P0.1) — **KRYTYCZNE**
- Compliance-by-design od P1
- Audit przed P6 launch

### 2. Regulacje hazardowe

#### Polska (ustawa z 19 listopada 2009)
- **Bukmacherzy z licencją PL:** STS, LVBet, Superbet, Fortuna, Betclic — legalnie betujemy
- **Bukmacherzy bez licencji PL:** Pinnacle, Betfair, Bet365 — **placing bets jest nielegalne z PL IP**
  - Rozwiązanie: data partner, który pobiera odds legalnie (traktujemy jako data source)
  - Nigdy nie placing bets na nielicencjonowanych
- **Podatki:**
  - Wygrane z licencjonowanych PL: **zwolnione z podatku**
  - Wygrane z nielicencjonowanych: **10% podatku + penalty**

#### Serwis tipster (B2C) w UE
- **Polska:** Brak osobnej licencji dla "samej porady" (nie betujemy za klientów)
- **Niektóre kraje UE:** Wymagają osobnej licencji tipster (Hiszpania, Francja)
- **UK (post-Brexit):** Gambling Commission authorization dla tipster services
- **Decyzja:** **SKU 9 (Telegram B2C) tylko po analizie prawnej per target market**

#### Serwis B2B (Value Feed API + dashboardy)
- **Legalnie bez licencji hazardowej** — sprzedajemy dane i narzędzia analityczne, nie oferujemy zakładów
- **Disclaimer wymagany:** "Data for informational purposes. Not gambling advice."
- **ToS zabrania:** resale as gambling service bez własnej licencji klienta

### 3. Podatki

#### Podatek CIT (firma sp. z o.o.)
- **19% CIT** od zysku (lub 9% mały podatnik do €2M przychodów)
- **Księgowy** zarządza, my dostarczamy faktury + dokumenty

#### VAT
- **23% VAT w PL** dla usług IT
- **Reverse charge** dla B2B intra-EU (nie naliczamy VAT, klient rozlicza)
- **0% dla usług poza UE** (z dokumentami eksportowymi)
- **OSS** (One Stop Shop) dla B2C digital services w UE (jeśli sprzedajemy do konsumentów w innych krajach UE, jednolite rozliczenie VAT)

#### Podatek od wygranych
- **Licencjonowani bukmacherzy PL:** 0% (zwolnione)
- **Nielicencjonowani:** 10% + penalty
- **Implikacja:** Tylko stawiamy u PL licensed

### 4. Licencje oprogramowania

#### Używane open-source
- Python + libraries (MIT, BSD, Apache 2.0 → wolno komercyjnie)
- Next.js (MIT → wolno)
- Postgres (PostgreSQL license → wolno)
- TabPFN (MIT? sprawdzić)
- soccerdata (MIT? sprawdzić — **action item**)
- Jeff Sackmann tennis data (CC license — sprawdzić **DOKŁADNIE**, wymaga atrybucji)

#### Decyzja
- **Audit dependencies** w P0.1 (Prawnik + SWE)
- **Dokumentacja atrybucji** w `LICENSE.md` i credits w aplikacji
- **Unikać GPL/AGPL** (viral license), zastępujemy alternatywami

### 5. Terms of Service + Privacy Policy (P6)

#### Templates do adaptacji
- **Termly** (https://termly.io) — free generator dla basic ToS/PP
- **Iubenda** — paid, bardziej comprehensive
- **Prawnik review** — obowiązkowe przed publikacją

#### Kluczowe klauzule ToS
- Disclaimer: data for informational purposes
- No guarantee of accuracy / profit
- Liability limitation
- Prohibited uses (resale, scraping z nas, spam)
- Account termination conditions
- Refund policy
- Governing law (Polska lub inne, zależy od prawnika)

### 6. Security best practices

#### Application security
- **HTTPS everywhere** — Cloudflare SSL
- **CSRF protection** — standard library
- **SQL injection** — parameterized queries wszędzie (SQLAlchemy robi to natywnie)
- **XSS** — Next.js escaping + CSP headers
- **Rate limiting** — per token, per IP
- **Authentication** — Clerk (OAuth + MFA)
- **Secrets at rest encryption** — Doppler robi to natywnie

#### Data security
- **Encryption at rest** — Postgres tablespace encryption (jeśli sensitive data)
- **Encryption in transit** — TLS everywhere
- **Backup encryption** — B2 zapewnia, dodatkowo nasze klucze
- **Database access logging** — Postgres audit

#### Monitoring security
- **Better Stack / Grafana** — failed login attempts, suspicious patterns
- **Cloudflare WAF** — basic rules dla common attacks
- **Dependabot** — security updates dla dependencies

### 7. Incident response

#### Scenarios
1. **Database breach** — kradzież danych klientów
2. **Bookmaker account compromised** — ktoś wykrada credentials
3. **Model poisoning** — zły deployment psuje predictions
4. **DDoS** — atak na API
5. **Code leak** — źródła IP w publicznym repo

#### Runbook (do utworzenia w P5.40)
- Kto jest incident commander (zazwyczaj Lead)
- Communication channels (Slack #incidents)
- Escalation per severity (P0-P4)
- Post-mortem template
- GDPR breach notification (72h)

## Action items per faza

### P0
- [ ] **Konsultacja prawnika** — forma prawna, GDPR readiness, ToS draft (P0.1)
- [ ] **License audit dependencies** — sprawdzenie wszystkich używanych libraries
- [ ] **Doppler** + **1Password Teams** setup
- [ ] **Secrets migration** — wszystko co obecnie hardcoded → secrets vault
- [ ] **Pre-commit hooks** — detect-secrets

### P1
- [ ] **Security audit kodu** — pierwszy review przez SWE + Lead
- [ ] **Pipeline dependencies update** — pinned versions, security patches

### P2
- [ ] Data retention policy zaimplementowana

### P5
- [ ] **Backup encryption** działa
- [ ] **Monitoring security events** (failed logins, suspicious API calls)
- [ ] **Incident response runbook**

### P6.0
- [ ] **Privacy Policy** + **Terms of Service** opublikowane
- [ ] **Cookie consent** na landing
- [ ] **DPA template** dla klientów B2B
- [ ] **GDPR endpoints** (access, delete, export)
- [ ] **Legal review przez prawnika** — pełny audit
- [ ] **Disclaimer** na aplikacji i w ToS

### P6+
- [ ] **Regular pentest** — zewnętrzny audit raz na rok
- [ ] **Bug bounty** (opcjonalnie)
- [ ] **SOC 2 / ISO 27001** (gdy klienci enterprise żądają)

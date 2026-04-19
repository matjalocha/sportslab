# Polityka Prywatności — SportsLab (alpha)

**Wersja:** v0.1 — alpha draft
**Data wersji:** 2026-04-19
**Podstawa prawna:** rozporządzenie Parlamentu Europejskiego i Rady (UE) 2016/679 z dnia
27 kwietnia 2016 r. (RODO / GDPR), ustawa z dnia 10 maja 2018 r. o ochronie danych
osobowych (Dz.U. 2018 poz. 1000), ustawa z dnia 18 lipca 2002 r. o świadczeniu usług
drogą elektroniczną, dyrektywa 2002/58/WE (ePrivacy).

---

> **DISCLAIMER — do autora / zespołu SportsLab**
>
> Ten dokument jest wewnętrznym draftem, przygotowanym przez asystenta AI. **Nie jest
> poradą prawną.** Przed publikacją wewnątrz produktu wymagana jest weryfikacja przez
> radcę prawnego specjalizującego się w RODO/GDPR oraz uzupełnienie placeholderów
> `[PLACEHOLDER: ...]` faktycznymi danymi.

---

## 1. Administrator danych osobowych

Administratorem danych osobowych, w rozumieniu art. 4 pkt 7 RODO, jest:

- **Nazwa:** [PLACEHOLDER: nazwa spółki / przedsiębiorcy prowadzącego JDG]
- **Forma prawna:** [PLACEHOLDER: np. sp. z o.o. albo JDG]
- **NIP:** [PLACEHOLDER]
- **REGON:** [PLACEHOLDER]
- **KRS (jeśli dotyczy):** [PLACEHOLDER]
- **Adres siedziby:** [PLACEHOLDER: ulica, nr, kod pocztowy, miasto]
- **Email kontaktowy (sprawy RODO):** [PLACEHOLDER: privacy@sportslab.app]
- **Email ogólny:** [PLACEHOLDER: kontakt@sportslab.app]

dalej: **„Administrator"** lub **„SportsLab"**.

## 2. Inspektor Ochrony Danych (DPO)

Zgodnie z art. 37 ust. 1 RODO, Administrator nie jest zobowiązany do wyznaczenia
Inspektora Ochrony Danych, ponieważ:

- nie jest organem publicznym,
- przetwarzanie danych nie wiąże się z regularnym i systematycznym monitorowaniem
  osób na dużą skalę,
- nie przetwarza w głównej działalności danych szczególnych kategorii (art. 9 RODO)
  ani danych dotyczących wyroków skazujących (art. 10 RODO) na dużą skalę.

W razie pytań dotyczących przetwarzania danych osobowych należy kontaktować się na
adres email: [PLACEHOLDER: privacy@sportslab.app]. Administrator zobowiązuje się do
odpowiedzi w terminie nie dłuższym niż **30 dni** (art. 12 ust. 3 RODO).

## 3. Kategorie zbieranych danych

Administrator zbiera i przetwarza następujące kategorie danych osobowych:

### 3.1. Dane konta

- adres email (identyfikator konta),
- hasło (w formie nieodwracalnego hashu — bcrypt/argon2),
- data utworzenia konta,
- data ostatniego logowania,
- status weryfikacji emaila,
- opcjonalnie: nazwa użytkownika / nick, język interfejsu, strefa czasowa.

Źródło danych: bezpośrednio od Użytkownika przy rejestracji.

### 3.2. Dane behawioralne / analityczne

- adres IP (w logach serwerowych — anonimizowany po 90 dniach),
- user-agent (przeglądarka, system operacyjny),
- czas i typ interakcji z Serwisem (strony przeglądane, kliknięcia),
- identyfikator sesji,
- metryki wydajnościowe (czas odpowiedzi, błędy frontendu).

Źródło: automatycznie gromadzone podczas korzystania z Serwisu. W fazie alpha Administrator
korzysta wyłącznie z narzędzi first-party (self-hosted) lub privacy-friendly
(np. Plausible Analytics, PostHog self-hosted).

### 3.3. Dane bukmacherskie (opcjonalne, w zakresie alpha — dobrowolne)

- historia własnych zakładów Użytkownika (bet history), o ile Użytkownik zdecyduje
  się ją ręcznie wpisać lub zintegrować,
- wyniki tych zakładów (sukces/porażka, stake, kurs),
- preferowany bankroll (dla kalkulacji Kelly),
- preferowany bukmacher / waluta.

Źródło: wyłącznie od Użytkownika, na zasadzie dobrowolności. Dane te są używane do
personalizacji rekomendacji i raportów ROI prywatnych dla Użytkownika.

### 3.4. Dane płatnicze (w fazie paid)

W fazie alpha (free tier) **Administrator nie zbiera** żadnych danych płatniczych.

Od momentu uruchomienia paid tier płatności będą obsługiwane przez **Stripe Inc.**
(patrz § 6). Administrator nie otrzymuje i nie przechowuje:
- pełnego numeru karty płatniczej (PAN),
- kodu CVV,
- daty ważności karty.

Administrator otrzymuje i przechowuje:
- identyfikator klienta w Stripe (`cus_…`),
- identyfikator subskrypcji,
- status subskrypcji (aktywna, anulowana, past_due),
- ostatnie 4 cyfry karty i marka karty (Visa/Mastercard) — dla wsparcia technicznego,
- kraj wystawcy karty (dla celów VAT OSS).

### 3.5. Dane marketingowe (opcjonalne, na zgodę)

- zgoda na otrzymywanie newslettera (timestamp, treść zgody),
- zgoda na komunikaty marketingowe w produkcie,
- preferencje kategorii treści,
- interakcje z emailami marketingowymi (open/click — na podstawie uzasadnionego interesu,
  z możliwością sprzeciwu).

### 3.6. Dane komunikacyjne

- treść reklamacji,
- korespondencja email z supportem,
- wiadomości w kanałach Telegram Usługodawcy (w zakresie niezbędnym do moderacji i
  obsługi).

### 3.7. Kategorie szczególne i danych dzieci

- **Dane szczególnych kategorii** (art. 9 RODO) — Administrator **nie przetwarza**
  danych o zdrowiu, pochodzeniu etnicznym, poglądach politycznych, przynależności
  związkowej, orientacji seksualnej.
- **Dane dzieci** (poniżej 16 lat) — Administrator **nie przetwarza** danych osób
  poniżej 18 lat (warunek uczestnictwa — § 3 Regulaminu).

## 4. Podstawy prawne przetwarzania (art. 6 RODO)

Dla każdej kategorii danych Administrator wskazuje podstawę prawną przetwarzania:

| Kategoria danych | Cel przetwarzania | Podstawa prawna (art. 6 RODO) | Okres retencji |
|---|---|---|---|
| Dane konta (email, hash hasła) | Świadczenie Usługi, założenie i utrzymanie Konta | **Art. 6 ust. 1 lit. b RODO** — wykonanie umowy | Do usunięcia Konta + 30 dni (buffer backup); dalej: tylko dane wymagane prawem |
| Dane behawioralne (IP, sesja, logi) | Bezpieczeństwo Serwisu, wykrywanie nadużyć, logi operacyjne | **Art. 6 ust. 1 lit. f RODO** — uzasadniony interes (bezpieczeństwo) | 90 dni (rotacja logów); anonimizacja IP |
| Dane behawioralne — analityka produktowa | Poprawa produktu, analityka użycia | **Art. 6 ust. 1 lit. f RODO** — uzasadniony interes (rozwój Usługi) | 12 miesięcy, potem agregacja (brak ID osobowych) |
| Dane bukmacherskie (bet history) | Personalizacja rekomendacji, raporty ROI | **Art. 6 ust. 1 lit. b RODO** — wykonanie umowy; **lit. a** — zgoda dobrowolna na rozszerzoną personalizację | Do usunięcia Konta |
| Dane płatnicze (paid tier) | Obsługa subskrypcji, billing, VAT | **Art. 6 ust. 1 lit. b RODO** — wykonanie umowy; **lit. c** — obowiązek prawny (księgowość, VAT) | 5 lat (wymóg księgowy) + 6 lat (przedawnienie podatkowe) |
| Dane marketingowe | Newsletter, komunikaty marketingowe | **Art. 6 ust. 1 lit. a RODO** — zgoda | Do odwołania zgody; historia zgód: 5 lat (dowód) |
| Dane komunikacyjne (reklamacje) | Obsługa reklamacji, dochodzenie roszczeń | **Art. 6 ust. 1 lit. b** (wykonanie umowy), **lit. c** (obowiązek prawny), **lit. f** (dochodzenie roszczeń) | 6 lat (przedawnienie roszczeń KC) |
| Dokumenty księgowe (faktury) | Wymogi księgowe, VAT, podatek dochodowy | **Art. 6 ust. 1 lit. c RODO** — obowiązek prawny | 5 lat (Ordynacja podatkowa, ustawa o rachunkowości) |

## 5. Okres retencji

Administrator przechowuje dane osobowe **nie dłużej niż jest to niezbędne** do celów,
dla których zostały zebrane, zgodnie z tabelą w § 4 powyżej. Po upływie okresu retencji
dane są usuwane lub anonimizowane w taki sposób, że nie można ich ponownie przypisać
do konkretnej osoby.

**Kopie zapasowe (backup):** Administrator wykonuje regularne kopie zapasowe systemów.
Usunięcie danych z głównej bazy nie oznacza natychmiastowego usunięcia z kopii zapasowych —
dane są usuwane z backupów w ramach normalnej rotacji (maksymalnie **30 dni** od daty
usunięcia z bazy głównej).

## 6. Odbiorcy danych (sub-processors)

Administrator korzysta z zewnętrznych dostawców usług (procesorów), z którymi zawarł
umowy powierzenia przetwarzania danych (Data Processing Agreement — DPA) zgodnie z
art. 28 RODO oraz, dla transferów do państw trzecich, Standardowe Klauzule Umowne
(Standard Contractual Clauses — SCC).

Aktualna lista sub-processorów na dzień wersji tego dokumentu:

| Dostawca | Rola | Lokalizacja | Podstawa transferu | Link do DPA |
|---|---|---|---|---|
| **Clerk, Inc.** | Uwierzytelnianie, zarządzanie kontami | USA (siedziba: Delaware) | SCC (moduł 2 — C2P); weryfikacja DPF | [clerk.com/legal/dpa](https://clerk.com/legal/dpa) |
| **Stripe, Inc.** (paid) | Płatności online, billing, VAT OSS | USA + Irlandia (Stripe Payments Europe, Ltd.) | SCC (moduł 2); DPF | [stripe.com/legal/dpa](https://stripe.com/legal/dpa) |
| **Vercel, Inc.** | Hosting frontend (Next.js) | USA; edge nodes globalne (w tym UE) | SCC + EU-US DPF; UK IDTA / addendum | [vercel.com/legal/dpa](https://vercel.com/legal/dpa) |
| **Hetzner Online GmbH** | Hosting backend, bazy danych, workers | Niemcy (Falkenstein, Nürnberg) | Brak transferu poza UE — Hetzner przetwarza w UE | [hetzner.com/rechtliches/auftragsverarbeitung](https://www.hetzner.com/rechtliches/auftragsverarbeitung/) |
| **Telegram Messenger Inc.** | Kanał komunikacji z Użytkownikami | Wielka Brytania (siedziba operatora w UK) | **Decyzja adekwatności KE z 28.06.2021** (UK adequacy decision) | Regulamin Telegram — brak oddzielnego DPA dla bot operators |
| **Backblaze, Inc.** (B2) | Backup cloud storage | USA (Kalifornia) | SCC (moduł 2); weryfikacja DPF | [backblaze.com/company/privacy-dpa.html](https://www.backblaze.com/company/privacy-dpa.html) |
| **[PLACEHOLDER: dostawca email, np. Postmark / Resend]** | Wysyłka emaili transakcyjnych | [PLACEHOLDER: USA] | [PLACEHOLDER: SCC + DPF] | [PLACEHOLDER] |
| **[PLACEHOLDER: dostawca analityki, np. Plausible / PostHog self-hosted]** | Analityka produktowa | [PLACEHOLDER: UE — Niemcy / self-hosted] | [PLACEHOLDER] | [PLACEHOLDER] |

Źródła referencyjne:
- [Stripe Data Processing Agreement](https://stripe.com/legal/dpa) (dostęp 2026-04-19),
- [Vercel Data Processing Addendum](https://vercel.com/legal/dpa) (dostęp 2026-04-19),
- [Stripe Sub-Processors](https://support.stripe.com/questions/stripe-s-sub-processors-and-vetting-process).

Administrator zobowiązuje się do:
- weryfikacji każdego sub-processora pod kątem zgodności z RODO (due diligence),
- powiadomienia Użytkowników z wyprzedzeniem 30 dni o zmianie lub dodaniu sub-processora
  przetwarzającego dane osobowe Użytkowników,
- publikacji aktualnej listy sub-processorów w niniejszej Polityce lub pod osobnym adresem.

## 7. Transfer danych do państw trzecich

Niektóre sub-processory mają siedzibę w USA lub innych krajach poza Europejskim Obszarem
Gospodarczym (EOG). Administrator zapewnia odpowiedni poziom ochrony danych zgodnie
z rozdziałem V RODO:

1. **EU-US Data Privacy Framework (DPF)** — na podstawie decyzji wykonawczej Komisji
   Europejskiej z dnia 10 lipca 2023 r. (2023/1795), transfer danych do certyfikowanych
   podmiotów w USA jest zgodny z RODO.
2. **Standardowe Klauzule Umowne (SCC)** — zgodnie z decyzją KE 2021/914 z dnia
   4 czerwca 2021 r., stosowane zastępczo lub uzupełniająco do DPF.
3. **Transfer Impact Assessment (TIA)** — dla transferów do USA i innych państw trzecich
   Administrator przeprowadził (albo przeprowadzi przed pierwszym transferem) ocenę
   skutków transferu danych, zgodnie z wytycznymi EROD 01/2020.
4. **UK adequacy** — Wielka Brytania (Telegram) korzysta z decyzji adekwatności KE z
   28 czerwca 2021 r.

Na pisemne żądanie (email: [PLACEHOLDER: privacy@sportslab.app]) Administrator udostępni
Użytkownikowi kopię zastosowanych zabezpieczeń (SCC, wynik TIA) lub inne informacje
dotyczące transferu.

## 8. Prawa Użytkownika (art. 15–22 RODO)

Użytkownikowi, którego dane dotyczą, przysługują następujące prawa:

### 8.1. Prawo dostępu (art. 15 RODO)
Prawo do uzyskania od Administratora potwierdzenia, czy przetwarzane są dane osobowe
dotyczące Użytkownika, a jeżeli tak — dostępu do tych danych oraz kopii.

### 8.2. Prawo do sprostowania (art. 16 RODO)
Prawo do żądania sprostowania nieprawidłowych danych lub uzupełnienia niekompletnych.
Użytkownik może samodzielnie zaktualizować większość danych w panelu Konta.

### 8.3. Prawo do usunięcia („prawo do bycia zapomnianym", art. 17 RODO)
Prawo do żądania usunięcia danych, o ile nie zachodzi przesłanka wyłączająca (np.
obowiązek prawny przechowywania faktur przez 5 lat).

### 8.4. Prawo do ograniczenia przetwarzania (art. 18 RODO)
Prawo do żądania wstrzymania przetwarzania danych, np. w okresie weryfikacji poprawności
lub dopóki nie zostanie rozstrzygnięty sprzeciw.

### 8.5. Prawo do przenoszenia danych (art. 20 RODO)
Prawo do otrzymania danych w ustrukturyzowanym, powszechnie używanym formacie nadającym
się do odczytu maszynowego (CSV / JSON) oraz prawo do żądania przesłania ich bezpośrednio
innemu administratorowi (o ile jest technicznie możliwe).

### 8.6. Prawo do sprzeciwu (art. 21 RODO)
Prawo do sprzeciwu wobec przetwarzania danych na podstawie **uzasadnionego interesu
Administratora** (art. 6 ust. 1 lit. f RODO), w tym profilowania. W przypadku marketingu
bezpośredniego — sprzeciw jest zawsze skuteczny bez uzasadnienia.

### 8.7. Prawo do niepodlegania decyzjom zautomatyzowanym (art. 22 RODO)
Administrator **nie podejmuje** wobec Użytkowników decyzji wywołujących skutki prawne
lub w podobny sposób istotnie na nich wpływających, opartych wyłącznie na zautomatyzowanym
przetwarzaniu (w tym profilowaniu). Rekomendacje i analizy publikowane w Serwisie są
**informacją**, a nie decyzją wywołującą skutki prawne.

### 8.8. Prawo do wycofania zgody (art. 7 ust. 3 RODO)
Jeśli przetwarzanie odbywa się na podstawie zgody, Użytkownik może ją w każdej chwili
wycofać (bez wpływu na zgodność z prawem przetwarzania sprzed wycofania).

### 8.9. Jak wykonać swoje prawa

- **Samodzielnie w panelu Konta** — zmiana danych, wycofanie zgód marketingowych, usunięcie
  Konta.
- **Emailem** — [PLACEHOLDER: privacy@sportslab.app]. Administrator odpowiada w ciągu
  **30 dni** (art. 12 ust. 3 RODO; przedłużenie do 3 miesięcy w szczególnie skomplikowanych
  przypadkach z uzasadnieniem).
- **Listownie** — na adres siedziby Administratora.

Administrator **nie pobiera opłat** za realizację praw z art. 15–22 RODO, chyba że
żądania są ewidentnie nieuzasadnione lub nadmierne (art. 12 ust. 5 RODO) — wówczas
Administrator może pobrać rozsądną opłatę lub odmówić rozpatrzenia.

### 8.10. Prawo skargi do PUODO (art. 77 RODO)

Użytkownikowi przysługuje prawo wniesienia skargi do organu nadzorczego — **Prezesa
Urzędu Ochrony Danych Osobowych**:

- Adres: ul. Stawki 2, 00-193 Warszawa
- Strona: [uodo.gov.pl](https://www.uodo.gov.pl)
- Infolinia: 606-950-000

## 9. Cookies i technologie śledzące

Serwis wykorzystuje pliki cookies (ciasteczka) oraz zbliżone technologie (local storage,
session storage) na podstawie art. 173 ustawy Prawo telekomunikacyjne (implementacja
dyrektywy ePrivacy 2002/58/WE) oraz art. 6 RODO.

Rodzaje cookies:

- **Niezbędne (essential):** sesja logowania, CSRF, ustawienia bezpieczeństwa —
  podstawa: art. 6 ust. 1 lit. b RODO (wykonanie umowy); **nie wymagają zgody**.
- **Preferencji:** język, motyw, zapamiętane ustawienia — art. 6 ust. 1 lit. a RODO (zgoda).
- **Analityczne:** statystyki użycia (Plausible lub PostHog) — art. 6 ust. 1 lit. a RODO
  (zgoda) lub art. 6 ust. 1 lit. f (uzasadniony interes — jeżeli analityka privacy-friendly
  bez identyfikatora osobowego).
- **Marketingowe:** w fazie alpha **nie są stosowane**.

Szczegółowe zasady i lista plików cookies zostaną opisane w osobnym dokumencie **Cookie
Policy**, który będzie stanowił uzupełnienie niniejszej Polityki Prywatności.

W fazie alpha Administrator zobowiązuje się do ograniczenia cookies do niezbędnych
oraz analitycznych privacy-friendly (bez identyfikatorów osobowych).

## 10. Bezpieczeństwo danych

Administrator stosuje środki techniczne i organizacyjne zapewniające ochronę danych
osobowych adekwatną do zagrożeń (art. 32 RODO), w tym:

- **Szyfrowanie w tranzycie:** TLS 1.3 dla wszystkich połączeń,
- **Szyfrowanie w spoczynku:** szyfrowanie baz danych (PostgreSQL/Timescale) i backupów (B2 server-side encryption),
- **Hashowanie haseł:** algorytm odporny na brute-force (bcrypt / argon2id),
- **Kontrola dostępu:** principle of least privilege; logi dostępu do baz produkcyjnych,
- **Regularne backupy:** offsite na Backblaze B2 z retencją 30 dni,
- **Monitoring i alerty:** SIEM / log aggregation; powiadomienia o anomaliach,
- **Incident response:** procedura zgłoszenia naruszenia do PUODO w 72h (art. 33 RODO)
  i powiadomienia Użytkowników (art. 34 RODO), jeżeli naruszenie powoduje wysokie ryzyko.

## 11. Zmiany Polityki

1. Administrator zastrzega prawo zmiany niniejszej Polityki w szczególności w przypadku:
   - zmian w przepisach prawa,
   - zmian listy sub-processorów,
   - zmian w zakresie funkcjonalności Usługi.
2. O zmianach Administrator zawiadomi Użytkowników **z wyprzedzeniem co najmniej 14 dni**
   — poprzez email na adres przypisany do Konta oraz komunikat w panelu Użytkownika.
3. W przypadku zmian istotnych (np. nowa kategoria danych, nowy cel przetwarzania)
   Administrator uzyska od Użytkownika ponowną zgodę, jeżeli wymagają tego przepisy.

## 12. Kontakt

W sprawach dotyczących przetwarzania danych osobowych należy kontaktować się z Administratorem:

- **Email:** [PLACEHOLDER: privacy@sportslab.app]
- **Adres:** [PLACEHOLDER: adres siedziby]
- **Ogólny kontakt:** [PLACEHOLDER: kontakt@sportslab.app]

---

**Wersja:** v0.1 — alpha draft
**Data wersji:** 2026-04-19
**Historia zmian:**
- v0.1 (2026-04-19) — draft wewnętrzny, SPO-152, przed review prawnika (RODO/GDPR).

---

> **DISCLAIMER (powtórzony):** Ten dokument jest wewnętrznym draftem. **Nie jest poradą
> prawną.** Przed opublikowaniem i przed uruchomieniem paid tier wymagana weryfikacja
> przez radcę prawnego specjalizującego się w RODO/GDPR. Wszystkie `[PLACEHOLDER: ...]`
> należy uzupełnić rzeczywistymi danymi Administratora.

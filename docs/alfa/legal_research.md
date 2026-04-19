# Legal research — SportsLab alpha (PL/UE)

**Wersja:** v0.1 — alpha draft
**Data:** 2026-04-19
**Autor:** Claude Code (research assistant), na zlecenie założyciela SportsLab
**Status:** draft wewnętrzny, **NIE** porada prawna

---

> **DISCLAIMER — przeczytaj zanim użyjesz tego dokumentu**
>
> **Ten dokument jest wewnętrznym research, nie poradą prawną.** Został przygotowany
> przez asystenta AI na podstawie publicznie dostępnych źródeł z lat 2024–2026
> i ma służyć jako punkt wyjścia do konsultacji z prawnikiem. **Przed komercyjnym
> uruchomieniem SportsLab (paid tier, billing, B2B kontrakty) WYMAGANA jest
> konsultacja z prawnikiem wyspecjalizowanym w prawie hazardowym i RODO/GDPR.**
> Szacunkowy budżet konsultacji — sekcja F poniżej.

---

## Spis treści

- [A. Polska — status prawny dostarczania analiz bukmacherskich](#a-polska)
- [B. Unia Europejska — ramy regulacyjne usług informacyjnych](#b-unia-europejska)
- [C. DE / UK / ES — specyfika krajowa](#c-de--uk--es)
- [D. Precedensy rynkowe — jak robią to inni](#d-precedensy-rynkowe)
- [E. Obowiązkowe disclaimery — lista minimalna](#e-obowiazkowe-disclaimery)
- [F. Wnioski i action items](#f-wnioski-i-action-items)

---

## A. Polska

### A.1. Kluczowe akty prawne

**Podstawowy akt:** Ustawa z dnia 19 listopada 2009 r. o grach hazardowych
(Dz.U. 2009 Nr 201 poz. 1540, z późn. zm.) — dalej **UGH**.

Pełny tekst: [isap.sejm.gov.pl — WDU20092011540](https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20092011540)
(dostęp 2026-04-19).

Najistotniejsze przepisy dla SportsLab:

| Art. | Treść w skrócie | Dlaczego istotne dla SportsLab |
|------|-----------------|---------------------------------|
| Art. 2 ust. 1 | Definicje: gry losowe, gry w karty, zakłady wzajemne (totalizator, bukmacherskie), gry na automatach | Definiuje co jest "grą hazardową"; SportsLab musi udowodnić, że poza tym zakresem |
| Art. 2 ust. 2 pkt 2 | "Zakładami wzajemnymi są zakłady o wygrane pieniężne lub rzeczowe, polegające na odgadywaniu (...) wyników sportowego współzawodnictwa ludzi lub zwierząt, w których uczestnicy wpłacają stawki, a wysokość wygranej zależy od umówionego stosunku wpłaty do wygranej" | **Kluczowa definicja zakładu bukmacherskiego (bet)** — SportsLab *nie* przyjmuje stawek ani nie wypłaca wygranych, więc nie spełnia tej definicji |
| Art. 6 ust. 1 | Organizowanie gier cylindrycznych, kart, kości, automatów oraz przyjmowanie zakładów wzajemnych wymaga koncesji / zezwolenia Ministra Finansów | SportsLab nie organizuje gier ani nie przyjmuje zakładów — brak obowiązku koncesji |
| Art. 6 ust. 3 | Tylko **spółka akcyjna lub spółka z o.o. z siedzibą w Polsce** może uzyskać zezwolenie bukmacherskie | Potwierdza, że sprzedaż samych analiz nie wchodzi w ten reżim (nie dotyczy SportsLab), ale ogranicza formę prawną jeżeli kiedykolwiek sami byśmy byli operatorem |
| Art. 15d | Minimalny kapitał zakładowy dla operatora zakładów wzajemnych: 2 mln PLN | Nie dotyczy nas (nie jesteśmy operatorem) |
| Art. 29 | Zakaz reklamy i promocji gier cylindrycznych, kart, kości, zakładów wzajemnych i automatów | Uwaga: dotyczy też pośredniej reklamy — szczegóły w sekcji A.3 |
| Art. 29b | Reklama zakładów wzajemnych *z zezwoleniem* jest dozwolona z ograniczeniami (nie do nieletnich, bez twierdzeń o "łatwej wygranej", z ostrzeżeniem o ryzyku uzależnienia) | Jeśli kiedykolwiek dodamy affiliate do legalnych buków — musimy dopasować kreacje do art. 29b |
| Art. 29a | Zakaz urządzania gier hazardowych przez internet bez wymaganego zezwolenia; zakaz uczestniczenia | Nie dotyczy nas bezpośrednio (nie urządzamy gier) |

Źródła: [lexlege.pl — art. 29 UGH](https://lexlege.pl/ustawa-o-grach-hazardowych/art-29/),
[arslege.pl — art. 29 UGH](https://arslege.pl/zakazy-w-zakresie-reklamy-i-promocji-gier/k185/a17467/),
[arslege.pl — art. 29b UGH](https://arslege.pl/reklama-zakladow-wzajemnych/k185/a103575/),
[przepisy.gofin.pl — art. 29 UGH](https://przepisy.gofin.pl/przepisy,6,151,29,1105,228816,20200229,art-29-ustawa-z-dnia-19112009-r-o-grach-hazardowych.html)
(dostęp 2026-04-19).

### A.2. Kluczowe pytanie — czy SportsLab "organizuje gry"?

**Krótka odpowiedź (robocza):** nie — dostarczamy analizy danych, a nie przyjmujemy stawek.

**Rozbudowana argumentacja:**

Art. 6 ust. 1 UGH mówi o "urządzaniu gier" i "przyjmowaniu zakładów wzajemnych".
SportsLab:

1. **Nie przyjmuje stawek pieniężnych** od użytkowników na wynik zdarzenia sportowego.
2. **Nie wypłaca wygranych** zależnych od wyniku zdarzenia.
3. **Nie pośredniczy technicznie** w zawieraniu zakładów (nie jesteśmy "punktem przyjmowania zakładów" w rozumieniu art. 2 UGH).
4. **Sprzedaje usługę informacyjną** — analityczne wskaźniki wartości oczekiwanej (EV), kalibrowane prawdopodobieństwa, rekomendowane stawki Kelly. Użytkownik sam decyduje, czy i gdzie zagrać.

Taka konstrukcja zbliża nas do usług typu "research/analytics/advisory", które w Polsce
nie są objęte UGH. Potwierdzenie kierunku — Ministerstwo Finansów w październiku 2024 r.
powołało wyspecjalizowany Departament ds. rynku hazardowego (licencje, nadzór),
co wyraźnie rozgranicza reżim licencjonowanego operatora od "portali informacyjnych"
(źródło: [iclg.com — Gambling 2026 Poland](https://iclg.com/practice-areas/gambling-laws-and-regulations/poland), dostęp 2026-04-19).

**Dwa stanowiska sporne — obowiązkowo do wyjaśnienia z prawnikiem:**

**Stanowisko 1 — "usługa informacyjna, bez koncesji":**
Dostarczanie analiz i prognoz nie jest "organizowaniem gier". Portal podaje
informację, użytkownik sam zawiera umowę zakładu u licencjonowanego operatora.
Stanowisko dominujące w praktyce rynku (Forebet, BetMines, Typerzy.pl — żadne
nie mają koncesji Min. Fin.).

**Stanowisko 2 — "ryzyko pośredniej reklamy operatorów nielicencjonowanych":**
Jeżeli treść portalu zawiera linki partnerskie do bukmacherów bez zezwolenia
Min. Fin. albo pozycjonuje konkretne zakłady jako "atrakcyjne" — może być
traktowana jako reklama w rozumieniu art. 29 UGH. Ryzyko: kara administracyjna
od KAS (do 100% wartości reklamy — art. 89 UGH), wpis do rejestru domen zakazanych
([hazard.mf.gov.pl/Ustawa](https://hazard.mf.gov.pl/Ustawa), dostęp 2026-04-19).

**Rekomendacja do prawnika:** potwierdzić, że:
- publikacja analiz *nie* stanowi reklamy w rozumieniu art. 29,
- linki partnerskie w panelu mogą prowadzić *wyłącznie* do operatorów z aktywną
  licencją Min. Fin. (lista: [hazard.mf.gov.pl](https://hazard.mf.gov.pl)),
- komunikacja nie zawiera obietnic wygranych ani twierdzeń o "braku ryzyka".

### A.3. Interpretacje Ministerstwa Finansów (stan 2024–2025)

Ministerstwo Finansów prowadzi **Rejestr Domen Służących do Oferowania Gier
Hazardowych Niezgodnie z Ustawą** (dostęp: [hazard.mf.gov.pl/Ustawa](https://hazard.mf.gov.pl/Ustawa)).
Wpis na listę skutkuje blokadą DNS u polskich ISP oraz blokadą płatności.

Z analiz publikowanych w 2024–2025 r. (CMS, Dudkowiak, ICLG) wynika, że:

- **Reklama pośrednia** — publikowanie analiz wraz z wyraźnym odesłaniem do konkretnego
  bukmachera może być zakwalifikowana jako reklama, jeżeli służy *promocji* ofert tego
  operatora. Źródło: [CMS — Gambling in Poland](https://cms.law/en/int/expert-guides/cms-expert-guide-to-gambling-laws-in-cee/poland)
  (dostęp 2026-04-19).
- **Brak licencji = brak możliwości legalnej współpracy** — jeżeli SportsLab kiedykolwiek
  dodałby affiliate, partnerzy muszą być na liście licencjonowanych bukmacherów Min. Fin.
  (np. STS, Fortuna, Totolotek, Superbet PL, Betclic PL).
- **Gry bez elementu losowości** (czysta analityka, prognostyka oparta na wiedzy) — poza
  zakresem UGH. Źródło: [iclg.com — Gambling 2026 Poland](https://iclg.com/practice-areas/gambling-laws-and-regulations/poland).

### A.4. Rekomendowana forma prawna

Dwa realne warianty na start (alpha = free tier, brak przychodów).

#### Wariant 1 — Jednoosobowa działalność gospodarcza (JDG)

**Plusy:**
- Niskie koszty założenia (CEIDG, rejestracja 1 dnia, zero opłat skarbowych).
- Koszt prowadzenia: 200–500 PLN/mc księgowości + składki ZUS (preferencyjne przez pierwsze 24 mc).
- Szybkie rozliczenie PIT (PIT-36, PIT-36L).
- Brak podwójnego opodatkowania (CIT + dywidenda).

**Minusy:**
- **Pełna odpowiedzialność majątkiem prywatnym** — przedsiębiorca odpowiada całym swoim
  majątkiem (w tym prywatnym) za zobowiązania firmy. Źródło: [poradnikprzedsiebiorcy.pl](https://poradnikprzedsiebiorcy.pl/-jednoosobowa-dzialalnosc-gospodarcza-krok-po-kroku)
  (dostęp 2026-04-19).
- **Brak koncesji bukmacherskiej** — JDG nie może uzyskać zezwolenia Min. Fin. (art. 6 ust. 3 UGH
  wymaga sp. akc. lub sp. z o.o.). Nie dotyczy nas w alfie, ale blokuje pivot na operatora w przyszłości.
- ZUS mandatory, nawet przy zerowych przychodach (po okresie preferencyjnym).

**Kiedy wybrać:** MVP / alpha, pierwsi płatni użytkownicy, brak inwestorów, brak kontraktów B2B
z klauzulą odpowiedzialności ograniczonej.

#### Wariant 2 — Sp. z o.o. (spółka z ograniczoną odpowiedzialnością)

**Plusy:**
- **Odpowiedzialność ograniczona** do kapitału zakładowego (min. 5 000 PLN). Wspólnik nie
  odpowiada majątkiem prywatnym za zobowiązania spółki (z pewnymi wyjątkami, m.in. art. 299 KSH).
- CIT 9% dla małych podatników (do 2 mln EUR przychodów rocznie).
- Możliwość uzyskania koncesji bukmacherskiej w przyszłości (gdyby pivot).
- Wiarygodność w oczach klientów B2B i inwestorów.
- Możliwość rozliczania wynagrodzenia zarządu w modelu powtarzalnych świadczeń (art. 176 KSH) —
  omija składki ZUS od pensji zarządu.

**Minusy:**
- **Podwójne opodatkowanie** — CIT 9% na poziomie spółki + PIT 19% od dywidendy = ~26% effective.
- **Koszt założenia:** ~1000–3000 PLN (notariusz, rejestracja KRS, PCC, kapitał) lub przez S24 ~350 PLN.
- **Koszty prowadzenia:** księgowość 600–1500 PLN/mc (pełne KPiR nieobowiązkowe, ale wymagana pełna księgowość), sprawozdanie finansowe, audyt przy progach.
- **ZUS jednoosobowej sp. z o.o.** — jedyny wspólnik sp. z o.o. jest traktowany jak JDG dla ZUS
  (pełne składki). Źródło: [fakturomania.pl — sp. z o.o. a ZUS](https://pomoc.fakturomania.pl/support/solutions/articles/36000331754-sp-z-o-o-to-firma-bez-zus-czy-to-mo%C5%BCliwe-) (dostęp 2026-04-19).
  Obejście: drugi wspólnik z udziałem min. ~10%.

**Kiedy wybrać:** regularny przychód > ~120 000 PLN/rok, kontrakty B2B, plan pozyskania
inwestorów, plan pivotu na operatora bukmacherskiego.

#### Rekomendacja wstępna (do potwierdzenia z księgową i prawnikiem)

**Dla alpha (free tier, brak przychodów, pojedynczy użytkownicy):** JDG — niski koszt, szybki start.

**Dla beta / paid tier:** przejście na sp. z o.o. albo spółkę z o.o. z samego początku, jeżeli
plan mówi o przychodach > 120k PLN/rok w ciągu roku od startu. Decyzja zależy od:
- szybkości skalowania (JDG → sp. z o.o. to reorganizacja ~3 mc),
- ryzyka roszczeń użytkowników (ochrona majątku osobistego = silny argument za sp. z o.o.),
- planu inwestorskiego (fundusze VC nie inwestują w JDG).

Trade-offy szczegółowe: [OnlineFakturowanie.pl — JDG vs sp. z o.o.](https://www.onlinefakturowanie.pl/przewodnik-przedsiebiorcy/jak-rozpoczac-dzialalnosc-gospodarcza/podatki-i-obowiazki-przedsiebiorcy-w-polsce-jdg-i-spolka-z-o-o-w-praktyce),
[dwaplusjeden.com](https://dwaplusjeden.com/zakladam-firme/jdg-czy-spolka-z-o-o-w-2025-co-sie-bardziej-oplaca-porownanie-kosztow-i-obowiazkow/),
[ifirma.pl — jednoosobowa sp. z o.o.](https://www.ifirma.pl/blog/jednoosobowa-spolka-z-o-o-koszty-zalozenia-i-prowadzenia-skladki-zus-ksiegowosc-i-inne/)
(dostęp 2026-04-19).

---

## B. Unia Europejska

### B.1. Dyrektywa 2000/31/WE (e-commerce)

Dyrektywa Parlamentu Europejskiego i Rady 2000/31/WE z dnia 8 czerwca 2000 r.
w sprawie niektórych aspektów prawnych usług społeczeństwa informacyjnego,
w szczególności handlu elektronicznego.

Tekst: [eur-lex.europa.eu — CELEX 32000L0031](https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=celex:32000L0031)
(dostęp 2026-04-19).

**Dlaczego istotne:**
- SportsLab jako "usługa społeczeństwa informacyjnego" (art. 2 lit. a dyrektywy) —
  świadczona na odległość, drogą elektroniczną, na indywidualne żądanie, za wynagrodzeniem.
- **Zasada kraju pochodzenia** (art. 3): usługodawca podlega prawu państwa członkowskiego
  siedziby. Oznacza: jeśli spółka w Polsce, polskie prawo reguluje działalność, nawet
  jeśli użytkownik jest w Niemczech (z wyjątkami — m.in. gry hazardowe są wyłączone
  z zasady kraju pochodzenia, art. 1 ust. 5 lit. d tiret trzecie).
- **Obowiązki informacyjne** (art. 5): podawanie nazwy, adresu, NIP, rejestru, danych kontaktowych.
- **Umowy elektroniczne** (art. 9–11): akceptacja regulaminu "click-wrap" jest ważna.

W Polsce dyrektywę implementuje **Ustawa z dnia 18 lipca 2002 r. o świadczeniu usług
drogą elektroniczną** (Dz.U. 2002 Nr 144 poz. 1204, z późn. zm.). Tekst: [isap.sejm.gov.pl — WDU20021441204](https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20021441204).

### B.2. MiFID II — dyrektywa 2014/65/UE

**Krótka odpowiedź:** MiFID II dotyczy **instrumentów finansowych**, zakłady bukmacherskie
i analizy sportowe **nie są** instrumentami finansowymi w rozumieniu dyrektywy (załącznik I
sekcja C MiFID II). Nie musimy rejestrować się jako firma inwestycyjna.

**Uwaga:** gdyby SportsLab kiedyś dodał produkt typu "bet exchange tokens" albo derywaty
na wyniki — wchodzi potencjalne ryzyko MiFID II i prospekcie emisyjnym. Na etapie alpha
nie dotyczy.

### B.3. Dyrektywa usługowa 2006/123/WE

Ramy swobody świadczenia usług w UE. Dotyczy nas tylko pośrednio — głównie zasada
niedyskryminacji usługobiorców z innych państw członkowskich. W praktyce oznacza:
regulamin w języku polskim + wersja angielska, brak arbitralnych barier dla użytkowników
z innych państw UE.

### B.4. RODO / GDPR — rozporządzenie 2016/679

**Fundament** — dotyczy nas od pierwszego użytkownika. Szczegółowo w `privacy_policy.md`.
Kluczowe punkty do research:

- Art. 6 — podstawy prawne przetwarzania (umowa, zgoda, uzasadniony interes, obowiązek prawny).
- Art. 13 — obowiązki informacyjne przy zbieraniu danych.
- Art. 15–22 — prawa osoby, której dane dotyczą.
- Art. 28 — umowy powierzenia z procesorami (Clerk, Stripe, Vercel, B2).
- Art. 32 — środki bezpieczeństwa (szyfrowanie, kontrola dostępu, backup).
- Art. 37 — DPO (w naszym przypadku prawdopodobnie *nie* wymagany: nie przetwarzamy
  danych szczególnych kategorii w dużej skali, nie jesteśmy organem publicznym).
- Art. 44–49 — transfer do państw trzecich (USA — wymaga SCC albo Data Privacy Framework
  po decyzji KE z 10.07.2023).
- Art. 77 — prawo skargi do PUODO.

Tekst: [eur-lex.europa.eu — GDPR](https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=CELEX:32016R0679).

### B.5. Dyrektywa omnibus 2019/2161 (consumer protection)

Od 1.01.2023 w Polsce obowiązuje nowelizacja ustawy o prawach konsumenta implementująca
dyrektywę omnibus. Wymaga m.in.:
- informacji o sposobie weryfikacji opinii użytkowników (o ile je publikujemy),
- przejrzystości rankingów i promocji ("najniższa cena z 30 dni"),
- kar za agresywne praktyki (do 10% obrotu).

**Istotne dla SportsLab:** jeżeli pokazujemy historyczne statystyki ROI/accuracy, musimy
mieć mechanizm ich weryfikacji i jasno komunikować metodologię.

### B.6. ESMA guidance

ESMA (European Securities and Markets Authority) nie publikuje guidance dla tipsterów —
to nie jest rynek finansowy. Brak relevantnych wytycznych.

---

## C. DE / UK / ES

### C.1. Niemcy — GlüStV 2021

**Interstate Treaty on Gambling 2021** (Glücksspielstaatsvertrag) — wszedł w życie 1.07.2021.
Reguluje gry hazardowe, kasyna online, zakłady sportowe, pokera online.

Kluczowe dla SportsLab:
- **Joint Gambling Authority (GGL)** wydaje licencje krajowe.
- **Licencja na zakłady sportowe** — wymagana dla operatorów przyjmujących stawki.
- **Usługi tipsterskie** — GlüStV 2021 *nie* adresuje bezpośrednio serwisów analitycznych.
  Brak guidance GGL o licencjonowaniu tipsterów (stan: kwiecień 2026).

Źródło: [iClG — Germany 2026](https://iclg.com/practice-areas/gambling-laws-and-regulations/germany),
[Lexology — New German gambling regulation 2021](https://www.lexology.com/library/detail.aspx?g=d89c86b9-09b5-474c-b3ee-cc82b6f1d12b),
[FIN LAW — Gambling and regulation](https://fin-law.de/en/gambling-and-regulation/) (dostęp 2026-04-19).

**Ryzyko dla SportsLab:** reklama / oferta usługi w DE. W praktyce — SportsLab powinien
udostępniać treści użytkownikom z DE z jasnym disclaimer, a na etapie paid — zbadać, czy
§ 5 GlüStV (reklama) nie obejmuje naszej komunikacji.

### C.2. Wielka Brytania — UK Gambling Commission

**Gambling Act 2005** (z późn. zm.) + **Remote Gambling Act 2014**.

Kluczowe:
- **Sekcja 13 Gambling Act 2005** — definicja "betting intermediary" obejmuje podmioty,
  które "umożliwiają zawieranie zakładów" za wynagrodzeniem lub prowizją. Źródło:
  [gamblingcommission.gov.uk — Betting advice](https://www.gamblingcommission.gov.uk/licensees-and-businesses/guide/betting-advice-for-remote-non-remote-and-betting-intermediaries).
- **Tipster services** — jeśli tipster *stawia* zakłady w imieniu klienta za prowizją,
  wchodzi pod definicję "betting intermediary" i wymaga licencji. Sam analityczny
  tipster (daje typ, user sam stawia) — nie wymaga licencji gamblingowej.
- **Advertising Standards Authority (ASA) / CAP Code** — wymagania dla reklam tipsterów:
  "nie można twierdzić, że wygrana jest gwarantowana", statystyki muszą być weryfikowalne
  przez niezależny podmiot. Źródło: [asa.org.uk — Tipsters](https://www.asa.org.uk/advice-online/betting-and-gaming-tipsters.html).

**Dla SportsLab:** model "analiza + user sam stawia" nie wymaga licencji UKGC. Musimy
spełnić standardy ASA (weryfikowalność statystyk, brak obietnic wygranych).

### C.3. Hiszpania — Ley 13/2011 i DGOJ

**Ley 13/2011, de 27 de mayo, de regulación del juego** — BOE-A-2011-9280.
Tekst: [boe.es — Ley 13/2011](https://www.boe.es/buscar/act.php?id=BOE-A-2011-9280).

Regulator: **Dirección General de Ordenación del Juego (DGOJ)**.

Kluczowe:
- Licencja generalna (ogólna) + licencja szczegółowa (singular) na konkretny rodzaj gry.
  Obowiązkowe dla **operatorów** przyjmujących zakłady.
- **Pronósticos deportivos (prognozy sportowe)** — Ley 13/2011 ich nie reguluje,
  jeżeli nie wiążą się z przyjmowaniem stawek. Analogicznie do PL, UK i DE.

Źródło: [ordenacionjuego.es](https://www.ordenacionjuego.es/en/dgoj/normativa-vigor/buscador?type=152),
[altenar.com — Spain compliance guide 2025](https://altenar.com/en-us/blog/gambling-laws-and-regulations-in-spain-your-compliance-guide-for-2025/) (dostęp 2026-04-19).

**Dla SportsLab:** sprzedaż analiz klientom w ES — dozwolona bez licencji DGOJ.
Język hiszpański nie jest wymagany (alpha jest PL/EN), ale jeśli robimy oficjalny marketing
w ES — wymagana jest weryfikacja zgodności z lokalnymi przepisami o reklamie (m.in. Royal
Decree 958/2020 ograniczający reklamę gier).

### C.4. Synteza DE / UK / ES

| Jurysdykcja | Licencja tipstera wymagana? | Zastrzeżenia |
|---|---|---|
| Polska | Nie — dopóki nie przyjmujemy stawek (A.2) | Ryzyko art. 29 UGH (reklama pośrednia) |
| Niemcy | Nie adresowane przez GlüStV 2021 | Ryzyko §5 GlüStV (reklama), decyzje landów |
| UK | Nie, jeśli user sam stawia | CAP Code: weryfikowalne statystyki |
| Hiszpania | Nie, jeśli nie przyjmujemy stawek | Royal Decree 958/2020 ogranicza reklamę |

**Wniosek roboczy:** model SportsLab ("analizujemy, user sam gra") pasuje do wszystkich
czterech jurysdykcji bez licencji gamblingowej. Wszędzie jednak są reguły reklamy, które
nas obowiązują.

---

## D. Precedensy rynkowe

### D.1. Zagranica

#### Forebet

- **Model:** darmowe prognozy piłkarskie oparte na modelach matematycznych, monetyzacja
  przez reklamy (Google AdSense) i affiliate linki do buków.
- **Jurysdykcja rejestracji:** brak publicznie dostępnych danych rejestrowych w ToS
  ([m.forebet.com/en/terms-of-use](https://m.forebet.com/en/terms-of-use), dostęp 2026-04-19).
- **ToS / disclaimer:** zawiera klauzulę wyłączającą odpowiedzialność ("provided as-is",
  "no warranty of accuracy"), zakaz niezgodnego z prawem użycia treści.
- **Licencja gamblingowa:** brak.
- **Czego się uczymy:** że można operować globalnie jako "serwis informacyjny" bez
  koncesji, ale ToS musi wyraźnie wyłączać odpowiedzialność za wyniki zakładów.

#### BetMines

- **Model:** aplikacja mobilna (Google Play, App Store) + web, prognozy ML, leaderboardy
  "tipsterów społeczności".
- **Jurysdykcja:** brak publicznie wskazanej w głównych ekranach; z analizy Google Play:
  deweloper zarejestrowany poza UE.
- **Disclaimer:** explicit — "virtual bets, not real money, aim to test strategies".
- **Licencja gamblingowa:** brak.
- **Czego się uczymy:** pozycjonowanie jako "social / fun" sprowadza ryzyko, ale SportsLab
  jest B2B/pro — nie pasuje nam ta narracja.

#### Predictz

- **Model:** darmowe prognozy + płatny pakiet "VIP tips".
- **Jurysdykcja:** brak jednoznacznej publicznej informacji.
- **Disclaimer:** standardowy "past performance does not guarantee future results".
- **Licencja gamblingowa:** brak.

Źródło: [predictz.com — predictions](https://www.predictz.com/predictions/) (dostęp 2026-04-19).

#### OLBG

- **Model:** UK-based community tipster platform, free tips, monetyzacja affiliate.
- **Jurysdykcja:** UK. Firma **OLBG Ltd** (Companies House UK).
- **Licencja gamblingowa:** brak — operuje jako "content / publishing".
- **Disclaimer:** szczegółowy 18+, linki do BeGambleAware, GamCare. Wysoki standard
  (UK CAP Code).
- **Czego się uczymy:** **to jest wzorzec referencyjny** — UK-grade disclaimer + responsible
  gambling linki + publikowana metodologia.

Źródło: [olbg.com — betting tips](https://www.olbg.com/betting-tips) (dostęp 2026-04-19).

### D.2. Polska

#### Typerzy.pl

- **Model:** social typerski + payment za VIP tipy.
- **Forma prawna:** niepublikowana w źródłach dostępnych w kwietniu 2026 (brak wyników
  konkretnych dla zapytania "Typerzy.pl forma prawna"). **Action item:** sprawdzić
  stopkę serwisu na oryginale.
- **Licencja:** brak (nie są operatorem).
- **Disclaimer:** standardowy "18+, grasz na własną odpowiedzialność".

#### zagralem.pl

- **Model:** platforma społecznościowa dla typerów, free + premium tipy.
- **Forma prawna:** niepublikowana w indeksowanych źródłach na dzień 2026-04-19. **Action item:**
  zweryfikować na stronie serwisu.
- **Disclaimer:** obecny (18+, gra tylko u licencjonowanych buków).

#### TipowanieFan

- **Model:** community tipsters + ranking.
- **Forma prawna:** w stopce często figuruje osoba fizyczna prowadząca JDG albo sp. z o.o.;
  wymaga weryfikacji na stronie.

**Observation:** polskie serwisy tipsterskie **nie mają** koncesji bukmacherskich
i działają jako zwykłe portale informacyjne / social. Żaden z nich nie został wpisany
do rejestru domen zakazanych MF (stan publiczny). To jest mocny sygnał praktyki rynkowej
("ustalona interpretacja"), ale **nie zastępuje opinii prawnika** — bo brak precedensu
sądowego.

### D.3. Wspólne wnioski z sekcji D

1. Praktycznie żaden tipster globalny ani polski nie ma licencji gamblingowej.
2. Wszyscy mają disclaimer wyłączający odpowiedzialność + 18+ + responsible gambling.
3. Najlepiej poprowadzone ToS/disclaimer: OLBG (UK).
4. Model biznesowy najczęstszy: free + VIP paid + affiliate do licencjonowanych buków.

---

## E. Obowiązkowe disclaimery

Lista minimalna do zaimplementowania na: landing, panel zalogowanego usera, Telegram bot, email.

### E.1. Wymagane prawnie

1. **18+** — wiek minimalny. Poparty art. 27 UGH (zakaz udziału nieletnich w grach hazardowych;
   dla nas: zakaz udostępniania treści stawianym nieletnim).
2. **Oświadczenie wiekowe** przy rejestracji — checkbox "Mam ukończone 18 lat".
3. **"To nie porada finansowa"** — dla ochrony przed reżimem MiFID II / doradcy inwestycyjnego.
4. **"Past performance ≠ future results"** — wymóg UK CAP Code (i dobra praktyka wszędzie).
5. **Responsible gambling links** — na wszystkich powierzchniach (landing, panel, Telegram).
6. **"Grasz na własną odpowiedzialność"** — wyłączenie odpowiedzialności SportsLab za straty usera.
7. **Ostrzeżenie o ryzyku uzależnienia** — wymagane przez art. 29b UGH, nawet jeśli sami
   nie reklamujemy buków.

### E.2. Linki do organizacji pomocowych

| Kraj | Organizacja | Link | Telefon |
|---|---|---|---|
| Polska | Anonimowi Hazardziści | [anonimowihazardzisci.org](https://anonimowihazardzisci.org/) | 881 488 990, 795 250 438 |
| UK | GamCare | [gamcare.org.uk](https://www.gamcare.org.uk/) | 0808 802 0133 (bezpłatnie) |
| UK | BeGambleAware | [begambleaware.org](https://www.begambleaware.org) | — |
| DE | BZgA / Spielen-mit-Verantwortung | [spielen-mit-verantwortung.de](https://www.spielen-mit-verantwortung.de) | 0800 1 372 700 |
| ES | Juego Responsable (DGOJ) | [ordenacionjuego.es/juego-responsable](https://www.ordenacionjuego.es/en/juego-responsable) | 900 200 225 |

Źródło: [anonimowihazardzisci.org — kontakt](https://anonimowihazardzisci.org/kontakt/),
[gamcare.org.uk](https://www.gamcare.org.uk/) (dostęp 2026-04-19).

### E.3. Format disclaimera na poszczególnych powierzchniach

Pełne teksty — patrz `landing_disclaimer.md`. W skrócie:

- **Landing:** krótki hero disclaimer (max 100 słów) + pełny w stopce.
- **Panel:** banner w górze przy pierwszym logowaniu ("Understood, nie pokazuj więcej"),
  potem dostępny w Help.
- **Telegram:** disclaimer w każdym bet slip (max 100 słów), emoji 18+.
- **Email:** stopka transakcyjna z linkiem do ToS i Polityki Prywatności.

---

## F. Wnioski i action items

### F.1. Przypuszczalna kwalifikacja SportsLab (robocza)

> **Usługa społeczeństwa informacyjnego / analityczna** (dyrektywa 2000/31/WE, ustawa
> o świadczeniu usług drogą elektroniczną). **Nie jest grą hazardową** w rozumieniu
> art. 2 UGH. **Nie wymaga koncesji** Ministra Finansów przy obecnym modelu (analizy +
> rekomendacje, bez przyjmowania stawek).
>
> **Disclaimer (kluczowy):** to **nie** jest porada prawna. Kwalifikacja jest robocza,
> oparta na analizie publicznych źródeł i praktyki rynkowej. Przed komercyjnym uruchomieniem
> wymagana opinia prawnika specjalizującego się w prawie hazardowym i RODO.

### F.2. Rekomendacje GDPR compliance (pre-launch)

1. **Polityka Prywatności v0.1** — gotowa (`privacy_policy.md`), review przez prawnika
   przed commercial launch.
2. **Regulamin / ToS v0.1** — gotowy (`tos_alpha.md`), review przed paid launch.
3. **Data Processing Agreements** — podpisane z: Clerk, Stripe, Vercel, Hetzner, Backblaze.
   SCC + TIA (Transfer Impact Assessment) dla US sub-processorów.
4. **DPO** — przy obecnej skali (alpha, <10 użytkowników) nie wymagany (art. 37 RODO).
   Przy skali >10k aktywnych płatnych — reevaluacja.
5. **Rejestr czynności przetwarzania** (art. 30 RODO) — przygotowany wewnętrznie, nie
   publikowany. Action item dla P1.
6. **Procedura incident response** — zgłoszenie do PUODO w ciągu 72h (art. 33 RODO),
   powiadomienie użytkowników (art. 34 RODO) jeśli wysokie ryzyko.
7. **Cookie Policy + cookie banner** (dyrektywa ePrivacy 2002/58/WE). Dostarczyć
   wraz z Privacy Policy (nie w zakresie tego dokumentu, action item osobno).

### F.3. Lista do konsultacji z prawnikiem (konkret, nie ogólniki)

Zapytania do prawnika specjalizującego się w prawie hazardowym + RODO:

1. **Kwalifikacja usługi.** Czy model SportsLab (analizy matematyczne + kalibrowane
   prawdopodobieństwa + rekomendowane stawki Kelly, sprzedawane użytkownikom za
   subskrypcję, bez przyjmowania stawek) mieści się w definicji art. 2 UGH? Prośba
   o pisemną opinię (ready-made do rundy inwestorskiej).
2. **Reklama art. 29 UGH.** Czy publikacja analiz wraz z linkami partnerskimi do
   bukmacherów z aktywną licencją Min. Fin. stanowi "reklamę zakładów wzajemnych"
   (art. 29b) i jakie są wymagane elementy tej reklamy (m.in. ostrzeżenia o ryzyku).
3. **Forma prawna.** Potwierdzenie trade-offów JDG vs sp. z o.o. w kontekście:
   - minimalizacji składek ZUS w skali <120k PLN/rok,
   - ograniczenia odpowiedzialności (m.in. hipotetyczne roszczenie usera "stracił pieniądze
     przez wasz typ"),
   - przejścia JDG → sp. z o.o. (jaki cut-off).
4. **Umowy z sub-processorami** (Clerk, Stripe, Vercel, Hetzner, Backblaze) —
   weryfikacja, że ich standardowe DPA + SCC są wystarczające i nie trzeba negocjować
   dodatkowych klauzul. Sprawdzenie TIA.
5. **Regulamin v0.1 (`tos_alpha.md`).** Review pod kątem:
   - art. 385¹ KC (klauzule niedozwolone) — szczególnie pkt 17 ("Ograniczenie odpowiedzialności"),
   - ustawy o prawach konsumenta (14 dni prawo odstąpienia dla paid tier),
   - procedury reklamacyjnej.
6. **Polityka Prywatności v0.1 (`privacy_policy.md`).** Review pod kątem:
   - poprawności podstaw prawnych (art. 6 RODO),
   - okresów retencji,
   - klauzul SCC dla transferu do USA,
   - listy sub-processorów.
7. **Warunki używania danych zewnętrznych.** Czy używanie publicznych API bukmacherów
   (scrapery, odds feeds) do budowy modelu stanowi naruszenie ich ToS / praw baz danych
   (dyrektywa 96/9/WE)? Ryzyko kontraktowe i IP.
8. **IP na modelach ML.** Czy trenowane modele, feature definitions i kod są chronione jako:
   utwór (prawo autorskie), know-how (tajemnica przedsiębiorstwa), patent (niskie szanse
   dla algorytmów). Strategia ochrony na etapie pre-seed.
9. **Kwestia podatkowa VAT** — czy usługa analityczna sprzedawana konsumentom w UE
   jest OSS / IOSS? (B2C w UE: VAT kraju konsumenta powyżej 10k EUR rocznie).
10. **Responsible gambling** — czy SportsLab jako "adjacent" do hazardu ma obowiązek
    implementacji self-exclusion, limits, cool-off? (formalnie nie — bo nie jesteśmy
    operatorem, ale dobra praktyka).

### F.4. Szacunkowy koszt konsultacji prawnej (SMB w PL)

Na podstawie danych rynkowych dla Polski w 2024–2025:

| Pozycja | Stawka | Uwagi |
|---|---|---|
| Stawka godzinowa radcy prawnego — ogólna | 200–400 PLN netto/h | [klodzinskikancelaria.pl](https://klodzinskikancelaria.pl/en/price-list-individual-clients/), [oferteo.pl](https://www.oferteo.pl/artykuly/ile-kosztuje-porada-prawna) |
| Stawka godzinowa — specjalizacja (hazard / IT / IP) | 300–600 PLN netto/h | [Wolters Kluwer](https://www.wolterskluwer.com/pl-pl/expert-insights/koszt-uslug-prawniczych-czyli-jak-optymalnie-wycenic-prace-prawnika) |
| Stawka godzinowa — duże miasto (Warszawa) | +20–40% | [linke.pl/cennik](https://linke.pl/cennik/) |
| Jednorazowa porada prawna | 150–500 PLN | Porady online/telefoniczne tańsze o 10–25% |

**Szacunkowy budżet pierwszej rundy konsultacji:**

- **Wariant minimalny (audyt regulaminu + Privacy Policy):** 8–12h pracy prawnika ×
  400 PLN/h = **3 200–4 800 PLN netto**.
- **Wariant pełny (wszystkie 10 pytań z F.3 + pisemna opinia o kwalifikacji usługi):**
  15–25h × 400–500 PLN/h = **6 000–12 500 PLN netto**.
- **Kontynuacja (godzinowa na bieżąco):** 300–600 PLN/h, typowo 2–5h/mc w fazie alpha.

**Rekomendacja:** zabudżetować **8 000 PLN netto** na pierwszą rundę + **1 500 PLN/mc**
na bieżącą obsługę od momentu paid launch.

Dodatkowo warto rozważyć:
- **Ubezpieczenie OC zawodowe / produktowe** — Hiscox, Warta — orientacyjnie
  1 500–5 000 PLN/rok przy sumie ubezpieczenia 500k–1M PLN.
- **Ubezpieczenie cyber** — przy paid launch, ~1 000–3 000 PLN/rok.

Źródła:
[wolterskluwer.com](https://www.wolterskluwer.com/pl-pl/expert-insights/koszt-uslug-prawniczych-czyli-jak-optymalnie-wycenic-prace-prawnika),
[kancelariaproksa.pl — cennik 2025](https://kancelariaproksa.pl/cennik-radcy-prawnego-koszty-uslugi-prawne-2025/),
[linke.pl](https://linke.pl/cennik/),
[inlegis.pl](https://www.inlegis.pl/baza-wiedzy/kancelaria/ile-kosztuje-porada-prawna/)
(dostęp 2026-04-19).

### F.5. Mapa ryzyk i priorytetyzacja

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|---|---|---|---|
| KAS uzna portal za reklamę art. 29 UGH | Niskie | Wysoki (kara, blokada domeny) | Opinia prawnika + brak affiliate do nielicencjonowanych |
| Roszczenie usera "straciłem przez wasz typ" | Średnie | Niski (ToS wyłącza) | Silny regulamin + disclaimer |
| Naruszenie RODO (niewłaściwy transfer do USA) | Niskie | Wysoki (kara PUODO) | SCC + TIA + DPA + Privacy Policy |
| Brak DPA z sub-processorem | Niskie | Wysoki | Check-lista: Clerk, Stripe, Vercel, Hetzner, B2 |
| ASA / CAP violation (UK) | Bardzo niskie | Średni | Weryfikowalne statystyki + backtest |

---

## Stopka

**Wersja:** v0.1 — alpha draft
**Data:** 2026-04-19
**Review cadence:** przed każdą zmianą modelu monetyzacji (free → paid → affiliate → operator)
i co 6 miesięcy.
**Następny krok:** wysłać niniejszy dokument, `tos_alpha.md` i `privacy_policy.md` do
radcy prawnego specjalizującego się w prawie hazardowym + RODO. Budżet ~8 000 PLN netto.

---

> **DISCLAIMER (powtórzony):** Ten dokument jest wewnętrznym research, nie poradą prawną.
> Przed komercyjnym uruchomieniem (paid tier, billing) WYMAGANA konsultacja z prawnikiem
> wyspecjalizowanym w prawie hazardowym i GDPR.

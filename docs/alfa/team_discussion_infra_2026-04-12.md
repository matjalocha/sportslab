# Dyskusja zespolowa: Kluczowe decyzje infrastrukturalne

- **Data**: 2026-04-12
- **Moderator**: System Architect
- **Perspektywy**: Lead, Architect, SWE, MLEng, DataEng, Designer
- **Status**: Do decyzji foundera

---

## Stan obecny (fakty)

Przed analiza -- twarde dane o repo i systemie:

- **Pliki zrodlowe (.py)**: ~95 plikow w `packages/ml-in-sports/src/`
- **Pliki testowe (.py)**: ~75 plikow w `packages/ml-in-sports/tests/`
- **Testy**: 1349 (wedlug alpha_launch_plan.md)
- **Features ML**: 935 kolumn, 95k meczow, 14 lig
- **Pozostale pliki w repo**: ~30 dokumentow (`ideas/`, `docs/`), 8 plikow infra, 6 eksperymentow YAML, 10+ agentow Claude Code
- **Laczna wielkosc kodu**: ~170 plikow Pythona + ~50 dokumentow Markdown + konfigi = ~250 plikow sledzonych w git
- **Dane (poza gitem)**: `data/`, `reports/`, `predictions/`, `.venv/` -- kilka GB
- **Istniejace ADR**: 17 (ADR-0001 do ADR-0017)
- **Maszyny dostepne**: Dev PC (Windows, potezny), Laptop (always-on capable), Raspberry Pi 4 (4GB), darmowe VM (potezne, zdalne)
- **ADR-0017**: Zaakceptowana architektura dual-machine (Pi + Dev PC) -- to jest baseline do rozszerzenia

---

## Q1: Monorepo -- zostawic czy podzielic?

### Analiza ilosciowa

| Metryka | Wartosc | Granica problemowa |
|---------|---------|-------------------|
| Pliki w git (bez .git/) | ~300 | Problematyczne od ~5000+ |
| Czas `git status` | <1s | Problematyczne od >5s |
| Czas CI (pytest) | ~2-4 min (szacunek) | Problematyczne od >15 min |
| Zespol | 1 osoba + Claude Code | Problematyczne od 5+ niezaleznych teamow |
| Jezyki | Python (jedyny runtime) | Problematyczne gdy 3+ runtimey |
| Deployable units | 1 (ml-in-sports na Pi) | Problematyczne gdy 5+ z roznymi cyklami |

### Argumenty ZA utrzymaniem monorepo

1. **Jeden kontrybutor** -- solo founder nie potrzebuje izolacji miedzy zespolami. Monorepo nie generuje "contributor friction" bo nie ma contributor*ow*.
2. **Jeden jezyk runtime** -- caly produkcyjny kod to Python. Brak konfliktu TypeScript/Python w CI (frontend to Framer/Lovable, nie w repo).
3. **Jeden deployable** -- na Pi jedzie `ml-in-sports`. Landing to Lovable. Panel (jesli powstanie) to osobny serwis. Nie ma potrzeby niezaleznych release cycles.
4. **Cross-cutting zmiany** -- feature w `features/` wymaga testu w `tests/`, aktualizacji CLI w `cli/`, eksperymentu w `experiments/`. Jeden PR, jeden commit.
5. **Prosta konfiguracja** -- jeden `pyproject.toml`, jedno `uv sync`, jedno `pytest`. Zero wersjonowania miedzy repo.
6. **Wielkosc jest mala** -- 300 plikow to MALY repo. Linux kernel to 70,000+ plikow. Chromium to 300,000+. Google trzyma miliardy linii w jednym monorepo.

### Argumenty ZA podzielem

1. **Czystosc koncepcyjna** -- `sportslab-ml` (Python package), `sportslab-web` (jesli Next.js dashboard), `sportslab-infra` (Terraform/Docker) to czyste granice.
2. **CI izolacja** -- zmiana w `docs/` nie odpala testow Pythona. (Ale: path filtering w GitHub Actions rozwiazuje to za 5 minut).
3. **Gotowanie zaby** -- jesli nie podzielimy teraz, "kiedys bedzie za pozno." (Ale: "kiedys" to 3-5 lat. Teraz jest za wczesnie.)

### Argumenty PRZECIW podzialom

1. **Overhead koordynacji** -- 2+ repo = 2+ `pyproject.toml`, 2+ CI configs, wersjonowanie miedzy repo (jaki `ml-in-sports` v1.3 wspiera jaki `sportslab-api` v2.1?).
2. **Cross-repo changes** -- nowa feature wymaga PR w repo ML + PR w repo API + PR w repo infra. Dla solo foundera to 3x wiecej pracy na pusta formalnosc.
3. **Claude Code context** -- subagenci czytaja jedno repo. Polyrepo wymaga przelaczania kontekstu miedzy repo w kazdej sesji.
4. **Koszt podzialu pozniej jest niski** -- `git filter-branch` lub `git subtree split` wyciaga `packages/ml-in-sports/` do osobnego repo w 30 minut. To nie jest nieodwracalna decyzja.

### Kiedy monorepo staje sie problemem?

| Symptom | Kiedy to realistyczne dla SportsLab |
|---------|-------------------------------------|
| CI trwa >15 min | R5+, gdy bedzie 10 lig + 3 sporty (test suite rosnie) |
| Contributor friction (merge conflicts) | Gdy zatrudnisz 3+ deweloperow na roznych czesciach |
| Deployment coupling (zmiana w docs deployuje API) | Nigdy, jesli masz path filtering w CI |
| Repo clone >5 min | Nigdy -- kod jest maly, dane sa poza gitem |

### Rekomendacja (Architect)

**[PEWNE] Zostajemy z monorepo.** Zero argumentow za podzielem ktory oplacalby sie teraz. Podzial generuje overhead bez benefitu. Rewizja w R5+ gdy zespol urasta do 3+ osob lub CI przekracza 15 minut.

Jedyna zmiana: jesli powstanie panel (Q2), zrobi sie w osobnym repo (Lovable/Supabase) LUB jako `apps/panel/` w monorepo. Decyzja o tym nie blokuje niczego teraz.

---

## Q2: Panel uzytkownika zamiast (lub obok) Telegramu

### Czego dotyczy decyzja

Founder sugeruje: "kazdy mialby panel do ktorego sie loguje i tam dostaje bety, a przez Telegram tylko marketing."

### Argumenty ZA panelem (Lead + Designer)

1. **Profesjonalizm** -- panel z logowaniem wyglada jak produkt, nie jak kanale Telegram. Dla B2B wazne.
2. **Retencja** -- uzytkownik loguje sie codziennie, widzi historie, equity curve, ustawienia. To buduje nawyk.
3. **Analytics** -- wiesz kto sie logujesz, jak czesto, co klika. Na Telegramie masz zero danych.
4. **Upsell** -- panel jest fundamentem dla platnego API (R6). Telegram nie skaluje sie do platnego produktu.
5. **Personalizacja** -- kazdy uzytkownik moze miec inne ligi, inne limity, inny bankroll.
6. **Track record** -- public track record page na panelu jest bardziej wiarygodna niz screenshoty z Telegramu.

### Argumenty PRZECIW panelowi teraz (Architect + SWE)

1. **Czas** -- minimum 2-3 tygodnie roboczy na panel (auth + API + frontend + deploy). Przy 4 tygodniach do alphy, to 50-75% budgetu czasu.
2. **Kompleksnosc** -- panel wymaga: Clerk/Supabase Auth (auth), FastAPI backend (API), Next.js/Lovable (frontend), Postgres user tables, hosting. Kazdy z tych elementow to nowa surface area do utrzymania.
3. **Alpha to nie produkt** -- alpha to 25-50 osob, free, celem jest walidacja modelu live. Panel nie zmienia jakosci prognoz.
4. **Telegram juz dziala** -- zero kodu, zero infra, zero kosztow. Kod jest gotowy i przetestowany (ADR-0016).
5. **Przedwczesna optymalizacja UX** -- nie wiemy jeszcze co uzytkownicy chca widziec w panelu. Lepiej dostac feedback z alphy na Telegramie, potem zbudowac panel oparty o realne potrzeby.

### Scenariusze implementacji

| Podejscie | Czas | Koszt/mies. | Zlozonosc | Kiedy |
|-----------|------|-------------|-----------|-------|
| **A: Telegram only (alpha)** | 0 dni | 0 PLN | Gotowe | Teraz |
| **B: Lovable panel (Supabase auth)** | 5-7 dni | ~50-100 PLN (Supabase Pro) | Srednia | Po alpie, R6 |
| **C: Next.js + Clerk + FastAPI** | 15-20 dni | ~100-200 PLN (Clerk + hosting) | Wysoka | R6 |
| **D: Streamlit (internal only)** | 1-2 dni | 0 PLN | Niska | Wewnetrzne narzedzie teraz |

### Rekomendacja (Architect)

**[PEWNE] Alpha = Telegram (0 dodatkowego kodu).**
**[HIPOTEZA] Post-alpha (R6) = Lovable/Next.js panel.** Kolejnosc:

1. **Tydzien 1-4 (alpha)**: Telegram only. Skupienie na jakosci prognoz.
2. **Po alpie**: zbierz feedback -- czego uzytkownikom brakowalo? Jakie dane chcieli zobaczyc?
3. **R6 krok 2**: zbuduj panel oparty o feedback. Lovable (wariant B) jesli chcesz szybko. Next.js (wariant C) jesli potrzebujesz customizacji.
4. **Telegram zostaje**: kanale marketingowe + push notifications linkujace do panelu.

Streamlit (wariant D) mozna zbudowac w 1-2 dni jako wewnetrzne narzedzie do monitorowania pipeline'u. Nie jest to priorytet, ale jesli founder chce wizualne dashboard dla siebie (zamiast czytania logow), to tani koszt.

---

## Q3: Laptop jako always-on server

### Porownanie: Laptop vs Pi vs VPS

| Parametr | Laptop | Raspberry Pi 4 | VPS (Hetzner CX32) |
|----------|--------|-----------------|---------------------|
| **RAM** | 8-16 GB | 4 GB | 8 GB |
| **CPU** | x86_64, 4-8 core | ARM, 4 core (1.5 GHz) | x86_64, 4 vCPU |
| **Dysk** | SSD 256-1TB | microSD/USB SSD | 80 GB NVMe |
| **Pobor mocy** | 30-60W (plugged) | 5-10W | 0W local |
| **Koszt/mies.** | ~15-40 PLN pradu | ~3-7 PLN pradu | ~90-100 PLN |
| **Uptime** | Sredni (aktualizacje Win, sleep) | Bardzo wysoki (Linux, headless) | Bardzo wysoki (datacenter SLA) |
| **Publiczny IP** | Nie (NAT, CGNAT) | Nie (NAT) | Tak |
| **Halasy** | Wentylator | Brak | N/A |
| **Zuzycie baterii** | Degradacja po roku 24/7 | N/A | N/A |
| **Awaria zasilania** | UPS bateria (1-2h) | Wymaga UPS | Datacenter UPS+generator |

### Glowne ryzyka laptopa jako serwera

1. **Windows Update** -- wymuszony restart co 1-4 tygodnie. Pipeline pomija dzien. **[RYZYKO]** Mozna opoznic ale nie wyeliminowac (chyba ze Linux).
2. **Sleep/Hibernate** -- laptop domyslnie usypia po zamknieciu klapy. Konfigurowalny, ale wymaga uwagi.
3. **Degradacja baterii** -- 24/7 na 100% ladowania degraduje Li-ion do ~60% pojemnosci w rok. Mozna ustawic limit ladowania na 60% (jesli BIOS wspiera).
4. **Wentylator** -- pod ciaglym obciazeniem (Postgres, Python) wentylator pracuje. Moze przeszkadzac w pokoju.
5. **Cieplo** -- laptop nie jest zaprojektowany na 24/7 obciazenie. Thermal throttling mozliwy.

### Zalety laptopa nad Pi

1. **RAM** -- 8-16 GB vs 4 GB. Postgres + backend + Python inference komfortowo sie miesci.
2. **CPU** -- x86_64, szybszy niz ARM. Training jest feasible (w przeciwienstwie do Pi).
3. **SSD** -- wieksza i szybsza niz USB SSD na Pi.
4. **Ekran** -- debugging bez SSH.
5. **Backup jesli Pi padnie** -- mozna przeniesc pipeline na laptopa w 30 minut.

### Rekomendacja (Architect + SWE)

**[HIPOTEZA] Laptop jako DODATKOWA maszyna obok Pi, nie zamiast.**

Konkretnie:
- **Pi** pozostaje primary production server (cron, inference, Telegram, Postgres) -- zgodnie z ADR-0017. Jest cichy, tani, stabilny.
- **Laptop** wchodzi jako maszyna do:
  - Uruchamiania scraperow wymagajacych headless Chrome (Sofascore) -- obecnie rola Dev PC
  - Backupu: jesli Pi padnie, pipeline idzie na laptopa
  - Hostowania uslugi jesli Pi nie wyrabia (np. panel Streamlit)
  - Noclegi: laptop moze robic nocny heavy-lifting (retraining z cron, jesli Dev PC jest wylaczony)

**Nie rekomenduje** uruchamiania Postgres production na laptopie. Powody:
1. Windows Update restartuje baze w srodku nocy
2. Laptop moze zostac zabrany ze sobq
3. Pi jest stabilniejszy jako headless Linux server

---

## Q4: Darmowe potezne VM do retreningu

### Co powinno dzialac na VM

| Komponent | Wymagania | VM nadaje sie? |
|-----------|-----------|---------------|
| Trening modeli (LightGBM/XGBoost) | 4+ GB RAM, szybki CPU | Tak -- idealny use case |
| Trening TabPFN | 8+ GB RAM, GPU korzystny | Tak |
| MLflow server + UI | 512 MB RAM, dysk | Tak, ALE: dostep do UI wymaga SSH tunnel |
| Eksperymenty backtestowe | 4+ GB RAM, szybki CPU | Tak |
| Eksperymenty feature engineering | 4+ GB RAM, pandas | Tak |
| Postgres production | 1+ GB RAM, always-on | **Nie** -- jesli VM moze zniknac |
| Daily pipeline | always-on, cron | **Nie** -- jesli VM moze zniknac |

### Kluczowe pytania o VM [DO SPRAWDZENIA]

1. **Persistencja** -- Czy VM jest gwarantowane 24/7/365? Czy moze zostac usuniete/zrestartowane bez ostrzezenia?
2. **Siec** -- Czy VM ma publiczny IP? Czy Pi/laptop moga sie do niego dolaczyc? (SSH, VPN, Tailscale?)
3. **Pojemnosc dysku** -- Ile GB? Czy dane persistuja miedzy restartami?
4. **Koszt po okresie darmowym** -- Czy VM stanie sie platna? Kiedy?
5. **Polityka uzywania** -- Czy komercyjne uzycie jest dozwolone?

### Rekomendacja pod warunkiem odpowiedzi na [DO SPRAWDZENIA]

**Jesli VM jest persistent i dostepny z LAN (SSH/Tailscale):**

1. **MLflow server** przenosisz na VM (zamiast Dev PC). UI dostepny via SSH tunnel lub Tailscale.
   - Zysk: MLflow dziala nawet gdy Dev PC jest wylaczony. Historia eksperymentow jest bezpieczna na VM.
2. **Trening modeli** na VM (zamiast Dev PC).
   - Zysk: Dev PC sluzy wylacznie do development w Claude Code. VM do heavy compute.
3. **Model sync**: VM trenuje -> SCP do Pi (`/app/models/production/model.pkl`).

**Jesli VM jest ephemeryczne (moze zniknac):**

1. VM sluzy WYLACZNIE do treningu (compute on demand).
2. MLflow zostaje na Dev PC (lub laptopie).
3. Po treningu: model + metryki kopiowane na Dev PC/Pi. VM moze zniknac.

**[RYZYKO]** Jesli VM jest darmowe "bo uczelnia/praca" -- uwaga na zmiane warunkow. Nie buduj krytycznej infrastruktury na darmowym zasobie bez gwarancji SLA.

---

## Q5: Optymalne przypisanie maszyn

### Proponowana architektura (4 maszyny)

Bazujac na analizie Q1-Q4, oto rekomendowane przypisanie:

```
+========================+     +========================+
|     DEV PC (Windows)   |     |    DARMOWE VM (Linux)  |
| ~~~~~~~~~~~~~~~~~~~~~~ |     | ~~~~~~~~~~~~~~~~~~~~~~ |
| - Claude Code / IDE    |     | - Trening modeli       |
| - Rozwoj kodu          |     | - MLflow server + UI   |
| - Testy lokalne        |     | - Eksperymenty (YAML)  |
| - Sofascore scraping   |     | - TabPFN (jesli GPU)   |
| - git push/pull        |     | - Heavy compute        |
| - Dostep do MLflow UI  |     |                        |
|   (via SSH tunnel/     |     | Dostep: SSH + Tailscale|
|    Tailscale do VM)    |     | Backup MLflow -> B2    |
+========================+     +========================+
          |                              |
          | git push                     | SCP model.pkl
          v                              v
+========================+     +========================+
|    LAPTOP (Linux/Win)  |     |  RASPBERRY PI 4 (ARM)  |
| ~~~~~~~~~~~~~~~~~~~~~~ |     | ~~~~~~~~~~~~~~~~~~~~~~ |
| - STANDBY / backup     |     | - Postgres 16          |
| - Scraping fallback    |     | - Daily cron pipeline  |
| - Nocne cronjobs       |     | - Inference (predict)  |
|   (jesli Dev PC off)   |     | - Telegram notify      |
| - Panel Streamlit      |     | - Backup PG -> B2      |
|   (internal, optional) |     | - healthchecks.io ping |
|                        |     |                        |
| Always-on: NIE domyslne|     | Always-on: TAK (24/7)  |
| Only-if-needed mode    |     | Primary production     |
+========================+     +========================+
```

### Szczegolowe przypisanie

| Komponent | Priorytet | Maszyna glowna | Fallback | Uzasadnienie |
|-----------|-----------|----------------|----------|-------------|
| **Postgres DB** | Krytyczny | Raspberry Pi 4 | Laptop | Pi = always-on, Linux, stabilny. OOM risk zarzadzany przez tuning (256MB shared_buffers). |
| **Daily pipeline (cron)** | Krytyczny | Raspberry Pi 4 | Laptop | Lekki (inference only), 5W, niezawodny. |
| **Telegram bot** | Krytyczny | Raspberry Pi 4 | Laptop | Czesc daily pipeline, ta sama maszyna. |
| **FastAPI backend** | Niepotrzebny alpha | --- | Laptop | Dopiero w R6. Jesli powstanie: laptop lub VPS. Nie Pi (za malo RAM). |
| **MLflow server** | Wazny | VM (jesli persistent) | Dev PC | VM daje always-on MLflow. Jesli VM ephemeryczny: Dev PC. |
| **Trening modeli** | Wazny | VM | Dev PC | VM ma wiecej mocy. Dev PC jako fallback. |
| **Eksperymenty** | Wazny | VM + Dev PC | --- | VM do duzych run. Dev PC do szybkich iteracji. |
| **Landing page** | Wazny alpha | Lovable (hosted) | --- | Zero infra wlasnej. Lovable hostuje za darmo/tanio. |
| **Panel uzytkownika** | Post-alpha | Lovable/laptop | --- | Lovable jesli hosted panel. Laptop jesli Streamlit internal. |
| **Scraping (Sofascore)** | Sredni | Dev PC | Laptop | Headless Chrome wymaga x86_64 + RAM. |
| **Scraping (FDCOUK, ELO)** | Sredni | Raspberry Pi 4 | --- | Lekkie HTTP requesty, ARM OK. |
| **Backup** | Krytyczny | Pi -> B2 (Backblaze) | --- | pg_dump + b2 upload, juz zaprojektowane. |
| **Monitoring** | Wazny | healthchecks.io (hosted) | --- | Free tier, 20 checkow. Zero infra. |
| **Rozwoj kodu** | Krytyczny | Dev PC | --- | Claude Code, IDE, git. |

### Przeplywy danych

```
1. TRENING (ad hoc, 1-2x/tydzien):
   Dev PC (edycja kodu) 
     -> git push -> VM pulls 
     -> VM: sl backtest run --mlflow
     -> VM: mlflow transition --stage Production
     -> VM: scp model.pkl pi@<pi-ip>:/app/models/production/
   
2. DAILY PIPELINE (cron, codziennie 06:00):
   Pi: sl pipeline run --fast (scrape FDCOUK, STS odds)
     -> sl features build
     -> sl predict run --model-path /app/models/production/model.pkl
     -> sl notify bet-slip (Telegram)
   
3. EVENING (cron, codziennie 23:30):
   Pi: sl results run -> sl notify results (Telegram)

4. WEEKLY (cron, poniedzialek 07:30):
   Pi: sl weekly run (raport tygodniowy -> Telegram)

5. SCRAPING (ad hoc na Dev PC):
   Dev PC: sl scrape-sofascore run
     -> scp data/sofascore_cache/ pi@<pi-ip>:/app/data/
   
6. BACKUP (cron, codziennie 03:00):
   Pi: pg_dump | gzip | b2 upload
```

---

## Wplyw na timeline 4-tygodniowy

### Czy architektura 4-maszynowa zmienia plan?

**NIE -- plan alpha pozostaje 4 tygodnie.** Powody:

1. **Pi setup** -- juz zaplanowany w `docs/alpha_launch_plan.md`, sekcja 2.2. Nic sie nie zmienia.
2. **Laptop** -- w trybie standby, zero konfiguracji wymaganej na alpha. Staje sie aktywny dopiero jesli Pi padnie.
3. **VM** -- MLflow na VM zamiast Dev PC to 2-3h migracji. Mozna zrobic rownolegle z innymi zadaniami.
4. **Panel** -- odlozony na post-alpha. Zero wplywu na timeline.

### Jedyna zmiana w planie

Zamiast:
- ADR-0017: dual-machine (Pi + Dev PC)

Mamy:
- ADR-0017 (superseded by ADR-0019): quad-machine (Pi = production, Dev PC = development, VM = compute, Laptop = standby)

Dodatkowy czas: ~3h na konfiguracje VM (Tailscale, MLflow migration). Nie zmienia 4-tygodniowego planu.

---

## Podsumowanie decyzji

| Pytanie | Decyzja | Pewnosc | ADR |
|---------|---------|---------|-----|
| Q1: Monorepo | Zostajemy | [PEWNE] | ADR-0018 |
| Q2: Panel | Telegram na alpha, panel post-alpha | [PEWNE] alpha, [HIPOTEZA] panel | Brak (ADR-0016 obowiazuje) |
| Q3: Laptop | Standby/backup, nie primary | [HIPOTEZA] | ADR-0019 |
| Q4: VM | MLflow + trening jesli persistent | [DO SPRAWDZENIA] persistencja VM | ADR-0019 |
| Q5: Przypisanie | Pi=prod, VM=compute, DevPC=dev, Laptop=standby | [HIPOTEZA] VM czesc | ADR-0019 |

---

## Otwarte pytania do foundera [DO SPRAWDZENIA]

1. **VM -- jaka to maszyna?** Uczelnia? Praca? Cloud free tier? Jakie SLA?
2. **VM -- czy jest persistent?** Czy dane przetrwaja restart? Czy VM moze zniknac?
3. **VM -- siec?** Publiczny IP? VPN? Tailscale?
4. **VM -- ile RAM/CPU/dysk?** Specyfikacja.
5. **VM -- czy komercyjne uzycie jest dozwolone?**
6. **Laptop -- jaki OS?** Windows czy Linux? Ile RAM?
7. **Laptop -- czy bedzie always-on?** Czy moze stac na polce podlaczony do pradu?
8. **Laptop -- bateria?** Czy mozna ustawic limit ladowania?

Odpowiedzi na te pytania moga zmienic rekomendacje w ADR-0019.

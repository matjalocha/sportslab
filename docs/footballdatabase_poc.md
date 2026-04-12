# footballdatabase.eu Scraper PoC

Date: 2026-04-07

## Verdict

Technically feasible for a conservative, cache-first scraper, but not suitable for high-volume crawling without a hard page budget and careful scheduling.

The public competition page tested was:

- `https://www.footballdatabase.eu/pl/rozgrywki/ogolne/22323-premier_league/2025-2026`

Observed result:

- HTTP 200 from a single controlled request.
- Static HTML length about 331 KB.
- No headless browser needed for the first competition-page layer.
- Page includes fixtures/results in `div#results table.list`.
- Page includes visible navigation to individual rankings and club stats.
- Public JS exposes AJAX helpers such as `putgames()` and `nextpage()`, but those should be a second-phase integration, not the first crawler path.
- Live smoke test with the PoC parser extracted 10 fixtures from the current visible Premier League round, including match ID, home/away teams, kickoff timestamp, timezone, status, and match URL.

## robots.txt / blocking risk

Observed `robots.txt` includes:

- `Crawl-Delay: 2`
- Disallowed search/query-like paths such as search, players lists, results filters, and many parameterized URLs.
- Canonical competition URLs like `/pl/rozgrywki/ogolne/...` were not globally disallowed in the observed file.

The site UI also showed a page-view quota warning for non-logged-in users. That means the crawler should not be designed as a broad spider.

Recommended guardrails:

- Default delay at least 2.5 seconds between network requests.
- Default max pages per run, e.g. 20 pages.
- On-disk HTML cache by URL hash.
- Seeded URL list only, not recursive link discovery by default.
- No scraping of disallowed search/player-list/result-query pages.
- Stop immediately on 403, 429, captcha, or quota-warning detection.
- Prefer refresh schedules like daily/weekly deltas over historical full backfills.

## Data available from canonical competition pages

The tested competition page exposed:

- Round fixtures/results.
- Match URLs and match IDs.
- Club URLs and club display names.
- Upcoming/played status from score cell.
- Kickoff timestamps embedded in `moment.tz(...)` JavaScript.
- Modules for transfers, best XI, hot players, individual rankings, club rankings, form, attack/defense/attendance, general stats.

The first PoC parser implemented:

- `FootballDatabaseScraper.scrape_competition_fixtures(url)`
- `parse_competition_fixtures(html, competition_url)`
- `FootballDatabaseFixture` dataclass

Files:

- `packages/ml-in-sports/src/ml_in_sports/processing/scrapers/footballdatabase.py`
- `packages/ml-in-sports/tests/processing/scrapers/test_footballdatabase.py`

## Recommended production path

1. Start with competition-page fixtures/results parser only.
2. Add a seed registry that maps SportsLab leagues/seasons to known canonical URLs.
3. Persist raw HTML snapshots to object storage or local cache before parsing.
4. Add parser tests from saved fixtures for each target page type.
5. Add quota/captcha detectors before any broad run.
6. Only after stable parser coverage, evaluate minimal AJAX calls for ranking pages that are not fully present in the initial DOM.
7. Keep football-data.co.uk as primary source where it already covers odds/results; use footballdatabase.eu to enrich fields that football-data lacks.

## Decision

I would proceed, but only with a responsible crawler architecture:

- yes for seeded, cache-first, low-rate enrichment;
- no for blind large-scale crawling;
- no for bypassing quota, captcha, login, or robots restrictions.

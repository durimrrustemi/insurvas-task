# Partner Outreach Pipeline — Implementation Plan

Take-home for INSURVAS. 7 days, solo. Judged on: working demo, code I can explain and change live, write-up, and quality of decisions.

## 1. What we're building (one paragraph)

A tool that finds call centers (BPOs) worldwide from public web data, ranks them on English quality / insurance experience / size with the evidence shown, drafts personalised first messages and follow-ups per channel (email, LinkedIn, WhatsApp) for human review, and tracks each center through stages (found → contacted → replied → in talks → test calls → signed / lost) with a 3-day follow-up reminder. Nothing sends automatically.

## 2. Business facts the design depends on

- INSURVAS sells final expense (funeral cost) life insurance to US seniors 60+.
- Centers bring their own leads and sell INSURVAS live transfers. INSURVAS supplies nothing. Pitch = "we buy your live transfers, start with test calls."
- No warm network exists. Discovery is cold, worldwide. Ranking cannot be calibrated against known partners, so every score must show its evidence and weights live in config.
- Consent (TCPA) and licensing are what blow up deals later. Compliance signals are part of qualification.
- "Signed" = agreed price per transfer, daily volume, hours, quality threshold, after a test batch.

## 3. Decisions (made, not asked)

| Decision | Choice | Why |
|---|---|---|
| Stack | Backend: Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, Postgres only (tests run against a Postgres test DB in compose/CI, transaction-rollback per test). Frontend: Next.js (App Router) + TypeScript, Tailwind, shadcn/ui. `docker compose up` runs db + api + web. Full REST API under `/api/v1`, OpenAPI docs at `/docs` | What I'm fastest in; Python is the better fit for crawling/scoring; Next.js matches their frontend; Docker gives one-command setup; one DB dialect avoids surprises |
| Discovery source | Serper (Google results via API) + Google Places API, both behind a `Source` protocol | No scraping of search engines; adding a source is one file |
| Enrichment | httpx async fetch of homepage + up to 3 inner pages (services/about/careers/clients), respect robots.txt, cache to disk | Enough signal, polite, reproducible |
| Scoring | Weighted signals per criterion, weights in `config/scoring.yaml`, every signal stores source URL + matched text | Explainable, changeable live on the call |
| LLM | Anthropic SDK, one provider behind `app/services/llm.py`; used for English-quality grading, evidence extraction, message drafting | Single place to swap models |
| Messages | Generated from a per-partner "angle" grounded in cited evidence; templates per channel with hard length limits; every message has a review status | "Real person who did homework" + nothing sends without approval |
| Reminder rule | 3 days without a touch → needs attention; configurable | From the brief |
| Countries | `config/countries.yaml`: 12 English-BPO countries with baseline English score, timezone, preferred channel | Adding a country = one YAML entry (live-change candidate) |
| Demo data | Seed script creates 30 realistic partners across stages; live discovery demoed on one small country | Demo never depends on a 20-minute crawl |
| Auth | None | Single-user tool; note in write-up |

## 4. Data model

```
partners        id, name, website, country, city, timezone, type (bpo|vendor),
                stage, stage_entered_at, owner_note, blocker (enum|null),
                score_total, score_english, score_insurance, score_size, score_compliance,
                engagement_terms (json: price_per_transfer, daily_volume, hours, quality_threshold),
                created_at, updated_at
contacts        id, partner_id, name, role, email, linkedin_url, whatsapp, source_url
signals         id, partner_id, criterion (english|insurance|size|compliance),
                key, value, weight, source_url, matched_text, created_at
pages           id, partner_id, url, fetched_at, status, text_path (cache)
messages        id, partner_id, channel (email|linkedin|whatsapp), sequence (0=first,1..n=followup),
                subject, body, angle, evidence_ids (json), status (draft|approved|rejected|sent),
                send_after, created_at
activities      id, partner_id, kind (touch|reply|note|stage_change|blocker), channel, body, at
discovery_runs  id, country, queries (json), started_at, finished_at, found, new
```

Stage enum: `found, contacted, replied, in_talks, test_calls, signed, lost`.
Blocker enum: `no_response, pricing, compliance, capacity, waiting_on_them, waiting_on_us`.

Readiness checklist (derived, not stored): required fields per stage transition, e.g. `in_talks → test_calls` needs a named contact, compliance signal present, agreed test batch size.

## 5. Modules

Repo layout:
```
backend/   FastAPI app, SQLAlchemy models, Alembic, services, CLI (typer), tests (pytest)
frontend/  Next.js app, calls backend via /api (NEXT_PUBLIC_API_URL)
config/    YAML shared by backend; frontend reads it through /api/config
docker-compose.yml, Makefile (setup / dev / test / lint / seed / discover / demo)
```

### 5.1 Finder (`backend/app/discovery/`)
- `sources/serper.py`, `sources/places.py` implement `Source.search(query, country) -> list[Candidate]` (Protocol).
- `queries.py`: builds 15–25 queries per country from `config/queries.yaml` templates (e.g. "call center outsourcing {city}", "BPO insurance campaign {country}", "live transfer call center {country}").
- `dedupe.py`: normalise domain, merge candidates.
- `fetch.py`: httpx + asyncio, robots-aware, concurrency 8, timeout 10s, cache in `.cache/pages/`.
- `extract.py`: text via trafilatura/BeautifulSoup, find inner links by keyword (services, about, careers, clients, industries).
- CLI: `make discover COUNTRY=PH LIMIT=50` → `python -m app.cli discover --country PH --limit 50`.
- API: `POST /api/discovery/runs` (background task), `GET /api/discovery/runs/{id}`.

### 5.2 Scorer (`backend/app/scoring/`)
- `signals/english.py`: country baseline (config), site-English LLM grade 1–5, keyword claims ("native English", "US clients", "neutral accent"), US/UK/AU client logos/case studies.
- `signals/insurance.py`: weighted keywords (final expense, live transfer, Medicare, life insurance, TCPA, licensed, carriers), insurance case studies, insurance-related job postings on careers page.
- `signals/size.py`: stated seats/agents/employees, number of locations, years in business, 24/7 claims, careers page depth.
- `signals/compliance.py`: TCPA/DNC/consent/recording/PCI/HIPAA/ISO mentions.
- `score.py`: weighted sum per criterion from `config/scoring.yaml`; unknown = None, shown as gap, never silently 0.
- Every signal row stores `source_url` + `matched_text`.
- Pure functions, no DB access, so they're trivially unit-tested.

### 5.3 Writer (`backend/app/outreach/`)
- `angle.py`: LLM picks 1–2 concrete facts from signals → one-sentence angle per partner.
- `draft.py`: generates first message + 3 follow-ups per channel from `config/cadence.yaml` (day 0 / 3 / 7 / 14; intents: intro, value-add, nudge, close-loop). Prompt forbids claims not in evidence. Hard limits enforced in code after generation: WhatsApp ≤ 300 chars, LinkedIn note ≤ 300, email ≤ 120 words + subject.
- All drafts land as `status=draft`. Approve / edit / reject in UI. "Mark as sent" is manual and logs an activity.
- Prompts in `backend/app/prompts/*.py` as named constants.

### 5.4 Tracker (`frontend/app/` + `backend/app/api/`)
- `/partners` — list with filters (country, stage, score, blocker), sort by score / days since last touch.
- `/partners/[id]` — profile: score breakdown with evidence links, contacts, messages with review controls, activity timeline, readiness checklist, blocker, terms (on test_calls/signed).
- `/board` — kanban by stage, drag to move (logs stage_change).
- `/attention` — needs attention: no touch ≥ 3 days, stale in stage ≥ 7 days, open blockers. Sorted by urgency.
- `/discover` — pick country, run discovery (small limit live), review candidates, accept/reject.
- `/config` — read-only view of current weights, cadence, countries (shows the "change is in config" story).

## 5.5 Scoring formula (implement exactly this)

Each criterion (english, insurance, size, compliance) has signals with `weight` and `value` 0–1, from `config/scoring.yaml`.

```
criterion_score = Σ(weight_i × value_i) / Σ(weight_i)      over signals found
coverage        = Σ(weight_i found) / Σ(weight_i possible)
total           = Σ(criterion_weight_c × criterion_score_c) / Σ(criterion_weight_c)   over criteria with coverage > 0
confidence      = weighted mean of coverage across criteria (by criterion_weight)
```

- Starting criterion weights: insurance 0.35, English 0.30, size 0.20, compliance 0.15. Documented as priors.
- English gets a baseline signal from `countries.yaml` (`english_baseline`, weight 1) so it's overridden by real evidence.
- Unknown is `None`, never 0. UI shows `total`, `confidence`, and per-criterion score + coverage + evidence rows. Sort by `total` ("high potential") or `total × confidence` ("safe bets").
- No ML, no learned weights: there are no labelled outcomes yet. Lost reasons and test-call results are the future labels.

## 5.6 Gates (separate from scoring)

`config/gates.yaml` lists hard requirements. Initial: `us_hours`, `compliance`. Each has three states per partner: `confirmed | unknown | no`.

- `confirmed`: from site evidence or a manual tick (logged as an activity with source).
- `unknown`: partner stays eligible for outreach; the first message asks the question; transition to `test_calls` is blocked until confirmed.
- `no`: partner auto-transitions to `lost` with reason `gate:<name>`.
- Gates never enter the weighted score. A gate failure can't be averaged away.

## 5.7 Triage over discovery (shapes Writer and Attention)

BPOs actively look for buyers; reply rates will be high. The scarce thing is quality, not conversations.

- First message doubles as qualification: asks US hours, insurance lines done before, seats, own lead sourcing, consent process. Reply quality is itself a signal.
- Default cadence: 2 follow-ups (config allows 4).
- Attention view priority order: (1) replied and gates look good but not in test calls, (2) in test calls past expected end date, (3) no touch ≥ 3 days, (4) stale in stage ≥ 7 days, (5) new high-score candidates not yet contacted.
- One-click lost with reason from the partner page; expect most of the pipeline to die there.
- Overclaim flag: if a reply or manual note states seats/years far above what the site shows, flag it (simple ratio heuristic, visible on the card).
- Lost reasons feed `/funnel`: % lost per reason per stage.

## 6. Config files

- `config/countries.yaml` — code, name, english_baseline (0–1), timezone, preferred_channels [..], cities [..]
- `config/scoring.yaml` — per criterion: signal weights, thresholds, criterion weights for total
- `config/cadence.yaml` — follow-up days and intents per channel
- `config/queries.yaml` — query templates
- `config/gates.yaml` — hard requirements and their evidence keywords
- `.env.example` — DATABASE_URL, DATABASE_URL_TEST, SERPER_API_KEY, GOOGLE_PLACES_KEY, ANTHROPIC_API_KEY, MOCK_LLM=1

Other fixed choices: `uv` + `pnpm`; UUIDv7 primary keys; UTC timestamptz; seed = 30 partners over 6 countries and all stages, 2 with open blockers, 3 overdue; `MOCK_LLM=1` default, real key opt-in. See CONVENTIONS.md for everything else.

## 7. Day plan (Oct 29 – Nov 4)

| Day | Goal | Done when |
|---|---|---|
| Thu 29 | Scaffold: docker-compose (db/api/web), FastAPI + SQLAlchemy models + Alembic, seed CLI, config loaders, partner list + detail pages in Next.js | `make setup && make dev` shows 30 seeded partners |
| Fri 30 | Finder: Serper + Places sources, queries, dedupe, async fetch+cache, extract | `make discover COUNTRY=PH LIMIT=30` writes partners + pages |
| Sat 31 | Scorer: all four signal modules, evidence rows, score breakdown UI | Top 10 PH partners ranked with visible evidence |
| Sun 1 | Writer: angle, drafts per channel, cadence, review UI | Approve/edit/reject a 4-message sequence for one partner |
| Mon 2 | Tracker: kanban, attention view, blockers, readiness checklist, terms, activity log | Move a partner found→signed with full timeline |
| Tue 3 | Hardening: tests (scoring, cadence, dedupe), lint, error handling on bad sites, README, one-command setup, record video | Fresh clone runs in 3 commands; 5-min video recorded |
| Wed 4 | Write-up, final review, prepare live-change candidates, submit | Repo public, write-up ≤ 1 page, email sent |

Buffer rule: if a day slips, cut `/discover` live UI (keep CLI) before cutting anything in Tracker or Writer.

## 8. Demo script (≤ 5 min)

1. `/discover` — run PH with limit 15 live; show candidates appear with scores and evidence.
2. Open one partner — score breakdown, click an evidence link, show a gap ("size: unknown").
3. Generate outreach — show angle, email + WhatsApp drafts, edit one line, approve.
4. Mark contacted → log a reply → move to in talks → readiness checklist flags missing compliance evidence.
5. `/attention` — show a partner untouched 4 days and one blocked on pricing.
6. Open `config/scoring.yaml`, change a weight, refresh, ranking changes.

## 9. Write-up outline (≤ 1 page)

- What I built and the 3 decisions that shaped it (cold worldwide discovery, evidence-first scoring, human-approved outreach).
- Why these sources and not scraping LinkedIn/Google.
- Where AI got it wrong: hallucinated insurance experience before I forced source URLs; generic messages before grounding on evidence; English grading inconsistency across runs.
- What I'd build next with a month: reply ingestion from Gmail/WhatsApp, test-call quality scoring feeding back into weights, multi-user ownership, handoff of signed partners into the INSURVAS admin console as a partner entity with rates.
- Known limits: scores are priors until test calls validate them; single user; no auth.

## 10. Live-change candidates (rehearse each)

- Add a country in `countries.yaml`.
- Change reminder from 3 to 2 days in `cadence.yaml`.
- Add a stage (`contract_review`) — touches enum, board column, readiness rules.
- Add a signal (`has_pricing_page`) to size scoring.
- Change WhatsApp limit to 200 chars.

## 11. Quality bar

- Backend: ruff + mypy (strict on `scoring/` and `outreach/`), pytest for scoring math, cadence dates, dedupe, readiness rules, API tests against Postgres (rollback per test).
- Frontend: TypeScript strict, ESLint, Prettier.
- `make test` and `make lint` run both sides; GitHub Actions runs them on push.
- README: what it is, `git clone && cp .env.example .env && docker compose up` setup, env vars, how scoring works, how to add a country/source/signal.
- Small, frequent commits with clear messages; history is read.
- No secrets in repo. `.env.example` only.

## 12. Claude Code working rules

- Read this file and `config/*.yaml` before any task.
- One module per session; finish with tests passing and a commit.
- Never add a dependency without stating why in the commit message.
- No fabricated partner data outside `backend/app/seed.py`; seed data must be clearly synthetic (names like "Example BPO Cebu").
- Every LLM prompt lives in `backend/app/prompts/` as a named constant, never inline.
- Scoring and cadence logic are pure Python functions; keep DB and HTTP out of them.
- Frontend never computes scores or reminders; it renders what the API returns.

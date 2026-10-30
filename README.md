# INSURVAS Partner Pipeline

Finds call centers (BPOs) worldwide from public web data, ranks them on insurance experience, English quality, size and compliance with the evidence shown, drafts personalised outreach per channel for human review, and tracks each center from `found` to `signed` or `lost`. Nothing is sent automatically.

## Run it

Requires Docker.

```bash
git clone <repo> && cd insurvas-task
cp .env.example .env
docker compose up
```

- Web: http://localhost:3000 · API docs: http://localhost:8000/docs
- First start runs the migrations and seeds 30 clearly synthetic partners (`example-bpo-N.test`). Later starts skip the seed.
- Port clash? Set `DB_PORT`, `API_PORT`, `WEB_PORT` in `.env`.

Works without any API keys: `MOCK_LLM=1` returns canned LLM output, and discovery simply finds nothing without search keys.

| Variable | Purpose |
|---|---|
| `SERPER_API_KEY` | Google results via Serper, for discovery |
| `GOOGLE_PLACES_KEY` | Google Places, for discovery |
| `ANTHROPIC_API_KEY` + `MOCK_LLM=0` | Real angle and message drafting |
| `LLM_MODEL` | Model for those calls (default `claude-sonnet-5-5`) |

## Commands

```bash
make test                       # backend pytest (Postgres, rollback per test) + frontend lint
make lint                       # ruff, mypy --strict on scoring/outreach/rules, eslint, tsc, prettier
make discover COUNTRY=PH LIMIT=15
make score COUNTRY=PH
```

Everything runs inside the containers, so no local Python or Node is needed. CI runs the same checks on every push (`.github/workflows/ci.yml`).

## How it works

**Finder** (`backend/app/discovery/`): query templates × country cities → Serper/Places → dedupe on normalised domain → fetch homepage + up to 3 inner pages (robots-aware, cached 30 days in `.cache/pages/`). Bad sites (DNS, TLS, timeouts, odd charsets) are recorded and skipped, never fatal.

**Scorer** (`backend/app/scoring/`): pure functions turn page text into signal rows, each with `source_url` and `matched_text`.

```
criterion_score = Σ(weight × value) / Σ(weight)          over signals found
coverage        = Σ(weight found) / Σ(weight possible)
total           = Σ(criterion_weight × criterion_score) / Σ(criterion_weight)   over criteria with coverage > 0
confidence      = coverage averaged by criterion_weight
```

Unknown is `None`, never 0. The weights in `config/scoring.yaml` are priors: there are no labelled outcomes yet.

**Gates** (`config/gates.yaml`): hard requirements (US hours, compliance), deliberately kept out of the score so a failure can't be averaged away. Each one is `confirmed` (keyword evidence or a manual tick), `unknown`, or `no`. A `no` moves the partner to `lost` with reason `gate:<name>`.

**Readiness** (`backend/app/rules.py`): `POST /partners/{id}/stage` refuses a move (422 `gate_blocked`) until the checks for that stage pass. `in_talks` needs a named contact. `test_calls` needs both gates and an agreed test batch size. `signed` needs price per transfer, daily volume, hours and a quality threshold. The UI shows the same checklist from `GET /partners/{id}/readiness` and never computes it itself.

**Writer** (`backend/app/outreach/`): an angle grounded in the evidence rows, then first message + follow-ups per channel on the cadence in `config/cadence.yaml`. Length limits are enforced in code after generation. Every draft starts as `draft` and has to be approved by a person.

**Tracker**: `/board` kanban, `/attention` (replied, no touch ≥ 3 days, stale ≥ 7 days, blockers), and the partner page (score evidence, gates, terms, blocker, timeline).

## Changing behaviour

Config is loaded once at startup, so edit the YAML and restart the API with `docker compose restart api`.

- **Add a country**: add an entry in `config/countries.yaml` (code, english_baseline, timezone, channels, cities).
- **Change the reminder**: `reminder_days` in `config/cadence.yaml`.
- **Change a weight**: `config/scoring.yaml`, then `make score` to re-rank.
- **Add a signal**: add a weight entry under its criterion in `config/scoring.yaml` and the detection in `backend/app/scoring/signals/<criterion>.py`.
- **Add a source**: a class with `async search(query, country) -> list[Candidate]` in `backend/app/discovery/sources/` (the `Source` protocol), registered in `discovery/runner.py`.
- **Add a gate**: an entry in `config/gates.yaml` with `evidence_keywords` and `required_before`.

## Deliberately left out

Auth and multi-user (single-user tool), sending messages, reply ingestion, LinkedIn/Google scraping, and a job queue (a discovery run executes inside the request). See `LATER.md`.

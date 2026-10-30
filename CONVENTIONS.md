# Conventions

How this repo is built. Read with PLAN.md. If something here conflicts with a nicer idea, follow this file and note the idea in LATER.md.

## Tooling

- Python 3.12, `uv` for deps and venv (`uv sync`, `uv run`). `pyproject.toml` + `uv.lock` committed.
- Node 22, `pnpm` (`pnpm-lock.yaml` committed).
- `docker compose up` starts `db` (Postgres 16), `api` (FastAPI, uvicorn --reload), `web` (Next.js dev). `db_test` is a second database on the same Postgres for tests.
- `Makefile` targets: `setup`, `dev`, `test`, `lint`, `fmt`, `migrate`, `seed`, `discover COUNTRY= LIMIT=`, `demo` (migrate + seed + dev).
- Pre-commit: ruff (lint + format), mypy on `scoring/` and `outreach/`, prettier + eslint on frontend.
- CI: GitHub Actions, Postgres service, runs `make lint test` on push.

## Repo layout

```
backend/
  app/
    main.py            FastAPI app factory, routers, exception handlers
    settings.py        pydantic-settings, single Settings object
    config.py          loads config/*.yaml into frozen dataclasses once
    db.py              engine, session factory, get_session dependency
    models/            SQLAlchemy models, one file per table
    schemas/           Pydantic I/O models: XCreate, XRead, XUpdate
    api/v1/            routers, thin; one file per resource
    services/          business logic, talks to DB, raises domain errors
    discovery/         sources/, queries.py, dedupe.py, fetch.py, extract.py
    scoring/           pure functions, no DB/HTTP
    outreach/          pure functions + LLM calls via services/llm.py
    prompts/           prompt constants, one per file, named with version suffix
    services/llm.py    the only place the Anthropic SDK is imported
    seed.py            synthetic seed data
    cli.py             typer CLI: discover, score, seed
  alembic/
  tests/
frontend/
  app/                 routes: partners, partners/[id], board, attention, discover, config
  components/          PascalCase.tsx
  lib/api.ts           typed client, the only place fetch() is called
  lib/types.ts         generated or hand-written types matching schemas
config/
  countries.yaml  scoring.yaml  cadence.yaml  gates.yaml  queries.yaml
docs/decisions/        ADR-001-sources.md etc. (short)
PLAN.md  CONVENTIONS.md  WRITEUP.md  LATER.md  README.md
```

## Naming

- Python: `snake_case` functions/vars/modules, `PascalCase` classes, `UPPER_SNAKE` constants. Modules singular (`partner.py`). Enums are `StrEnum`.
- DB: tables plural snake (`partners`, `signals`). PK `id` UUIDv7. FKs `partner_id`. Every table has `created_at`, `updated_at` (UTC, timestamptz). Enums as Postgres enums.
- API: `/api/v1/<plural-noun>`; actions as sub-resources (`POST /partners/{id}/stage`). No verbs in paths.
- Schemas: `PartnerCreate`, `PartnerRead`, `PartnerUpdate`. Never return ORM objects.
- Frontend: components `PascalCase.tsx`, hooks `useThing.ts`, route folders kebab-case.
- Prompts: `DRAFT_EMAIL_V1`, `ANGLE_V1`, `ENGLISH_GRADE_V1`. Prompt name stored on the row it produced.

## Layers and rules

- Router → service → DB. Routers validate input, call one service function, map result to a Read schema. No business logic in routers.
- `scoring/` and `outreach/` never import SQLAlchemy or httpx. They take plain dataclasses/dicts and return the same.
- Stage changes only through `services.partners.transition(session, partner_id, to_stage, reason=None)`. It checks the allowed-transition table and the gates, writes the activity, and raises `InvalidTransition` or `GateBlocked`. Nothing else writes `stage`.
- Partners are unique on `domain` (normalised: lowercase, no scheme, no `www.`). Discovery upserts, never duplicates.
- Page cache: `.cache/pages/<sha1(url)>.json` with `fetched_at`; re-fetch only if older than 30 days or `--force`.
- Config YAML is loaded once at startup. Changing a file and restarting the API is the supported way to change behaviour. `GET /api/v1/config` returns the loaded config.

## Errors

- Domain exceptions in `app/errors.py`: `NotFound`, `Conflict`, `InvalidTransition`, `GateBlocked`, `ExternalServiceError`.
- One exception handler in `main.py` maps them to 404 / 409 / 409 / 422 / 502.
- Response shape: `{"error": {"code": "invalid_transition", "message": "...", "details": {...}}}`.
- Services never raise `HTTPException`.

## REST resource map

```
GET    /api/v1/partners                 ?country=&stage=&blocker=&min_score=&sort=&limit=&offset=
POST   /api/v1/partners
GET    /api/v1/partners/{id}
PATCH  /api/v1/partners/{id}
DELETE /api/v1/partners/{id}

POST   /api/v1/partners/{id}/stage      {to, reason?}
POST   /api/v1/partners/{id}/score      recompute
POST   /api/v1/partners/{id}/outreach   {channels?: [...]} → drafts

GET    /api/v1/partners/{id}/signals
POST   /api/v1/partners/{id}/signals    manual signal or gate confirmation
PATCH  /api/v1/signals/{id}             override value/weight

GET    /api/v1/partners/{id}/contacts
POST   /api/v1/partners/{id}/contacts
PATCH  /api/v1/contacts/{id}
DELETE /api/v1/contacts/{id}

GET    /api/v1/partners/{id}/messages
PATCH  /api/v1/messages/{id}            body, subject, status

GET    /api/v1/partners/{id}/activities
POST   /api/v1/partners/{id}/activities {kind, channel?, body}

GET    /api/v1/attention
GET    /api/v1/board
GET    /api/v1/funnel

GET    /api/v1/discovery/runs
POST   /api/v1/discovery/runs           {country, limit} → 202 {id}
GET    /api/v1/discovery/runs/{id}
GET    /api/v1/discovery/runs/{id}/candidates
POST   /api/v1/discovery/candidates/{id}/accept
POST   /api/v1/discovery/candidates/{id}/reject

GET    /api/v1/config
GET    /api/v1/health
```

Status codes: 200 read/update, 201 create, 202 async run accepted, 204 delete. Lists return `{"items": [...], "total": n, "limit": l, "offset": o}`.

## LLM

- `services/llm.py` exposes `complete_json(prompt_name, prompt, variables, schema: type[BaseModel]) -> BaseModel`.
- Retries 3× with backoff, timeout 30s, logs prompt name, tokens, latency, cost estimate per call.
- `MOCK_LLM=1` (default in `.env.example`) returns deterministic canned JSON per prompt name from `tests/fixtures/llm/`. Tests and the demo-without-key run on this.
- Output is always JSON validated by a Pydantic model. On validation failure: log, raise `ExternalServiceError`, never return partial data.
- Prompts receive only structured evidence (signal rows), never raw page text, except the English-grade prompt which gets at most 1,500 chars of homepage text.
- Message length limits are enforced in code after generation, not trusted to the prompt.

## Testing

- pytest, `DATABASE_URL_TEST`, each test in a transaction rolled back at teardown. Factories in `tests/factories.py`.
- Pure modules (`scoring`, `outreach.cadence`, `discovery.dedupe`, transition rules) get table-driven tests. Minimum cases: all evidence / no evidence / contradictory evidence / gate blocked.
- API tests hit the app via `httpx.AsyncClient` with `MOCK_LLM=1`.
- Frontend: no unit tests. One Playwright smoke test if time remains on day 6; otherwise skip and say so.

## Git

- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`. Imperative subject ≤ 72 chars, body explains why when not obvious.
- Small commits, one concern each. `main` only. Tag `v0.1-demo` at submission.
- Never commit `.env`, `.cache/`, `node_modules/`, `.venv/`.

## Frontend

- Server components fetch lists via `lib/api.ts`; client components only for interaction (kanban drag, review buttons, dialogs). After a mutation call `router.refresh()`.
- No global state library. No charts library; the funnel is a table plus simple bars in CSS.
- shadcn/ui components as-is. Don't restyle.
- Dates shown in partner timezone where relevant, otherwise local; stored UTC.

## Scope discipline

- Not building: auth, sending, reply ingestion, LinkedIn/Google scraping, a job queue, multi-user. Each is one line in WRITEUP.md under "deliberately left out".
- Anything new goes to LATER.md, not into the code.

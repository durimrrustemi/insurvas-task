.PHONY: setup dev test lint fmt migrate seed discover score recompute demo down

API = docker compose run --rm api uv run
WEB = docker compose run --rm --no-deps web

# Migrations and seeding also run on every `docker compose up` (see docker-compose.yml),
# so `setup` only prepares .env and images.
setup:
	cp -n .env.example .env || true
	docker compose build

dev:
	docker compose up

down:
	docker compose down

test:
	$(API) pytest -q
	$(WEB) pnpm lint

lint:
	$(API) ruff check .
	$(API) ruff format --check .
	$(API) mypy app/scoring app/outreach app/rules.py
	$(WEB) sh -c "pnpm lint && pnpm exec tsc --noEmit && pnpm exec prettier --check ."

fmt:
	$(API) ruff check --fix .
	$(API) ruff format .
	$(WEB) pnpm format

migrate:
	$(API) alembic upgrade head

seed:
	$(API) python -m app.cli seed

discover:
	$(API) python -m app.cli discover --country $(COUNTRY) --limit $(LIMIT)

score:
	$(API) python -m app.cli score $(if $(COUNTRY),--country $(COUNTRY),) $(if $(PARTNER),--partner $(PARTNER),)

# Re-apply scoring.yaml weights to stored evidence (no crawling). Restart the api first.
recompute:
	$(API) python -m app.cli score --recompute $(if $(COUNTRY),--country $(COUNTRY),)

demo: setup dev

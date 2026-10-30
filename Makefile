.PHONY: setup dev test lint fmt migrate seed discover score demo

setup:
	cp -n .env.example .env || true
	docker compose build
	docker compose up -d db
	sleep 2
	docker compose run --rm api uv run alembic upgrade head
	docker compose down

dev:
	docker compose up

test:
	docker compose run --rm api uv run pytest -x -q
	cd frontend && pnpm lint

lint:
	docker compose run --rm api uv run ruff check .
	docker compose run --rm api uv run ruff format --check .
	cd frontend && pnpm lint

fmt:
	docker compose run --rm api uv run ruff check --fix .
	docker compose run --rm api uv run ruff format .
	cd frontend && pnpm format

migrate:
	docker compose run --rm api uv run alembic upgrade head

seed:
	docker compose run --rm api uv run python -m app.cli seed

discover:
	docker compose run --rm api uv run python -m app.cli discover --country $(COUNTRY) --limit $(LIMIT)

score:
	docker compose run --rm api uv run python -m app.cli score $(if $(COUNTRY),--country $(COUNTRY),) $(if $(PARTNER),--partner $(PARTNER),)

demo: migrate seed dev

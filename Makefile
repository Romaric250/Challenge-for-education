SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: setup dev api web lint format typecheck test migrate generate-client compose-up compose-down check

setup:
	pnpm install
	uv sync --project apps/api --all-groups --python 3.12
	@if [ ! -f .env ]; then cp .env.example .env; fi
	$(MAKE) compose-up
	$(MAKE) migrate

dev:
	bash scripts/dev.sh

api:
	uv run --project apps/api --directory apps/api uvicorn tutor_api.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log

web:
	pnpm --filter @rwanda-ai-tutor/web dev

lint:
	uv run --project apps/api --directory apps/api ruff check src tests
	uv run --project apps/api --directory apps/api ruff format --check src tests
	pnpm exec turbo run lint
	pnpm exec prettier --check .

format:
	uv run --project apps/api --directory apps/api ruff check --fix src tests
	uv run --project apps/api --directory apps/api ruff format src tests
	pnpm exec prettier --write .

typecheck:
	uv run --project apps/api --directory apps/api mypy
	pnpm exec turbo run typecheck

test: migrate
	uv run --project apps/api --directory apps/api pytest
	pnpm exec turbo run test

migrate: compose-up
	uv run --project apps/api --directory apps/api alembic upgrade head

generate-client:
	bash scripts/generate-api-client.sh

compose-up:
	docker compose -f infra/docker-compose.yml up -d --wait postgres

compose-down:
	docker compose -f infra/docker-compose.yml down

check: lint typecheck test

#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose -f infra/docker-compose.yml up -d --wait postgres
uv run --directory apps/api alembic upgrade head

uv run --directory apps/api uvicorn tutor_api.main:app \
  --reload \
  --host 127.0.0.1 \
  --port 8000 \
  --no-access-log &
api_pid=$!

pnpm --filter @rwanda-ai-tutor/web dev &
web_pid=$!

cleanup() {
  kill "$api_pid" "$web_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM
wait -n "$api_pid" "$web_pid"

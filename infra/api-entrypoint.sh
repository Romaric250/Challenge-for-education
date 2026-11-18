#!/bin/sh
set -eu

alembic upgrade head

if [ "${TRUST_PROXY:-false}" = "true" ]; then
  exec uvicorn tutor_api.main:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --no-access-log \
    --proxy-headers
fi

exec uvicorn tutor_api.main:app \
  --host "${API_HOST:-0.0.0.0}" \
  --port "${API_PORT:-8000}" \
  --no-access-log

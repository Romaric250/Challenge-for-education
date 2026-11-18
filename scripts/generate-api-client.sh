#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

uv run --project apps/api --directory apps/api python -m tutor_api.openapi_export
pnpm --filter @rwanda-ai-tutor/api-client generate
pnpm exec prettier --write \
  packages/api-client/openapi.json \
  packages/api-client/src/schema.d.ts \
  packages/api-client/src/index.ts

# Local setup

This is the foundation of the Rwanda AI Tutor: a Next.js shell, a FastAPI service, and Postgres with pgvector. Sign-in, document ingestion, and tutoring are added in later phases. The commands below start what exists today.

## Tools

- Node.js 22
- pnpm 12 (`package.json` pins the version)
- uv, which installs Python 3.12 for the API
- Docker, for local Postgres

GNU Make runs the shortcuts in the `Makefile`. The same steps are written out below if `make` is not on your PATH.

## First run

From the repository root:

```bash
pnpm install
uv sync --project apps/api --all-groups --python 3.12
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d --wait postgres
uv run --project apps/api --directory apps/api alembic upgrade head
```

Or, with Make:

```bash
make setup
```

Start the API and the web app:

```bash
bash scripts/dev.sh
```

- Web: http://localhost:3000
- API liveness: http://localhost:8000/health/live
- API readiness: http://localhost:8000/health/ready
- OpenAPI: http://localhost:8000/api/docs

`/health/live` answers while the process is up. `/health/ready` returns 200 only when Postgres accepts a query. With `LLM_PROVIDER=none`, the provider check is reported as `not_configured` and does not fail readiness. A configured provider is probed with a short HTTP request; any response below 500 counts as reachable, including an authentication failure.

Readiness uses its own JSON document and HTTP status. Every other error uses `application/problem+json` with a stable `code`.

## Checks

```bash
uv run --project apps/api --directory apps/api ruff check src tests
uv run --project apps/api --directory apps/api ruff format --check src tests
uv run --project apps/api --directory apps/api mypy
uv run --project apps/api --directory apps/api pytest
pnpm exec turbo run lint typecheck build
pnpm exec prettier --check .
```

`pytest` includes integration tests that need the migrated database from the steps above. Unit tests alone:

```bash
uv run --project apps/api --directory apps/api pytest -m "not integration"
```

Regenerate the TypeScript client after the API schema changes:

```bash
bash scripts/generate-api-client.sh
```

The script writes `packages/api-client/openapi.json` and `packages/api-client/src/schema.d.ts`. CI fails if those files are out of date.

## Database

Local development uses the `pgvector/pgvector:pg16` image. The database name, user, and password are `tutor`. That password is for this local container only.

The first migration enables the `vector` extension and records the embedding dimension `1024` in `schema_meta`. `1024` matches BAAI bge-m3, the multilingual model the ingestion phase will use unless an ADR changes it. Nothing is embedded yet. Changing the dimension means a new migration and, once chunks exist, a re-embed. Do not edit `0001_enable_pgvector` after it has been applied.

`updated_at` on application tables is maintained by the `set_updated_at` trigger created in that migration.

### Neon

Create a Neon project and copy its pooled connection string. Put it in `DATABASE_URL`. A Neon URL looks like:

```text
postgresql://USER:PASSWORD@HOST/DB?sslmode=require
```

The API accepts `postgresql://` and `postgresql+asyncpg://`. It removes `sslmode` and `channel_binding` from the query string, because asyncpg does not accept those libpq parameters, and turns `sslmode=require` into an encrypted connection.

Run the same Alembic upgrade against that URL:

```bash
uv run --project apps/api --directory apps/api alembic upgrade head
```

Neon provides pgvector. The migration creates the extension in the database you point at. Do not commit the Neon URL.

## API process

The container entrypoint migrates, then starts uvicorn. Build it with the full Compose profile when you want the API in Docker instead of on the host:

```bash
docker compose -f infra/docker-compose.yml --profile full up --build
```

`TRUST_PROXY=true` turns on uvicorn proxy headers. Leave it false unless the process sits behind a proxy you control.

Interactive docs are on outside production. Set `DOCS_ENABLED=false` to hide `/api/docs` and `/api/openapi.json`. Production leaves them off unless `DOCS_ENABLED=true`.

## Layout

```text
apps/api     FastAPI service
apps/web     Next.js application
packages/config      shared TypeScript, ESLint, and theme entry
packages/api-client  client generated from the OpenAPI document
infra        Compose file and the API image
```

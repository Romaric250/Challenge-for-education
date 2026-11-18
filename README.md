# Rwanda AI Tutor

Curriculum-grounded tutor for Rwandan secondary schools. This repository is the web client, the API, and the database migrations.

The current tree is the foundation: tooling, a versioned API with health checks, Postgres with pgvector, and a Next.js shell. Accounts, ingestion, retrieval, and the learning interface are built on top of this layout.

## Run it locally

You need Node.js 22, pnpm 12, uv, and Docker. From a checkout:

```bash
make setup
bash scripts/dev.sh
```

`make setup` installs JavaScript and Python dependencies, creates `.env` from `.env.example` when it is missing, starts Postgres, and applies migrations.

The web app is at http://localhost:3000. The API is at http://localhost:8000. Readiness is http://localhost:8000/health/ready.

Details, the Neon connection, and the individual commands are in [docs/setup.md](docs/setup.md).

## Common commands

| Command                | What it does                                          |
| ---------------------- | ----------------------------------------------------- |
| `make setup`           | Install dependencies, start Postgres, migrate         |
| `bash scripts/dev.sh`  | API with reload, and the Next.js dev server           |
| `make test`            | Migrate, then run the API tests and workspace tests   |
| `make lint`            | Ruff, ESLint, and Prettier                            |
| `make typecheck`       | mypy and TypeScript                                   |
| `make generate-client` | Refresh `packages/api-client` from the OpenAPI schema |

Python dependencies are pinned in `apps/api/uv.lock`. JavaScript dependencies are pinned in `pnpm-lock.yaml`.

## Project layout

```text
apps/api                  FastAPI application
apps/web                  Next.js application
packages/api-client       TypeScript client generated from OpenAPI
packages/config           Shared ESLint, TypeScript, and theme entry
data/corpus               Source PDFs, git-ignored
data/glossary             English to Kinyarwanda terminology
data/sequences            Learning sequences
prompts                   Versioned tutor prompts
infra                     Docker image and Compose
docs                      Setup and design notes
```

The API package is `tutor_api`. Settings come from the environment and from `.env`. See `.env.example`.

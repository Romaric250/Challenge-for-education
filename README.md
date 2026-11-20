# Rwanda AI Tutor

Curriculum-grounded tutor for Rwandan secondary schools. This repository is the web client, the API, and the database migrations.

Students sign in with a school code, ask questions, and get answers that cite the ingested curriculum. Teachers manage classes. Admins ingest PDFs and choose the model provider. The interface is in English and Kinyarwanda.

## Run it locally

You need Node.js 22, pnpm 12, uv, and Docker. From a checkout:

```bash
make setup
bash scripts/dev.sh
```

`make setup` installs JavaScript and Python dependencies, creates `.env` from `.env.example` when it is missing, starts Postgres, and applies migrations.

Seed a demo school and a short original mathematics booklet:

```bash
uv run --directory apps/api python -m tutor_api.cli.seed_demo
```

Sign in at http://localhost:3000 as school `demo`, username `student`, password `orchard-cedar-19`. The teacher account is `teacher` / `orchard-maple-19`.

To create the first real admin instead, set `SEED_ADMIN_SCHOOL_CODE`, `SEED_ADMIN_USERNAME`, and `SEED_ADMIN_PASSWORD`, then run `uv run --directory apps/api python -m tutor_api.cli.seed_admin`.

The web app is at http://localhost:3000. The API is at http://localhost:8000. Readiness is http://localhost:8000/health/ready. Set `JWT_SECRET` before starting the API. The value in `.env.example` is for local use only.

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

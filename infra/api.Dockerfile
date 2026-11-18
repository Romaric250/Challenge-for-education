FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /bin/

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/uv.lock ./
COPY apps/api/src ./src
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./alembic.ini
COPY infra/api-entrypoint.sh /entrypoint.sh

RUN uv sync --frozen --no-dev \
    && chmod +x /entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

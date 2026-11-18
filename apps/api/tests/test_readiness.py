import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from tutor_api.core.settings import Settings, get_settings
from tutor_api.db.constants import DEFAULT_EMBEDDING_DIMENSION
from tutor_api.db.engine import create_database_engine
from tutor_api.main import create_app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_baseline_records_extension_and_dimension() -> None:
    engine = create_database_engine(get_settings())
    try:
        async with engine.connect() as connection:
            extension = await connection.scalar(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            dimension = await connection.scalar(
                text("SELECT value FROM schema_meta WHERE key = 'embedding_dimension'")
            )
    finally:
        await engine.dispose()
    assert extension == "vector"
    assert dimension == str(DEFAULT_EMBEDDING_DIMENSION)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_updated_at_trigger_advances_the_timestamp() -> None:
    engine = create_database_engine(get_settings())
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                before = await connection.execute(
                    text("SELECT updated_at FROM schema_meta WHERE key = 'embedding_dimension'")
                )
                previous = before.scalar_one()
                await asyncio.sleep(0.02)
                await connection.execute(
                    text("UPDATE schema_meta SET value = value WHERE key = 'embedding_dimension'")
                )
                after = await connection.execute(
                    text("SELECT updated_at FROM schema_meta WHERE key = 'embedding_dimension'")
                )
                current = after.scalar_one()
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
    assert current > previous


@pytest.mark.integration
def test_readiness_reports_database_and_unconfigured_provider(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"]["status"] == "up"
    assert body["checks"]["provider"]["status"] == "not_configured"


def test_readiness_fails_when_the_database_is_down() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+asyncpg://tutor:tutor@127.0.0.1:1/tutor",
        database_connect_timeout_seconds=1,
        log_level="WARNING",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"]["status"] == "down"

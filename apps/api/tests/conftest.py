import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://tutor:tutor@localhost:5432/tutor",
)
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("JWT_SECRET", "test-secret-key-with-32-characters")

if os.environ.get("APP_ENV") == "production":
    raise RuntimeError("Refusing to run tests when APP_ENV is production")

from tutor_api.core.settings import Settings, get_settings
from tutor_api.main import create_app


@pytest.fixture
def settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client

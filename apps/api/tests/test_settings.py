import pytest
from pydantic import ValidationError

from tutor_api.core.settings import Settings, get_settings
from tutor_api.db.constants import DEFAULT_EMBEDDING_DIMENSION
from tutor_api.db.engine import asyncpg_connect_config


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_rejects_non_postgres_url() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="mysql://localhost/tutor")


def test_rejects_wildcard_cors_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://tutor:tutor@localhost/tutor",
            cors_origins=["*"],
        )


def test_docs_default_off_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOCS_ENABLED", raising=False)
    settings = Settings(
        _env_file=None,
        app_env="production",
        database_url="postgresql+asyncpg://tutor:tutor@localhost/tutor",
    )
    assert settings.resolved_docs_enabled() is False


def test_openai_compatible_provider_requires_base_url() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://tutor:tutor@localhost/tutor",
            llm_provider="openai_compatible",
        )


def test_default_embedding_dimension_matches_baseline() -> None:
    assert DEFAULT_EMBEDDING_DIMENSION == 1024


def test_neon_url_enables_ssl_without_libpq_params() -> None:
    url, connect_args = asyncpg_connect_config(
        "postgresql://tutor_user:secret@ep-example.neon.tech/tutor?sslmode=require&channel_binding=require"
    )
    assert url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in url
    assert "channel_binding" not in url
    assert connect_args["ssl"] is True


def test_explicit_ssl_disable() -> None:
    _url, connect_args = asyncpg_connect_config(
        "postgresql://tutor_user:secret@localhost:5432/tutor?sslmode=disable"
    )
    assert connect_args["ssl"] is False

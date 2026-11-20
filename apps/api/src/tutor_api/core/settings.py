from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import make_url

from tutor_api.db.constants import DEFAULT_EMBEDDING_DIMENSION

AppEnvironment = Literal["local", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LlmProviderName = Literal["none", "anthropic", "openai_compatible", "fake"]
EmbedderName = Literal["hashing", "openai_compatible"]
_LOCAL_JWT_SECRET = "local-development-secret-change-me"  # noqa: S105


def _env_files() -> tuple[str, ...]:
    # Developers run commands from the repository root or from apps/api.
    # The published image has neither checkout and is configured only by variables.
    candidates: list[Path] = []
    for parent in Path(__file__).resolve().parents:
        if (parent / "pnpm-workspace.yaml").is_file():
            candidates.append(parent / ".env")
            break
    candidates.append(Path.cwd() / ".env")
    unique: list[str] = []
    for candidate in candidates:
        if not candidate.is_file():
            continue
        resolved = str(candidate.resolve())
        if resolved not in unique:
            unique.append(resolved)
    return tuple(unique)


def _parse_http_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError("must be an http or https URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("must not include credentials")
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("must be an origin without a path or query")
    return value.strip().rstrip("/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnvironment = "local"
    app_name: str = "Rwanda AI Tutor"
    log_level: LogLevel = "INFO"
    log_json: bool | None = None
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    trust_proxy: bool = False

    database_url: str
    database_echo: bool = False
    database_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=30)

    # Recorded by migration 0001_enable_pgvector. Changing it needs a new migration
    # and a re-embed of every chunk.
    embedding_dimension: int = Field(default=DEFAULT_EMBEDDING_DIMENSION, ge=1, le=8192)

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    docs_enabled: bool | None = None
    max_request_bytes: int = Field(default=26_214_400, ge=1_024, le=32_000_000)

    jwt_secret: SecretStr = Field(min_length=32)
    access_token_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_days: int = Field(default=7, ge=1, le=30)
    login_lockout_threshold: int = Field(default=5, ge=3, le=20)
    chat_requests_per_minute: int = Field(default=12, ge=1, le=120)
    chat_requests_per_day: int = Field(default=80, ge=1, le=2000)
    conversation_retention_days: int = Field(default=365, ge=1, le=3650)

    llm_provider: LlmProviderName = "none"
    llm_model: str = "claude-sonnet-4-5"
    llm_base_url: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    embedder: EmbedderName = "hashing"
    embedding_model: str = "BAAI/bge-m3"
    embedding_base_url: str | None = None
    embedding_api_key: SecretStr | None = None
    relevance_threshold: float = Field(default=0.2, gt=0, le=1)
    retrieval_limit: int = Field(default=8, ge=1, le=20)
    context_token_budget: int = Field(default=1800, ge=200, le=8000)
    ocr_confidence_threshold: float = Field(default=0.55, gt=0, le=1)
    readiness_timeout_seconds: float = Field(default=2.0, gt=0, le=10)

    @field_validator("log_level", mode="before")
    @classmethod
    def uppercase_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.upper()
        return value

    @field_validator("database_url")
    @classmethod
    def require_postgres(cls, value: str) -> str:
        driver = make_url(value).drivername
        if driver not in {"postgresql", "postgres", "postgresql+asyncpg"}:
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return value

    @field_validator("cors_origins")
    @classmethod
    def require_explicit_origins(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("At least one CORS origin is required")
        cleaned = [_parse_http_url(origin) for origin in values]
        if any(origin == "*" for origin in cleaned):
            raise ValueError("CORS origins cannot include a wildcard")
        return cleaned

    @field_validator("llm_base_url", "anthropic_base_url", "embedding_base_url")
    @classmethod
    def require_http_provider_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _parse_http_url(value)

    @model_validator(mode="after")
    def require_provider_configuration(self) -> Self:
        if self.llm_provider == "openai_compatible" and self.llm_base_url is None:
            raise ValueError("LLM_BASE_URL is required when LLM_PROVIDER is openai_compatible")
        if self.embedder == "openai_compatible" and self.embedding_base_url is None:
            raise ValueError("EMBEDDING_BASE_URL is required when EMBEDDER is openai_compatible")
        if self.llm_provider == "fake" and self.app_env != "test":
            raise ValueError("LLM_PROVIDER=fake is only available when APP_ENV is test")
        if self.app_env == "production" and self.jwt_secret.get_secret_value() == _LOCAL_JWT_SECRET:
            raise ValueError("JWT_SECRET must be changed in production")
        return self

    def resolved_docs_enabled(self) -> bool:
        if self.docs_enabled is None:
            return self.app_env != "production"
        return self.docs_enabled

    def use_json_logs(self) -> bool:
        if self.log_json is None:
            return self.app_env == "production"
        return self.log_json

    def provider_probe_url(self) -> str | None:
        if self.llm_provider in {"none", "fake"}:
            return None
        if self.llm_provider == "anthropic":
            return f"{self.anthropic_base_url}/v1/models"
        if self.llm_base_url is None:
            return None
        return f"{self.llm_base_url}/models"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

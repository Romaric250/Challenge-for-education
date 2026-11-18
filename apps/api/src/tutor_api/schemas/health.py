from typing import Literal

from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    status: Literal["up", "down", "not_configured"]
    latency_ms: int | None = None
    detail: str | None = None


class ReadinessChecks(BaseModel):
    database: DependencyStatus
    provider: DependencyStatus


class ReadinessReport(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: ReadinessChecks


class LiveStatus(BaseModel):
    status: Literal["live"]


class ServiceIdentity(BaseModel):
    name: str
    version: str
    api_version: Literal["v1"] = Field(default="v1")

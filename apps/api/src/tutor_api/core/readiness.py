import asyncio

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine

from tutor_api.core.settings import Settings
from tutor_api.db.health import check_database
from tutor_api.schemas.health import DependencyStatus, ReadinessChecks, ReadinessReport


async def check_provider(settings: Settings) -> DependencyStatus:
    probe_url = settings.provider_probe_url()
    if probe_url is None:
        return DependencyStatus(status="not_configured")

    started = asyncio.get_running_loop().time()
    try:
        async with httpx.AsyncClient(timeout=settings.readiness_timeout_seconds) as client:
            response = await client.get(probe_url)
    except httpx.HTTPError:
        return DependencyStatus(status="down", detail="unreachable")

    latency_ms = int((asyncio.get_running_loop().time() - started) * 1000)
    if response.status_code >= 500:
        return DependencyStatus(
            status="down",
            latency_ms=latency_ms,
            detail=f"http_{response.status_code}",
        )
    return DependencyStatus(status="up", latency_ms=latency_ms)


async def build_readiness_report(engine: AsyncEngine, settings: Settings) -> ReadinessReport:
    database, provider = await asyncio.gather(
        check_database(engine),
        check_provider(settings),
    )
    ready = database.status == "up" and provider.status in {"up", "not_configured"}
    return ReadinessReport(
        status="ready" if ready else "not_ready",
        checks=ReadinessChecks(database=database, provider=provider),
    )

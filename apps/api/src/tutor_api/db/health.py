import time

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from tutor_api.core.logging import get_logger
from tutor_api.schemas.health import DependencyStatus

_log = get_logger(__name__)


async def check_database(engine: AsyncEngine) -> DependencyStatus:
    started = time.perf_counter()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        _log.warning("database_check_failed", error_type=exc.__class__.__name__)
        return DependencyStatus(status="down", detail=exc.__class__.__name__)
    latency_ms = int((time.perf_counter() - started) * 1000)
    return DependencyStatus(status="up", latency_ms=latency_ms)

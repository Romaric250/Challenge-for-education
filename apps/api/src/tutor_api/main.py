from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tutor_api import __version__
from tutor_api.api.exception_handlers import register_exception_handlers
from tutor_api.api.health import router as health_router
from tutor_api.api.v1.router import router as v1_router
from tutor_api.core.logging import configure_logging, get_logger
from tutor_api.core.security import (
    CsrfMiddleware,
    RequestContextMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from tutor_api.core.settings import Settings, get_settings
from tutor_api.db.engine import create_database_engine
from tutor_api.db.session import create_session_factory
from tutor_api.llm.providers import Breaker

_log = get_logger("tutor_api")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings if settings is not None else get_settings()
    configure_logging(resolved)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(resolved)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.settings = resolved
        _log.info(
            "api_started",
            env=resolved.app_env,
            docs_enabled=resolved.resolved_docs_enabled(),
            llm_provider=resolved.llm_provider,
            trust_proxy=resolved.trust_proxy,
        )
        try:
            yield
        finally:
            await engine.dispose()
            _log.info("api_stopped")

    docs_enabled = resolved.resolved_docs_enabled()
    app = FastAPI(
        title=resolved.app_name,
        version=__version__,
        docs_url="/api/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.breaker = Breaker()
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(v1_router, prefix="/api/v1")
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=resolved.max_request_bytes)
    app.add_middleware(SecurityHeadersMiddleware, settings=resolved)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(CsrfMiddleware, settings=resolved)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    return app


app = create_app()

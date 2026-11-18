from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tutor_api.core.settings import Settings

_SSL_REQUIRED = frozenset({"require", "verify-ca", "verify-full"})


def asyncpg_connect_config(database_url: str) -> tuple[str, dict[str, object]]:
    # asyncpg rejects libpq's sslmode query parameter, so it is applied as a connect argument.
    url = make_url(database_url)
    query = dict(url.query)
    sslmode = str(query.pop("sslmode", "")).lower()
    query.pop("channel_binding", None)
    if url.drivername in {"postgresql", "postgres"}:
        url = url.set(drivername="postgresql+asyncpg")
    cleaned: URL = url.set(query=query)
    connect_args: dict[str, object] = {}
    if sslmode in _SSL_REQUIRED:
        connect_args["ssl"] = True
    elif sslmode == "disable":
        connect_args["ssl"] = False
    return cleaned.render_as_string(hide_password=False), connect_args


def create_database_engine(settings: Settings) -> AsyncEngine:
    url, connect_args = asyncpg_connect_config(settings.database_url)
    connect_args["timeout"] = settings.database_connect_timeout_seconds
    return create_async_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=settings.database_echo,
    )

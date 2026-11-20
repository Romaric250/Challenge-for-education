import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import tutor_api.models as models
from tutor_api.core.settings import get_settings
from tutor_api.db.base import Base
from tutor_api.db.engine import asyncpg_connect_config
from tutor_api.models import SchemaMeta

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
if SchemaMeta.__table__.name not in target_metadata.tables:
    raise RuntimeError("SchemaMeta is not registered on the SQLAlchemy metadata")
if "users" not in target_metadata.tables or models.User.__table__.name != "users":
    raise RuntimeError("Domain models are not registered on the SQLAlchemy metadata")


def run_migrations_offline() -> None:
    url, _connect_args = asyncpg_connect_config(get_settings().database_url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    url, connect_args = asyncpg_connect_config(get_settings().database_url)
    configuration["sqlalchemy.url"] = url
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

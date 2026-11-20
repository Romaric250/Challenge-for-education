from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.api.pagination import decode_cursor
from tutor_api.models.identity import AuditLog, AuthThrottle, School, User


async def school_by_code(session: AsyncSession, code: str) -> School | None:
    return await session.scalar(select(School).where(func.lower(School.code) == code.lower()))


async def school_by_id(session: AsyncSession, school_id: UUID) -> School | None:
    return await session.get(School, school_id)


async def user_by_school_username(
    session: AsyncSession,
    school_code: str,
    username: str,
) -> User | None:
    statement = (
        select(User)
        .join(School, School.id == User.school_id)
        .where(
            func.lower(School.code) == school_code.lower(),
            func.lower(User.username) == username.lower(),
        )
    )
    return await session.scalar(statement)


async def user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(func.lower(User.email) == email.lower()))


async def throttle_row(
    session: AsyncSession,
    subject_hash: str,
    kind: str,
) -> AuthThrottle | None:
    return await session.scalar(
        select(AuthThrottle).where(
            AuthThrottle.subject_hash == subject_hash,
            AuthThrottle.kind == kind,
        )
    )


async def list_schools(
    session: AsyncSession,
    *,
    cursor: str | None,
    limit: int,
) -> list[School]:
    statement = select(School).order_by(School.created_at.desc(), School.id.desc())
    if cursor is not None:
        created_at, entity_id = decode_cursor(cursor)
        statement = statement.where(tuple_(School.created_at, School.id) < (created_at, entity_id))
    return list(await session.scalars(statement.limit(limit + 1)))


async def write_audit(
    session: AsyncSession,
    *,
    actor_id: UUID | None,
    school_id: UUID | None,
    action: str,
    target_type: str,
    target_id: str,
    detail: Mapping[str, object] | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor_id,
            school_id=school_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=dict(detail or {}),
        )
    )

from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.api.pagination import decode_cursor
from tutor_api.models.identity import ClassEnrollment, ClassGroup, User


async def user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def list_users(
    session: AsyncSession,
    *,
    school_id: UUID | None,
    role: str | None,
    teacher_id: UUID | None,
    cursor: str | None,
    limit: int,
) -> list[User]:
    statement = select(User).where(User.deleted_at.is_(None))
    if school_id is not None:
        statement = statement.where(User.school_id == school_id)
    if role is not None:
        statement = statement.where(User.role == role)
    if teacher_id is not None:
        statement = statement.join(ClassEnrollment, ClassEnrollment.student_id == User.id).join(
            ClassGroup, ClassGroup.id == ClassEnrollment.class_id
        )
        statement = statement.where(ClassGroup.teacher_id == teacher_id)
    statement = statement.order_by(User.created_at.desc(), User.id.desc())
    if cursor is not None:
        created_at, entity_id = decode_cursor(cursor)
        statement = statement.where(tuple_(User.created_at, User.id) < (created_at, entity_id))
    return list(await session.scalars(statement.limit(limit + 1)))


async def students_in_class(
    session: AsyncSession,
    class_id: UUID,
    *,
    cursor: str | None,
    limit: int,
) -> list[User]:
    statement = (
        select(User)
        .join(ClassEnrollment, ClassEnrollment.student_id == User.id)
        .where(ClassEnrollment.class_id == class_id, User.deleted_at.is_(None))
        .order_by(User.created_at.desc(), User.id.desc())
    )
    if cursor is not None:
        created_at, entity_id = decode_cursor(cursor)
        statement = statement.where(tuple_(User.created_at, User.id) < (created_at, entity_id))
    return list(await session.scalars(statement.limit(limit + 1)))


async def classes_for_actor(
    session: AsyncSession,
    *,
    school_id: UUID | None,
    teacher_id: UUID | None,
    student_id: UUID | None,
    cursor: str | None,
    limit: int,
) -> list[ClassGroup]:
    statement = select(ClassGroup)
    if student_id is not None:
        statement = statement.join(
            ClassEnrollment, ClassEnrollment.class_id == ClassGroup.id
        ).where(ClassEnrollment.student_id == student_id)
    if school_id is not None:
        statement = statement.where(ClassGroup.school_id == school_id)
    if teacher_id is not None:
        statement = statement.where(ClassGroup.teacher_id == teacher_id)
    statement = statement.order_by(ClassGroup.created_at.desc(), ClassGroup.id.desc())
    if cursor is not None:
        created_at, entity_id = decode_cursor(cursor)
        statement = statement.where(
            tuple_(ClassGroup.created_at, ClassGroup.id) < (created_at, entity_id)
        )
    return list(await session.scalars(statement.limit(limit + 1)))

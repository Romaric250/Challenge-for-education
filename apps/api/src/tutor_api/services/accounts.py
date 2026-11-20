import asyncio
import csv
import io
import re
import secrets
from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.core.errors import DomainError
from tutor_api.core.passwords import hash_password, validate_password
from tutor_api.models.identity import ClassEnrollment, ClassGroup, RefreshToken, School, User
from tutor_api.models.learning import Conversation
from tutor_api.repositories.schools import school_by_code, school_by_id, write_audit
from tutor_api.repositories.users import classes_for_actor, list_users, user_by_id
from tutor_api.schemas.accounts import (
    AccountExport,
    ClassPublic,
    ImportedStudent,
    RoleName,
    SchoolPublic,
    UserCreate,
    UserPublic,
)
from tutor_api.services.auth import new_temporary_password

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def public_user(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        school_id=user.school_id,
        role=cast(RoleName, user.role),
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        preferred_language=cast(Literal["en", "rw"], user.preferred_language),
        must_change_password=user.must_change_password,
        is_super_admin=user.is_super_admin,
        is_active=user.is_active,
    )


def public_school(school: School) -> SchoolPublic:
    return SchoolPublic(
        id=school.id,
        name=school.name,
        code=school.code,
        teacher_can_view_transcripts=school.teacher_can_view_transcripts,
    )


def public_class(group: ClassGroup) -> ClassPublic:
    return ClassPublic(
        id=group.id,
        school_id=group.school_id,
        teacher_id=group.teacher_id,
        name=group.name,
        subject_code=group.subject_code,
    )


def _forbidden(detail: str) -> DomainError:
    return DomainError(status_code=403, code="forbidden", title="Forbidden", detail=detail)


def _missing(detail: str) -> DomainError:
    return DomainError(status_code=404, code="not_found", title="Not found", detail=detail)


def assert_school_access(actor: User, school_id: UUID) -> None:
    if actor.is_super_admin or actor.school_id == school_id:
        return
    raise _forbidden("That school is outside your account.")


async def create_school(
    session: AsyncSession,
    actor: User,
    *,
    name: str,
    code: str,
) -> School:
    if not actor.is_super_admin:
        raise _forbidden("Only a super admin can create a school.")
    existing = await school_by_code(session, code)
    if existing is not None:
        raise DomainError(
            status_code=409,
            code="conflict",
            title="Conflict",
            detail="A school with that code already exists.",
        )
    school = School(name=name.strip(), code=code.lower())
    session.add(school)
    await session.flush()
    await write_audit(
        session,
        actor_id=actor.id,
        school_id=school.id,
        action="school.created",
        target_type="school",
        target_id=str(school.id),
    )
    await session.commit()
    return school


async def update_school(
    session: AsyncSession,
    actor: User,
    school_id: UUID,
    *,
    name: str | None,
    teacher_can_view_transcripts: bool | None,
) -> School:
    if actor.role != "admin" and not actor.is_super_admin:
        raise _forbidden("Only an admin can update a school.")
    assert_school_access(actor, school_id)
    school = await school_by_id(session, school_id)
    if school is None:
        raise _missing("That school does not exist.")
    if name is not None:
        school.name = name.strip()
    if teacher_can_view_transcripts is not None:
        school.teacher_can_view_transcripts = teacher_can_view_transcripts
    await write_audit(
        session,
        actor_id=actor.id,
        school_id=school.id,
        action="school.updated",
        target_type="school",
        target_id=str(school.id),
    )
    await session.commit()
    return school


async def create_user(
    session: AsyncSession,
    actor: User,
    body: UserCreate,
) -> tuple[User, str | None]:
    school_id = body.school_id or actor.school_id
    assert_school_access(actor, school_id)
    if actor.role == "student" or (actor.role == "teacher" and body.role != "student"):
        raise _forbidden("You cannot create that kind of account.")
    if body.role == "student" and body.email is not None:
        raise DomainError(
            status_code=422,
            code="validation_error",
            title="Validation failed",
            detail="Student accounts sign in with a school code and username.",
        )
    if body.email is not None and _EMAIL.fullmatch(body.email) is None:
        raise DomainError(
            status_code=422,
            code="validation_error",
            title="Validation failed",
            detail="The email address is invalid.",
        )
    if await school_by_id(session, school_id) is None:
        raise _missing("That school does not exist.")
    taken = await session.scalar(
        select(User.id).where(User.school_id == school_id, User.username == body.username.lower())
    )
    if taken is not None:
        raise DomainError(
            status_code=409,
            code="conflict",
            title="Conflict",
            detail="That username is already used in this school.",
        )
    temporary: str | None = None
    password = body.password
    if password is None:
        password = new_temporary_password(body.username)
        temporary = password
    problem = validate_password(password, username=body.username)
    if problem is not None:
        raise DomainError(
            status_code=422,
            code="weak_password",
            title="Validation failed",
            detail=problem,
        )
    user = User(
        school_id=school_id,
        role=body.role,
        username=body.username.lower(),
        email=body.email.lower() if body.email else None,
        display_name=body.display_name.strip(),
        password_hash=await asyncio.to_thread(hash_password, password),
        preferred_language=body.preferred_language,
        must_change_password=True,
        consent_recorded_at=datetime.now(UTC),
    )
    session.add(user)
    await session.flush()
    await write_audit(
        session,
        actor_id=actor.id,
        school_id=school_id,
        action="user.created",
        target_type="user",
        target_id=str(user.id),
        detail={"role": body.role},
    )
    await session.commit()
    return user, temporary


async def set_user_active(
    session: AsyncSession,
    actor: User,
    user_id: UUID,
    *,
    is_active: bool | None,
    display_name: str | None,
) -> User:
    user = await _managed_user(session, actor, user_id)
    if is_active is not None:
        user.is_active = is_active
    if display_name is not None:
        user.display_name = display_name.strip()
    await write_audit(
        session,
        actor_id=actor.id,
        school_id=user.school_id,
        action="user.updated",
        target_type="user",
        target_id=str(user.id),
    )
    await session.commit()
    return user


async def reset_password(session: AsyncSession, actor: User, user_id: UUID) -> str:
    user = await _managed_user(session, actor, user_id)
    if actor.role == "teacher":
        teaches = await session.scalar(
            select(ClassEnrollment.id)
            .join(ClassGroup, ClassGroup.id == ClassEnrollment.class_id)
            .where(ClassEnrollment.student_id == user.id, ClassGroup.teacher_id == actor.id)
        )
        if teaches is None:
            raise _forbidden("You can reset passwords only for students in your classes.")
    temporary = new_temporary_password(user.username)
    user.password_hash = await asyncio.to_thread(hash_password, temporary)
    user.must_change_password = True
    await write_audit(
        session,
        actor_id=actor.id,
        school_id=user.school_id,
        action="user.password_reset",
        target_type="user",
        target_id=str(user.id),
    )
    await session.commit()
    return temporary


async def export_account(session: AsyncSession, actor: User, user_id: UUID) -> AccountExport:
    user = await _managed_user(session, actor, user_id)
    classes = await classes_for_actor(
        session,
        school_id=user.school_id,
        teacher_id=user.id if user.role == "teacher" else None,
        student_id=user.id if user.role == "student" else None,
        cursor=None,
        limit=100,
    )
    count = await session.scalar(
        select(func.count()).select_from(Conversation).where(Conversation.student_id == user.id)
    )
    await write_audit(
        session,
        actor_id=actor.id,
        school_id=user.school_id,
        action="user.exported",
        target_type="user",
        target_id=str(user.id),
    )
    await session.commit()
    return AccountExport(
        user=public_user(user),
        classes=[public_class(group) for group in classes],
        conversation_count=int(count or 0),
        exported_at=datetime.now(UTC),
    )


async def delete_account(session: AsyncSession, actor: User, user_id: UUID) -> None:
    if actor.id == user_id:
        raise _forbidden("You cannot delete the account you are signed in with.")
    user = await _managed_user(session, actor, user_id)
    user.display_name = "Removed account"
    user.username = f"removed-{user.id.hex[:12]}"
    user.email = None
    user.password_hash = await asyncio.to_thread(hash_password, secrets.token_urlsafe(24))
    user.is_active = False
    user.is_super_admin = False
    user.deleted_at = datetime.now(UTC)
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await write_audit(
        session,
        actor_id=actor.id,
        school_id=user.school_id,
        action="user.deleted",
        target_type="user",
        target_id=str(user.id),
    )
    await session.commit()


async def visible_users(
    session: AsyncSession,
    actor: User,
    *,
    school_id: UUID | None,
    role: str | None,
    cursor: str | None,
    limit: int,
) -> list[User]:
    if actor.role == "student":
        raise _forbidden("Students cannot list accounts.")
    teacher_id = None
    scoped_school: UUID | None = actor.school_id
    if actor.is_super_admin:
        scoped_school = school_id
    elif school_id is not None and school_id != actor.school_id:
        raise _forbidden("That school is outside your account.")
    if actor.role == "teacher":
        teacher_id = actor.id
        role = "student"
    return await list_users(
        session,
        school_id=scoped_school,
        role=role,
        teacher_id=teacher_id,
        cursor=cursor,
        limit=limit,
    )


async def create_class(
    session: AsyncSession,
    actor: User,
    *,
    name: str,
    subject_code: str,
    teacher_id: UUID | None,
) -> ClassGroup:
    if actor.role == "student":
        raise _forbidden("Students cannot create a class.")
    assigned = actor.id if actor.role == "teacher" else teacher_id
    if assigned is None:
        raise DomainError(
            status_code=422,
            code="validation_error",
            title="Validation failed",
            detail="Choose the teacher for this class.",
        )
    teacher = await user_by_id(session, assigned)
    if teacher is None or teacher.role != "teacher" or teacher.deleted_at is not None:
        raise _missing("That teacher does not exist.")
    assert_school_access(actor, teacher.school_id)
    if actor.role == "teacher" and teacher.id != actor.id:
        raise _forbidden("You can create classes only for yourself.")
    group = ClassGroup(
        school_id=teacher.school_id,
        teacher_id=teacher.id,
        name=name.strip(),
        subject_code=subject_code,
    )
    session.add(group)
    await session.flush()
    await write_audit(
        session,
        actor_id=actor.id,
        school_id=group.school_id,
        action="class.created",
        target_type="class",
        target_id=str(group.id),
    )
    await session.commit()
    return group


async def enroll_student(
    session: AsyncSession,
    actor: User,
    class_id: UUID,
    student_id: UUID,
) -> None:
    group = await _class_for_manager(session, actor, class_id)
    student = await user_by_id(session, student_id)
    if (
        student is None
        or student.role != "student"
        or student.school_id != group.school_id
        or student.deleted_at is not None
    ):
        raise _missing("That student does not exist in this school.")
    existing = await session.scalar(
        select(ClassEnrollment.id).where(
            ClassEnrollment.class_id == group.id,
            ClassEnrollment.student_id == student.id,
        )
    )
    if existing is not None:
        return
    session.add(ClassEnrollment(class_id=group.id, student_id=student.id))
    await write_audit(
        session,
        actor_id=actor.id,
        school_id=group.school_id,
        action="class.enrolled",
        target_type="class",
        target_id=str(group.id),
        detail={"student_id": str(student.id)},
    )
    await session.commit()


async def import_students(
    session: AsyncSession,
    actor: User,
    class_id: UUID,
    payload: str,
) -> list[ImportedStudent]:
    group = await _class_for_manager(session, actor, class_id)
    reader = csv.DictReader(io.StringIO(payload))
    if reader.fieldnames is None or not {"username", "display_name"}.issubset(reader.fieldnames):
        raise DomainError(
            status_code=422,
            code="validation_error",
            title="Validation failed",
            detail="The CSV must include username and display_name columns.",
        )
    created: list[ImportedStudent] = []
    for line_number, row in enumerate(reader, start=2):
        username = (row.get("username") or "").strip().lower()
        display_name = (row.get("display_name") or "").strip()
        if not username and not display_name:
            continue
        if not re.fullmatch(r"[a-z0-9._-]{2,64}", username) or not display_name:
            raise DomainError(
                status_code=422,
                code="validation_error",
                title="Validation failed",
                detail=f"Row {line_number} has an invalid username or display name.",
            )
        taken = await session.scalar(
            select(User.id).where(User.school_id == group.school_id, User.username == username)
        )
        if taken is not None:
            raise DomainError(
                status_code=409,
                code="conflict",
                title="Conflict",
                detail=f"Row {line_number} uses a username that already exists.",
            )
        temporary = new_temporary_password(username)
        user = User(
            school_id=group.school_id,
            role="student",
            username=username,
            display_name=display_name,
            password_hash=await asyncio.to_thread(hash_password, temporary),
            must_change_password=True,
            consent_recorded_at=datetime.now(UTC),
        )
        session.add(user)
        await session.flush()
        session.add(ClassEnrollment(class_id=group.id, student_id=user.id))
        created.append(
            ImportedStudent(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                temporary_password=temporary,
            )
        )
    await write_audit(
        session,
        actor_id=actor.id,
        school_id=group.school_id,
        action="class.imported",
        target_type="class",
        target_id=str(group.id),
        detail={"count": len(created)},
    )
    await session.commit()
    return created


async def _managed_user(session: AsyncSession, actor: User, user_id: UUID) -> User:
    if actor.role == "student":
        raise _forbidden("You cannot manage accounts.")
    user = await user_by_id(session, user_id)
    if user is None or user.deleted_at is not None:
        raise _missing("That account does not exist.")
    assert_school_access(actor, user.school_id)
    if actor.role == "teacher" and user.role != "student":
        raise _forbidden("Teachers can manage student accounts only.")
    return user


async def _class_for_manager(session: AsyncSession, actor: User, class_id: UUID) -> ClassGroup:
    group = await session.get(ClassGroup, class_id)
    if group is None:
        raise _missing("That class does not exist.")
    assert_school_access(actor, group.school_id)
    if actor.role == "teacher" and group.teacher_id != actor.id:
        raise _forbidden("That class belongs to another teacher.")
    if actor.role == "student":
        raise _forbidden("Students cannot change a class.")
    return group


async def update_profile(
    session: AsyncSession,
    user: User,
    *,
    display_name: str | None,
    preferred_language: str | None,
) -> User:
    if display_name is not None:
        user.display_name = display_name.strip()
    if preferred_language is not None:
        user.preferred_language = preferred_language
    await session.commit()
    return user


async def record_consent(session: AsyncSession, user: User) -> User:
    user.consent_recorded_at = datetime.now(UTC)
    await session.commit()
    return user

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.api.deps import require_ready_user
from tutor_api.api.pagination import encode_cursor
from tutor_api.core.errors import DomainError
from tutor_api.db.session import get_db_session
from tutor_api.models.identity import ClassEnrollment, ClassGroup, School, User
from tutor_api.repositories.schools import list_schools, school_by_id
from tutor_api.repositories.users import classes_for_actor, students_in_class
from tutor_api.schemas.accounts import (
    AccountExport,
    ClassCreate,
    ClassPage,
    ClassPublic,
    EnrollRequest,
    ImportResult,
    PasswordResetResult,
    SchoolCreate,
    SchoolPage,
    SchoolPublic,
    SchoolUpdate,
    UserCreate,
    UserCreated,
    UserPage,
    UserPublic,
    UserUpdate,
)
from tutor_api.services.accounts import (
    assert_school_access,
    create_class,
    create_school,
    create_user,
    delete_account,
    enroll_student,
    export_account,
    import_students,
    public_class,
    public_school,
    public_user,
    reset_password,
    set_user_active,
    update_school,
    visible_users,
)

router = APIRouter(tags=["accounts"])


def _user_page(rows: list[User], limit: int) -> UserPage:
    visible = rows[:limit]
    cursor = None
    if len(rows) > limit and visible:
        last = visible[-1]
        cursor = encode_cursor(last.created_at, last.id)
    return UserPage(items=[public_user(user) for user in visible], next_cursor=cursor)


def _school_page(rows: list[School], limit: int) -> SchoolPage:
    visible = rows[:limit]
    cursor = None
    if len(rows) > limit and visible:
        last = visible[-1]
        cursor = encode_cursor(last.created_at, last.id)
    return SchoolPage(items=[public_school(school) for school in visible], next_cursor=cursor)


def _class_page(rows: list[ClassGroup], limit: int) -> ClassPage:
    visible = rows[:limit]
    cursor = None
    if len(rows) > limit and visible:
        last = visible[-1]
        cursor = encode_cursor(last.created_at, last.id)
    return ClassPage(items=[public_class(group) for group in visible], next_cursor=cursor)


@router.post("/schools", response_model=SchoolPublic)
async def create_school_route(
    body: SchoolCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> SchoolPublic:
    school = await create_school(session, actor, name=body.name, code=body.code)
    return public_school(school)


@router.get("/schools", response_model=SchoolPage)
async def list_schools_route(
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> SchoolPage:
    if actor.is_super_admin:
        rows = await list_schools(session, cursor=cursor, limit=limit)
        return _school_page(rows, limit)
    school = await school_by_id(session, actor.school_id)
    if school is None:
        return SchoolPage(items=[], next_cursor=None)
    return SchoolPage(items=[public_school(school)], next_cursor=None)


@router.patch("/schools/{school_id}", response_model=SchoolPublic)
async def update_school_route(
    school_id: UUID,
    body: SchoolUpdate,
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> SchoolPublic:
    school = await update_school(
        session,
        actor,
        school_id,
        name=body.name,
        teacher_can_view_transcripts=body.teacher_can_view_transcripts,
    )
    return public_school(school)


@router.post("/users", response_model=UserCreated)
async def create_user_route(
    body: UserCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> UserCreated:
    user, temporary = await create_user(session, actor, body)
    return UserCreated(**public_user(user).model_dump(), temporary_password=temporary)


@router.get("/users", response_model=UserPage)
async def list_users_route(
    role: str | None = None,
    school_id: UUID | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> UserPage:
    if role is not None and role not in {"admin", "teacher", "student"}:
        raise DomainError(
            status_code=422,
            code="validation_error",
            title="Validation failed",
            detail="The role filter is invalid.",
        )
    rows = await visible_users(
        session,
        actor,
        school_id=school_id,
        role=role,
        cursor=cursor,
        limit=limit,
    )
    return _user_page(rows, limit)


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user_route(
    user_id: UUID,
    body: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> UserPublic:
    user = await set_user_active(
        session,
        actor,
        user_id,
        is_active=body.is_active,
        display_name=body.display_name,
    )
    return public_user(user)


@router.post("/users/{user_id}/password-reset", response_model=PasswordResetResult)
async def reset_password_route(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> PasswordResetResult:
    temporary = await reset_password(session, actor, user_id)
    return PasswordResetResult(user_id=user_id, temporary_password=temporary)


@router.get("/users/{user_id}/export", response_model=AccountExport)
async def export_user_route(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> AccountExport:
    return await export_account(session, actor, user_id)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user_route(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> None:
    await delete_account(session, actor, user_id)


@router.post("/classes", response_model=ClassPublic)
async def create_class_route(
    body: ClassCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> ClassPublic:
    group = await create_class(
        session,
        actor,
        name=body.name,
        subject_code=body.subject_code,
        teacher_id=body.teacher_id,
    )
    return public_class(group)


@router.get("/classes", response_model=ClassPage)
async def list_classes_route(
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> ClassPage:
    school_id = None if actor.is_super_admin else actor.school_id
    teacher_id = actor.id if actor.role == "teacher" else None
    student_id = actor.id if actor.role == "student" else None
    rows = await classes_for_actor(
        session,
        school_id=school_id,
        teacher_id=teacher_id,
        student_id=student_id,
        cursor=cursor,
        limit=limit,
    )
    return _class_page(rows, limit)


@router.post("/classes/{class_id}/students", status_code=204)
async def enroll_route(
    class_id: UUID,
    body: EnrollRequest,
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> None:
    await enroll_student(session, actor, class_id, body.student_id)


@router.get("/classes/{class_id}/students", response_model=UserPage)
async def list_class_students_route(
    class_id: UUID,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> UserPage:
    group = await session.get(ClassGroup, class_id)
    if group is None:
        raise DomainError(
            status_code=404,
            code="not_found",
            title="Not found",
            detail="That class does not exist.",
        )
    assert_school_access(actor, group.school_id)
    if actor.role == "teacher" and group.teacher_id != actor.id:
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="That class belongs to another teacher.",
        )
    if actor.role == "student":
        membership = await session.scalar(
            select(ClassEnrollment.id).where(
                ClassEnrollment.class_id == group.id,
                ClassEnrollment.student_id == actor.id,
            )
        )
        if membership is None:
            raise DomainError(
                status_code=403,
                code="forbidden",
                title="Forbidden",
                detail="You are not enrolled in that class.",
            )
    rows = await students_in_class(session, group.id, cursor=cursor, limit=limit)
    return _user_page(rows, limit)


@router.post("/classes/{class_id}/students/import", response_model=ImportResult)
async def import_students_route(
    class_id: UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_ready_user),
) -> ImportResult:
    raw = await file.read()
    if len(raw) > 1_000_000:
        raise DomainError(
            status_code=413,
            code="payload_too_large",
            title="Payload too large",
            detail="The CSV is larger than 1 MB.",
        )
    try:
        payload = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise DomainError(
            status_code=422,
            code="validation_error",
            title="Validation failed",
            detail="The CSV must be UTF-8.",
        ) from exc
    created = await import_students(session, actor, class_id, payload)
    return ImportResult(created=created)

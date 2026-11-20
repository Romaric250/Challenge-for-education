from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.api.cookies import ACCESS_COOKIE
from tutor_api.core.errors import DomainError
from tutor_api.core.settings import Settings
from tutor_api.core.tokens import decode_access_token
from tutor_api.db.session import get_db_session
from tutor_api.models.identity import User


def client_address(request: Request) -> str:
    settings: Settings = request.app.state.settings
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
    if request.client is None:
        return "unknown"
    return request.client.host


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    header = request.headers.get("authorization")
    token: str | None = None
    if header is not None and header.lower().startswith("bearer "):
        token = header[7:].strip()
    else:
        token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise DomainError(
            status_code=401,
            code="unauthorized",
            title="Unauthorized",
            detail="Sign in to continue.",
        )
    settings: Settings = request.app.state.settings
    try:
        payload = decode_access_token(token, settings)
        subject = payload["sub"]
        if not isinstance(subject, str):
            raise ValueError("invalid_token")
        user_id = UUID(subject)
    except ValueError as exc:
        raise DomainError(
            status_code=401,
            code="unauthorized",
            title="Unauthorized",
            detail="Sign in to continue.",
        ) from exc
    user = await session.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise DomainError(
            status_code=401,
            code="unauthorized",
            title="Unauthorized",
            detail="Sign in to continue.",
        )
    return user


async def require_ready_user(user: User = Depends(get_current_user)) -> User:
    if user.must_change_password:
        raise DomainError(
            status_code=403,
            code="password_change_required",
            title="Forbidden",
            detail="Change the temporary password before continuing.",
        )
    return user

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.api.cookies import REFRESH_COOKIE, clear_session_cookies, set_session_cookies
from tutor_api.api.deps import client_address, get_current_user, require_ready_user
from tutor_api.core.errors import DomainError
from tutor_api.core.settings import Settings
from tutor_api.db.session import get_db_session
from tutor_api.models.identity import User
from tutor_api.schemas.accounts import UserPublic
from tutor_api.schemas.auth import (
    ConsentRequest,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdate,
    RefreshRequest,
    SessionTokens,
)
from tutor_api.services.accounts import public_user, record_consent, update_profile
from tutor_api.services.auth import change_password, login, logout, rotate_refresh

router = APIRouter(prefix="/auth", tags=["auth"])


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def _tokens(user: User, access: str, refresh: str) -> SessionTokens:
    return SessionTokens(
        access_token=access,
        refresh_token=refresh,
        must_change_password=user.must_change_password,
        user=public_user(user),
    )


@router.post("/login", response_model=SessionTokens)
async def login_route(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> SessionTokens:
    user, access, refresh = await login(session, _settings(request), body, client_address(request))
    set_session_cookies(response, _settings(request), access, refresh)
    return _tokens(user, access, refresh)


@router.post("/refresh", response_model=SessionTokens)
async def refresh_route(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> SessionTokens:
    raw = None if body is None else body.refresh_token
    if not raw:
        raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise DomainError(
            status_code=401,
            code="invalid_refresh",
            title="Unauthorized",
            detail="The refresh token is invalid.",
        )
    user, access, refresh = await rotate_refresh(session, _settings(request), raw)
    set_session_cookies(response, _settings(request), access, refresh)
    return _tokens(user, access, refresh)


@router.post("/logout", status_code=204)
async def logout_route(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    raw = None if body is None else body.refresh_token
    if not raw:
        raw = request.cookies.get(REFRESH_COOKIE)
    await logout(session, raw)
    clear_session_cookies(response, _settings(request))


@router.post("/password", response_model=SessionTokens)
async def password_route(
    body: PasswordChangeRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> SessionTokens:
    access, refresh = await change_password(
        session,
        _settings(request),
        user,
        body.current_password,
        body.new_password,
    )
    set_session_cookies(response, _settings(request), access, refresh)
    return _tokens(user, access, refresh)


@router.get("/me", response_model=UserPublic)
async def me_route(user: User = Depends(get_current_user)) -> UserPublic:
    return public_user(user)


@router.patch("/me", response_model=UserPublic)
async def update_me_route(
    body: ProfileUpdate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> UserPublic:
    updated = await update_profile(
        session,
        user,
        display_name=body.display_name,
        preferred_language=body.preferred_language,
    )
    return public_user(updated)


@router.post("/consent")
async def consent_route(
    body: ConsentRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> UserPublic:
    updated = await record_consent(session, user)
    return public_user(updated)

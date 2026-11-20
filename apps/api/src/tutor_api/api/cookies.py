from fastapi import Response

from tutor_api.core.settings import Settings

ACCESS_COOKIE = "tutor_access"
REFRESH_COOKIE = "tutor_refresh"


def set_session_cookies(
    response: Response,
    settings: Settings,
    access_token: str,
    refresh_token: str,
) -> None:
    secure = settings.app_env == "production"
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=settings.access_token_minutes * 60,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/v1/auth",
        max_age=settings.refresh_token_days * 24 * 60 * 60,
    )


def clear_session_cookies(response: Response, settings: Settings) -> None:
    secure = settings.app_env == "production"
    response.delete_cookie(ACCESS_COOKIE, path="/", secure=secure, samesite="lax", httponly=True)
    response.delete_cookie(
        REFRESH_COOKIE,
        path="/api/v1/auth",
        secure=secure,
        samesite="lax",
        httponly=True,
    )

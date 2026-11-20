import asyncio
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.core.errors import DomainError
from tutor_api.core.ids import uuid7
from tutor_api.core.passwords import hash_password, validate_password, verify_password
from tutor_api.core.settings import Settings
from tutor_api.core.tokens import (
    encode_access_token,
    hash_client_address,
    hash_refresh_secret,
    new_refresh_secret,
)
from tutor_api.models.identity import AuthThrottle, RefreshToken, User
from tutor_api.repositories.schools import (
    throttle_row,
    user_by_email,
    user_by_school_username,
    write_audit,
)
from tutor_api.schemas.auth import LoginRequest


def _invalid_credentials() -> DomainError:
    return DomainError(
        status_code=401,
        code="invalid_credentials",
        title="Unauthorized",
        detail="The school, username, or password is incorrect.",
    )


def _locked() -> DomainError:
    return DomainError(
        status_code=429,
        code="rate_limited",
        title="Too many attempts",
        detail="Sign-in is temporarily locked. Try again later.",
    )


async def _reject_if_locked(session: AsyncSession, subject_hash: str, kind: str) -> None:
    row = await throttle_row(session, subject_hash, kind)
    if row is not None and row.locked_until is not None and row.locked_until > datetime.now(UTC):
        raise _locked()


async def _record_failure(
    session: AsyncSession,
    settings: Settings,
    subject_hash: str,
    kind: str,
) -> None:
    row = await throttle_row(session, subject_hash, kind)
    if row is None:
        row = AuthThrottle(subject_hash=subject_hash, kind=kind, failures=0)
        session.add(row)
    row.failures += 1
    if row.failures >= settings.login_lockout_threshold:
        step = max(row.failures // settings.login_lockout_threshold, 1)
        seconds = min(60 * (2 ** (step - 1)), 900)
        row.locked_until = datetime.now(UTC) + timedelta(seconds=seconds)


async def _clear_failure(session: AsyncSession, subject_hash: str, kind: str) -> None:
    row = await throttle_row(session, subject_hash, kind)
    if row is not None:
        await session.delete(row)


async def issue_tokens(session: AsyncSession, settings: Settings, user: User) -> tuple[str, str]:
    access = encode_access_token(
        settings=settings,
        user_id=user.id,
        school_id=user.school_id,
        role=user.role,
        must_change_password=user.must_change_password,
    )
    raw, digest = new_refresh_secret()
    session.add(
        RefreshToken(
            user_id=user.id,
            family_id=uuid7(),
            token_hash=digest,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    await session.flush()
    return access, raw


async def login(
    session: AsyncSession,
    settings: Settings,
    body: LoginRequest,
    address: str,
) -> tuple[User, str, str]:
    ip_hash = hash_client_address(address, settings)
    account_key = (body.email or f"{body.school_code}:{body.username}").lower()
    account_hash = hash_client_address(account_key, settings)
    await _reject_if_locked(session, ip_hash, "ip")
    await _reject_if_locked(session, account_hash, "account")
    user = await _match_user(session, body)
    password_ok = False
    if user is not None:
        password_ok = await asyncio.to_thread(verify_password, body.password, user.password_hash)
    if user is None or not password_ok:
        await _record_failure(session, settings, ip_hash, "ip")
        await _record_failure(session, settings, account_hash, "account")
        await session.commit()
        raise _invalid_credentials()
    await _clear_failure(session, ip_hash, "ip")
    await _clear_failure(session, account_hash, "account")
    user.last_login_at = datetime.now(UTC)
    access, refresh = await issue_tokens(session, settings, user)
    await write_audit(
        session,
        actor_id=user.id,
        school_id=user.school_id,
        action="auth.login",
        target_type="user",
        target_id=str(user.id),
    )
    await session.commit()
    return user, access, refresh


async def _match_user(session: AsyncSession, body: LoginRequest) -> User | None:
    if body.email:
        user = await user_by_email(session, body.email)
        if user is None or user.role == "student":
            return None
    else:
        user = await user_by_school_username(
            session,
            body.school_code or "",
            body.username or "",
        )
    if user is None or not user.is_active or user.deleted_at is not None:
        return None
    return user


async def rotate_refresh(
    session: AsyncSession,
    settings: Settings,
    raw_token: str,
) -> tuple[User, str, str]:
    digest = hash_refresh_secret(raw_token)
    token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == digest).with_for_update()
    )
    if token is None or token.expires_at <= datetime.now(UTC):
        raise DomainError(
            status_code=401,
            code="invalid_refresh",
            title="Unauthorized",
            detail="The refresh token is invalid.",
        )
    if token.revoked_at is not None:
        now = datetime.now(UTC)
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == token.family_id)
            .values(revoked_at=now)
        )
        await session.commit()
        raise DomainError(
            status_code=401,
            code="refresh_reused",
            title="Unauthorized",
            detail="This session was revoked because a refresh token was reused.",
        )
    user = await session.get(User, token.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise DomainError(
            status_code=401,
            code="invalid_refresh",
            title="Unauthorized",
            detail="The refresh token is invalid.",
        )
    now = datetime.now(UTC)
    raw, digest = new_refresh_secret()
    replacement = RefreshToken(
        user_id=user.id,
        family_id=token.family_id,
        token_hash=digest,
        expires_at=now + timedelta(days=settings.refresh_token_days),
    )
    session.add(replacement)
    await session.flush()
    token.revoked_at = now
    token.replaced_by_id = replacement.id
    access = encode_access_token(
        settings=settings,
        user_id=user.id,
        school_id=user.school_id,
        role=user.role,
        must_change_password=user.must_change_password,
    )
    await session.commit()
    return user, access, raw


async def logout(session: AsyncSession, raw_token: str | None) -> None:
    if raw_token:
        token = await session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_secret(raw_token))
        )
        if token is not None:
            await session.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.family_id == token.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=datetime.now(UTC))
            )
            await write_audit(
                session,
                actor_id=token.user_id,
                school_id=None,
                action="auth.logout",
                target_type="user",
                target_id=str(token.user_id),
            )
    await session.commit()


async def change_password(
    session: AsyncSession,
    settings: Settings,
    user: User,
    current_password: str,
    new_password: str,
) -> tuple[str, str]:
    matches = await asyncio.to_thread(verify_password, current_password, user.password_hash)
    if not matches:
        raise _invalid_credentials()
    problem = validate_password(new_password, username=user.username)
    if problem is not None:
        raise DomainError(
            status_code=422,
            code="weak_password",
            title="Validation failed",
            detail=problem,
        )
    user.password_hash = await asyncio.to_thread(hash_password, new_password)
    user.must_change_password = False
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    access, refresh = await issue_tokens(session, settings, user)
    await write_audit(
        session,
        actor_id=user.id,
        school_id=user.school_id,
        action="auth.password_changed",
        target_type="user",
        target_id=str(user.id),
    )
    await session.commit()
    return access, refresh


def new_temporary_password(username: str) -> str:
    for _ in range(5):
        candidate = secrets.token_urlsafe(12)
        if validate_password(candidate, username=username) is None:
            return candidate
    return secrets.token_urlsafe(18)

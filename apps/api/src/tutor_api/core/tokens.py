import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import jwt
from jwt import InvalidTokenError

from tutor_api.core.settings import Settings

TokenKind = Literal["access", "refresh"]


def encode_access_token(
    *,
    settings: Settings,
    user_id: UUID,
    school_id: UUID,
    role: str,
    must_change_password: bool,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "school_id": str(school_id),
        "role": role,
        "must_change_password": must_change_password,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> dict[str, object]:
    try:
        payload = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"])
    except InvalidTokenError as exc:
        raise ValueError("invalid_token") from exc
    if payload.get("type") != "access" or not isinstance(payload.get("sub"), str):
        raise ValueError("invalid_token")
    return payload


def new_refresh_secret() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_refresh_secret(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_client_address(address: str, settings: Settings) -> str:
    material = f"{settings.jwt_secret.get_secret_value()}:{address}".encode()
    return hashlib.sha256(material).hexdigest()

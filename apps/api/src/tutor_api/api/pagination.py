import base64
from datetime import datetime
from uuid import UUID

from tutor_api.core.errors import DomainError


def encode_cursor(created_at: datetime, entity_id: UUID) -> str:
    raw = f"{created_at.isoformat()}|{entity_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_cursor(value: str) -> tuple[datetime, UUID]:
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")
        timestamp, entity_id = decoded.split("|", maxsplit=1)
        parsed = datetime.fromisoformat(timestamp)
        return parsed, UUID(entity_id)
    except (ValueError, UnicodeError) as exc:
        raise DomainError(
            status_code=400,
            code="bad_cursor",
            title="Bad request",
            detail="The page cursor is invalid.",
        ) from exc

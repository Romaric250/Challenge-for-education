import secrets
from datetime import UTC, datetime
from uuid import UUID


def uuid7() -> UUID:
    """Sortable identifier. Python 3.12 has no uuid.uuid7, so this follows RFC 9562."""
    timestamp = int(datetime.now(UTC).timestamp() * 1000)
    value = (timestamp & ((1 << 48) - 1)) << 80
    random_bits = int.from_bytes(secrets.token_bytes(10), "big")
    value |= 0x7 << 76
    value |= random_bits & ((1 << 76) - 1)
    value &= ~(0x3 << 62)
    value |= 0x2 << 62
    return UUID(int=value)

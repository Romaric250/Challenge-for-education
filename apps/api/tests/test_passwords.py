from uuid import RFC_4122

from tutor_api.core.ids import uuid7
from tutor_api.core.passwords import hash_password, validate_password, verify_password


def test_password_rejects_short_and_common_values() -> None:
    assert validate_password("short", username="keza") == "Use at least 10 characters."
    assert validate_password("password123", username="keza") is not None
    assert validate_password("keza-secret", username="keza") is not None


def test_password_hash_round_trip() -> None:
    stored = hash_password("classroom-key")
    assert verify_password("classroom-key", stored) is True
    assert verify_password("other-secret", stored) is False


def test_uuid7_uses_the_time_ordered_layout() -> None:
    value = uuid7()
    assert value.version == 7
    assert value.variant is RFC_4122

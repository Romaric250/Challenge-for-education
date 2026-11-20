from functools import lru_cache
from importlib.resources import files

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

_HASHER = PasswordHasher()
_MIN_LENGTH = 10


@lru_cache(maxsize=1)
def _denylist() -> frozenset[str]:
    raw = files("tutor_api.data").joinpath("password_denylist.txt").read_text(encoding="utf-8")
    return frozenset(line.strip().lower() for line in raw.splitlines() if line.strip())


def validate_password(password: str, *, username: str) -> str | None:
    if len(password) < _MIN_LENGTH:
        return "Use at least 10 characters."
    lowered = password.lower()
    if username.lower() in lowered or lowered in _denylist():
        return "Choose a password that is not a common password or your username."
    return None


def hash_password(password: str) -> str:
    return _HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _HASHER.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False

import re
from pathlib import Path

import yaml

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?:\+250|0)7\d{8}")
_NID = re.compile(r"\b\d{16}\b")


def _patterns() -> dict[str, list[str]]:
    path = _guardrail_file()
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return {}
    patterns = loaded.get("patterns")
    if not isinstance(patterns, dict):
        return {}
    cleaned: dict[str, list[str]] = {}
    for key, value in patterns.items():
        if isinstance(key, str) and isinstance(value, list):
            cleaned[key] = [item for item in value if isinstance(item, str)]
    return cleaned


def _guardrail_file() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "prompts" / "guardrails.yaml"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("prompts/guardrails.yaml")


def screen(text: str) -> str | None:
    """Return a guardrail category, or None when the message can be tutored."""
    if _EMAIL.search(text) or _PHONE.search(text) or _NID.search(text):
        return "personal_data"
    lowered = text.lower()
    patterns = _patterns()
    for phrase in patterns.get("self_harm", []):
        if phrase.lower() in lowered:
            return "self_harm"
    for phrase in patterns.get("prompt_injection", []):
        if phrase.lower() in lowered:
            return "prompt_injection"
    for phrase in patterns.get("exam_dump", []):
        if phrase.lower() in lowered:
            return "exam_dump"
    return None


def redact_personal_data(text: str) -> str:
    redacted = _EMAIL.sub("[removed]", text)
    redacted = _PHONE.sub("[removed]", redacted)
    return _NID.sub("[removed]", redacted)

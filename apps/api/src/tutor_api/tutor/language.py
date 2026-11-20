import csv
import re
from functools import lru_cache
from pathlib import Path

_KINYARWANDA = frozenset(
    {"ni", "mu", "ku", "kwa", "cyangwa", "niba", "iki", "ibi", "ari", "nta", "kandi", "cyane"}
)


def detect_language(text: str) -> str:
    words = re.findall(r"[a-z']+", text.lower())
    if not words:
        return "en"
    hits = sum(1 for word in words if word in _KINYARWANDA)
    if hits >= 2 or hits / len(words) >= 0.2:
        return "rw"
    return "en"


@lru_cache(maxsize=1)
def _glossary() -> tuple[tuple[str, str], ...]:
    path = None
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "glossary" / "mathematics.v1.csv"
        if candidate.is_file():
            path = candidate
            break
    if path is None:
        return ()
    pairs: list[tuple[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            source = (row.get("term_rw") or "").strip().lower()
            target = (row.get("term_en") or "").strip()
            if source and target:
                pairs.append((source, target))
    return tuple(pairs)


def retrieval_query(text: str) -> str:
    rewritten = text
    for source, target in _glossary():
        rewritten = re.sub(re.escape(source), target, rewritten, flags=re.IGNORECASE)
    return rewritten

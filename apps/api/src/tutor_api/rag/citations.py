import re

_CITATION = re.compile(r"\[S(\d+)\]")


def cited_markers(text: str) -> list[int]:
    return [int(match) for match in _CITATION.findall(text)]


def citations_are_grounded(text: str, source_count: int) -> bool:
    if source_count < 1 or not text.strip():
        return False
    markers = cited_markers(text)
    if not markers or any(marker < 1 or marker > source_count for marker in markers):
        return False
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        if len(sentence) >= 40 and _CITATION.search(sentence) is None:
            return False
    return True

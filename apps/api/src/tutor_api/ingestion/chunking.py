import re
from dataclasses import dataclass

_PARAGRAPH = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class ChunkDraft:
    page_start: int
    page_end: int
    content_type: str
    plain_text: str
    token_estimate: int


def estimate_tokens(text: str) -> int:
    return max(len(text) // 4, 1)


def chunk_text(
    *,
    page_number: int,
    content_type: str,
    text: str,
    token_budget: int = 500,
) -> list[ChunkDraft]:
    cleaned = text.strip()
    if not cleaned:
        return []
    if content_type in {"table", "equation", "image"}:
        return [
            ChunkDraft(
                page_start=page_number,
                page_end=page_number,
                content_type=content_type,
                plain_text=cleaned,
                token_estimate=estimate_tokens(cleaned),
            )
        ]
    paragraphs = [part.strip() for part in _PARAGRAPH.split(cleaned) if part.strip()]
    if not paragraphs:
        paragraphs = [cleaned]
    drafts: list[ChunkDraft] = []
    current: list[str] = []
    current_tokens = 0
    for paragraph in paragraphs:
        tokens = estimate_tokens(paragraph)
        if current and current_tokens + tokens > token_budget:
            drafts.append(_draft(page_number, current))
            current = current[-1:]
            current_tokens = estimate_tokens(current[0])
        current.append(paragraph)
        current_tokens += tokens
    if current:
        drafts.append(_draft(page_number, current))
    return drafts


def _draft(page_number: int, paragraphs: list[str]) -> ChunkDraft:
    text = "\n\n".join(paragraphs)
    return ChunkDraft(
        page_start=page_number,
        page_end=page_number,
        content_type="text",
        plain_text=text,
        token_estimate=estimate_tokens(text),
    )

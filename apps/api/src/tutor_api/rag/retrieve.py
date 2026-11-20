from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.models.corpus import Chunk, Document

_RRF_K = 60


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    page_start: int
    page_end: int
    content_type: str
    plain_text: str
    cosine: float
    lexical_rank: float | None
    score: float


async def retrieve(
    session: AsyncSession,
    query: str,
    query_vector: list[float],
    *,
    limit: int,
) -> list[RetrievedChunk]:
    if not query.strip():
        return []
    distance = Chunk.embedding.cosine_distance(query_vector)
    vector_rows = (
        await session.execute(
            select(Chunk.id, (1 - distance).label("cosine"))
            .where(Chunk.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )
    ).all()
    tsquery = func.plainto_tsquery("simple", query)
    rank = func.ts_rank(Chunk.search_vector, tsquery)
    lexical_rows = (
        await session.execute(
            select(Chunk.id, rank.label("rank"))
            .where(Chunk.search_vector.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(limit)
        )
    ).all()
    scores: dict[UUID, float] = {}
    cosines: dict[UUID, float] = {}
    ranks: dict[UUID, float] = {}
    for index, row in enumerate(vector_rows, start=1):
        chunk_id = row[0]
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (_RRF_K + index)
        cosines[chunk_id] = float(row[1] or 0)
    for index, row in enumerate(lexical_rows, start=1):
        chunk_id = row[0]
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (_RRF_K + index)
        ranks[chunk_id] = float(row[1] or 0)
    ordered = sorted(scores, key=lambda item: scores[item], reverse=True)[:limit]
    if not ordered:
        return []
    loaded = (
        await session.execute(
            select(Chunk, Document.title)
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.id.in_(ordered), Document.status == "ready")
        )
    ).all()
    by_id = {chunk.id: (chunk, title) for chunk, title in loaded}
    found: list[RetrievedChunk] = []
    for chunk_id in ordered:
        pair = by_id.get(chunk_id)
        if pair is None:
            continue
        chunk, title = pair
        found.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=title,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                content_type=chunk.content_type,
                plain_text=chunk.plain_text,
                cosine=cosines.get(chunk_id, 0.0),
                lexical_rank=ranks.get(chunk_id),
                score=scores[chunk_id],
            )
        )
    return found


def relevant(chunks: list[RetrievedChunk], *, threshold: float) -> bool:
    if not chunks:
        return False
    if any(chunk.lexical_rank is not None for chunk in chunks):
        return True
    return max(chunk.cosine for chunk in chunks) >= threshold

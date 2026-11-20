import asyncio
import hashlib
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.core.settings import Settings
from tutor_api.ingestion.chunking import chunk_text
from tutor_api.ingestion.embed import embed_texts
from tutor_api.ingestion.extract import chapter_spans, extract_pdf
from tutor_api.models.corpus import Chapter, Chunk, Document, DocumentPage, Subject
from tutor_api.repositories.schools import write_audit


async def ingest_pdf(
    session: AsyncSession,
    settings: Settings,
    *,
    path: Path,
    title: str,
    subject_code: str,
    subject_name: str,
    school_id: UUID | None,
    uploaded_by: UUID | None,
) -> Document:
    payload = await asyncio.to_thread(path.read_bytes)
    digest = hashlib.sha256(payload).hexdigest()
    existing = await session.scalar(select(Document).where(Document.file_hash == digest))
    if existing is not None and existing.status == "ready":
        return existing
    subject = await session.scalar(select(Subject).where(Subject.code == subject_code))
    if subject is None:
        subject = Subject(code=subject_code, name=subject_name)
        session.add(subject)
        await session.flush()
    document = existing or Document(
        school_id=school_id,
        subject_id=subject.id,
        uploaded_by=uploaded_by,
        title=title,
        source_name=path.name,
        file_hash=digest,
        status="processing",
    )
    if existing is None:
        session.add(document)
    else:
        document.status = "processing"
        document.title = title
        await session.execute(delete(Chunk).where(Chunk.document_id == document.id))
        await session.execute(delete(Chapter).where(Chapter.document_id == document.id))
        await session.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
    await session.flush()
    pages, warnings = await asyncio.to_thread(
        extract_pdf,
        path,
        ocr_threshold=settings.ocr_confidence_threshold,
    )
    spans = chapter_spans(pages)
    for page in pages:
        session.add(
            DocumentPage(
                document_id=document.id,
                page_number=page.number,
                kind=page.kind,
                text=page.text,
                ocr_confidence=page.ocr_confidence,
            )
        )
    chapter_rows: list[Chapter] = []
    for ordinal, span in enumerate(spans, start=1):
        chapter = Chapter(
            document_id=document.id,
            title=span.title,
            ordinal=ordinal,
            page_start=span.page_start,
            page_end=span.page_end,
        )
        session.add(chapter)
        chapter_rows.append(chapter)
    await session.flush()
    drafts = []
    for page in pages:
        content_type = page.kind if page.kind in {"table", "equation", "image"} else "text"
        if page.kind in {"blank", "mixed"}:
            content_type = "text"
        drafts.extend(
            chunk_text(page_number=page.number, content_type=content_type, text=page.text)
        )
    vectors = await embed_texts([draft.plain_text for draft in drafts], settings) if drafts else []
    for draft, vector in zip(drafts, vectors, strict=True):
        chapter_id = next(
            (
                chapter.id
                for chapter in chapter_rows
                if chapter.page_start <= draft.page_start <= chapter.page_end
            ),
            None,
        )
        session.add(
            Chunk(
                document_id=document.id,
                chapter_id=chapter_id,
                page_start=draft.page_start,
                page_end=draft.page_end,
                content_type=draft.content_type,
                plain_text=draft.plain_text,
                embedding=vector,
                token_estimate=draft.token_estimate,
            )
        )
    low_confidence = [
        page.number
        for page in pages
        if page.ocr_confidence is not None
        and page.ocr_confidence < settings.ocr_confidence_threshold
    ]
    document.status = "ready"
    document.page_count = len(pages)
    report: dict[str, object] = {
        "pages": len(pages),
        "chapters": len(spans),
        "chunks": len(drafts),
        "warnings": warnings,
        "low_confidence_pages": low_confidence,
        "embedder": settings.embedder,
    }
    document.report = report
    if uploaded_by is not None:
        await write_audit(
            session,
            actor_id=uploaded_by,
            school_id=school_id,
            action="document.ingested",
            target_type="document",
            target_id=str(document.id),
            detail={"file_hash": digest, "chunks": len(drafts)},
        )
    await session.commit()
    return document

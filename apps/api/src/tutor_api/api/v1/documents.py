import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.api.deps import require_ready_user
from tutor_api.core.errors import DomainError
from tutor_api.core.settings import Settings
from tutor_api.db.session import get_db_session
from tutor_api.ingestion.pipeline import ingest_pdf
from tutor_api.models.corpus import Document
from tutor_api.models.identity import User

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentPublic(BaseModel):
    id: UUID
    title: str
    source_name: str
    status: str
    page_count: int
    report: dict[str, object]


@router.get("", response_model=list[DocumentPublic])
async def list_documents(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> list[DocumentPublic]:
    statement = select(Document).order_by(Document.created_at.desc()).limit(100)
    if user.role != "admin" and not user.is_super_admin:
        statement = statement.where(Document.status == "ready")
    rows = (await session.scalars(statement)).all()
    return [_public(row) for row in rows]


@router.post("", response_model=DocumentPublic)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(min_length=1, max_length=240),
    subject_code: str = Form(default="mathematics", min_length=1, max_length=64),
    subject_name: str = Form(default="Mathematics", min_length=1, max_length=160),
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> DocumentPublic:
    if user.role != "admin" and not user.is_super_admin:
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="Only an admin can ingest a curriculum file.",
        )
    name = file.filename or "upload.pdf"
    if not name.lower().endswith(".pdf"):
        raise DomainError(
            status_code=415,
            code="unsupported_media_type",
            title="Unsupported media type",
            detail="Upload a PDF file.",
        )
    raw = await file.read()
    settings: Settings = request.app.state.settings
    with NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
        handle.write(raw)
        path = Path(handle.name)
    try:
        document = await ingest_pdf(
            session,
            settings,
            path=path,
            title=title.strip(),
            subject_code=subject_code.strip().lower(),
            subject_name=subject_name.strip(),
            school_id=None if user.is_super_admin else user.school_id,
            uploaded_by=user.id,
        )
    finally:
        await asyncio.to_thread(path.unlink, missing_ok=True)
    return _public(document)


def _public(document: Document) -> DocumentPublic:
    return DocumentPublic(
        id=document.id,
        title=document.title,
        source_name=document.source_name,
        status=document.status,
        page_count=document.page_count,
        report=document.report,
    )

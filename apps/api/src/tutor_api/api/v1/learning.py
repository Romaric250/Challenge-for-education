import json
from collections.abc import AsyncIterator
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tutor_api.api.deps import require_ready_user
from tutor_api.core.errors import DomainError
from tutor_api.core.settings import Settings
from tutor_api.db.session import get_db_session
from tutor_api.llm.providers import Breaker
from tutor_api.models.identity import ClassEnrollment, ClassGroup, School, User
from tutor_api.models.learning import Conversation, Feedback, Message, SequenceProgress
from tutor_api.repositories.schools import write_audit
from tutor_api.services.accounts import assert_school_access
from tutor_api.tutor.prompts import load_sequences
from tutor_api.tutor.turn import TutorEvent, stream_turn

router = APIRouter(tags=["learning"])


class ConversationCreate(BaseModel):
    title: str = Field(default="New lesson", min_length=1, max_length=160)


class ConversationPublic(BaseModel):
    id: UUID
    title: str
    language: str
    flagged: bool


class MessagePublic(BaseModel):
    id: UUID
    role: str
    content: str
    hint_level: int | None
    grounded: bool | None
    refused_reason: str | None
    citations: list[object]


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    action: str | None = Field(default=None, pattern=r"^(hint|full_answer|explain_en|explain_rw)$")


class FeedbackCreate(BaseModel):
    rating: Literal[-1, 1]
    comment: str | None = Field(default=None, max_length=1000)


@router.post("/conversations", response_model=ConversationPublic)
async def create_conversation(
    body: ConversationCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> ConversationPublic:
    if user.role != "student":
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="Only a student can start a lesson.",
        )
    conversation = Conversation(
        student_id=user.id,
        title=body.title.strip(),
        language=user.preferred_language,
    )
    session.add(conversation)
    await session.commit()
    return _conversation(conversation)


@router.get("/conversations", response_model=list[ConversationPublic])
async def list_conversations(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> list[ConversationPublic]:
    if user.role != "student":
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="Only a student can list their lessons.",
        )
    rows = (
        await session.scalars(
            select(Conversation)
            .where(Conversation.student_id == user.id)
            .order_by(Conversation.updated_at.desc())
            .limit(50)
        )
    ).all()
    return [_conversation(row) for row in rows]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessagePublic])
async def list_messages(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> list[MessagePublic]:
    conversation = await _visible_conversation(session, user, conversation_id)
    rows = (
        await session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
        )
    ).all()
    return [_message(row) for row in rows]


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    body: MessageCreate,
    request: Request,
    user: User = Depends(require_ready_user),
) -> StreamingResponse:
    if user.role != "student":
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="Only a student can send a lesson message.",
        )
    settings: Settings = request.app.state.settings
    breaker: Breaker = request.app.state.breaker
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory

    async def events() -> AsyncIterator[str]:
        async with factory() as session:
            stream = stream_turn(
                session,
                settings,
                breaker,
                user,
                conversation_id,
                body.content,
                body.action,
            )
            async for event in stream:
                yield _sse(event)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/messages/{message_id}/feedback", status_code=204)
async def leave_feedback(
    message_id: UUID,
    body: FeedbackCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> None:
    message = await session.get(Message, message_id)
    if message is None or message.role != "tutor":
        raise DomainError(
            status_code=404,
            code="not_found",
            title="Not found",
            detail="That tutor message does not exist.",
        )
    await _visible_conversation(session, user, message.conversation_id)
    existing = await session.scalar(
        select(Feedback).where(Feedback.message_id == message.id, Feedback.student_id == user.id)
    )
    if existing is None:
        session.add(
            Feedback(
                message_id=message.id,
                student_id=user.id,
                rating=body.rating,
                comment=body.comment,
            )
        )
    else:
        existing.rating = body.rating
        existing.comment = body.comment
    await session.commit()


@router.get("/sequences")
async def list_sequences(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> list[dict[str, object]]:
    sequences = load_sequences()
    progress_by_code: dict[str, SequenceProgress] = {}
    if user.role == "student":
        rows = (
            await session.scalars(
                select(SequenceProgress).where(SequenceProgress.student_id == user.id)
            )
        ).all()
        progress_by_code = {row.sequence_code: row for row in rows}
    enriched: list[dict[str, object]] = []
    for item in sequences:
        code = item.get("code")
        progress = progress_by_code.get(code) if isinstance(code, str) else None
        enriched.append(
            {
                **item,
                "step_index": progress.step_index if progress is not None else 0,
                "completed": bool(progress.completed) if progress is not None else False,
            }
        )
    return enriched


@router.post("/sequences/{code}/advance")
async def advance_sequence(
    code: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> dict[str, object]:
    if user.role != "student":
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="Only a student can follow a sequence.",
        )
    sequence = next((item for item in load_sequences() if item.get("code") == code), None)
    if sequence is None:
        raise DomainError(
            status_code=404,
            code="not_found",
            title="Not found",
            detail="That sequence does not exist.",
        )
    steps = sequence.get("steps")
    total = len(steps) if isinstance(steps, list) else 0
    progress = await session.scalar(
        select(SequenceProgress).where(
            SequenceProgress.student_id == user.id,
            SequenceProgress.sequence_code == code,
        )
    )
    if progress is None:
        progress = SequenceProgress(
            student_id=user.id,
            sequence_code=code,
            step_index=0 if total <= 1 else 1,
        )
        session.add(progress)
    elif progress.step_index + 1 < total:
        progress.step_index += 1
    progress.completed = total > 0 and progress.step_index >= total - 1
    await session.commit()
    return {"code": code, "step_index": progress.step_index, "completed": progress.completed}


@router.get("/teacher/transcripts", response_model=list[MessagePublic])
async def teacher_transcript(
    class_id: UUID = Query(),
    student_id: UUID = Query(),
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> list[MessagePublic]:
    if user.role != "teacher":
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="Only a teacher can open a transcript.",
        )
    school = await session.get(School, user.school_id)
    if school is None or not school.teacher_can_view_transcripts:
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="This school has not allowed teachers to read transcripts.",
        )
    group = await session.get(ClassGroup, class_id)
    if group is None or group.teacher_id != user.id:
        raise DomainError(
            status_code=404,
            code="not_found",
            title="Not found",
            detail="That class does not exist.",
        )
    enrolled = await session.scalar(
        select(ClassEnrollment.id).where(
            ClassEnrollment.class_id == group.id,
            ClassEnrollment.student_id == student_id,
        )
    )
    if enrolled is None:
        raise DomainError(
            status_code=404,
            code="not_found",
            title="Not found",
            detail="That student is not in this class.",
        )
    rows = (
        await session.scalars(
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Conversation.student_id == student_id)
            .order_by(Message.created_at.asc())
            .limit(200)
        )
    ).all()
    await write_audit(
        session,
        actor_id=user.id,
        school_id=user.school_id,
        action="transcript.viewed",
        target_type="user",
        target_id=str(student_id),
        detail={"class_id": str(class_id)},
    )
    await session.commit()
    return [_message(row) for row in rows]


async def _visible_conversation(
    session: AsyncSession,
    user: User,
    conversation_id: UUID,
) -> Conversation:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise DomainError(
            status_code=404,
            code="not_found",
            title="Not found",
            detail="That conversation does not exist.",
        )
    if user.role == "student" and conversation.student_id != user.id:
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="That conversation belongs to another student.",
        )
    if user.role != "student":
        assert_school_access(user, user.school_id)
    return conversation


def _conversation(conversation: Conversation) -> ConversationPublic:
    return ConversationPublic(
        id=conversation.id,
        title=conversation.title,
        language=conversation.language,
        flagged=conversation.flagged,
    )


def _message(message: Message) -> MessagePublic:
    return MessagePublic(
        id=message.id,
        role=message.role,
        content=message.content,
        hint_level=message.hint_level,
        grounded=message.grounded,
        refused_reason=message.refused_reason,
        citations=list(message.citations),
    )


def _sse(event: TutorEvent) -> str:
    return f"event: {event.kind}\ndata: {json.dumps(event.payload)}\n\n"

import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.core.errors import DomainError
from tutor_api.core.settings import Settings
from tutor_api.ingestion.embed import embed_texts
from tutor_api.llm.factory import estimate_cost, runtime_provider
from tutor_api.llm.providers import Breaker, Completion
from tutor_api.models.identity import User
from tutor_api.models.learning import Conversation, GuardrailEvent, MasteryState, Message
from tutor_api.rag.citations import citations_are_grounded
from tutor_api.rag.retrieve import RetrievedChunk, relevant, retrieve
from tutor_api.tutor.guardrails import redact_personal_data, screen
from tutor_api.tutor.language import detect_language, retrieval_query
from tutor_api.tutor.prompts import prompt_text, render_template

PROMPT_VERSION = "tutor.v1"


@dataclass(frozen=True)
class TutorEvent:
    kind: str
    payload: dict[str, object]


async def stream_turn(
    session: AsyncSession,
    settings: Settings,
    breaker: Breaker,
    user: User,
    conversation_id: UUID,
    content: str,
    action: str | None,
) -> AsyncIterator[TutorEvent]:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None or conversation.student_id != user.id:
        raise DomainError(
            status_code=404,
            code="not_found",
            title="Not found",
            detail="That conversation does not exist.",
        )
    await _enforce_chat_limit(session, settings, user.id)
    language = _language(content, action, user.preferred_language)
    conversation.language = language
    category = screen(content)
    stored = redact_personal_data(content) if category == "personal_data" else content.strip()
    hint_level = await _hint_level(session, conversation.id, action, category)
    session.add(Message(conversation_id=conversation.id, role="student", content=stored))
    if category in {"self_harm", "prompt_injection", "personal_data"}:
        reply = _blocked_reply(category, language)
        if category == "self_harm":
            conversation.flagged = True
        session.add(
            GuardrailEvent(
                conversation_id=conversation.id,
                user_id=user.id,
                category=category,
                action="refuse",
            )
        )
        message = await _save_tutor(
            session,
            conversation,
            reply,
            hint_level=hint_level,
            refused_reason=category,
            grounded=False,
            citations=[],
            provider=None,
            model=None,
            completion=None,
            latency_ms=0,
        )
        yield TutorEvent("token", {"text": reply})
        yield _done(message, grounded=False, refused=category)
        return
    started = time.perf_counter()
    vectors = await embed_texts([retrieval_query(content)], settings)
    chunks = await retrieve(
        session,
        retrieval_query(content),
        vectors[0],
        limit=settings.retrieval_limit,
    )
    yield TutorEvent(
        "retrieval",
        {"count": len(chunks), "latency_ms": int((time.perf_counter() - started) * 1000)},
    )
    if not relevant(chunks, threshold=settings.relevance_threshold):
        reply = _line(prompt_text("refusal.v1.txt"), language)
        message = await _save_tutor(
            session,
            conversation,
            reply,
            hint_level=hint_level,
            refused_reason="not_in_curriculum",
            grounded=False,
            citations=[],
            provider=None,
            model=None,
            completion=None,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        yield TutorEvent("token", {"text": reply})
        yield _done(message, grounded=False, refused="not_in_curriculum")
        return
    selected = _fit(chunks, settings.context_token_budget)
    sources = "\n\n".join(
        f"[S{index}]\n{chunk.plain_text}" for index, chunk in enumerate(selected, start=1)
    )
    system = render_template(
        "tutor.v1.j2",
        hint_level=hint_level,
        language_name="Kinyarwanda" if language == "rw" else "English",
        sources=sources,
    )
    try:
        provider = await runtime_provider(session, settings, breaker)
    except RuntimeError as exc:
        raise DomainError(
            status_code=503,
            code="provider_unavailable",
            title="Provider unavailable",
            detail="No model provider is configured.",
        ) from exc
    model_started = time.perf_counter()
    completion = await provider.complete(system, stored)
    grounded = citations_are_grounded(completion.text, len(selected))
    if not grounded:
        correction = await provider.complete(
            system,
            f"{stored}\n\nAdd a valid [S#] citation to every sentence.",
        )
        completion = correction
        grounded = citations_are_grounded(completion.text, len(selected))
    answer = completion.text
    if not grounded:
        answer = _passages(selected)
        grounded = False
    citations = [
        {
            "marker": f"S{index}",
            "document": chunk.document_title,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "snippet": chunk.plain_text[:240],
            "chunk_id": str(chunk.chunk_id),
        }
        for index, chunk in enumerate(selected, start=1)
    ]
    message = await _save_tutor(
        session,
        conversation,
        answer,
        hint_level=hint_level,
        refused_reason=None,
        grounded=grounded,
        citations=citations,
        provider=provider.name,
        model=provider.model,
        completion=completion,
        latency_ms=int((time.perf_counter() - model_started) * 1000),
    )
    await _record_mastery(session, user.id, selected[0].document_title)
    await session.commit()
    for slice_text in _slices(answer):
        yield TutorEvent("token", {"text": slice_text})
    yield TutorEvent("citations", {"items": citations})
    yield _done(message, grounded=grounded, refused=None)


async def _enforce_chat_limit(session: AsyncSession, settings: Settings, user_id: UUID) -> None:
    now = datetime.now(UTC)
    minute_count = await _student_messages_since(session, user_id, now - timedelta(minutes=1))
    day_count = await _student_messages_since(session, user_id, now - timedelta(days=1))
    limited = minute_count >= settings.chat_requests_per_minute
    limited = limited or day_count >= settings.chat_requests_per_day
    if limited:
        raise DomainError(
            status_code=429,
            code="rate_limited",
            title="Too many requests",
            detail="The chat limit for this account has been reached.",
        )


async def _student_messages_since(
    session: AsyncSession,
    user_id: UUID,
    since: datetime,
) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.student_id == user_id,
            Message.role == "student",
            Message.created_at >= since,
        )
    )
    return int(count or 0)


def _language(content: str, action: str | None, preferred: str) -> str:
    if action == "explain_en":
        return "en"
    if action == "explain_rw":
        return "rw"
    detected = detect_language(content)
    if detected == "rw":
        return "rw"
    return preferred if preferred in {"en", "rw"} else "en"


async def _hint_level(
    session: AsyncSession,
    conversation_id: UUID,
    action: str | None,
    category: str | None,
) -> int:
    previous = await session.scalar(
        select(func.max(Message.hint_level)).where(
            Message.conversation_id == conversation_id,
            Message.role == "tutor",
        )
    )
    level = int(previous or 0)
    if action == "hint":
        level = min(level + 1, 4)
    elif action == "full_answer":
        level = 4
    if category == "exam_dump" and action != "full_answer":
        level = min(max(level, 1), 3)
    return level


def _blocked_reply(category: str, language: str) -> str:
    if category == "self_harm":
        return _line(prompt_text("support.v1.txt"), language)
    if category == "personal_data":
        if language == "rw":
            return (
                "Ntushyiremo telefoni, imeyili, cyangwa nomero y'indangamuntu. "
                "Subiramo ikibazo utazishyiramo."
            )
        return (
            "Remove phone numbers, email addresses, and identity numbers, "
            "then ask the question again."
        )
    if language == "rw":
        return "Nshobora kugufasha kwiga ikiciro, ntushobora guhindura amabwiriza yanjye."
    return (
        "I can help you learn this subject. I cannot follow instructions to ignore the curriculum."
    )


def _line(raw: str, language: str) -> str:
    prefix = "rw: " if language == "rw" else "en: "
    for line in raw.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return raw.strip()


def _fit(chunks: list[RetrievedChunk], budget: int) -> list[RetrievedChunk]:
    selected: list[RetrievedChunk] = []
    used = 0
    for chunk in chunks:
        tokens = max(len(chunk.plain_text) // 4, 1)
        if selected and used + tokens > budget:
            break
        selected.append(chunk)
        used += tokens
    return selected or chunks[:1]


def _passages(chunks: list[RetrievedChunk]) -> str:
    lines = [
        f"{chunk.plain_text.strip()} [S{index}]" for index, chunk in enumerate(chunks, start=1)
    ]
    return "\n\n".join(lines)


def _slices(text: str) -> list[str]:
    step = 48
    return [text[index : index + step] for index in range(0, len(text), step)] or [text]


async def _save_tutor(
    session: AsyncSession,
    conversation: Conversation,
    content: str,
    *,
    hint_level: int,
    refused_reason: str | None,
    grounded: bool,
    citations: Sequence[object],
    provider: str | None,
    model: str | None,
    completion: Completion | None,
    latency_ms: int,
) -> Message:
    input_tokens = None if completion is None else completion.input_tokens
    output_tokens = None if completion is None else completion.output_tokens
    cost = None
    if model is not None and input_tokens is not None and output_tokens is not None:
        cost = estimate_cost(model, input_tokens, output_tokens)
    message = Message(
        conversation_id=conversation.id,
        role="tutor",
        content=content,
        hint_level=hint_level,
        refused_reason=refused_reason,
        grounded=grounded,
        citations=citations,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        cost_usd=cost,
        prompt_version=PROMPT_VERSION,
        telemetry={"latency_ms": latency_ms},
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


def _done(message: Message, *, grounded: bool, refused: str | None) -> TutorEvent:
    return TutorEvent(
        "done",
        {
            "message_id": str(message.id),
            "grounded": grounded,
            "refused_reason": refused,
            "hint_level": message.hint_level,
        },
    )


async def _record_mastery(session: AsyncSession, student_id: UUID, topic: str) -> None:
    state = await session.scalar(
        select(MasteryState).where(
            MasteryState.student_id == student_id,
            MasteryState.subject_code == "mathematics",
            MasteryState.topic == topic[:160],
        )
    )
    if state is None:
        session.add(
            MasteryState(
                student_id=student_id,
                subject_code="mathematics",
                topic=topic[:160],
                level=1,
                evidence_count=1,
            )
        )
        return
    state.evidence_count += 1
    state.level = min(4, 1 + state.evidence_count // 2)

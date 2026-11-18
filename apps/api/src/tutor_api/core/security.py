import json
import re
import time
import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from tutor_api.core.errors import PROBLEM_MEDIA_TYPE, problem_body
from tutor_api.core.logging import get_logger
from tutor_api.core.settings import Settings

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_log = get_logger("tutor_api.access")


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin-1")
    return None


def _request_id(scope: Scope) -> str:
    # Client-supplied ids are kept only when they cannot break a log line or a header.
    supplied = _header(scope, b"x-request-id")
    if supplied is not None and _REQUEST_ID.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = _request_id(scope)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_context(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self._app(scope, receive, send_with_context)
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            path = str(scope.get("path", ""))
            log_event = _log.debug if path.startswith("/health/") else _log.info
            log_event(
                "request_completed",
                method=str(scope.get("method", "")),
                path=path,
                status=status_code,
                duration_ms=duration_ms,
            )
            structlog.contextvars.clear_contextvars()


def security_header_pairs(settings: Settings) -> list[tuple[bytes, bytes]]:
    headers = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
    ]
    if settings.app_env == "production":
        headers.append(
            (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
        )
    return headers


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self._app = app
        self._headers = security_header_pairs(settings)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(self._headers)
                message["headers"] = headers
            await send(message)

        await self._app(scope, receive, send_with_headers)


class _BodyTooLargeError(Exception):
    pass


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        content_length = _content_length(scope)
        path = str(scope.get("path", ""))
        if content_length is None and _content_length_invalid(scope):
            await _send_problem(
                send,
                status_code=400,
                code="bad_request",
                title="Bad request",
                detail="Content-Length must be an integer.",
                instance=path,
            )
            return
        if content_length is not None and content_length > self._max_bytes:
            await _send_payload_too_large(send, path)
            return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if isinstance(body, bytes):
                    received += len(body)
                if received > self._max_bytes:
                    raise _BodyTooLargeError
            return message

        async def track_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self._app(scope, limited_receive, track_send)
        except _BodyTooLargeError:
            if response_started:
                raise
            await _send_payload_too_large(send, path)


def _content_length(scope: Scope) -> int | None:
    raw = _header(scope, b"content-length")
    if raw is None:
        return None
    try:
        parsed = int(raw)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def _content_length_invalid(scope: Scope) -> bool:
    raw = _header(scope, b"content-length")
    if raw is None:
        return False
    try:
        return int(raw) < 0
    except ValueError:
        return True


async def _send_payload_too_large(send: Send, path: str) -> None:
    await _send_problem(
        send,
        status_code=413,
        code="payload_too_large",
        title="Payload too large",
        detail="The request body exceeds the configured limit.",
        instance=path,
    )


async def _send_problem(
    send: Send,
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    instance: str,
) -> None:
    body = json.dumps(
        problem_body(
            status_code=status_code,
            code=code,
            title=title,
            detail=detail,
            instance=instance,
        )
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", PROBLEM_MEDIA_TYPE.encode()),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})

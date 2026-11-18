import pytest
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from tutor_api.core.security import RequestSizeLimitMiddleware
from tutor_api.core.settings import Settings
from tutor_api.main import create_app


def test_rejects_body_over_the_configured_limit() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://tutor:tutor@127.0.0.1:5432/tutor",
        max_request_bytes=1024,
    )
    with TestClient(create_app(settings)) as client:
        response = client.post("/health/live", content=b"x" * 1025)
    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"


@pytest.mark.asyncio
async def test_rejects_a_non_numeric_content_length() -> None:
    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    app = RequestSizeLimitMiddleware(inner, max_bytes=100)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/health/live",
        "headers": [(b"content-length", b"nope")],
    }

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    messages: list[Message] = []

    async def send(message: Message) -> None:
        messages.append(message)

    await app(scope, receive, send)
    start = next(iter(messages))
    assert start["status"] == 400

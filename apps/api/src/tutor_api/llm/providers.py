import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from tutor_api.core.errors import DomainError
from tutor_api.core.settings import Settings


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int
    output_tokens: int


class Breaker:
    def __init__(self) -> None:
        self.failures = 0
        self.open_until: datetime | None = None

    def allow(self) -> bool:
        return self.open_until is None or datetime.now(UTC) >= self.open_until

    def success(self) -> None:
        self.failures = 0
        self.open_until = None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= 3:
            self.open_until = datetime.now(UTC) + timedelta(seconds=30)


class FakeProvider:
    name = "fake"
    model = "fake"

    async def complete(self, system: str, user: str) -> Completion:
        snippet = "The curriculum passage applies."
        marker = "[S1]\n"
        start = system.find(marker)
        if start >= 0:
            rest = system[start + len(marker) :].strip()
            line = rest.split("\n", maxsplit=1)[0].strip()
            if line:
                snippet = line[:240]
        text = f"{snippet} [S1]"
        return Completion(text=text, input_tokens=len(system) // 4, output_tokens=len(text) // 4)

    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        done = await self.complete(system, user)
        yield done.text


class _HttpProvider:
    name: str
    model: str

    def __init__(self, settings: Settings, breaker: Breaker, model: str) -> None:
        self._settings = settings
        self._breaker = breaker
        self.model = model

    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        done = await self.complete(system, user)
        step = 48
        for index in range(0, len(done.text), step):
            yield done.text[index : index + step]

    async def complete(self, system: str, user: str) -> Completion:
        raise NotImplementedError

    def _guard(self) -> None:
        if not self._breaker.allow():
            raise DomainError(
                status_code=503,
                code="provider_unavailable",
                title="Provider unavailable",
                detail="The model provider is temporarily unavailable.",
            )


class AnthropicProvider(_HttpProvider):
    name = "anthropic"

    async def complete(self, system: str, user: str) -> Completion:
        self._guard()
        if self._settings.anthropic_api_key is None:
            raise _missing_key()
        payload = {
            "model": self.model,
            "max_tokens": 800,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self._settings.anthropic_api_key.get_secret_value(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = await _post_json(
            f"{self._settings.anthropic_base_url}/v1/messages",
            payload,
            headers,
            self._breaker,
        )
        parts = body.get("content")
        text = ""
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    text += part["text"]
        usage = _mapping(body.get("usage"))
        return Completion(
            text=text,
            input_tokens=_int(usage.get("input_tokens")),
            output_tokens=_int(usage.get("output_tokens")),
        )


class OpenAICompatibleProvider(_HttpProvider):
    name = "openai_compatible"

    async def complete(self, system: str, user: str) -> Completion:
        self._guard()
        if self._settings.llm_base_url is None:
            raise _missing_key()
        headers = {"content-type": "application/json"}
        if self._settings.openai_api_key is not None:
            headers["authorization"] = f"Bearer {self._settings.openai_api_key.get_secret_value()}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        body = await _post_json(
            f"{self._settings.llm_base_url}/chat/completions",
            payload,
            headers,
            self._breaker,
        )
        choices = body.get("choices")
        text = ""
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                text = message["content"]
        usage = _mapping(body.get("usage"))
        return Completion(
            text=text,
            input_tokens=_int(usage.get("prompt_tokens")),
            output_tokens=_int(usage.get("completion_tokens")),
        )


def _missing_key() -> DomainError:
    return DomainError(
        status_code=503,
        code="provider_unavailable",
        title="Provider unavailable",
        detail="The model provider is not configured.",
    )


def _int(value: object) -> int:
    if isinstance(value, int):
        return value
    return 0


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


async def _post_json(
    url: str,
    payload: object,
    headers: dict[str, str],
    breaker: Breaker,
) -> dict[str, object]:
    last_error: Exception | None = None
    for _ in range(2):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
            if response.status_code >= 500 or response.status_code == 429:
                breaker.failure()
                last_error = RuntimeError(str(response.status_code))
                continue
            response.raise_for_status()
            parsed = response.json()
            if not isinstance(parsed, dict):
                raise RuntimeError("unexpected provider payload")
            breaker.success()
            return parsed
        except (httpx.HTTPError, json.JSONDecodeError, RuntimeError) as exc:
            breaker.failure()
            last_error = exc
    raise DomainError(
        status_code=503,
        code="provider_unavailable",
        title="Provider unavailable",
        detail="The model provider did not answer.",
    ) from last_error

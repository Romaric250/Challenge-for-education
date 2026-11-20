from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.core.settings import Settings
from tutor_api.llm.providers import (
    AnthropicProvider,
    Breaker,
    FakeProvider,
    OpenAICompatibleProvider,
)
from tutor_api.models.schema_meta import SchemaMeta

_PRICES: dict[str, tuple[str, str]] = {
    "claude-sonnet-4-5": ("3", "15"),
    "claude-haiku-4-5": ("1", "5"),
    "gpt-4o-mini": ("0.15", "0.60"),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    input_price, output_price = _PRICES.get(model, ("1", "3"))
    million = Decimal(1_000_000)
    return (Decimal(input_tokens) / million * Decimal(input_price)) + (
        Decimal(output_tokens) / million * Decimal(output_price)
    )


async def runtime_provider(
    session: AsyncSession,
    settings: Settings,
    breaker: Breaker,
) -> FakeProvider | AnthropicProvider | OpenAICompatibleProvider:
    stored = await session.scalar(select(SchemaMeta.value).where(SchemaMeta.key == "llm_provider"))
    model_row = await session.scalar(select(SchemaMeta.value).where(SchemaMeta.key == "llm_model"))
    name = stored or settings.llm_provider
    model = model_row or settings.llm_model
    if name == "fake":
        return FakeProvider()
    if name == "anthropic":
        return AnthropicProvider(settings, breaker, model)
    if name == "openai_compatible":
        return OpenAICompatibleProvider(settings, breaker, model)
    raise RuntimeError("LLM_PROVIDER is none")

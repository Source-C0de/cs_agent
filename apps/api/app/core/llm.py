"""
Anthropic API client wrapper that ALWAYS:
- Reads API key from SecretStr settings.
- Sends the `anthropic-beta: zero-retention-2024-12` header so Anthropic
  stores nothing — required for our BAA.
- Uses the configured brain / router model.

We deliberately keep this thin so we can swap to PydanticAI or raw httpx later.
"""
from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import get_settings

ZERO_RETENTION_HEADER = "anthropic-beta: zero-retention-2024-12"

_client: AsyncAnthropic | None = None


def get_anthropic_client() -> AsyncAnthropic:
    """Singleton accessor; tests can monkey-patch this."""
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    api_key = settings.anthropic_api_key
    if api_key is None:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not configured. "
            "Refusing to start the agent — a brain-less agent cannot serve customers."
        )

    default_headers: dict[str, str] = {}
    if settings.anthropic_zero_retention:
        default_headers["anthropic-beta"] = "zero-retention-2024-12"

    _client = AsyncAnthropic(
        api_key=api_key.get_secret_value(),
        default_headers=default_headers,
    )
    return _client


def brain_model() -> str:
    return get_settings().anthropic_brain_model


def router_model() -> str:
    return get_settings().anthropic_router_model


async def complete(
    *,
    system: str,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    tools: list[dict] | None = None,
    **kwargs: Any,
) -> Any:
    """Thin wrapper to keep call sites consistent and easy to mock."""
    client = get_anthropic_client()
    return await client.messages.create(
        model=model or brain_model(),
        system=system,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        tools=tools or [],
        **kwargs,
    )

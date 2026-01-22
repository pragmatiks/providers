"""Anthropic Messages API resource."""

from __future__ import annotations

from typing import Any, ClassVar

from anthropic import AsyncAnthropic
from pragma_sdk import Config, Field, Outputs, Resource


class MessagesConfig(Config):
    """Configuration for Anthropic Messages API.

    Attributes:
        api_key: Anthropic API key. Use a FieldReference to inject from pragma/secret.
        model: Model identifier (e.g., "claude-sonnet-4-20250514").
        messages: Conversation messages in Anthropic format.
        max_tokens: Maximum tokens in the response.
        system: Optional system prompt.
        temperature: Optional sampling temperature (0.0-1.0).
    """

    api_key: Field[str]
    model: str
    messages: list[dict[str, Any]]
    max_tokens: int
    system: str | None = None
    temperature: float | None = None


class MessagesOutputs(Outputs):
    """Outputs from Anthropic Messages API call.

    Attributes:
        id: Anthropic message ID.
        content: Response content blocks.
        model: Model used for generation.
        stop_reason: Reason generation stopped.
        input_tokens: Tokens in input.
        output_tokens: Tokens in output.
    """

    id: str
    content: list[dict[str, Any]]
    model: str
    stop_reason: str | None
    input_tokens: int
    output_tokens: int


class Messages(Resource[MessagesConfig, MessagesOutputs]):
    """Anthropic Messages API resource.

    Wraps the Claude Messages API for reactive AI completions.
    API keys can be injected via FieldReference from pragma/secret resources.

    Lifecycle:
        - on_create: Call Messages API
        - on_update: Regenerate if config changed
        - on_delete: No-op (stateless)
    """

    provider: ClassVar[str] = "anthropic"
    resource: ClassVar[str] = "messages"

    def _get_client(self) -> AsyncAnthropic:
        """Get Anthropic async client with configured API key."""
        return AsyncAnthropic(api_key=self.config.api_key)

    async def _call_api(self) -> MessagesOutputs:
        """Call the Messages API and return outputs."""
        client = self._get_client()

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": self.config.messages,
            "max_tokens": self.config.max_tokens,
        }

        if self.config.system is not None:
            kwargs["system"] = self.config.system

        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature

        response = await client.messages.create(**kwargs)

        return MessagesOutputs(
            id=response.id,
            content=[block.model_dump() for block in response.content],
            model=response.model,
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    async def on_create(self) -> MessagesOutputs:
        """Create by calling Messages API."""
        return await self._call_api()

    async def on_update(self, previous_config: MessagesConfig) -> MessagesOutputs:
        """Update by regenerating if config changed."""
        if previous_config == self.config and self.outputs is not None:
            return self.outputs

        return await self._call_api()

    async def on_delete(self) -> None:
        """Delete is a no-op since this resource is stateless."""

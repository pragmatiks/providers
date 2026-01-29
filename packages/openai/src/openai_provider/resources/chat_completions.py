"""OpenAI Chat Completions API resource."""

from __future__ import annotations

from typing import Any, ClassVar, cast

from openai import AsyncOpenAI
from pragma_sdk import Config, Field, Outputs, Resource


class ChatCompletionsConfig(Config):
    """Configuration for OpenAI Chat Completions API.

    Attributes:
        api_key: OpenAI API key. Use a FieldReference to inject from pragma/secret.
        model: Model identifier (e.g., "gpt-4o", "gpt-4o-mini").
        messages: Conversation messages including system prompt.
        max_tokens: Optional maximum tokens in the response.
        temperature: Optional sampling temperature (0.0-2.0).
    """

    api_key: Field[str]
    model: str
    messages: list[dict[str, Any]]
    max_tokens: int | None = None
    temperature: float | None = None


class ChatCompletionsOutputs(Outputs):
    """Outputs from OpenAI Chat Completions API call.

    Attributes:
        id: OpenAI completion ID.
        content: Response content string.
        model: Model used for generation.
        finish_reason: Reason generation stopped (stop, length, content_filter).
        prompt_tokens: Tokens in prompt.
        completion_tokens: Tokens in completion.
    """

    id: str
    content: str
    model: str
    finish_reason: str | None
    prompt_tokens: int
    completion_tokens: int


class ChatCompletions(Resource[ChatCompletionsConfig, ChatCompletionsOutputs]):
    """OpenAI Chat Completions API resource.

    Wraps the OpenAI Chat Completions API for reactive AI completions.
    API keys can be injected via FieldReference from pragma/secret resources.

    Lifecycle:
        - on_create: Call Chat Completions API
        - on_update: Regenerate if config changed
        - on_delete: No-op (stateless)
    """

    provider: ClassVar[str] = "openai"
    resource: ClassVar[str] = "chat_completions"

    def _get_client(self) -> AsyncOpenAI:
        """Get OpenAI async client with configured API key."""
        return AsyncOpenAI(api_key=cast(str, self.config.api_key))

    async def _call_api(self) -> ChatCompletionsOutputs:
        """Call the Chat Completions API and return outputs."""
        async with self._get_client() as client:
            kwargs: dict[str, Any] = {
                "model": self.config.model,
                "messages": self.config.messages,
            }

            if self.config.max_tokens is not None:
                kwargs["max_tokens"] = self.config.max_tokens

            if self.config.temperature is not None:
                kwargs["temperature"] = self.config.temperature

            response = await client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            content = choice.message.content or ""

            return ChatCompletionsOutputs(
                id=response.id,
                content=content,
                model=response.model,
                finish_reason=choice.finish_reason,
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
            )

    async def on_create(self) -> ChatCompletionsOutputs:
        """Create by calling Chat Completions API."""
        return await self._call_api()

    async def on_update(self, previous_config: ChatCompletionsConfig) -> ChatCompletionsOutputs:
        """Update by regenerating if config changed."""
        if previous_config == self.config and self.outputs is not None:
            return self.outputs

        return await self._call_api()

    async def on_delete(self) -> None:
        """Delete is a no-op since this resource is stateless."""

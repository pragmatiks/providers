"""OpenAI provider for Pragmatiks.

Provides Chat Completions API resources for AI completions
with reactive dependency management.
"""

from pragma_sdk import Provider

from openai_provider.resources import (
    ChatCompletions,
    ChatCompletionsConfig,
    ChatCompletionsOutputs,
)

openai = Provider(name="openai")

# Register resources
openai.resource("chat_completions")(ChatCompletions)

__all__ = [
    "openai",
    "ChatCompletions",
    "ChatCompletionsConfig",
    "ChatCompletionsOutputs",
]

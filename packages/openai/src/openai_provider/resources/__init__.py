"""Resource definitions for openai provider.

Import and export your Resource classes here for discovery by the runtime.
"""

from openai_provider.resources.chat_completions import (
    ChatCompletions,
    ChatCompletionsConfig,
    ChatCompletionsOutputs,
)

__all__ = [
    "ChatCompletions",
    "ChatCompletionsConfig",
    "ChatCompletionsOutputs",
]

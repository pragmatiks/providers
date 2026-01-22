"""Anthropic provider for Pragmatiks.

Provides Claude Messages API resources for AI completions
with reactive dependency management.
"""

from pragma_sdk import Provider

from anthropic_provider.resources import Messages, MessagesConfig, MessagesOutputs

anthropic = Provider(name="anthropic")

# Register resources
anthropic.resource("messages")(Messages)

__all__ = [
    "anthropic",
    "Messages",
    "MessagesConfig",
    "MessagesOutputs",
]

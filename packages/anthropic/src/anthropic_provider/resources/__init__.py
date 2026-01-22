"""Resource definitions for anthropic provider.

Import and export your Resource classes here for discovery by the runtime.
"""

from anthropic_provider.resources.messages import (
    Messages,
    MessagesConfig,
    MessagesOutputs,
)

__all__ = [
    "Messages",
    "MessagesConfig",
    "MessagesOutputs",
]

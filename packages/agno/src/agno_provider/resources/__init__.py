"""Resource definitions for agno provider."""

from agno_provider.resources.agent import (
    Agent,
    AgentConfig,
    AgentOutputs,
)
from agno_provider.resources.db import (
    DbPostgres,
    DbPostgresConfig,
    DbPostgresOutputs,
)
from agno_provider.resources.models import (
    AnthropicModel,
    AnthropicModelConfig,
    AnthropicModelOutputs,
    OpenAIModel,
    OpenAIModelConfig,
    OpenAIModelOutputs,
)
from agno_provider.resources.prompt import (
    Prompt,
    PromptConfig,
    PromptOutputs,
)
from agno_provider.resources.tools import (
    ToolsWebSearch,
    ToolsWebSearchConfig,
    ToolsWebSearchOutputs,
)


__all__ = [
    "Agent",
    "AgentConfig",
    "AgentOutputs",
    "AnthropicModel",
    "AnthropicModelConfig",
    "AnthropicModelOutputs",
    "DbPostgres",
    "DbPostgresConfig",
    "DbPostgresOutputs",
    "OpenAIModel",
    "OpenAIModelConfig",
    "OpenAIModelOutputs",
    "Prompt",
    "PromptConfig",
    "PromptOutputs",
    "ToolsWebSearch",
    "ToolsWebSearchConfig",
    "ToolsWebSearchOutputs",
]

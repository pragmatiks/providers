"""Abstract base class for Agno model resources.

Provides a common interface for all model resources (OpenAI, Anthropic, etc.)
so dependent resources can accept any model type.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from pragma_sdk import Config, Outputs

from agno_provider.resources.base import AgnoResource, AgnoSpec


if TYPE_CHECKING:
    from agno.models.base import Model as AgnoModel


class ModelConfig(Config):
    """Base configuration for all model resources.

    Attributes:
        id: The model identifier (e.g., "gpt-4o", "claude-sonnet-4-20250514").
    """

    id: str


class ModelOutputs(Outputs):
    """Base outputs for all model resources.

    Concrete model resources extend this with their spec field.
    """


class Model[ModelConfigT: ModelConfig, ModelOutputsT: ModelOutputs, SpecT: AgnoSpec, ModelT: "AgnoModel"](
    AgnoResource[ModelConfigT, ModelOutputsT, SpecT], ABC
):
    """Abstract base for Agno model resources.

    Concrete model resources must implement from_spec() to reconstruct
    the Agno model instance from a serialized specification.

    Type Parameters:
        ModelConfigT: The config type for this model resource.
        ModelT: The Agno model type returned by from_spec().
    """

    provider: ClassVar[str] = "agno"

    @abstractmethod
    async def on_create(self) -> ModelOutputsT:
        """Create returns serializable outputs with spec."""
        ...

    @abstractmethod
    async def on_update(self, previous_config: ModelConfigT) -> ModelOutputsT:
        """Update returns serializable outputs with spec."""
        ...

    async def on_delete(self) -> None:
        """Delete is a no-op since model resources are stateless."""


def model_from_spec(
    spec: OpenAIModelSpec | AnthropicModelSpec,
) -> AgnoModel:
    """Factory: create model from spec based on type.

    Args:
        spec: The model specification (OpenAI or Anthropic).

    Returns:
        Configured Agno model instance.

    Raises:
        TypeError: If spec type is unknown.
    """
    from agno_provider.resources.models.anthropic import AnthropicModel, AnthropicModelSpec  # noqa: PLC0415
    from agno_provider.resources.models.openai import OpenAIModel, OpenAIModelSpec  # noqa: PLC0415

    if isinstance(spec, OpenAIModelSpec):
        return OpenAIModel.from_spec(spec)

    if isinstance(spec, AnthropicModelSpec):
        return AnthropicModel.from_spec(spec)

    msg = f"Unknown model spec type: {type(spec)}"
    raise TypeError(msg)


if TYPE_CHECKING:
    from agno_provider.resources.models.anthropic import AnthropicModelSpec
    from agno_provider.resources.models.openai import OpenAIModelSpec

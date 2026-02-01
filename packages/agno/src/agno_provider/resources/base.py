"""Base classes for agno provider resources with spec pattern."""

from __future__ import annotations

from typing import TypeVar

from pragma_sdk import Config, Outputs, Resource
from pydantic import BaseModel


class AgnoSpec(BaseModel):
    """Base class for agno provider specs.

    Specs are serializable specifications that contain all values
    needed to reconstruct Agno SDK objects at runtime.
    """


ConfigT = TypeVar("ConfigT", bound=Config)
OutputT = TypeVar("OutputT", bound=Outputs)
SpecT = TypeVar("SpecT", bound=AgnoSpec)


class AgnoResource[ConfigT: Config, OutputT: Outputs, SpecT: AgnoSpec](Resource[ConfigT, OutputT]):
    """Base class for agno provider resources with spec pattern.

    All agno resources follow the spec pattern:
    - _build_spec() creates a serializable specification
    - from_spec() reconstructs Agno SDK objects from the spec
    - Outputs contain the spec for runtime reconstruction

    Note: _build_spec and from_spec are not abstract methods because:
    - Some resources need async _build_spec (to resolve dependencies)
    - Return types vary significantly between resources
    """

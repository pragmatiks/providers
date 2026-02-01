"""Agno tools/function resource for custom Python function tools."""

from __future__ import annotations

import inspect
from typing import Any, ClassVar

from agno.tools.function import Function
from pragma_sdk import Config, Outputs, Resource
from pydantic import model_validator


class FunctionParameter(Config):
    """Schema for a function parameter.

    Attributes:
        name: Parameter name.
        type: JSON Schema type (string, integer, number, boolean, array, object).
        description: Description of the parameter.
        required: Whether the parameter is required.
        default: Default value if not provided.
        enum: List of allowed values.
        items: Schema for array items (when type is array).
    """

    name: str
    type: str = "string"
    description: str | None = None
    required: bool = False
    default: Any = None
    enum: list[Any] | None = None
    items: dict[str, Any] | None = None


class ToolsFunctionConfig(Config):
    """Configuration for a custom function tool.

    Attributes:
        name: Function name used by the model.
        description: Description of what the function does.
        parameters: List of function parameters with their schemas.
        code: Python code for the function body.
        strict: Whether to enforce strict parameter validation.
        instructions: Optional instructions for using the tool.
        show_result: Whether to show the function result to the user.
        stop_after_tool_call: Whether to stop the agent after this tool is called.
        requires_confirmation: Whether to require user confirmation before execution.
        cache_results: Whether to cache function results.
        cache_ttl: Cache time-to-live in seconds.
    """

    name: str
    description: str | None = None
    parameters: list[FunctionParameter] = []
    code: str | None = None
    strict: bool | None = None
    instructions: str | None = None
    show_result: bool = True
    stop_after_tool_call: bool = False
    requires_confirmation: bool = False
    cache_results: bool = False
    cache_ttl: int = 3600

    @model_validator(mode="after")
    def validate_config(self) -> ToolsFunctionConfig:
        """Validate the function configuration.

        Returns:
            The validated config instance.

        Raises:
            ValueError: If function or parameter names are not valid Python identifiers.
        """
        if not self.name or not self.name.isidentifier():
            msg = f"Function name '{self.name}' is not a valid Python identifier"
            raise ValueError(msg)

        for param in self.parameters:
            if not param.name.isidentifier():
                msg = f"Parameter name '{param.name}' is not a valid Python identifier"
                raise ValueError(msg)

        return self


class ToolsFunctionOutputs(Outputs):
    """Outputs from tools/function resource.

    Attributes:
        name: Function name.
        description: Function description.
        parameters_schema: JSON Schema for the tool parameters.
    """

    name: str
    description: str | None
    parameters_schema: dict[str, Any]


class ToolsFunction(Resource[ToolsFunctionConfig, ToolsFunctionOutputs]):
    """Custom Python function tool resource.

    Stateless resource that wraps function tool configuration. Dependent
    resources (e.g., agno/agent) can call function() to get the Agno
    Function instance.

    The code field contains Python code that will be executed in the
    agent container context. Parameters are passed as local variables.

    Lifecycle:
        - on_create: Validate and return metadata
        - on_update: Re-validate with new config
        - on_delete: No-op (stateless)
    """

    provider: ClassVar[str] = "agno"
    resource: ClassVar[str] = "tools/function"

    def _build_json_schema(self) -> dict[str, Any]:
        """Build JSON Schema from parameter definitions.

        Returns:
            JSON Schema object for function parameters.
        """
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.config.parameters:
            prop: dict[str, Any] = {"type": param.type}

            if param.description:
                prop["description"] = param.description

            if param.default is not None:
                prop["default"] = param.default

            if param.enum:
                prop["enum"] = param.enum

            if param.items and param.type == "array":
                prop["items"] = param.items

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }

        if required:
            schema["required"] = required

        return schema

    def _build_outputs(self) -> ToolsFunctionOutputs:
        """Build outputs from current config.

        Returns:
            ToolsFunctionOutputs with function metadata.
        """
        return ToolsFunctionOutputs(
            name=self.config.name,
            description=self.config.description,
            parameters_schema=self._build_json_schema(),
        )

    def _create_entrypoint(self) -> Any:
        """Create a callable entrypoint from the code string.

        Returns:
            Callable function that executes the code.
        """
        if not self.config.code:
            return None

        param_names = [p.name for p in self.config.parameters]
        code = self.config.code

        def entrypoint(**kwargs: Any) -> Any:
            local_vars = dict(kwargs)
            exec(code, {}, local_vars)  # noqa: S102
            return local_vars.get("result")

        entrypoint.__name__ = self.config.name
        entrypoint.__doc__ = self.config.description

        params = [inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY) for name in param_names]
        entrypoint.__signature__ = inspect.Signature(params)  # type: ignore[attr-defined]

        return entrypoint

    def function(self) -> Function:
        """Returns the configured Agno Function instance.

        Called by dependent resources (e.g., agno/agent) that need
        the actual Function object for their tools list.

        Returns:
            Agno Function instance configured from this resource.
        """
        schema = self._build_json_schema()
        entrypoint = self._create_entrypoint()

        return Function(
            name=self.config.name,
            description=self.config.description,
            parameters=schema,
            entrypoint=entrypoint,
            strict=self.config.strict,
            instructions=self.config.instructions,
            show_result=self.config.show_result,
            stop_after_tool_call=self.config.stop_after_tool_call,
            requires_confirmation=self.config.requires_confirmation,
            cache_results=self.config.cache_results,
            cache_ttl=self.config.cache_ttl,
        )

    async def on_create(self) -> ToolsFunctionOutputs:
        """Create resource and return metadata.

        Returns:
            ToolsFunctionOutputs with function name and schema.
        """
        return self._build_outputs()

    async def on_update(self, previous_config: ToolsFunctionConfig) -> ToolsFunctionOutputs:  # noqa: ARG002
        """Update resource and return metadata.

        Args:
            previous_config: The previous configuration (unused for stateless resource).

        Returns:
            ToolsFunctionOutputs with updated function metadata.
        """
        return self._build_outputs()

    async def on_delete(self) -> None:
        """Delete is a no-op since this resource is stateless."""

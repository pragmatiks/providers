"""Tests for Agno tools/function resource."""

from __future__ import annotations

import pytest
from agno.tools.function import Function
from pragma_sdk.provider import ProviderHarness
from pydantic import ValidationError

from agno_provider import (
    ToolsFunction,
    ToolsFunctionConfig,
    ToolsFunctionOutputs,
)
from agno_provider.resources.tools.function import FunctionParameter


async def test_create_minimal_config(harness: ProviderHarness) -> None:
    """on_create with minimal config returns metadata."""
    config = ToolsFunctionConfig(name="simple_function")

    result = await harness.invoke_create(ToolsFunction, name="simple", config=config)

    assert result.success
    assert result.outputs is not None
    assert result.outputs.name == "simple_function"
    assert result.outputs.description is None
    assert result.outputs.parameters_schema == {"type": "object", "properties": {}}


async def test_create_with_description(harness: ProviderHarness) -> None:
    """on_create includes description in outputs."""
    config = ToolsFunctionConfig(
        name="search_web",
        description="Search the web for information",
    )

    result = await harness.invoke_create(ToolsFunction, name="search", config=config)

    assert result.success
    assert result.outputs is not None
    assert result.outputs.name == "search_web"
    assert result.outputs.description == "Search the web for information"


async def test_create_with_parameters(harness: ProviderHarness) -> None:
    """on_create generates JSON Schema from parameters."""
    config = ToolsFunctionConfig(
        name="search_web",
        description="Search the web",
        parameters=[
            FunctionParameter(
                name="query",
                type="string",
                description="Search query",
                required=True,
            ),
            FunctionParameter(
                name="max_results",
                type="integer",
                description="Maximum results to return",
                default=10,
            ),
        ],
    )

    result = await harness.invoke_create(ToolsFunction, name="search", config=config)

    assert result.success
    assert result.outputs is not None

    schema = result.outputs.parameters_schema
    assert schema["type"] == "object"
    assert "query" in schema["properties"]
    assert schema["properties"]["query"]["type"] == "string"
    assert schema["properties"]["query"]["description"] == "Search query"
    assert "max_results" in schema["properties"]
    assert schema["properties"]["max_results"]["type"] == "integer"
    assert schema["properties"]["max_results"]["default"] == 10
    assert schema["required"] == ["query"]


async def test_create_with_enum_parameter(harness: ProviderHarness) -> None:
    """on_create handles enum parameters correctly."""
    config = ToolsFunctionConfig(
        name="set_mode",
        parameters=[
            FunctionParameter(
                name="mode",
                type="string",
                enum=["fast", "balanced", "accurate"],
                required=True,
            ),
        ],
    )

    result = await harness.invoke_create(ToolsFunction, name="mode", config=config)

    assert result.success
    assert result.outputs is not None

    schema = result.outputs.parameters_schema
    assert schema["properties"]["mode"]["enum"] == ["fast", "balanced", "accurate"]


async def test_create_with_array_parameter(harness: ProviderHarness) -> None:
    """on_create handles array parameters with items schema."""
    config = ToolsFunctionConfig(
        name="process_items",
        parameters=[
            FunctionParameter(
                name="items",
                type="array",
                items={"type": "string"},
                required=True,
            ),
        ],
    )

    result = await harness.invoke_create(ToolsFunction, name="process", config=config)

    assert result.success
    assert result.outputs is not None

    schema = result.outputs.parameters_schema
    assert schema["properties"]["items"]["type"] == "array"
    assert schema["properties"]["items"]["items"] == {"type": "string"}


async def test_function_method_returns_agno_function(harness: ProviderHarness) -> None:
    """function() method returns configured Agno Function instance."""
    config = ToolsFunctionConfig(
        name="calculator",
        description="Perform calculations",
        parameters=[
            FunctionParameter(
                name="expression",
                type="string",
                description="Math expression to evaluate",
                required=True,
            ),
        ],
    )

    result = await harness.invoke_create(ToolsFunction, name="calc", config=config)

    assert result.success
    assert result.resource is not None

    func = result.resource.function()

    assert isinstance(func, Function)
    assert func.name == "calculator"
    assert func.description == "Perform calculations"
    assert func.parameters["type"] == "object"
    assert "expression" in func.parameters["properties"]


async def test_function_method_with_code(harness: ProviderHarness) -> None:
    """function() method creates entrypoint from code."""
    config = ToolsFunctionConfig(
        name="add_numbers",
        description="Add two numbers",
        parameters=[
            FunctionParameter(name="a", type="integer", required=True),
            FunctionParameter(name="b", type="integer", required=True),
        ],
        code="result = a + b",
    )

    result = await harness.invoke_create(ToolsFunction, name="add", config=config)

    assert result.success
    assert result.resource is not None

    func = result.resource.function()

    assert func.entrypoint is not None
    assert func.entrypoint(a=2, b=3) == 5


async def test_function_method_with_options(harness: ProviderHarness) -> None:
    """function() method passes through optional config."""
    config = ToolsFunctionConfig(
        name="dangerous_action",
        description="Perform a dangerous action",
        requires_confirmation=True,
        stop_after_tool_call=True,
        cache_results=True,
        cache_ttl=7200,
    )

    result = await harness.invoke_create(ToolsFunction, name="danger", config=config)

    assert result.success
    assert result.resource is not None

    func = result.resource.function()

    assert func.requires_confirmation is True
    assert func.stop_after_tool_call is True
    assert func.cache_results is True
    assert func.cache_ttl == 7200


def test_validation_invalid_parameter_name() -> None:
    """Config validation fails for invalid parameter names."""
    with pytest.raises(ValidationError) as exc_info:
        ToolsFunctionConfig(
            name="test_func",
            parameters=[
                FunctionParameter(name="invalid-name", type="string"),
            ],
        )

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert "not a valid Python identifier" in str(errors[0]["msg"])


def test_validation_empty_name_fails() -> None:
    """Config validation fails when name is empty."""
    with pytest.raises(ValidationError):
        ToolsFunctionConfig(name="")


async def test_update_changes_outputs(harness: ProviderHarness) -> None:
    """on_update returns updated metadata."""
    previous = ToolsFunctionConfig(
        name="old_name",
        description="Old description",
    )
    current = ToolsFunctionConfig(
        name="new_name",
        description="New description",
    )
    previous_outputs = ToolsFunctionOutputs(
        name="old_name",
        description="Old description",
        parameters_schema={"type": "object", "properties": {}},
    )

    result = await harness.invoke_update(
        ToolsFunction,
        name="test-func",
        config=current,
        previous_config=previous,
        current_outputs=previous_outputs,
    )

    assert result.success
    assert result.outputs is not None
    assert result.outputs.name == "new_name"
    assert result.outputs.description == "New description"


async def test_delete_success(harness: ProviderHarness) -> None:
    """on_delete completes without error (stateless resource)."""
    config = ToolsFunctionConfig(name="test_func")

    result = await harness.invoke_delete(ToolsFunction, name="test", config=config)

    assert result.success


def test_provider_name() -> None:
    """Resource has correct provider name."""
    assert ToolsFunction.provider == "agno"


def test_resource_type() -> None:
    """Resource has correct resource type."""
    assert ToolsFunction.resource == "tools/function"


def test_outputs_are_serializable() -> None:
    """Outputs contain only serializable data."""
    outputs = ToolsFunctionOutputs(
        name="test_func",
        description="Test function",
        parameters_schema={"type": "object", "properties": {"x": {"type": "string"}}},
    )

    assert outputs.name == "test_func"
    assert outputs.description == "Test function"

    serialized = outputs.model_dump_json()
    assert "test_func" in serialized
    assert "Test function" in serialized


async def test_multiple_required_parameters(harness: ProviderHarness) -> None:
    """Schema includes all required parameters."""
    config = ToolsFunctionConfig(
        name="multi_required",
        parameters=[
            FunctionParameter(name="a", type="string", required=True),
            FunctionParameter(name="b", type="integer", required=True),
            FunctionParameter(name="c", type="boolean", required=False),
        ],
    )

    result = await harness.invoke_create(ToolsFunction, name="multi", config=config)

    assert result.success
    assert result.outputs is not None
    assert set(result.outputs.parameters_schema["required"]) == {"a", "b"}


async def test_no_required_parameters(harness: ProviderHarness) -> None:
    """Schema omits required field when no parameters are required."""
    config = ToolsFunctionConfig(
        name="all_optional",
        parameters=[
            FunctionParameter(name="x", type="string", required=False),
        ],
    )

    result = await harness.invoke_create(ToolsFunction, name="optional", config=config)

    assert result.success
    assert result.outputs is not None
    assert "required" not in result.outputs.parameters_schema


async def test_function_without_code(harness: ProviderHarness) -> None:
    """function() with no code has None entrypoint."""
    config = ToolsFunctionConfig(
        name="no_code_func",
        description="Function without code",
    )

    result = await harness.invoke_create(ToolsFunction, name="nocode", config=config)

    assert result.success
    assert result.resource is not None

    func = result.resource.function()

    assert func.entrypoint is None


async def test_function_with_instructions(harness: ProviderHarness) -> None:
    """function() passes through instructions field."""
    config = ToolsFunctionConfig(
        name="instructed_func",
        instructions="Use this function carefully",
    )

    result = await harness.invoke_create(ToolsFunction, name="instr", config=config)

    assert result.success
    assert result.resource is not None

    func = result.resource.function()

    assert func.instructions == "Use this function carefully"

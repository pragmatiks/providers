"""Tests for Anthropic Messages resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from anthropic import APIError
from pragma_sdk.provider import ProviderHarness

from anthropic_provider import Messages, MessagesConfig, MessagesOutputs

if TYPE_CHECKING:
    from pytest_mock import MockerFixture, MockType


async def test_create_messages_success(
    harness: ProviderHarness,
    mock_anthropic_client: "MockType",
) -> None:
    """on_create calls Messages API and returns outputs."""
    config = MessagesConfig(
        api_key="sk-test-key",
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=100,
    )

    result = await harness.invoke_create(Messages, name="test-msg", config=config)

    assert result.success
    assert result.outputs is not None
    assert result.outputs.id == "msg_123abc"
    assert result.outputs.model == "claude-sonnet-4-20250514"
    assert result.outputs.stop_reason == "end_turn"
    assert result.outputs.input_tokens == 10
    assert result.outputs.output_tokens == 25
    assert result.outputs.content == [{"type": "text", "text": "Hello!"}]

    mock_anthropic_client.messages.create.assert_called_once()


async def test_create_with_system_prompt(
    harness: ProviderHarness,
    mock_anthropic_client: "MockType",
) -> None:
    """on_create passes system prompt to API."""
    config = MessagesConfig(
        api_key="sk-test-key",
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=100,
        system="You are a helpful assistant.",
    )

    result = await harness.invoke_create(Messages, name="test-msg", config=config)

    assert result.success
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "You are a helpful assistant."


async def test_create_with_temperature(
    harness: ProviderHarness,
    mock_anthropic_client: "MockType",
) -> None:
    """on_create passes temperature to API."""
    config = MessagesConfig(
        api_key="sk-test-key",
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=100,
        temperature=0.7,
    )

    result = await harness.invoke_create(Messages, name="test-msg", config=config)

    assert result.success
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.7


async def test_update_regenerates_on_config_change(
    harness: ProviderHarness,
    mock_anthropic_client: "MockType",
) -> None:
    """on_update regenerates when config changes."""
    previous = MessagesConfig(
        api_key="sk-test-key",
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=100,
    )
    current = MessagesConfig(
        api_key="sk-test-key",
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": "Updated prompt"}],
        max_tokens=100,
    )

    result = await harness.invoke_update(
        Messages,
        name="test-msg",
        config=current,
        previous_config=previous,
        current_outputs=MessagesOutputs(
            id="msg_old",
            content=[{"type": "text", "text": "Old response"}],
            model="claude-sonnet-4-20250514",
            stop_reason="end_turn",
            input_tokens=5,
            output_tokens=10,
        ),
    )

    assert result.success
    assert result.outputs is not None
    assert result.outputs.id == "msg_123abc"  # New response
    mock_anthropic_client.messages.create.assert_called_once()


async def test_update_returns_existing_when_unchanged(
    harness: ProviderHarness,
    mock_anthropic_client: "MockType",
) -> None:
    """on_update returns existing outputs when config unchanged."""
    config = MessagesConfig(
        api_key="sk-test-key",
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=100,
    )
    existing_outputs = MessagesOutputs(
        id="msg_existing",
        content=[{"type": "text", "text": "Existing response"}],
        model="claude-sonnet-4-20250514",
        stop_reason="end_turn",
        input_tokens=5,
        output_tokens=10,
    )

    result = await harness.invoke_update(
        Messages,
        name="test-msg",
        config=config,
        previous_config=config,
        current_outputs=existing_outputs,
    )

    assert result.success
    assert result.outputs == existing_outputs
    mock_anthropic_client.messages.create.assert_not_called()


async def test_delete_success(
    harness: ProviderHarness,
    mock_anthropic_client: "MockType",
) -> None:
    """on_delete completes without error (stateless resource)."""
    config = MessagesConfig(
        api_key="sk-test-key",
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=100,
    )

    result = await harness.invoke_delete(Messages, name="test-msg", config=config)

    assert result.success
    mock_anthropic_client.messages.create.assert_not_called()


async def test_api_error_propagates(
    harness: ProviderHarness,
    mocker: "MockerFixture",
) -> None:
    """API errors propagate correctly."""
    mock_client = mocker.MagicMock()
    mock_client.messages.create = mocker.AsyncMock(
        side_effect=APIError(
            message="Invalid API key",
            request=mocker.MagicMock(),
            body={"error": {"message": "Invalid API key"}},
        )
    )
    # Support async context manager protocol
    mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mocker.AsyncMock(return_value=None)

    mocker.patch(
        "anthropic_provider.resources.messages.AsyncAnthropic",
        return_value=mock_client,
    )

    config = MessagesConfig(
        api_key="invalid-key",
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=100,
    )

    result = await harness.invoke_create(Messages, name="test-msg", config=config)

    assert result.failed
    assert result.error is not None
    assert "Invalid API key" in str(result.error)


def test_provider_name() -> None:
    """Resource has correct provider name."""
    assert Messages.provider == "anthropic"


def test_resource_type() -> None:
    """Resource has correct resource type."""
    assert Messages.resource == "messages"

"""Tests for OpenAI ChatCompletions resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openai import APIError
from pragma_sdk.provider import ProviderHarness

from openai_provider import ChatCompletions, ChatCompletionsConfig, ChatCompletionsOutputs

if TYPE_CHECKING:
    from pytest_mock import MockerFixture, MockType


async def test_create_chat_completions_success(
    harness: ProviderHarness,
    mock_openai_client: "MockType",
) -> None:
    """on_create calls Chat Completions API and returns outputs."""
    config = ChatCompletionsConfig(
        api_key="sk-test-key",
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )

    result = await harness.invoke_create(ChatCompletions, name="test-chat", config=config)

    assert result.success
    assert result.outputs is not None
    assert result.outputs.id == "chatcmpl-abc123"
    assert result.outputs.model == "gpt-4o"
    assert result.outputs.finish_reason == "stop"
    assert result.outputs.prompt_tokens == 10
    assert result.outputs.completion_tokens == 15
    assert result.outputs.content == "Hello! How can I help you today?"

    mock_openai_client.chat.completions.create.assert_called_once()


async def test_create_with_system_message(
    harness: ProviderHarness,
    mock_openai_client: "MockType",
) -> None:
    """on_create passes system message in messages array."""
    config = ChatCompletionsConfig(
        api_key="sk-test-key",
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ],
    )

    result = await harness.invoke_create(ChatCompletions, name="test-chat", config=config)

    assert result.success
    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    assert len(call_kwargs["messages"]) == 2
    assert call_kwargs["messages"][0]["role"] == "system"


async def test_create_with_max_tokens(
    harness: ProviderHarness,
    mock_openai_client: "MockType",
) -> None:
    """on_create passes max_tokens to API."""
    config = ChatCompletionsConfig(
        api_key="sk-test-key",
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=100,
    )

    result = await harness.invoke_create(ChatCompletions, name="test-chat", config=config)

    assert result.success
    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 100


async def test_create_with_temperature(
    harness: ProviderHarness,
    mock_openai_client: "MockType",
) -> None:
    """on_create passes temperature to API."""
    config = ChatCompletionsConfig(
        api_key="sk-test-key",
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
    )

    result = await harness.invoke_create(ChatCompletions, name="test-chat", config=config)

    assert result.success
    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.7


async def test_update_regenerates_on_config_change(
    harness: ProviderHarness,
    mock_openai_client: "MockType",
) -> None:
    """on_update regenerates when config changes."""
    previous = ChatCompletionsConfig(
        api_key="sk-test-key",
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )
    current = ChatCompletionsConfig(
        api_key="sk-test-key",
        model="gpt-4o",
        messages=[{"role": "user", "content": "Updated prompt"}],
    )

    result = await harness.invoke_update(
        ChatCompletions,
        name="test-chat",
        config=current,
        previous_config=previous,
        current_outputs=ChatCompletionsOutputs(
            id="chatcmpl-old",
            content="Old response",
            model="gpt-4o",
            finish_reason="stop",
            prompt_tokens=5,
            completion_tokens=10,
        ),
    )

    assert result.success
    assert result.outputs is not None
    assert result.outputs.id == "chatcmpl-abc123"  # New response
    mock_openai_client.chat.completions.create.assert_called_once()


async def test_update_returns_existing_when_unchanged(
    harness: ProviderHarness,
    mock_openai_client: "MockType",
) -> None:
    """on_update returns existing outputs when config unchanged."""
    config = ChatCompletionsConfig(
        api_key="sk-test-key",
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )
    existing_outputs = ChatCompletionsOutputs(
        id="chatcmpl-existing",
        content="Existing response",
        model="gpt-4o",
        finish_reason="stop",
        prompt_tokens=5,
        completion_tokens=10,
    )

    result = await harness.invoke_update(
        ChatCompletions,
        name="test-chat",
        config=config,
        previous_config=config,
        current_outputs=existing_outputs,
    )

    assert result.success
    assert result.outputs == existing_outputs
    mock_openai_client.chat.completions.create.assert_not_called()


async def test_delete_success(
    harness: ProviderHarness,
    mock_openai_client: "MockType",
) -> None:
    """on_delete completes without error (stateless resource)."""
    config = ChatCompletionsConfig(
        api_key="sk-test-key",
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )

    result = await harness.invoke_delete(ChatCompletions, name="test-chat", config=config)

    assert result.success
    mock_openai_client.chat.completions.create.assert_not_called()


async def test_api_error_propagates(
    harness: ProviderHarness,
    mocker: "MockerFixture",
) -> None:
    """API errors propagate correctly."""
    mock_client = mocker.MagicMock()
    mock_completions = mocker.MagicMock()
    mock_completions.create = mocker.AsyncMock(
        side_effect=APIError(
            message="Invalid API key",
            request=mocker.MagicMock(),
            body={"error": {"message": "Invalid API key"}},
        )
    )
    mock_chat = mocker.MagicMock()
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    # Support async context manager protocol
    mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mocker.AsyncMock(return_value=None)

    mocker.patch(
        "openai_provider.resources.chat_completions.AsyncOpenAI",
        return_value=mock_client,
    )

    config = ChatCompletionsConfig(
        api_key="invalid-key",
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )

    result = await harness.invoke_create(ChatCompletions, name="test-chat", config=config)

    assert result.failed
    assert result.error is not None
    assert "Invalid API key" in str(result.error)


def test_provider_name() -> None:
    """Resource has correct provider name."""
    assert ChatCompletions.provider == "openai"


def test_resource_type() -> None:
    """Resource has correct resource type."""
    assert ChatCompletions.resource == "chat_completions"

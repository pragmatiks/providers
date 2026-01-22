"""Pytest configuration for openai provider tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pragma_sdk.provider import ProviderHarness

if TYPE_CHECKING:
    from pytest_mock import MockerFixture, MockType


@pytest.fixture
def harness() -> ProviderHarness:
    """Test harness for invoking lifecycle methods."""
    return ProviderHarness()


@pytest.fixture
def mock_openai_client(mocker: "MockerFixture") -> "MockType":
    """Mock AsyncOpenAI client with async context manager support."""
    mock_client = mocker.MagicMock()

    # Mock response
    mock_message = mocker.MagicMock()
    mock_message.content = "Hello! How can I help you today?"

    mock_choice = mocker.MagicMock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"

    mock_usage = mocker.MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 15

    mock_response = mocker.MagicMock()
    mock_response.id = "chatcmpl-abc123"
    mock_response.choices = [mock_choice]
    mock_response.model = "gpt-4o"
    mock_response.usage = mock_usage

    mock_completions = mocker.MagicMock()
    mock_completions.create = mocker.AsyncMock(return_value=mock_response)

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

    return mock_client

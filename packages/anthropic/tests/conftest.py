"""Pytest configuration for anthropic provider tests."""

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
def mock_anthropic_client(mocker: "MockerFixture") -> "MockType":
    """Mock AsyncAnthropic client with async context manager support."""
    mock_client = mocker.MagicMock()

    # Mock response
    mock_content_block = mocker.MagicMock()
    mock_content_block.model_dump.return_value = {"type": "text", "text": "Hello!"}

    mock_usage = mocker.MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 25

    mock_response = mocker.MagicMock()
    mock_response.id = "msg_123abc"
    mock_response.content = [mock_content_block]
    mock_response.model = "claude-sonnet-4-20250514"
    mock_response.stop_reason = "end_turn"
    mock_response.usage = mock_usage

    mock_messages = mocker.MagicMock()
    mock_messages.create = mocker.AsyncMock(return_value=mock_response)
    mock_client.messages = mock_messages

    # Support async context manager protocol
    mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mocker.AsyncMock(return_value=None)

    mocker.patch(
        "anthropic_provider.resources.messages.AsyncAnthropic",
        return_value=mock_client,
    )

    return mock_client

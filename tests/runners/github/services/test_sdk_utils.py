"""Tests for sdk_utils"""

from runners.github.services.sdk_utils import process_sdk_stream
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest


@pytest.mark.asyncio
async def test_process_sdk_stream():
    """Test process_sdk_stream"""

    # Arrange
    client = MagicMock()
    client.query = MagicMock()

    # Create an async iterator for receive_response
    async def mock_receive():
        text_block = MagicMock()
        text_block.__class__.__name__ = "TextBlock"
        text_block.text = "Test response"
        text_block.type = "text"

        msg = MagicMock()
        msg.__class__.__name__ = "AssistantMessage"
        msg.content = [text_block]
        msg.type = "message"

        yield msg

    client.receive_response = mock_receive

    on_thinking = MagicMock()
    on_tool_use = MagicMock()
    on_tool_result = MagicMock()
    on_text = MagicMock()
    on_structured_output = MagicMock()
    context_name = "test"
    model = "sonnet"
    max_messages = 10
    system_prompt = "Test prompt"
    agent_definitions = {}

    # Act
    result = await process_sdk_stream(
        client, on_thinking, on_tool_use, on_tool_result, on_text,
        on_structured_output, context_name, model, max_messages,
        system_prompt, agent_definitions
    )

    # Assert
    assert result is not None
    assert "result_text" in result
    assert result["result_text"] == "Test response"


@pytest.mark.asyncio
async def test_process_sdk_stream_with_empty_inputs():
    """Test process_sdk_stream with empty inputs"""

    # Arrange
    client = MagicMock()

    async def mock_receive():
        return
        yield  # Empty iterator

    client.receive_response = mock_receive

    on_thinking = MagicMock()
    on_tool_use = MagicMock()
    on_tool_result = MagicMock()
    on_text = MagicMock()
    on_structured_output = MagicMock()
    context_name = ""
    model = ""
    max_messages = 0
    system_prompt = ""
    agent_definitions = {}

    # Act
    result = await process_sdk_stream(
        client, on_thinking, on_tool_use, on_tool_result, on_text,
        on_structured_output, context_name, model, max_messages,
        system_prompt, agent_definitions
    )

    # Assert
    assert result is not None
    assert "result_text" in result


@pytest.mark.asyncio
async def test_process_sdk_stream_with_invalid_input():
    """Test process_sdk_stream with invalid input"""

    # Arrange & Act & Assert
    # The function processes what it receives, so even "invalid" inputs
    # won't raise exceptions - they just return empty results
    client = MagicMock()

    async def mock_receive():
        return
        yield  # Empty iterator

    client.receive_response = mock_receive

    result = await process_sdk_stream(
        client=client,
        on_thinking=None,
        on_tool_use=None,
        on_tool_result=None,
        on_text=None,
        on_structured_output=None,
        context_name="",
        model="",
        max_messages=0,
        system_prompt="",
        agent_definitions={}
    )

    assert result is not None

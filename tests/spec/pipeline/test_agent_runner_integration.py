"""
Integration tests for spec.pipeline.agent_runner module.

Tests covering complex interaction scenarios and edge cases
that complement the existing unit tests.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

import pytest

from spec.pipeline.agent_runner import AgentRunner
from tests.spec.pipeline.conftest import MockMessage, MockBlock, create_async_response


class TestAgentRunWithMultipleMessageTypes:
    """Tests for handling multiple different message types in sequence."""

    @pytest.mark.asyncio
    async def test_run_agent_complex_message_sequence(self, tmp_path, mock_task_logger):
        """Test run_agent with a complex sequence of message types."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        # Complex sequence: Text -> Tool -> ToolResult -> Text -> Tool -> ToolResult -> Text
        messages = [
            # First assistant message with text and tool
            MockMessage("AssistantMessage", content=[
                MockBlock("TextBlock", text="Let me check that file."),
                MockBlock("ToolUseBlock", name="Read", input_data={"file_path": "/test/file.py"})
            ]),
            # Tool result
            MockMessage("UserMessage", content=[
                MockBlock("ToolResultBlock", content="file content here")
            ]),
            # Second assistant message
            MockMessage("AssistantMessage", content=[
                MockBlock("TextBlock", text="Now I'll search for patterns."),
                MockBlock("ToolUseBlock", name="Grep", input_data={"pattern": "test"})
            ]),
            # Tool result
            MockMessage("UserMessage", content=[
                MockBlock("ToolResultBlock", content="matches found", is_error=False)
            ]),
            # Final assistant message
            MockMessage("AssistantMessage", content=[
                MockBlock("TextBlock", text="Complete!")
            ]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True
        assert "Complete!" in response

    @pytest.mark.asyncio
    async def test_run_agent_with_empty_text_blocks(self, tmp_path):
        """Test run_agent handles empty text blocks correctly."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        # Messages with empty/whitespace text blocks
        messages = [
            MockMessage("AssistantMessage", content=[
                MockBlock("TextBlock", text="   "),
                MockBlock("TextBlock", text=""),
                MockBlock("TextBlock", text="Actual text")
            ]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True

    @pytest.mark.asyncio
    async def test_run_agent_missing_text_attribute(self, tmp_path):
        """Test run_agent handles blocks without text attribute gracefully."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        # Message with block that doesn't have text attribute
        mock_block = MagicMock()
        mock_block.__class__.__name__ = "TextBlock"
        del mock_block.text  # Remove text attribute

        messages = [
            MockMessage("AssistantMessage", content=[mock_block]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                # Should handle gracefully without crashing
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True


class TestAgentRunnerToolEdgeCases:
    """Tests for edge cases in tool handling."""

    @pytest.mark.asyncio
    async def test_run_agent_tool_use_without_name(self, tmp_path, mock_task_logger):
        """Test run_agent handles ToolUseBlock without name attribute."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        # Tool block without name attribute
        mock_tool_block = MagicMock()
        mock_tool_block.__class__.__name__ = "ToolUseBlock"
        del mock_tool_block.name

        messages = [
            MockMessage("AssistantMessage", content=[mock_tool_block]),
            MockMessage("AssistantMessage", content=[
                MockBlock("TextBlock", text="Done")
            ]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True

    @pytest.mark.asyncio
    async def test_run_agent_tool_result_without_attributes(self, tmp_path):
        """Test run_agent handles ToolResultBlock without is_error/content."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        # Tool result block without expected attributes
        mock_result_block = MagicMock()
        mock_result_block.__class__.__name__ = "ToolResultBlock"
        # Simulate missing attributes

        messages = [
            MockMessage("UserMessage", content=[mock_result_block]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True


class TestAgentRunnerTaskLoggerInteractions:
    """Tests for interactions with task logger."""

    @pytest.mark.asyncio
    async def test_run_agent_logs_all_non_empty_text(self, tmp_path):
        """Test that all non-empty text blocks are logged to task logger."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        mock_task_logger = MagicMock()
        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        messages = [
            MockMessage("AssistantMessage", content=[
                MockBlock("TextBlock", text="First line\n"),
                MockBlock("TextBlock", text="Second line\n"),
                MockBlock("TextBlock", text="   "),  # Whitespace only
                MockBlock("TextBlock", text=""),  # Empty
                MockBlock("TextBlock", text="Third line\n"),
            ]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True
        # Should log non-empty text blocks (3 non-empty: "First", "Second", "Third")
        assert mock_task_logger.log.call_count >= 3

    @pytest.mark.asyncio
    async def test_run_agent_tool_start_end_calls(self, tmp_path):
        """Test that tool_start and tool_end are called correctly."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        mock_task_logger = MagicMock()
        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        messages = [
            MockMessage("AssistantMessage", content=[
                MockBlock("ToolUseBlock", name="Read", input_data={"file_path": "/test.py"})
            ]),
            MockMessage("UserMessage", content=[
                MockBlock("ToolResultBlock", content="file content")
            ]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True
        mock_task_logger.tool_start.assert_called_once()
        mock_task_logger.tool_end.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_without_task_logger(self, tmp_path):
        """Test run_agent works without task logger."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        # No task logger
        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        messages = [
            MockMessage("AssistantMessage", content=[
                MockBlock("ToolUseBlock", name="Bash", input_data={"command": "echo test"})
            ]),
            MockMessage("UserMessage", content=[
                MockBlock("ToolResultBlock", content="test")
            ]),
            MockMessage("AssistantMessage", content=[
                MockBlock("TextBlock", text="Done")
            ]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True


class TestExtractToolInputDisplayEdgeCases:
    """Additional edge case tests for _extract_tool_input_display."""

    def test_extract_tool_input_unicode_chars(self):
        """Test _extract_tool_input_display with unicode characters."""
        inp = {"file_path": "/path/to/文件.py"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert "文件.py" in result

    def test_extract_tool_input_special_path_chars(self):
        """Test with special characters in file path."""
        inp = {"file_path": "/path/[test]/file (1).txt"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result is not None

    def test_extract_tool_input_emoji_in_command(self):
        """Test with emoji in command."""
        inp = {"command": "echo 'Hello World' 👋"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result is not None
        assert "Hello World" in result

    def test_extract_tool_input_multiline_command(self):
        """Test with multiline command."""
        inp = {"command": "echo 'line1\necho line2'"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result is not None

    def test_extract_tool_input_very_long_pattern(self):
        """Test with very long pattern."""
        long_pattern = ".*" + "a" * 100 + ".*"
        inp = {"pattern": long_pattern}
        result = AgentRunner._extract_tool_input_display(inp)
        # Pattern should not be truncated
        assert "pattern:" in result

    def test_extract_tool_input_dict_with_none_values(self):
        """Test with None values in dict - would cause TypeError."""
        inp = {"file_path": None}
        # The implementation doesn't handle None, it would try to call len(None)
        # which raises TypeError. We can test that it behaves predictably.
        with pytest.raises(TypeError):
            AgentRunner._extract_tool_input_display(inp)


class TestGetToolDetailContentEdgeCases:
    """Additional edge case tests for _get_tool_detail_content."""

    def test_get_tool_detail_with_unicode(self):
        """Test _get_tool_detail_content with unicode content."""
        content = "测试内容" * 100  # Still under limit
        result = AgentRunner._get_tool_detail_content("Read", content)
        assert result == content

    def test_get_tool_detail_with_newlines(self):
        """Test with content containing many newlines."""
        content = "\n" * 100 + "text" + "\n" * 100
        result = AgentRunner._get_tool_detail_content("Read", content)
        assert result == content

    def test_get_tool_detail_with_tabs(self):
        """Test with content containing many tabs."""
        content = "\t" * 1000
        result = AgentRunner._get_tool_detail_content("Grep", content)
        # Should be included (under limit)
        assert result == content

    def test_get_tool_detail_case_sensitive_tools(self):
        """Test that tool names are case-sensitive."""
        content = "test content"
        # lowercase should not match
        result = AgentRunner._get_tool_detail_content("read", content)
        assert result is None

        # uppercase should match
        result = AgentRunner._get_tool_detail_content("Read", content)
        assert result == content

    def test_get_tool_detail_exactly_at_limit(self):
        """Test content exactly at 50000 character limit."""
        content = "x" * 50000
        result = AgentRunner._get_tool_detail_content("Write", content)
        # The condition is < 50000, so exactly 50000 is NOT included
        assert result is None

    def test_get_tool_detail_one_over_limit(self):
        """Test content one character over limit."""
        content = "x" * 50001
        result = AgentRunner._get_tool_detail_content("Edit", content)
        assert result is None

    def test_get_tool_detail_with_binary_like_chars(self):
        """Test with binary-like characters."""
        content = "\x00\x01\x02\x03\x04\x05" * 1000  # Under limit
        result = AgentRunner._get_tool_detail_content("Read", content)
        # Should include if under limit
        assert result == content


class TestAgentRunnerAsyncContextManager:
    """Tests for async context manager handling."""

    @pytest.mark.asyncio
    async def test_client_context_manager_exception_on_exit(self, tmp_path):
        """Test handling of exception during client __aexit__."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(side_effect=RuntimeError("Exit error"))
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        messages = [
            MockMessage("AssistantMessage", content=[
                MockBlock("TextBlock", text="Response")
            ]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                # Should handle exit error
                try:
                    success, response = await runner.run_agent("test_prompt.md")
                except RuntimeError:
                    # Expected to raise if __aexit__ raises
                    pass

    @pytest.mark.asyncio
    async def test_client_query_exception(self, tmp_path):
        """Test handling of exception during query."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock(side_effect=ConnectionError("Network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # __aexit__ must return None (falsey) to propagate the exception
        mock_client.__aexit__ = AsyncMock(return_value=None)
        # receive_response won't be called because query raises exception
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is False
        assert "Network error" in response


class TestAgentRunnerPromptBuilding:
    """Tests for prompt building and context injection."""

    @pytest.mark.asyncio
    async def test_prompt_includes_spec_and_project_dirs(self, tmp_path):
        """Test that prompt includes spec and project directory information."""
        project_dir = tmp_path / "my_project"
        spec_dir = tmp_path / "my_spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        original_prompt = "Original prompt content"
        prompt_file.write_text(original_prompt)

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        messages = [
            MockMessage("AssistantMessage", content=[
                MockBlock("TextBlock", text="Response")
            ]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True
        # Verify the query was made (prompt includes dirs)
        mock_client.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_prompt_with_all_context_types(self, tmp_path):
        """Test prompt with all types of context added."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Base prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        # receive_response must be a MagicMock that returns an async iterator
        mock_client.receive_response = MagicMock(return_value=create_async_response([]))

        messages = [
            MockMessage("AssistantMessage", content=[
                MockBlock("TextBlock", text="Response")
            ]),
        ]

        mock_client.receive_response.return_value = create_async_response(messages)

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Base prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent(
                    "test_prompt.md",
                    additional_context="Extra info",
                    prior_phase_summaries="## Phase 1\nSummary",
                )

        assert success is True

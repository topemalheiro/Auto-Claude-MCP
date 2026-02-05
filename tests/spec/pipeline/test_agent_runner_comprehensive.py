"""
Comprehensive tests for spec.pipeline.agent_runner module.

Tests for AgentRunner class covering all code paths including:
- Message handling (AssistantMessage, UserMessage)
- Tool execution (ToolUseBlock, ToolResultBlock)
- Error handling and logging
- Static helper methods
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from spec.pipeline.agent_runner import AgentRunner
from tests.spec.pipeline.conftest import MockMessage, MockBlock, create_async_response, create_async_response_exception


class TestAgentRunnerInit:
    """Tests for AgentRunner.__init__."""

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        project_dir = Path("/project")
        spec_dir = Path("/spec")
        model = "sonnet"
        task_logger = MagicMock()

        runner = AgentRunner(project_dir, spec_dir, model, task_logger)

        assert runner.project_dir == project_dir
        assert runner.spec_dir == spec_dir
        assert runner.model == model
        assert runner.task_logger == task_logger

    def test_init_without_task_logger(self):
        """Test initialization without task logger."""
        project_dir = Path("/project")
        spec_dir = Path("/spec")

        runner = AgentRunner(project_dir, spec_dir, "haiku", None)

        assert runner.task_logger is None


class TestAgentRunnerRunAgentSuccess:
    """Tests for AgentRunner.run_agent successful execution."""

    @pytest.mark.asyncio
    async def test_run_agent_with_text_response(self, tmp_path, mock_sdk_client, mock_task_logger):
        """Test run_agent with text-only response."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create prompt file
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)


        text_block = MockBlock("TextBlock", text="Response text")
        assistant_msg = MockMessage("AssistantMessage", content=[text_block])

        mock_sdk_client.receive_response.return_value = create_async_response([assistant_msg])

        with patch("core.client.create_client", return_value=mock_sdk_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True
        assert "Response text" in response

    @pytest.mark.asyncio
    async def test_run_agent_with_tool_use(self, tmp_path, mock_sdk_client, mock_task_logger):
        """Test run_agent with ToolUseBlock."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)

        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock()


        tool_block = MockBlock("ToolUseBlock", name="Read", input_data={"file_path": "/path/to/file.txt"})
        text_block = MockBlock("TextBlock", text="Done")
        assistant_msg = MockMessage("AssistantMessage", content=[tool_block, text_block])

        mock_sdk_client.receive_response.return_value = create_async_response([assistant_msg])

        with patch("core.client.create_client", return_value=mock_sdk_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True
        mock_task_logger.tool_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_with_tool_result(self, tmp_path, mock_sdk_client, mock_task_logger):
        """Test run_agent with ToolResultBlock (success case)."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)

        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock()


        # First assistant message with tool use
        tool_block = MockBlock("ToolUseBlock", name="Grep", input_data={"pattern": "test"})
        assistant_msg = MockMessage("AssistantMessage", content=[tool_block])

        # User message with tool result
        result_block = MockBlock("ToolResultBlock", content="Found 5 matches")
        user_msg = MockMessage("UserMessage", content=[result_block])

        mock_sdk_client.receive_response.return_value = create_async_response([assistant_msg, user_msg])

        with patch("core.client.create_client", return_value=mock_sdk_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True
        mock_task_logger.tool_end.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_with_tool_result_error(self, tmp_path, mock_sdk_client, mock_task_logger):
        """Test run_agent with ToolResultBlock error case."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)

        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock()


        tool_block = MockBlock("ToolUseBlock", name="Bash", input_data={"command": "ls"})
        assistant_msg = MockMessage("AssistantMessage", content=[tool_block])

        # Tool result with error
        result_block = MockBlock("ToolResultBlock", content="Command failed", is_error=True)
        user_msg = MockMessage("UserMessage", content=[result_block])

        mock_sdk_client.receive_response.return_value = create_async_response([assistant_msg, user_msg])

        with patch("core.client.create_client", return_value=mock_sdk_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True
        # tool_end should be called with success=False
        mock_task_logger.tool_end.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_with_thinking_budget(self, tmp_path, mock_sdk_client):
        """Test run_agent with thinking_budget parameter."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock()


        text_block = MockBlock("TextBlock", text="Response")
        assistant_msg = MockMessage("AssistantMessage", content=[text_block])

        mock_sdk_client.receive_response.return_value = create_async_response([assistant_msg])

        with patch("core.client.create_client") as mock_create_client:
            mock_create_client.return_value = mock_sdk_client
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent(
                    "test_prompt.md",
                    thinking_budget=8192
                )

        assert success is True
        # Verify create_client was called with thinking_budget
        mock_create_client.assert_called_once()
        call_kwargs = mock_create_client.call_args.kwargs
        assert "max_thinking_tokens" in call_kwargs
        assert call_kwargs["max_thinking_tokens"] == 8192

    @pytest.mark.asyncio
    async def test_run_agent_with_prior_phase_summaries(self, tmp_path, mock_sdk_client):
        """Test run_agent with prior_phase_summaries parameter."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock()


        text_block = MockBlock("TextBlock", text="Response")
        assistant_msg = MockMessage("AssistantMessage", content=[text_block])

        mock_sdk_client.receive_response.return_value = create_async_response([assistant_msg])

        with patch("core.client.create_client", return_value=mock_sdk_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent(
                    "test_prompt.md",
                    prior_phase_summaries="## Phase 1 Summary\nContent here"
                )

        assert success is True

    @pytest.mark.asyncio
    async def test_run_agent_logs_text_to_task_logger(self, tmp_path, mock_sdk_client, mock_task_logger):
        """Test run_agent logs text blocks to task logger."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)

        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock()


        # Multiple text blocks
        text_block1 = MockBlock("TextBlock", text="First part")
        text_block2 = MockBlock("TextBlock", text="Second part")
        assistant_msg = MockMessage("AssistantMessage", content=[text_block1, text_block2])

        mock_sdk_client.receive_response.return_value = create_async_response([assistant_msg])

        with patch("core.client.create_client", return_value=mock_sdk_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is True
        # Should log non-empty text
        assert mock_task_logger.log.call_count >= 2


class TestAgentRunnerRunAgentErrors:
    """Tests for AgentRunner.run_agent error handling."""

    @pytest.mark.asyncio
    async def test_run_agent_missing_prompt_file(self, tmp_path):
        """Test run_agent when prompt file doesn't exist."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        success, response = await runner.run_agent("nonexistent.md")

        assert success is False
        assert "not found" in response.lower()

    @pytest.mark.asyncio
    async def test_run_agent_exception_during_execution(self, tmp_path, mock_task_logger):
        """Test run_agent handles exceptions during execution."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)

        # Mock client that raises exception
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(side_effect=RuntimeError("SDK error"))

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent("test_prompt.md")

        assert success is False
        assert "SDK error" in response
        mock_task_logger.log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_exception_during_receive(self, tmp_path, mock_task_logger):
        """Test run_agent handles exception during receive_response."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        runner = AgentRunner(project_dir, spec_dir, "sonnet", mock_task_logger)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Important: __aexit__ must return None (not a mock) to properly propagate exceptions
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock receive_response to raise exception during iteration
        # Use MagicMock (not AsyncMock) so receive_response() returns an async iterable, not a coroutine
        from unittest.mock import MagicMock as RegularMagicMock
        mock_client.receive_response = RegularMagicMock(return_value=create_async_response_exception(
            ValueError("Stream error")
        ))

        # Patch create_client and use an existing prompt file
        with patch("core.client.create_client", return_value=mock_client):
            # Use an existing prompt file from the codebase
            success, response = await runner.run_agent("coder.md")

        assert success is False
        mock_task_logger.log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_with_additional_context(self, tmp_path, mock_sdk_client):
        """Test run_agent includes additional context in prompt."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Base prompt")

        runner = AgentRunner(project_dir, spec_dir, "sonnet", None)

        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock()


        text_block = MockBlock("TextBlock", text="Response")
        assistant_msg = MockMessage("AssistantMessage", content=[text_block])

        mock_sdk_client.receive_response.return_value = create_async_response([assistant_msg])

        with patch("core.client.create_client", return_value=mock_sdk_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path
                success, response = await runner.run_agent(
                    "test_prompt.md",
                    additional_context="Extra context here"
                )

        assert success is True


class TestExtractToolInputDisplay:
    """Tests for AgentRunner._extract_tool_input_display static method."""

    def test_extract_tool_input_pattern(self):
        """Test _extract_tool_input_display with pattern input."""
        inp = {"pattern": ".*test.*"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result == "pattern: .*test.*"

    def test_extract_tool_input_file_path_truncated(self):
        """Test _extract_tool_input_display truncates long file paths."""
        inp = {"file_path": "/very/long/path/to/some/deeply/nested/directory/file.txt"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result.startswith("...")
        assert result.endswith("file.txt")
        assert len(result) <= 50  # Should be truncated

    def test_extract_tool_input_file_path_short(self):
        """Test _extract_tool_input_display with short file path."""
        inp = {"file_path": "/src/file.txt"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result == "/src/file.txt"

    def test_extract_tool_input_command_truncated(self):
        """Test _extract_tool_input_display truncates long commands."""
        long_cmd = "some very long command with many arguments that should be truncated"
        inp = {"command": long_cmd}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result.endswith("...")
        assert len(result) <= 50  # Should be truncated

    def test_extract_tool_input_command_short(self):
        """Test _extract_tool_input_display with short command."""
        inp = {"command": "ls -la"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result == "ls -la"

    def test_extract_tool_input_path(self):
        """Test _extract_tool_input_display with path."""
        inp = {"path": "/some/path"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result == "/some/path"

    def test_extract_tool_input_non_dict(self):
        """Test _extract_tool_input_display with non-dict input."""
        result = AgentRunner._extract_tool_input_display("not a dict")
        assert result is None

    def test_extract_tool_input_empty_dict(self):
        """Test _extract_tool_input_display with empty dict."""
        result = AgentRunner._extract_tool_input_display({})
        assert result is None

    def test_extract_tool_input_unknown_keys(self):
        """Test _extract_tool_input_display with unknown keys."""
        inp = {"unknown_key": "value", "another_key": 123}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result is None


class TestGetToolDetailContent:
    """Tests for AgentRunner._get_tool_detail_content static method."""

    def test_get_tool_detail_read_small(self):
        """Test _get_tool_detail_content for Read with small content."""
        result = AgentRunner._get_tool_detail_content("Read", "Small content")
        assert result == "Small content"

    def test_get_tool_detail_grep_medium(self):
        """Test _get_tool_detail_content for Grep with medium content."""
        content = "x" * 1000  # Still under 50000
        result = AgentRunner._get_tool_detail_content("Grep", content)
        assert result == content

    def test_get_tool_detail_bash_large(self):
        """Test _get_tool_detail_content for Bash with large content."""
        content = "x" * 60000  # Over 50000
        result = AgentRunner._get_tool_detail_content("Bash", content)
        assert result is None  # Too large

    def test_get_tool_detail_edit_exactly_at_limit(self):
        """Test _get_tool_detail_content at exactly 50000 chars."""
        content = "x" * 50000
        result = AgentRunner._get_tool_detail_content("Edit", content)
        assert result is None  # At limit (not < 50000) returns None

    def test_get_tool_detail_write_over_limit(self):
        """Test _get_tool_detail_content for Write over limit."""
        content = "x" * 50001
        result = AgentRunner._get_tool_detail_content("Write", content)
        assert result is None

    def test_get_tool_detail_unsupported_tool(self):
        """Test _get_tool_detail_content for unsupported tool."""
        result = AgentRunner._get_tool_detail_content("UnknownTool", "Some content")
        assert result is None

    def test_get_tool_detail_empty_content(self):
        """Test _get_tool_detail_content with empty content."""
        result = AgentRunner._get_tool_detail_content("Read", "")
        assert result == ""

    def test_get_tool_detail_none_content(self):
        """Test _get_tool_detail_content with None content converted to string."""
        result = AgentRunner._get_tool_detail_content("Grep", None)
        # None converts to "None" string, which is short enough
        assert result is not None

    def test_get_tool_detail_all_supported_tools(self):
        """Test _get_tool_detail_content for all supported tools."""
        content = "Test content"
        supported_tools = ["Read", "Grep", "Bash", "Edit", "Write"]

        for tool in supported_tools:
            result = AgentRunner._get_tool_detail_content(tool, content)
            assert result == content

    def test_get_tool_detail_binary_like_content(self):
        """Test _get_tool_detail_content with binary-like content."""
        # Content that might be from a binary file
        content = "\x00\x01\x02" * 10000  # Short but binary
        result = AgentRunner._get_tool_detail_content("Read", content)
        # Should still return if under length limit
        assert result == content

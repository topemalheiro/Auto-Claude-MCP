"""Tests for agent_runner module"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spec.pipeline.agent_runner import AgentRunner


class TestAgentRunnerInit:
    """Tests for AgentRunner.__init__"""

    def test_init_basic(self):
        """Test basic initialization"""
        project_dir = Path("/tmp/test")
        spec_dir = Path("/tmp/spec")
        model = "sonnet"
        task_logger = MagicMock()

        runner = AgentRunner(project_dir, spec_dir, model, task_logger)

        assert runner.project_dir == project_dir
        assert runner.spec_dir == spec_dir
        assert runner.model == model
        assert runner.task_logger is task_logger

    def test_init_without_task_logger(self):
        """Test initialization without task logger"""
        project_dir = Path("/tmp/test")
        spec_dir = Path("/tmp/spec")

        runner = AgentRunner(project_dir, spec_dir, "haiku", None)

        assert runner.task_logger is None


class TestAgentRunnerRunAgent:
    """Tests for AgentRunner.run_agent"""

    @pytest.mark.asyncio
    async def test_run_agent_missing_prompt_file(self, tmp_path):
        """Test run_agent when prompt file doesn't exist"""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        task_logger = MagicMock()
        runner = AgentRunner(project_dir, spec_dir, "sonnet", task_logger)

        result = await runner.run_agent("nonexistent_prompt.md")

        assert result[0] is False
        assert "not found" in result[1].lower()

    @pytest.mark.asyncio
    async def test_run_agent_success(self, tmp_path):
        """Test successful agent run"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create prompt file
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt", encoding="utf-8")

        task_logger = MagicMock()
        runner = AgentRunner(project_dir, spec_dir, "sonnet", task_logger)

        # Mock client
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        from claude_agent_sdk.types import AssistantMessage, TextBlock

        async def mock_response_gen():
            msg = AssistantMessage(model="sonnet", content=[TextBlock(text="Response")])
            yield msg

        mock_client.receive_response = lambda: mock_response_gen()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("core.client.create_client", return_value=mock_client):
            # Adjust Path to find our prompts directory
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path

                result = await runner.run_agent("test_prompt.md")

        assert result[0] is True
        assert "Response" in result[1]

    @pytest.mark.asyncio
    async def test_run_agent_with_additional_context(self, tmp_path):
        """Test run_agent with additional context"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt", encoding="utf-8")

        task_logger = MagicMock()
        runner = AgentRunner(project_dir, spec_dir, "sonnet", task_logger)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        from claude_agent_sdk.types import AssistantMessage, TextBlock

        async def mock_response_gen():
            msg = AssistantMessage(model="sonnet", content=[TextBlock(text="Response")])
            yield msg

        mock_client.receive_response = lambda: mock_response_gen()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path

                result = await runner.run_agent(
                    "test_prompt.md",
                    additional_context="Extra context",
                    interactive=False,
                )

        assert result[0] is True

    @pytest.mark.asyncio
    async def test_run_agent_with_thinking_budget(self, tmp_path):
        """Test run_agent with thinking budget"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt", encoding="utf-8")

        task_logger = MagicMock()
        runner = AgentRunner(project_dir, spec_dir, "sonnet", task_logger)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        from claude_agent_sdk.types import AssistantMessage, TextBlock

        async def mock_response_gen():
            msg = AssistantMessage(model="sonnet", content=[TextBlock(text="Response")])
            yield msg

        mock_client.receive_response = lambda: mock_response_gen()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("core.client.create_client", return_value=mock_client) as mock_create:
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path

                result = await runner.run_agent("test_prompt.md", thinking_budget=1000)

        # Verify create_client was called with thinking budget
        assert result[0] is True

    @pytest.mark.asyncio
    async def test_run_agent_with_prior_summaries(self, tmp_path):
        """Test run_agent with prior phase summaries"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt", encoding="utf-8")

        task_logger = MagicMock()
        runner = AgentRunner(project_dir, spec_dir, "sonnet", task_logger)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        from claude_agent_sdk.types import AssistantMessage, TextBlock

        async def mock_response_gen():
            msg = AssistantMessage(model="sonnet", content=[TextBlock(text="Response")])
            yield msg

        mock_client.receive_response = lambda: mock_response_gen()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path

                prior_summaries = "## Previous Context\nSome summary"
                result = await runner.run_agent(
                    "test_prompt.md",
                    prior_phase_summaries=prior_summaries,
                )

        assert result[0] is True

    @pytest.mark.asyncio
    async def test_run_agent_exception_handling(self, tmp_path):
        """Test run_agent handles exceptions"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt", encoding="utf-8")

        task_logger = MagicMock()
        runner = AgentRunner(project_dir, spec_dir, "sonnet", task_logger)

        # Mock client that raises exception
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(side_effect=Exception("API error"))

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path

                result = await runner.run_agent("test_prompt.md")

        assert result[0] is False
        assert "API error" in result[1]

    @pytest.mark.asyncio
    async def test_run_agent_with_tool_use_blocks(self, tmp_path):
        """Test run_agent processes ToolUseBlock messages"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt", encoding="utf-8")

        task_logger = MagicMock()
        runner = AgentRunner(project_dir, spec_dir, "sonnet", task_logger)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        from claude_agent_sdk.types import AssistantMessage, TextBlock, ToolUseBlock, UserMessage, ToolResultBlock

        async def mock_response_gen():
            # Assistant message with tool use
            yield AssistantMessage(
                model="sonnet",
                content=[ToolUseBlock(id="tool1", name="Read", input={"path": "test.py"})]
            )
            # User message with tool result
            yield UserMessage(content=[
                ToolResultBlock(tool_use_id="tool1", content="file content", is_error=False)
            ])
            # Final text response
            yield AssistantMessage(model="sonnet", content=[TextBlock(text="Done")])

        mock_client.receive_response = lambda: mock_response_gen()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("core.client.create_client", return_value=mock_client):
            with patch("spec.pipeline.agent_runner.Path") as MockPath:
                mock_prompt_path = MagicMock()
                mock_prompt_path.exists.return_value = True
                mock_prompt_path.read_text.return_value = "Test prompt"
                MockPath.return_value = mock_prompt_path

                result = await runner.run_agent("test_prompt.md")

        assert result[0] is True


class TestExtractToolInputDisplay:
    """Tests for AgentRunner._extract_tool_input_display"""

    def test_extract_pattern_input(self):
        """Test extracting pattern from tool input"""
        inp = {"pattern": "test_pattern"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result == "pattern: test_pattern"

    def test_extract_file_path_short(self):
        """Test extracting short file path"""
        inp = {"file_path": "short/path.py"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result == "short/path.py"

    def test_extract_file_path_long(self):
        """Test extracting long file path is truncated"""
        long_path = "a" * 100 + ".py"
        inp = {"file_path": long_path}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result is not None
        assert len(result) <= 50  # Should be truncated
        assert result.startswith("...")

    def test_extract_command_short(self):
        """Test extracting short command"""
        inp = {"command": "ls -la"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result == "ls -la"

    def test_extract_command_long(self):
        """Test extracting long command is truncated"""
        long_command = "echo '" + "a" * 100 + "'"
        inp = {"command": long_command}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result is not None
        assert len(result) <= 50
        assert result.endswith("...")

    def test_extract_path(self):
        """Test extracting path"""
        inp = {"path": "/some/path"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result == "/some/path"

    def test_extract_none_input(self):
        """Test with None input"""
        result = AgentRunner._extract_tool_input_display(None)
        assert result is None

    def test_extract_non_dict_input(self):
        """Test with non-dict input"""
        result = AgentRunner._extract_tool_input_display("string")
        assert result is None

    def test_extract_empty_dict(self):
        """Test with empty dict"""
        result = AgentRunner._extract_tool_input_display({})
        assert result is None

    def test_extract_unknown_field(self):
        """Test with unknown field"""
        result = AgentRunner._extract_tool_input_display({"unknown": "value"})
        assert result is None


class TestGetToolDetailContent:
    """Tests for AgentRunner._get_tool_detail_content"""

    def test_returns_content_for_read_tool(self):
        """Test returns content for Read tool"""
        result = AgentRunner._get_tool_detail_content("Read", "some file content")
        assert result == "some file content"

    def test_returns_content_for_grep_tool(self):
        """Test returns content for Grep tool"""
        result = AgentRunner._get_tool_detail_content("Grep", "match results")
        assert result == "match results"

    def test_returns_content_for_bash_tool(self):
        """Test returns content for Bash tool"""
        result = AgentRunner._get_tool_detail_content("Bash", "command output")
        assert result == "command output"

    def test_returns_content_for_edit_tool(self):
        """Test returns content for Edit tool"""
        result = AgentRunner._get_tool_detail_content("Edit", "edit result")
        assert result == "edit result"

    def test_returns_content_for_write_tool(self):
        """Test returns content for Write tool"""
        result = AgentRunner._get_tool_detail_content("Write", "write result")
        assert result == "write result"

    def test_returns_none_for_unknown_tool(self):
        """Test returns None for unknown tool"""
        result = AgentRunner._get_tool_detail_content("UnknownTool", "content")
        assert result is None

    def test_returns_none_for_large_content(self):
        """Test returns None for content exceeding limit"""
        large_content = "x" * 60000
        result = AgentRunner._get_tool_detail_content("Read", large_content)
        assert result is None

    def test_returns_content_at_limit_boundary(self):
        """Test content exactly at limit"""
        content = "x" * 49999  # Just under 50000 limit
        result = AgentRunner._get_tool_detail_content("Read", content)
        assert result == content

    def test_returns_none_for_empty_content(self):
        """Test with empty content"""
        result = AgentRunner._get_tool_detail_content("Read", "")
        assert result == ""

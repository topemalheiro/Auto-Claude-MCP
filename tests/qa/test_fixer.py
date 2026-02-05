"""
Tests for qa.fixer module.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.backend.qa.fixer import load_qa_fixer_prompt, run_qa_fixer_session

from .conftest import create_async_response, create_async_response_exception, create_spec_files, MockMessage, MockBlock


class TestLoadQaFixerPrompt:
    """Tests for load_qa_fixer_prompt."""

    def test_load_prompt_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading the fixer prompt when file exists."""
        # Mock the prompt file path
        mock_prompt_content = "# QA Fixer Prompt\n\nFix the issues."
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = mock_prompt_content

        with patch("apps.backend.qa.fixer.QA_PROMPTS_DIR", Path("/mock/prompts")):
            with patch.object(Path, "__truediv__", return_value=mock_file):
                result = load_qa_fixer_prompt()

        assert result == mock_prompt_content

    def test_load_prompt_not_found(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test loading when prompt file doesn't exist."""
        from apps.backend.qa import fixer

        # Save the original value
        original_dir = fixer.QA_PROMPTS_DIR

        try:
            # Set to a non-existent path within temp directory
            nonexistent_dir = tmp_path / "does" / "not" / "exist"
            monkeypatch.setattr(fixer, "QA_PROMPTS_DIR", nonexistent_dir)
            with pytest.raises(FileNotFoundError, match="QA fixer prompt not found"):
                fixer.load_qa_fixer_prompt()
        finally:
            # Restore original value
            monkeypatch.setattr(fixer, "QA_PROMPTS_DIR", original_dir)


class TestRunQaFixerSession:
    """Tests for run_qa_fixer_session."""

    @pytest.mark.asyncio
    async def test_fixes_applied(self, temp_spec_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA fixer session successfully applies fixes."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        # Create QA_FIX_REQUEST.md
        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request\n\nFix the issues.")

        # Update plan to have ready_for_qa_revalidation
        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(temp_spec_dir, plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Applying fixes..."),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "test.py")}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_fixer_session(
            mock_sdk_client,
            temp_spec_dir,
            fix_session=1,
            verbose=False,
        )

        assert status == "fixed"
        assert "Applying fixes" in response

    @pytest.mark.asyncio
    async def test_fixes_assumed_applied(self, temp_spec_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test fixer returns 'fixed' even when status not updated."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Fixes applied."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_fixer_session(
            mock_sdk_client,
            temp_spec_dir,
            fix_session=1,
        )

        assert status == "fixed"
        # Status not updated but fixes assumed applied

    @pytest.mark.asyncio
    async def test_error_no_fix_request(self, temp_spec_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test fixer returns error when QA_FIX_REQUEST.md doesn't exist."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        status, response = await run_qa_fixer_session(
            mock_sdk_client,
            temp_spec_dir,
            fix_session=1,
        )

        assert status == "error"
        assert "QA_FIX_REQUEST.md not found" in response

    @pytest.mark.asyncio
    async def test_error_exception(self, temp_spec_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test fixer handles exceptions."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        mock_sdk_client.receive_response.return_value = create_async_response_exception(Exception("SDK error"))

        status, response = await run_qa_fixer_session(
            mock_sdk_client,
            temp_spec_dir,
            fix_session=1,
        )

        assert status == "error"
        assert "SDK error" in response

    @pytest.mark.asyncio
    async def test_with_project_dir(self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test fixer derives project_dir from spec_dir when not provided."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        # Update plan with ready_for_qa_revalidation
        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(temp_spec_dir, plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Fixing..."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        # Pass None for project_dir - should derive from spec_dir
        status, _ = await run_qa_fixer_session(
            mock_sdk_client,
            temp_spec_dir,
            fix_session=1,
            project_dir=None,
        )

        assert status == "fixed"

    @pytest.mark.asyncio
    async def test_with_memory_context(self, temp_spec_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test fixer loads memory context."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(temp_spec_dir, plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Fixes complete."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.fixer.get_graphiti_context", new_callable=AsyncMock) as mock_memory:
            mock_memory.return_value = "Previous fix patterns: Add error handling."

            status, _ = await run_qa_fixer_session(
                mock_sdk_client,
                temp_spec_dir,
                fix_session=1,
            )

            assert status == "fixed"
            mock_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_saves_memory_on_success(self, temp_spec_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test that fixer saves memory after successful session."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(temp_spec_dir, plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Done."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.fixer.save_session_memory", new_callable=AsyncMock) as mock_save:
            status, _ = await run_qa_fixer_session(
                mock_sdk_client,
                temp_spec_dir,
                fix_session=1,
            )

            assert status == "fixed"
            mock_save.assert_called_once()
            call_args = mock_save.call_args[1]
            assert call_args["success"] is True
            assert call_args["session_num"] == 1

    @pytest.mark.asyncio
    async def test_with_task_logger(self, temp_spec_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock, mock_task_logger: MagicMock) -> None:
        """Test fixer integrates with task logger."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(temp_spec_dir, plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Applying fixes..."),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": "/path/to/file.py"}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[MockBlock("ToolResultBlock", content="Success")],
            ),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.fixer.get_task_logger", return_value=mock_task_logger):
            status, _ = await run_qa_fixer_session(
                mock_sdk_client,
                temp_spec_dir,
                fix_session=1,
            )

            assert status == "fixed"
            # Verify logging occurred
            mock_task_logger.log.assert_called()
            mock_task_logger.tool_start.assert_called()
            mock_task_logger.tool_end.assert_called()

    @pytest.mark.asyncio
    async def test_verbose_mode(self, temp_spec_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock, capsys: pytest.CaptureFixture) -> None:
        """Test fixer with verbose mode."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(temp_spec_dir, plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Fixing..."),
                    MockBlock("ToolUseBlock", name="Bash", input_data={"command": "npm test"}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        await run_qa_fixer_session(
            mock_sdk_client,
            temp_spec_dir,
            fix_session=1,
            verbose=True,
        )

        captured = capsys.readouterr()
        # In verbose mode, tool input should be shown
        assert "Input:" in captured.out or "npm test" in captured.out

    @pytest.mark.asyncio
    async def test_handles_tool_error(self, temp_spec_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock, mock_task_logger: MagicMock) -> None:
        """Test fixer handles tool errors gracefully."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(temp_spec_dir, plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Running command..."),
                    MockBlock("ToolUseBlock", name="Bash", input_data={"command": "npm install"}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[
                    MockBlock("ToolResultBlock", is_error=True, content="Package not found"),
                ],
            ),
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Trying alternative..."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.fixer.get_task_logger", return_value=mock_task_logger):
            status, _ = await run_qa_fixer_session(
                mock_sdk_client,
                temp_spec_dir,
                fix_session=1,
            )

            assert status == "fixed"
            # Verify error was logged (check for at least one call with success=False)
            mock_task_logger.tool_end.assert_called()
            # Find any call with success=False
            has_error_call = any(
                call.kwargs.get("success") is False
                for call in mock_task_logger.tool_end.call_args_list
            )
            assert has_error_call, "Expected at least one tool_end call with success=False"

    @pytest.mark.asyncio
    async def test_includes_session_context(self, temp_spec_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test fixer includes session context in prompt."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(temp_spec_dir, plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Applying..."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        await run_qa_fixer_session(
            mock_sdk_client,
            temp_spec_dir,
            fix_session=5,
        )

        # Verify session context was in the prompt
        prompt_arg = mock_sdk_client.query.call_args[0][0]
        assert "**Fix Session**: 5" in prompt_arg
        assert str(temp_spec_dir) in prompt_arg
        assert "QA_FIX_REQUEST.md" in prompt_arg

"""
Tests for qa.reviewer module.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.backend.qa.reviewer import run_qa_agent_session

from .conftest import create_async_response, create_async_response_exception, create_spec_files, MockMessage, MockBlock


class TestRunQaAgentSession:
    """Tests for run_qa_agent_session."""

    @pytest.mark.asyncio
    async def test_approved_status(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer session with approved status."""
        create_spec_files(temp_spec_dir, approved_plan)

        # Mock SDK responses - use async iterator
        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="QA review complete. All criteria met."),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[
                    MockBlock("ToolResultBlock", content="Success"),
                ],
            ),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
            verbose=False,
        )

        assert status == "approved"
        assert "QA review complete" in response

    @pytest.mark.asyncio
    async def test_rejected_status(self, temp_spec_dir: Path, temp_project_dir: Path, rejected_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer session with rejected status."""
        create_spec_files(temp_spec_dir, rejected_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Found critical issues."),
                    MockBlock("ToolUseBlock", name="Write", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[MockBlock("ToolResultBlock", content="Success")],
            ),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
        )

        assert status == "rejected"
        assert "Found critical issues" in response

    @pytest.mark.asyncio
    async def test_error_status_no_update(self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer session when agent doesn't update plan."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        # Agent produces output but doesn't update implementation_plan.json
        messages = [
            MockMessage(
                "AssistantMessage",
                content=[MockBlock("TextBlock", text="Looking at files...")],
            ),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
        )

        assert status == "error"
        assert "did not update" in response

    @pytest.mark.asyncio
    async def test_error_status_exception(self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer session when exception occurs."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        mock_sdk_client.receive_response.return_value = create_async_response_exception(Exception("Connection lost"))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
        )

        assert status == "error"
        assert "Connection lost" in response

    @pytest.mark.asyncio
    async def test_with_previous_error_context(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer session with previous error context for self-correction."""
        create_spec_files(temp_spec_dir, approved_plan)

        previous_error = {
            "error_type": "missing_implementation_plan_update",
            "error_message": "Failed to update qa_signoff",
            "consecutive_errors": 2,
            "expected_action": "Update implementation_plan.json",
            "file_path": str(temp_spec_dir / "implementation_plan.json"),
        }

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Corrected QA review."),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[MockBlock("ToolResultBlock", content="Success")],
            ),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=3,
            max_iterations=50,
            previous_error=previous_error,
        )

        assert status == "approved"
        mock_sdk_client.query.assert_called_once()
        # Verify error context was in the prompt
        prompt_arg = mock_sdk_client.query.call_args[0][0]
        assert "PREVIOUS ITERATION FAILED" in prompt_arg
        assert "This is attempt 3" in prompt_arg

    @pytest.mark.asyncio
    async def test_with_memory_context(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer session loads memory context."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="QA complete."),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.get_graphiti_context", new_callable=AsyncMock) as mock_memory:
            mock_memory.return_value = "Previous QA patterns: Check authentication edge cases."

            status, response = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "approved"
            mock_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_saves_memory_on_approved(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test that memory is saved after successful QA."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Approved."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.save_session_memory", new_callable=AsyncMock) as mock_save:
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "approved"
            mock_save.assert_called_once()
            call_args = mock_save.call_args[1]
            assert call_args["success"] is True
            assert call_args["session_num"] == 1

    @pytest.mark.asyncio
    async def test_saves_memory_on_rejected(self, temp_spec_dir: Path, temp_project_dir: Path, rejected_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test that memory is saved after rejected QA with issues."""
        create_spec_files(temp_spec_dir, rejected_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Issues found."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.save_session_memory", new_callable=AsyncMock) as mock_save:
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "rejected"
            mock_save.assert_called_once()
            call_args = mock_save.call_args[1]
            assert call_args["success"] is False
            # Check that issues were captured in discoveries
            assert "gotchas_encountered" in call_args["discoveries"]

    @pytest.mark.asyncio
    async def test_with_task_logger(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock, mock_task_logger: MagicMock) -> None:
        """Test QA reviewer session integrates with task logger."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="QA review text output."),
                    MockBlock("ToolUseBlock", name="Read", input_data={"file_path": "/path/to/file.py"}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[
                    MockBlock("ToolResultBlock", content="File content here"),
                ],
            ),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.get_task_logger", return_value=mock_task_logger):
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "approved"
            # Verify text was logged
            mock_task_logger.log.assert_called()
            # Verify tool start/end was logged
            mock_task_logger.tool_start.assert_called()
            mock_task_logger.tool_end.assert_called()

    @pytest.mark.asyncio
    async def test_verbose_mode(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock, capsys: pytest.CaptureFixture) -> None:
        """Test QA reviewer session with verbose mode."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Reviewing..."),
                    MockBlock(
                        "ToolUseBlock",
                        name="Bash",
                        input_data={"command": "pytest tests/ -v"},
                    ),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
            verbose=True,
        )

        captured = capsys.readouterr()
        # In verbose mode, tool input should be shown
        assert "Input:" in captured.out or "pytest tests/" in captured.out

    @pytest.mark.asyncio
    async def test_handles_tool_error(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock, mock_task_logger: MagicMock) -> None:
        """Test QA reviewer handles tool errors gracefully."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Running tests..."),
                    MockBlock("ToolUseBlock", name="Bash", input_data={"command": "pytest"}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[
                    MockBlock("ToolResultBlock", is_error=True, content="Test failed: assertion error"),
                ],
            ),
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Tests failed, reviewing issues."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.get_task_logger", return_value=mock_task_logger):
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "approved"
            # Verify error was logged with success=False (check for at least one call)
            mock_task_logger.tool_end.assert_called()
            # Find any call with success=False
            has_error_call = any(
                call.kwargs.get("success") is False
                for call in mock_task_logger.tool_end.call_args_list
            )
            assert has_error_call, "Expected at least one tool_end call with success=False"

    @pytest.mark.asyncio
    async def test_no_messages_received(self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer when no messages are received."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response([]))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
        )

        assert status == "error"
        assert "No messages received" in response

    @pytest.mark.asyncio
    async def test_no_tools_used(self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer when agent doesn't use any tools."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[MockBlock("TextBlock", text="Looking at files...")],
            ),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
        )

        assert status == "error"
        assert "No tools were used" in response


class TestRunQaAgentSessionEdgeCases:
    """Tests for edge cases in run_qa_agent_session."""

    @pytest.mark.asyncio
    async def test_empty_response_text(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer with empty response text but valid status update."""
        create_spec_files(temp_spec_dir, approved_plan)

        # Agent updates the plan but produces no text output
        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock", content="Success")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
        )

        assert status == "approved"
        # Response may be empty, but status is correct

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer with multiple tool calls in sequence."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Reviewing tests..."),
                    MockBlock("ToolUseBlock", name="Read", input_data={"file_path": "/test1.py"}),
                    MockBlock("ToolUseBlock", name="Read", input_data={"file_path": "/test2.py"}),
                    MockBlock("ToolUseBlock", name="Bash", input_data={"command": "pytest"}),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[
                    MockBlock("ToolResultBlock", content="Content 1"),
                    MockBlock("ToolResultBlock", content="Content 2"),
                    MockBlock("ToolResultBlock", content="Tests passed"),
                    MockBlock("ToolResultBlock", content="Updated"),
                ],
            ),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
        )

        assert status == "approved"
        assert "Reviewing tests" in response

    @pytest.mark.asyncio
    async def test_tool_input_display_truncation(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test that long file paths in tool input are properly truncated."""
        create_spec_files(temp_spec_dir, approved_plan)

        long_path = "/very/long/path/that/goes/on/and/on/" + "x" * 100 + "/file.py"
        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Checking file..."),
                    MockBlock("ToolUseBlock", name="Read", input_data={"file_path": long_path}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
        )

        assert status == "approved"

    @pytest.mark.asyncio
    async def test_pattern_in_tool_input(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test Grep tool input displays pattern correctly."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Searching..."),
                    MockBlock("ToolUseBlock", name="Grep", input_data={"pattern": "def test_"}),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[
                    MockBlock("ToolResultBlock", content="Found matches"),
                    MockBlock("ToolResultBlock", content="Updated"),
                ],
            ),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
        )

        assert status == "approved"

    @pytest.mark.asyncio
    async def test_detail_content_stored_for_specific_tools(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock, mock_task_logger: MagicMock) -> None:
        """Test that detail content is stored for Read, Grep, Bash, Edit, Write tools."""
        create_spec_files(temp_spec_dir, approved_plan)

        large_content = "x" * 1000  # Under 50000 limit
        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Analyzing..."),
                    MockBlock("ToolUseBlock", name="Read", input_data={"file_path": "/test.py"}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[MockBlock("ToolResultBlock", content=large_content)],
            ),
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.get_task_logger", return_value=mock_task_logger):
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "approved"
            # Verify detail was stored for Read tool
            mock_task_logger.tool_end.assert_called()
            # Find the call with detail content
            has_detail_call = any(
                "detail" in call.kwargs and call.kwargs["detail"] is not None
                for call in mock_task_logger.tool_end.call_args_list
            )
            assert has_detail_call, "Expected tool_end to store detail content for Read tool"

    @pytest.mark.asyncio
    async def test_large_content_not_stored_in_detail(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock, mock_task_logger: MagicMock) -> None:
        """Test that very large content is not stored in detail."""
        create_spec_files(temp_spec_dir, approved_plan)

        huge_content = "x" * 60000  # Over 50000 limit
        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Reading large file..."),
                    MockBlock("ToolUseBlock", name="Read", input_data={"file_path": "/large.py"}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[MockBlock("ToolResultBlock", content=huge_content)],
            ),
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.get_task_logger", return_value=mock_task_logger):
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "approved"
            # Find the Read tool_end call - detail should be None for large content
            for call in mock_task_logger.tool_end.call_args_list:
                if "detail" in call.kwargs:
                    # Large content should not be stored
                    if call.kwargs.get("detail") is not None:
                        assert len(call.kwargs["detail"]) < 50000

    @pytest.mark.asyncio
    async def test_text_with_whitespace_only_not_logged(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock, mock_task_logger: MagicMock) -> None:
        """Test that whitespace-only text is not logged."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="   "),
                    MockBlock("TextBlock", text="\n\n"),
                    MockBlock("TextBlock", text="Actual content"),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.get_task_logger", return_value=mock_task_logger):
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "approved"
            # Should only log once for "Actual content", not for whitespace
            log_calls = [call for call in mock_task_logger.log.call_args_list]
            assert len(log_calls) <= 2  # At most one log call for actual content

    @pytest.mark.asyncio
    async def test_unknown_tool_name(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test handling of unknown tool names."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Using custom tool..."),
                    MockBlock("ToolUseBlock", name="UnknownTool", input_data={"data": "value"}),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[
                    MockBlock("ToolResultBlock", content="Tool result"),
                    MockBlock("ToolResultBlock", content="Updated"),
                ],
            ),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=1,
            max_iterations=50,
        )

        assert status == "approved"

    @pytest.mark.asyncio
    async def test_very_long_tool_error_truncated(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock, mock_task_logger: MagicMock) -> None:
        """Test that very long tool errors are truncated."""
        create_spec_files(temp_spec_dir, approved_plan)

        very_long_error = "Error: " + "x" * 1000
        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Running command..."),
                    MockBlock("ToolUseBlock", name="Bash", input_data={"command": "pytest"}),
                ],
            ),
            MockMessage(
                "UserMessage",
                content=[MockBlock("ToolResultBlock", is_error=True, content=very_long_error)],
            ),
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.get_task_logger", return_value=mock_task_logger):
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "approved"
            # Find the error call - should be truncated to 500 chars
            for call in mock_task_logger.tool_end.call_args_list:
                if call.kwargs.get("success") is False:
                    result = call.kwargs.get("result", "")
                    assert len(result) <= 500

    @pytest.mark.asyncio
    async def test_no_task_logger(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test QA reviewer works when task logger is not available."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="QA review..."),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(temp_spec_dir / "implementation_plan.json")}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.get_task_logger", return_value=None):
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "approved"

    @pytest.mark.asyncio
    async def test_session_context_in_prompt(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test that QA session number and max iterations are included in prompt."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Reviewing..."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        await run_qa_agent_session(
            mock_sdk_client,
            temp_project_dir,
            temp_spec_dir,
            qa_session=3,
            max_iterations=10,
        )

        # Verify session context was in the prompt
        prompt_arg = mock_sdk_client.query.call_args[0][0]
        assert "**QA Session**: 3" in prompt_arg
        assert "**Max Iterations**: 10" in prompt_arg

    @pytest.mark.asyncio
    async def test_memory_save_with_discoveries(self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test that memory save includes discoveries dictionary."""
        create_spec_files(temp_spec_dir, approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Approved."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.save_session_memory", new_callable=AsyncMock) as mock_save:
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=2,
                max_iterations=50,
            )

            assert status == "approved"
            call_args = mock_save.call_args[1]
            discoveries = call_args["discoveries"]
            assert "files_understood" in discoveries
            assert "patterns_found" in discoveries
            assert "gotchas_encountered" in discoveries
            # Verify pattern was added
            assert any("QA session 2" in p for p in discoveries["patterns_found"])

    @pytest.mark.asyncio
    async def test_rejected_issues_extracted_for_memory(self, temp_spec_dir: Path, temp_project_dir: Path, rejected_plan: dict, mock_sdk_client: MagicMock) -> None:
        """Test that rejected issues are properly extracted and saved to memory."""
        create_spec_files(temp_spec_dir, rejected_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Issues found."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        with patch("apps.backend.qa.reviewer.save_session_memory", new_callable=AsyncMock) as mock_save:
            status, _ = await run_qa_agent_session(
                mock_sdk_client,
                temp_project_dir,
                temp_spec_dir,
                qa_session=1,
                max_iterations=50,
            )

            assert status == "rejected"
            call_args = mock_save.call_args[1]
            discoveries = call_args["discoveries"]
            gotchas = discoveries["gotchas_encountered"]
            # Verify issues from rejected_plan are captured
            assert len(gotchas) == 2  # Two issues in rejected_plan fixture
            assert any("Test failure" in g for g in gotchas)
            assert any("Style issue" in g for g in gotchas)

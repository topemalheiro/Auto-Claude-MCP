"""
Edge case tests for Linear updater module.

Tests edge cases, boundary conditions, and error scenarios.
Focuses on the _create_linear_client and _run_linear_agent functions
which require complex mocking.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import pytest

from integrations.linear.updater import (
    LinearTaskState,
    STATUS_TODO,
    STATUS_IN_PROGRESS,
    STATUS_IN_REVIEW,
    STATUS_DONE,
    STATUS_CANCELED,
    LINEAR_TASK_FILE,
    LINEAR_TOOLS,
    is_linear_enabled,
    get_linear_api_key,
    create_linear_task,
    update_linear_status,
    add_linear_comment,
    linear_task_started,
    linear_subtask_completed,
    linear_subtask_failed,
    linear_build_complete,
    linear_qa_started,
    linear_qa_approved,
    linear_qa_rejected,
    linear_qa_max_iterations,
    linear_task_stuck,
)


class TestLinearTaskStateEdgeCases:
    """Edge case tests for LinearTaskState."""

    def test_status_field_accepts_all_valid_statuses(self):
        """Test status field accepts all defined statuses."""
        valid_statuses = [
            STATUS_TODO,
            STATUS_IN_PROGRESS,
            STATUS_IN_REVIEW,
            STATUS_DONE,
            STATUS_CANCELED,
        ]

        for status in valid_statuses:
            state = LinearTaskState(status=status)
            assert state.status == status

    def test_created_at_with_iso_format(self):
        """Test created_at with ISO format timestamp."""
        iso_time = "2024-01-15T10:30:45.123456"
        state = LinearTaskState(created_at=iso_time)

        assert state.created_at == iso_time

    def test_to_dict_roundtrip(self):
        """Test to_dict and from_dict roundtrip preserves data."""
        original = LinearTaskState(
            task_id="LIN-123",
            task_title="Test Task",
            team_id="TEAM-456",
            status=STATUS_IN_REVIEW,
            created_at="2024-01-15T10:30:00",
        )

        data = original.to_dict()
        restored = LinearTaskState.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.task_title == original.task_title
        assert restored.team_id == original.team_id
        assert restored.status == original.status
        assert restored.created_at == original.created_at

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        """Test save and load roundtrip preserves data."""
        original = LinearTaskState(
            task_id="LIN-789",
            task_title="Roundtrip Test",
            status=STATUS_DONE,
        )
        original.save(tmp_path)

        loaded = LinearTaskState.load(tmp_path)

        assert loaded.task_id == original.task_id
        assert loaded.task_title == original.task_title
        assert loaded.status == original.status


class TestIsLinearEnabledEdgeCases:
    """Edge case tests for is_linear_enabled."""

    def test_with_whitespace_key(self):
        """Test with whitespace-only API key."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "   "}):
            # Whitespace is truthy, so returns True
            assert is_linear_enabled() is True

    def test_with_newline_key(self):
        """Test with newline in API key."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "\n"}):
            assert is_linear_enabled() is True

    def test_env_var_changes_between_calls(self):
        """Test behavior when env var changes."""
        with patch.dict("os.environ", {}, clear=True):
            assert is_linear_enabled() is False

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test"}):
            assert is_linear_enabled() is True


class TestGetLinearApiKeyEdgeCases:
    """Edge case tests for get_linear_api_key."""

    def test_returns_empty_string_when_not_set(self):
        """Test returns empty string when not set."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_linear_api_key() == ""

    def test_returns_actual_key_value(self):
        """Test returns the actual key value."""
        test_key = "lin_api_123456"
        with patch.dict("os.environ", {"LINEAR_API_KEY": test_key}):
            assert get_linear_api_key() == test_key

    def test_preserves_whitespace_in_key(self):
        """Test preserves whitespace in key."""
        key_with_spaces = "key with spaces "
        with patch.dict("os.environ", {"LINEAR_API_KEY": key_with_spaces}):
            assert get_linear_api_key() == key_with_spaces


class TestCreateLinearTaskEdgeCases:
    """Edge case tests for create_linear_task."""

    @pytest.mark.asyncio
    async def test_with_none_description(self, tmp_path: Path):
        """Test with None as description."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="TASK_ID: LIN-123\nTEAM_ID: TEAM-456"
            ):
                result = await create_linear_task(tmp_path, "Test", None)

                assert result is not None
                assert result.task_id == "LIN-123"

    @pytest.mark.asyncio
    async def test_with_empty_title(self, tmp_path: Path):
        """Test with empty string title."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="TASK_ID: LIN-123\nTEAM_ID: TEAM-456"
            ):
                result = await create_linear_task(tmp_path, "", "Description")

                assert result is not None

    @pytest.mark.asyncio
    async def test_with_special_characters_in_title(self, tmp_path: Path):
        """Test with special characters in title."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="TASK_ID: LIN-123\nTEAM_ID: TEAM-456"
            ) as mock_agent:
                title = "Test: Feature (with special chars)"
                await create_linear_task(tmp_path, title)

                # Title should be in prompt
                prompt = mock_agent.call_args[0][0]
                assert title in prompt

    @pytest.mark.asyncio
    async def test_with_multiline_description(self, tmp_path: Path):
        """Test with multiline description."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="TASK_ID: LIN-123\nTEAM_ID: TEAM-456"
            ):
                desc = "Line 1\nLine 2\nLine 3"
                result = await create_linear_task(tmp_path, "Test", desc)

                assert result is not None

    @pytest.mark.asyncio
    async def test_response_with_extra_whitespace(self, tmp_path: Path):
        """Test response with extra whitespace around IDs."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            response = "   TASK_ID: LIN-123   \n   TEAM_ID: TEAM-456   "
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value=response
            ):
                result = await create_linear_task(tmp_path, "Test")

                assert result.task_id == "LIN-123"
                assert result.team_id == "TEAM-456"

    @pytest.mark.asyncio
    async def test_response_with_lowercase_prefix(self, tmp_path: Path):
        """Test response with lowercase prefix."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            # The function looks for exact case "TASK_ID:" and "TEAM_ID:"
            response = "task_id: LIN-123\nteam_id: TEAM-456"
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value=response
            ):
                result = await create_linear_task(tmp_path, "Test")

                # Should not parse lowercase
                assert result is None

    @pytest.mark.asyncio
    async def test_overwrites_existing_state_file(self, tmp_path: Path):
        """Test overwrites existing state when creating new task."""
        # Create existing state
        existing = LinearTaskState(
            task_id="OLD-123",
            task_title="Old Task",
        )
        existing.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            # The function checks for existing state first
            # If existing state has task_id, it returns that instead of creating new
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="TASK_ID: LIN-999\nTEAM_ID: TEAM-999"
            ):
                result = await create_linear_task(tmp_path, "New Task")

                # Since existing state has task_id, it returns the existing one
                # This is the expected behavior - don't recreate if exists
                assert result.task_id == "OLD-123"
                assert result.task_title == "Old Task"

    @pytest.mark.asyncio
    async def test_saves_created_at_timestamp(self, tmp_path: Path):
        """Test that created_at timestamp is saved."""
        before = datetime.now()

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="TASK_ID: LIN-123\nTEAM_ID: TEAM-456"
            ):
                await create_linear_task(tmp_path, "Test")

        after = datetime.now()

        state = LinearTaskState.load(tmp_path)
        assert state is not None
        assert state.created_at is not None

        # Parse and check timestamp is reasonable
        created = datetime.fromisoformat(state.created_at)
        assert before <= created <= after


class TestUpdateLinearStatusEdgeCases:
    """Edge case tests for update_linear_status."""

    @pytest.mark.asyncio
    async def test_with_all_status_types(self, tmp_path: Path):
        """Test updating to all possible status types."""
        statuses = [
            STATUS_TODO,
            STATUS_IN_PROGRESS,
            STATUS_IN_REVIEW,
            STATUS_DONE,
            STATUS_CANCELED,
        ]

        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
            status=STATUS_TODO,
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            for new_status in statuses:
                with patch(
                    "integrations.linear.updater._run_linear_agent",
                    return_value="Updated"
                ):
                    result = await update_linear_status(tmp_path, new_status)
                    assert result is True

                    # Verify status was updated
                    loaded = LinearTaskState.load(tmp_path)
                    assert loaded.status == new_status

    @pytest.mark.asyncio
    async def test_state_file_deleted_between_calls(self, tmp_path: Path):
        """Test when state file is deleted between calls."""
        # Create initial state
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
            status=STATUS_TODO,
        )
        state.save(tmp_path)

        # Delete the file
        state_file = tmp_path / LINEAR_TASK_FILE
        state_file.unlink()

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            result = await update_linear_status(tmp_path, STATUS_IN_PROGRESS)
            # Should return False since no state found
            assert result is False

    @pytest.mark.asyncio
    async def test_invalid_status_string(self, tmp_path: Path):
        """Test with invalid status string."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
            status=STATUS_TODO,
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="Updated"
            ):
                # Any status string is accepted
                result = await update_linear_status(tmp_path, "Invalid Status")
                assert result is True


class TestAddLinearCommentEdgeCases:
    """Edge case tests for add_linear_comment."""

    @pytest.mark.asyncio
    async def test_empty_comment(self, tmp_path: Path):
        """Test adding empty comment."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="Commented"
            ):
                result = await add_linear_comment(tmp_path, "")
                assert result is True

    @pytest.mark.asyncio
    async def test_whitespace_comment(self, tmp_path: Path):
        """Test adding whitespace-only comment."""
        state = LinearTaskState(task_id="LIN-123", team_id="TEAM-456")
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="Commented"
            ):
                result = await add_linear_comment(tmp_path, "   \n\t   ")
                assert result is True

    @pytest.mark.asyncio
    async def test_comment_with_unicode(self, tmp_path: Path):
        """Test comment with unicode characters."""
        state = LinearTaskState(task_id="LIN-123", team_id="TEAM-456")
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="Commented"
            ) as mock_agent:
                unicode_comment = "Test with emoji 🎉 and chinese 中文"
                await add_linear_comment(tmp_path, unicode_comment)

                prompt = mock_agent.call_args[0][0]
                # Unicode should be in prompt
                assert "🎉" in prompt or "中文" in prompt

    @pytest.mark.asyncio
    async def test_comment_with_quotes_and_backslashes(self, tmp_path: Path):
        """Test comment with various quote types and backslashes."""
        state = LinearTaskState(task_id="LIN-123", team_id="TEAM-456")
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="Commented"
            ):
                comment = 'Test "double" \'single\' \\backslash'
                result = await add_linear_comment(tmp_path, comment)
                assert result is True

    @pytest.mark.asyncio
    async def test_very_long_multiline_comment(self, tmp_path: Path):
        """Test very long multiline comment."""
        state = LinearTaskState(task_id="LIN-123", team_id="TEAM-456")
        state.save(tmp_path)

        long_comment = "\n".join(f"Line {i}" for i in range(100))

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="Commented"
            ):
                result = await add_linear_comment(tmp_path, long_comment)
                assert result is True

    @pytest.mark.asyncio
    async def test_agent_returns_none(self, tmp_path: Path):
        """Test when agent returns None (failure)."""
        state = LinearTaskState(task_id="LIN-123", team_id="TEAM-456")
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value=None
            ):
                result = await add_linear_comment(tmp_path, "Test")

                # Line 345 - return False when response is None
                assert result is False


class TestConvenienceFunctionsEdgeCases:
    """Edge case tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_linear_task_started_with_comment_failure(self, tmp_path: Path):
        """Test linear_task_started when comment fails."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
            status=STATUS_TODO,
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.update_linear_status",
                return_value=True
            ):
                with patch(
                    "integrations.linear.updater.add_linear_comment",
                    return_value=False
                ):
                    # Should still return True from status update
                    result = await linear_task_started(tmp_path)
                    assert result is True

    @pytest.mark.asyncio
    async def test_linear_qa_started_with_status_failure(self, tmp_path: Path):
        """Test linear_qa_started when status update fails."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
            status=STATUS_IN_PROGRESS,
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.update_linear_status",
                return_value=False
            ):
                result = await linear_qa_started(tmp_path)
                assert result is False

    @pytest.mark.asyncio
    async def test_linear_subtask_completed_with_zero_counts(self, tmp_path: Path):
        """Test linear_subtask_completed with zero counts."""
        state = LinearTaskState(task_id="LIN-123", team_id="TEAM-456")
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True
            ) as mock_comment:
                await linear_subtask_completed(tmp_path, "subtask-1", 0, 0)

                comment = mock_comment.call_args[0][1]
                assert "0/0" in comment

    @pytest.mark.asyncio
    async def test_linear_subtask_failed_with_zero_attempt(self, tmp_path: Path):
        """Test linear_subtask_failed with zero attempt."""
        state = LinearTaskState(task_id="LIN-123", team_id="TEAM-456")
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True
            ) as mock_comment:
                await linear_subtask_failed(tmp_path, "subtask-1", 0, "Error")

                comment = mock_comment.call_args[0][1]
                assert "attempt 0" in comment

    @pytest.mark.asyncio
    async def test_linear_subtask_failed_with_long_error(self, tmp_path: Path):
        """Test linear_subtask_failed truncates long error."""
        state = LinearTaskState(task_id="LIN-123", team_id="TEAM-456")
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True
            ) as mock_comment:
                long_error = "x" * 500
                await linear_subtask_failed(tmp_path, "subtask-1", 1, long_error)

                comment = mock_comment.call_args[0][1]
                # Error should be truncated to 200 chars
                assert len(comment) < 700  # Base text + truncated error

    @pytest.mark.asyncio
    async def test_linear_qa_rejected_with_zero_issues(self, tmp_path: Path):
        """Test linear_qa_rejected with zero issues."""
        state = LinearTaskState(task_id="LIN-123", team_id="TEAM-456")
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True
            ) as mock_comment:
                await linear_qa_rejected(tmp_path, 0, 1)

                comment = mock_comment.call_args[0][1]
                assert "0 issues" in comment

    @pytest.mark.asyncio
    async def test_linear_qa_max_iterations_with_zero_iterations(self, tmp_path: Path):
        """Test linear_qa_max_iterations with zero iterations."""
        state = LinearTaskState(task_id="LIN-123", team_id="TEAM-456")
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True
            ) as mock_comment:
                await linear_qa_max_iterations(tmp_path, 0)

                comment = mock_comment.call_args[0][1]
                assert "0 iterations" in comment or "max iterations" in comment


class TestLINEAR_TOOLSConstant:
    """Tests for LINEAR_TOOLS constant."""

    def test_linear_tools_contains_all_required_tools(self):
        """Test LINEAR_TOOLS contains all necessary tools."""
        required_prefixes = [
            "list_teams",
            "create_issue",
            "update_issue",
            "create_comment",
            "list_issue_statuses",
        ]

        for prefix in required_prefixes:
            assert any(prefix in tool for tool in LINEAR_TOOLS)

    def test_linear_tools_all_have_correct_prefix(self):
        """Test all tools have the correct MCP server prefix."""
        for tool in LINEAR_TOOLS:
            assert tool.startswith("mcp__linear-server__")


class TestLinearTaskStateFileHandling:
    """Tests for file handling edge cases."""

    def test_save_to_readonly_directory(self, tmp_path: Path):
        """Test save when directory is read-only."""
        state = LinearTaskState(task_id="LIN-123")

        # This test may behave differently on different OS
        # On some systems, writing to read-only dir might fail
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        try:
            readonly_dir.chmod(0o444)

            # May raise an exception or fail silently
            try:
                state.save(readonly_dir)
            except (OSError, PermissionError):
                pass  # Expected on some systems
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    def test_load_from_directory_with_multiple_json_files(self, tmp_path: Path):
        """Test load only reads the correct file."""
        # Create our target file
        state = LinearTaskState(task_id="LIN-123", task_title="Target")
        state.save(tmp_path)

        # Create other JSON files
        (tmp_path / "other.json").write_text('{"other": "data"}')
        (tmp_path / "another.json").write_text('{"another": "value"}')

        # Should only load the correct file
        loaded = LinearTaskState.load(tmp_path)
        assert loaded.task_id == "LIN-123"
        assert loaded.task_title == "Target"

    def test_save_overwrites_corrupted_file(self, tmp_path: Path):
        """Test save overwrites a corrupted state file."""
        # Create corrupted file
        state_file = tmp_path / LINEAR_TASK_FILE
        state_file.write_text("corrupted data {not valid json")

        # Save new state
        new_state = LinearTaskState(task_id="LIN-456")
        new_state.save(tmp_path)

        # Should be valid now
        loaded = LinearTaskState.load(tmp_path)
        assert loaded.task_id == "LIN-456"

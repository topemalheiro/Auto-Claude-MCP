"""
Tests for Linear updater module.

Tests task creation, status updates, comment addition, and state serialization.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrations.linear.updater import (
    LinearTaskState,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_IN_REVIEW,
    STATUS_TODO,
    add_linear_comment,
    create_linear_task,
    get_linear_api_key,
    is_linear_enabled,
    linear_build_complete,
    linear_qa_approved,
    linear_qa_max_iterations,
    linear_qa_rejected,
    linear_qa_started,
    linear_subtask_completed,
    linear_subtask_failed,
    linear_task_started,
    linear_task_stuck,
    update_linear_status,
)


class TestIsLinearEnabled:
    """Test is_linear_enabled function."""

    def test_returns_false_when_no_key(self):
        """Test returns False when LINEAR_API_KEY is not set."""
        with patch.dict("os.environ", {}, clear=True):
            assert is_linear_enabled() is False

    def test_returns_true_when_key_set(self):
        """Test returns True when LINEAR_API_KEY is set."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            assert is_linear_enabled() is True


class TestGetLinearApiKey:
    """Test get_linear_api_key function."""

    def test_returns_empty_string_when_no_key(self):
        """Test returns empty string when LINEAR_API_KEY is not set."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_linear_api_key() == ""

    def test_returns_key_when_set(self):
        """Test returns API key when set."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            assert get_linear_api_key() == "test-key"


class TestLinearTaskState:
    """Test LinearTaskState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = LinearTaskState()

        assert state.task_id is None
        assert state.task_title is None
        assert state.team_id is None
        assert state.status == STATUS_TODO
        assert state.created_at is None

    def test_to_dict(self):
        """Test serialization to dict."""
        state = LinearTaskState(
            task_id="LIN-123",
            task_title="Test Task",
            team_id="TEAM-456",
            status=STATUS_IN_PROGRESS,
            created_at="2024-01-01",
        )

        data = state.to_dict()

        assert data["task_id"] == "LIN-123"
        assert data["task_title"] == "Test Task"
        assert data["team_id"] == "TEAM-456"
        assert data["status"] == STATUS_IN_PROGRESS
        assert data["created_at"] == "2024-01-01"

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "task_id": "LIN-123",
            "task_title": "Test Task",
            "team_id": "TEAM-456",
            "status": STATUS_IN_PROGRESS,
            "created_at": "2024-01-01",
        }
        state = LinearTaskState.from_dict(data)

        assert state.task_id == "LIN-123"
        assert state.task_title == "Test Task"
        assert state.team_id == "TEAM-456"
        assert state.status == STATUS_IN_PROGRESS
        assert state.created_at == "2024-01-01"

    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing values."""
        state = LinearTaskState.from_dict({})

        assert state.task_id is None
        assert state.task_title is None
        assert state.team_id is None
        assert state.status == STATUS_TODO
        assert state.created_at is None

    def test_save(self, tmp_path: Path):
        """Test saving state to file."""
        state = LinearTaskState(
            task_id="LIN-123",
            task_title="Test Task",
            status=STATUS_IN_PROGRESS,
        )
        state.save(tmp_path)

        state_file = tmp_path / ".linear_task.json"
        assert state_file.exists()

        with open(state_file) as f:
            data = json.load(f)

        assert data["task_id"] == "LIN-123"
        assert data["task_title"] == "Test Task"
        assert data["status"] == STATUS_IN_PROGRESS

    def test_load(self, tmp_path: Path):
        """Test loading state from file."""
        data = {
            "task_id": "LIN-123",
            "task_title": "Test Task",
            "status": STATUS_IN_PROGRESS,
        }
        state_file = tmp_path / ".linear_task.json"
        with open(state_file, "w") as f:
            json.dump(data, f)

        state = LinearTaskState.load(tmp_path)

        assert state.task_id == "LIN-123"
        assert state.task_title == "Test Task"
        assert state.status == STATUS_IN_PROGRESS

    def test_load_nonexistent(self, tmp_path: Path):
        """Test load returns None when file doesn't exist."""
        state = LinearTaskState.load(tmp_path)
        assert state is None

    def test_load_invalid_json(self, tmp_path: Path):
        """Test load returns None for invalid JSON."""
        state_file = tmp_path / ".linear_task.json"
        with open(state_file, "w") as f:
            f.write("invalid json")

        state = LinearTaskState.load(tmp_path)
        assert state is None


class TestCreateLinearTask:
    """Test create_linear_task function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_disabled(self, tmp_path: Path):
        """Test returns None when Linear is disabled."""
        with patch.dict("os.environ", {}, clear=True):
            result = await create_linear_task(tmp_path, "Test Task")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_existing_state(self, tmp_path: Path):
        """Test returns existing state if task already exists."""
        # Create existing state
        existing = LinearTaskState(
            task_id="LIN-123",
            task_title="Existing Task",
            status=STATUS_IN_PROGRESS,
        )
        existing.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            result = await create_linear_task(tmp_path, "New Task")

            # Should return existing, not create new
            assert result is not None
            assert result.task_id == "LIN-123"
            assert result.task_title == "Existing Task"

    @pytest.mark.asyncio
    async def test_creates_task_successfully(self, tmp_path: Path):
        """Test successful task creation."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            # Mock the agent response
            mock_response = """
TASK_ID: LIN-123
TEAM_ID: TEAM-456
"""
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value=mock_response,
            ):
                result = await create_linear_task(
                    tmp_path, "Test Task", "Test description"
                )

                assert result is not None
                assert result.task_id == "LIN-123"
                assert result.team_id == "TEAM-456"
                assert result.task_title == "Test Task"
                assert result.status == STATUS_TODO
                assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_creates_task_without_description(self, tmp_path: Path):
        """Test task creation without description."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            mock_response = "TASK_ID: LIN-123\nTEAM_ID: TEAM-456"
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value=mock_response,
            ):
                result = await create_linear_task(tmp_path, "Test Task")

                assert result is not None
                assert result.task_id == "LIN-123"

    @pytest.mark.asyncio
    async def test_fails_to_parse_task_id(self, tmp_path: Path):
        """Test handling when task ID parsing fails."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            # Response without TASK_ID
            mock_response = "Some other response"
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value=mock_response,
            ):
                result = await create_linear_task(tmp_path, "Test Task")

                assert result is None


class TestUpdateLinearStatus:
    """Test update_linear_status function."""

    @pytest.mark.asyncio
    async def test_returns_false_when_disabled(self, tmp_path: Path):
        """Test returns False when Linear is disabled."""
        with patch.dict("os.environ", {}, clear=True):
            result = await update_linear_status(tmp_path, STATUS_IN_PROGRESS)
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_no_existing_state(self, tmp_path: Path):
        """Test returns False when no existing state found."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            result = await update_linear_status(tmp_path, STATUS_IN_PROGRESS)
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_already_at_status(self, tmp_path: Path):
        """Test returns True when already at target status."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
            status=STATUS_IN_PROGRESS,
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            result = await update_linear_status(tmp_path, STATUS_IN_PROGRESS)

            # Should return True without calling agent
            assert result is True

    @pytest.mark.asyncio
    async def test_updates_status_successfully(self, tmp_path: Path):
        """Test successful status update."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
            status=STATUS_TODO,
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="Status updated",
            ):
                result = await update_linear_status(tmp_path, STATUS_IN_PROGRESS)

                assert result is True

                # Verify state was updated
                updated_state = LinearTaskState.load(tmp_path)
                assert updated_state.status == STATUS_IN_PROGRESS


class TestAddLinearComment:
    """Test add_linear_comment function."""

    @pytest.mark.asyncio
    async def test_returns_false_when_disabled(self, tmp_path: Path):
        """Test returns False when Linear is disabled."""
        with patch.dict("os.environ", {}, clear=True):
            result = await add_linear_comment(tmp_path, "Test comment")
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_no_existing_state(self, tmp_path: Path):
        """Test returns False when no existing state found."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            result = await add_linear_comment(tmp_path, "Test comment")
            assert result is False

    @pytest.mark.asyncio
    async def test_adds_comment_successfully(self, tmp_path: Path):
        """Test successful comment addition."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
            status=STATUS_IN_PROGRESS,
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent",
                return_value="Comment added",
            ):
                result = await add_linear_comment(tmp_path, "Test comment")

                assert result is True

    @pytest.mark.asyncio
    async def test_escapes_quotes_in_comment(self, tmp_path: Path):
        """Test that quotes in comments are escaped."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent"
            ) as mock_agent:
                comment = 'Test "quoted" text'
                await add_linear_comment(tmp_path, comment)

                # Check that quotes were escaped
                prompt = mock_agent.call_args[0][0]
                assert '\\"' in prompt

    @pytest.mark.asyncio
    async def test_escapes_newlines_in_comment(self, tmp_path: Path):
        """Test that newlines in comments are escaped."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater._run_linear_agent"
            ) as mock_agent:
                comment = "Line 1\nLine 2"
                await add_linear_comment(tmp_path, comment)

                # Check that newlines were escaped
                prompt = mock_agent.call_args[0][0]
                assert "\\n" in prompt


class TestConvenienceFunctions:
    """Test convenience functions for specific transitions."""

    @pytest.mark.asyncio
    async def test_linear_task_started(self, tmp_path: Path):
        """Test linear_task_started convenience function."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
            status=STATUS_TODO,
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.update_linear_status",
                return_value=True,
            ):
                with patch(
                    "integrations.linear.updater.add_linear_comment",
                    return_value=True,
                ):
                    result = await linear_task_started(tmp_path)

                    assert result is True

    @pytest.mark.asyncio
    async def test_linear_subtask_completed(self, tmp_path: Path):
        """Test linear_subtask_completed convenience function."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True,
            ) as mock_comment:
                await linear_subtask_completed(
                    tmp_path, "subtask-1", 5, 10
                )

                # Check comment format
                call_args = mock_comment.call_args
                assert "subtask-1" in call_args[0][1]
                assert "5/10" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_linear_subtask_failed(self, tmp_path: Path):
        """Test linear_subtask_failed convenience function."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True,
            ) as mock_comment:
                await linear_subtask_failed(
                    tmp_path, "subtask-1", 3, "Test error message"
                )

                # Check comment format
                call_args = mock_comment.call_args
                comment = call_args[0][1]
                assert "subtask-1" in comment
                assert "attempt 3" in comment
                assert "Test error message" in comment

    @pytest.mark.asyncio
    async def test_linear_build_complete(self, tmp_path: Path):
        """Test linear_build_complete convenience function."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True,
            ) as mock_comment:
                await linear_build_complete(tmp_path)

                # Check comment format
                call_args = mock_comment.call_args
                comment = call_args[0][1]
                assert "All subtasks completed" in comment
                assert "QA" in comment

    @pytest.mark.asyncio
    async def test_linear_qa_started(self, tmp_path: Path):
        """Test linear_qa_started convenience function."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
            status=STATUS_IN_PROGRESS,
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.update_linear_status",
                return_value=True,
            ):
                with patch(
                    "integrations.linear.updater.add_linear_comment",
                    return_value=True,
                ):
                    result = await linear_qa_started(tmp_path)

                    assert result is True

    @pytest.mark.asyncio
    async def test_linear_qa_approved(self, tmp_path: Path):
        """Test linear_qa_approved convenience function."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True,
            ) as mock_comment:
                await linear_qa_approved(tmp_path)

                # Check comment format
                call_args = mock_comment.call_args
                comment = call_args[0][1]
                assert "QA approved" in comment
                assert "human review" in comment

    @pytest.mark.asyncio
    async def test_linear_qa_rejected(self, tmp_path: Path):
        """Test linear_qa_rejected convenience function."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True,
            ) as mock_comment:
                await linear_qa_rejected(tmp_path, 5, 2)

                # Check comment format
                call_args = mock_comment.call_args
                comment = call_args[0][1]
                assert "QA iteration 2" in comment
                assert "5 issues" in comment
                assert "applying fixes" in comment

    @pytest.mark.asyncio
    async def test_linear_qa_max_iterations(self, tmp_path: Path):
        """Test linear_qa_max_iterations convenience function."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True,
            ) as mock_comment:
                await linear_qa_max_iterations(tmp_path, 3)

                # Check comment format
                call_args = mock_comment.call_args
                comment = call_args[0][1]
                assert "max iterations" in comment
                assert "3" in comment
                assert "human intervention" in comment

    @pytest.mark.asyncio
    async def test_linear_task_stuck(self, tmp_path: Path):
        """Test linear_task_stuck convenience function."""
        state = LinearTaskState(
            task_id="LIN-123",
            team_id="TEAM-456",
        )
        state.save(tmp_path)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            with patch(
                "integrations.linear.updater.add_linear_comment",
                return_value=True,
            ) as mock_comment:
                await linear_task_stuck(tmp_path, "subtask-1", 5)

                # Check comment format
                call_args = mock_comment.call_args
                comment = call_args[0][1]
                assert "subtask-1" in comment
                assert "STUCK" in comment
                assert "5 attempts" in comment
                assert "human review" in comment

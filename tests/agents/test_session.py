"""Tests for agents.session module."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

from agents.session import is_tool_concurrency_error, post_session_processing, run_agent_session
from task_logger import LogPhase, LogEntryType


class TestIsToolConcurrencyError:
    """Test is_tool_concurrency_error function."""

    def test_returns_false_for_none(self):
        """Test that None error returns False."""
        assert is_tool_concurrency_error(None) is False

    def test_returns_false_for_non_concurrency_error(self):
        """Test that non-concurrency errors return False."""
        error = ValueError("some other error")
        assert is_tool_concurrency_error(error) is False

    def test_returns_false_for_400_without_concurrency(self):
        """Test that 400 error without concurrency keywords returns False."""
        error = Exception("400 bad request")
        assert is_tool_concurrency_error(error) is False

    def test_returns_true_for_400_with_tool_concurrency(self):
        """Test that 400 with 'tool' and 'concurrency' returns True."""
        error = Exception("400 error: too many tool use concurrency")
        assert is_tool_concurrency_error(error) is True

    def test_returns_true_for_400_with_too_many_tools(self):
        """Test that 400 with 'too many tools' returns True."""
        error = Exception("400: too many tools in request")
        assert is_tool_concurrency_error(error) is True

    def test_returns_true_for_400_with_concurrent_tool(self):
        """Test that 400 with 'concurrent tool' returns True."""
        error = Exception("400: concurrent tool limit exceeded")
        assert is_tool_concurrency_error(error) is True

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        error = Exception("400: TOOL CONCURRENCY ERROR")
        assert is_tool_concurrency_error(error) is True

    def test_returns_false_for_non_400_concurrency_error(self):
        """Test that non-400 concurrency errors return False."""
        error = Exception("500 error: tool concurrency")
        assert is_tool_concurrency_error(error) is False


class TestPostSessionProcessing:
    """Test post_session_processing function."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.fixture
    def mock_plan(self, mock_spec_dir):
        """Create a mock implementation plan."""
        import json

        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {
                            "id": "subtask-1",
                            "description": "Test subtask",
                            "status": "completed",
                        }
                    ],
                }
            ],
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))
        return plan

    @pytest.mark.asyncio
    async def test_completed_subtask(self, mock_spec_dir, mock_project_dir):
        """Test processing for completed subtask."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is True
            recovery_manager.record_attempt.assert_called_once()
            status_manager.update_subtasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_completed_subtask_with_sync(self, mock_spec_dir, mock_project_dir):
        """Test completed subtask with spec sync to source."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=True), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_completed_subtask_with_new_commit(self, mock_spec_dir, mock_project_dir):
        """Test completed subtask with new commit recorded."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.get_latest_commit", return_value="def456"), \
             patch("agents.session.get_commit_count", return_value=6), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is True
            recovery_manager.record_good_commit.assert_called_once_with("def456", "subtask-1")

    @pytest.mark.asyncio
    async def test_completed_subtask_with_linear_enabled(self, mock_spec_dir, mock_project_dir):
        """Test completed subtask with Linear integration enabled."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        recovery_manager.get_attempt_count = MagicMock(return_value=1)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 5}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")), \
             patch("agents.session.linear_subtask_completed", new_callable=AsyncMock) as mock_linear:

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=True,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is True
            mock_linear.assert_called_once()

    @pytest.mark.asyncio
    async def test_completed_subtask_with_insights(self, mock_spec_dir, mock_project_dir):
        """Test completed subtask with extracted insights."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        insights = {
            "file_insights": ["file1.py: modified function"],
            "patterns_discovered": ["pattern1: uses factory pattern"],
        }

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value=insights), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_completed_subtask_insight_extraction_fails(self, mock_spec_dir, mock_project_dir):
        """Test completed subtask when insight extraction fails."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, side_effect=Exception("Extraction failed")), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            # Should still complete successfully even if insight extraction fails
            assert result is True

    @pytest.mark.asyncio
    async def test_completed_subtask_file_based_memory(self, mock_spec_dir, mock_project_dir):
        """Test completed subtask with file-based memory fallback."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "file")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_completed_subtask_memory_save_fails(self, mock_spec_dir, mock_project_dir):
        """Test completed subtask when memory save fails."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(False, None)):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            # Should still complete successfully even if memory save fails
            assert result is True

    @pytest.mark.asyncio
    async def test_completed_subtask_memory_save_raises(self, mock_spec_dir, mock_project_dir):
        """Test completed subtask when memory save raises exception."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, side_effect=Exception("Save failed")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            # Should still complete successfully even if memory save raises
            assert result is True

    @pytest.mark.asyncio
    async def test_in_progress_subtask(self, mock_spec_dir, mock_project_dir):
        """Test processing for in_progress subtask."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "in_progress"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "in_progress"}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is False
            recovery_manager.record_attempt.assert_called_once()

    @pytest.mark.asyncio
    async def test_in_progress_subtask_with_new_commit(self, mock_spec_dir, mock_project_dir):
        """Test in_progress subtask with partial progress commit."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "in_progress"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "in_progress"}), \
             patch("agents.session.get_latest_commit", return_value="def456"), \
             patch("agents.session.get_commit_count", return_value=6), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is False
            recovery_manager.record_good_commit.assert_called_once_with("def456", "subtask-1")

    @pytest.mark.asyncio
    async def test_in_progress_subtask_with_linear(self, mock_spec_dir, mock_project_dir):
        """Test in_progress subtask with Linear integration."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        recovery_manager.get_attempt_count = MagicMock(return_value=2)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "in_progress"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "in_progress"}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")), \
             patch("agents.session.linear_subtask_failed", new_callable=AsyncMock) as mock_linear:

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=True,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is False
            mock_linear.assert_called_once()

    @pytest.mark.asyncio
    async def test_in_progress_insight_extraction_fails(self, mock_spec_dir, mock_project_dir):
        """Test in_progress subtask when insight extraction fails."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "in_progress"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "in_progress"}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, side_effect=Exception("Extraction failed")), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            # Should still return False even if insight extraction fails
            assert result is False

    @pytest.mark.asyncio
    async def test_in_progress_memory_save_fails(self, mock_spec_dir, mock_project_dir):
        """Test in_progress subtask when memory save fails."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "in_progress"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "in_progress"}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, side_effect=Exception("Save failed")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            # Should still return False even if memory save fails
            assert result is False

    @pytest.mark.asyncio
    async def test_pending_subtask(self, mock_spec_dir, mock_project_dir):
        """Test processing for pending subtask (no progress)."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        recovery_manager.get_attempt_count = MagicMock(return_value=1)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "pending"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "pending"}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")), \
             patch("agents.session.linear_subtask_failed", new_callable=AsyncMock) as mock_linear:

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=True,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is False
            recovery_manager.record_attempt.assert_called_once()
            mock_linear.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_subtask(self, mock_spec_dir, mock_project_dir):
        """Test processing for failed subtask."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        recovery_manager.get_attempt_count = MagicMock(return_value=3)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "failed"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "failed"}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={
                 "file_insights": ["file1.py: attempted fix"],
                 "patterns_discovered": [],
             }), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")), \
             patch("agents.session.linear_subtask_failed", new_callable=AsyncMock) as mock_linear:

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=True,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is False
            recovery_manager.record_attempt.assert_called_once()
            mock_linear.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_subtask_insight_extraction_fails(self, mock_spec_dir, mock_project_dir):
        """Test failed subtask when insight extraction fails."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        recovery_manager.get_attempt_count = MagicMock(return_value=1)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "failed"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "failed"}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, side_effect=Exception("Extraction failed")), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")), \
             patch("agents.session.linear_subtask_failed", new_callable=AsyncMock):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=True,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            # Should still return False even if insight extraction fails
            assert result is False

    @pytest.mark.asyncio
    async def test_failed_subtask_memory_save_fails(self, mock_spec_dir, mock_project_dir):
        """Test failed subtask when memory save fails."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        recovery_manager.get_attempt_count = MagicMock(return_value=1)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "failed"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "failed"}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, side_effect=Exception("Save failed")), \
             patch("agents.session.linear_subtask_failed", new_callable=AsyncMock):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=True,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            # Should still return False even if memory save fails
            assert result is False

    @pytest.mark.asyncio
    async def test_no_plan_found(self, mock_spec_dir, mock_project_dir):
        """Test when implementation plan cannot be loaded."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value=None):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_subtask_not_found(self, mock_spec_dir, mock_project_dir):
        """Test when subtask is not found in plan."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "other"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value=None):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is False


class TestRunAgentSession:
    """Test run_agent_session function."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.mark.asyncio
    async def test_successful_session_continue(self, mock_spec_dir):
        """Test a successful session that returns continue status."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock messages simulating a response
        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"

        # Create a proper mock for the TextBlock with text attribute
        mock_text_block = MagicMock()
        mock_text_block.__class__.__name__ = "TextBlock"
        mock_text_block.text = "Response text"

        mock_assistant_message.content = [mock_text_block]

        # Setup receive_response to yield messages and then stop
        async def mock_receive():
            yield mock_assistant_message
            # No more messages - generator stops

        mock_client.receive_response = mock_receive

        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=MagicMock()):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            # The response should accumulate text from the message
            assert response == "Response text"
            assert error_info == {}

    @pytest.mark.asyncio
    async def test_successful_session_complete(self, mock_spec_dir):
        """Test a successful session that returns complete status."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"

        # Create a proper mock for the TextBlock with text attribute
        mock_text_block = MagicMock()
        mock_text_block.__class__.__name__ = "TextBlock"
        mock_text_block.text = "Done"

        mock_assistant_message.content = [mock_text_block]

        async def mock_receive():
            yield mock_assistant_message

        mock_client.receive_response = mock_receive

        with patch("agents.session.is_build_complete", return_value=True), \
             patch("agents.session.get_task_logger", return_value=MagicMock()):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "complete"
            assert response == "Done"
            assert error_info == {}

    @pytest.mark.asyncio
    async def test_session_with_concurrency_error(self, mock_spec_dir):
        """Test session handling tool concurrency error."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(side_effect=Exception("400: tool concurrency error"))

        with patch("agents.session.get_task_logger", return_value=MagicMock()):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "error"
            assert error_info["type"] == "tool_concurrency"
            assert "400" in error_info["message"]

    @pytest.mark.asyncio
    async def test_session_with_generic_error(self, mock_spec_dir):
        """Test session handling generic error."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(side_effect=ValueError("Some error"))

        with patch("agents.session.get_task_logger", return_value=MagicMock()):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "error"
            assert error_info["type"] == "other"
            assert "Some error" in error_info["message"]
            assert error_info["exception_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_session_with_tool_use_pattern(self, mock_spec_dir):
        """Test session with tool use containing pattern input."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block with pattern input
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Grep"
        mock_tool_use_block.input = {"pattern": "test.*pattern", "path": "/test"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        # Create mock result block
        mock_result_block = MagicMock()
        mock_result_block.__class__.__name__ = "ToolResultBlock"
        mock_result_block.content = "Found 5 matches"
        mock_result_block.is_error = False

        mock_user_message = MagicMock()
        mock_user_message.__class__.__name__ = "UserMessage"
        mock_user_message.content = [mock_result_block]

        async def mock_receive():
            yield mock_assistant_message
            yield mock_user_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"pattern": "test.*pattern", "path": "/test"}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            mock_logger.tool_start.assert_called_once()
            mock_logger.tool_end.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_with_tool_use_file_path(self, mock_spec_dir):
        """Test session with tool use containing file_path input."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block with long file path
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Read"
        mock_tool_use_block.input = {"file_path": "/very/long/path/that/exceeds/fifty/characters/and/needs/to/be/truncated.txt"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        async def mock_receive():
            yield mock_assistant_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"file_path": "/very/long/path/that/exceeds/fifty/characters/and/needs/to/be/truncated.txt"}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            mock_logger.tool_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_with_tool_use_command(self, mock_spec_dir):
        """Test session with tool use containing command input."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block with long command
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Bash"
        mock_tool_use_block.input = {"command": "very long command that exceeds fifty characters and needs truncation"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        async def mock_receive():
            yield mock_assistant_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"command": "very long command that exceeds fifty characters and needs truncation"}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            mock_logger.tool_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_with_tool_result_blocked(self, mock_spec_dir):
        """Test session with blocked tool result."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Bash"
        mock_tool_use_block.input = {"command": "rm -rf /"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        # Create mock blocked result
        mock_result_block = MagicMock()
        mock_result_block.__class__.__name__ = "ToolResultBlock"
        mock_result_block.content = "Command blocked by security policy"
        mock_result_block.is_error = True

        mock_user_message = MagicMock()
        mock_user_message.__class__.__name__ = "UserMessage"
        mock_user_message.content = [mock_result_block]

        async def mock_receive():
            yield mock_assistant_message
            yield mock_user_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"command": "rm -rf /"}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            # Verify tool_end was called with success=False
            mock_logger.tool_end.assert_called_once()
            call_kwargs = mock_logger.tool_end.call_args[1]
            assert call_kwargs["success"] is False
            assert call_kwargs["result"] == "BLOCKED"

    @pytest.mark.asyncio
    async def test_session_with_tool_result_error(self, mock_spec_dir):
        """Test session with tool result error (not blocked)."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Bash"
        mock_tool_use_block.input = {"command": "invalid command"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        # Create mock error result
        mock_result_block = MagicMock()
        mock_result_block.__class__.__name__ = "ToolResultBlock"
        mock_result_block.content = "command not found: invalid"
        mock_result_block.is_error = True

        mock_user_message = MagicMock()
        mock_user_message.__class__.__name__ = "UserMessage"
        mock_user_message.content = [mock_result_block]

        async def mock_receive():
            yield mock_assistant_message
            yield mock_user_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"command": "invalid command"}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            mock_logger.tool_end.assert_called_once()
            call_kwargs = mock_logger.tool_end.call_args[1]
            assert call_kwargs["success"] is False

    @pytest.mark.asyncio
    async def test_session_with_tool_result_success_verbose(self, mock_spec_dir):
        """Test session with successful tool result in verbose mode."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Bash"
        mock_tool_use_block.input = {"command": "echo test"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        # Create mock success result
        mock_result_block = MagicMock()
        mock_result_block.__class__.__name__ = "ToolResultBlock"
        mock_result_block.content = "test output"
        mock_result_block.is_error = False

        mock_user_message = MagicMock()
        mock_user_message.__class__.__name__ = "UserMessage"
        mock_user_message.content = [mock_result_block]

        async def mock_receive():
            yield mock_assistant_message
            yield mock_user_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"command": "echo test"}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=True,  # Enable verbose mode
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            mock_logger.tool_end.assert_called_once()
            call_kwargs = mock_logger.tool_end.call_args[1]
            assert call_kwargs["success"] is True

    @pytest.mark.asyncio
    async def test_session_with_text_logging(self, mock_spec_dir):
        """Test session with text block logging to task logger."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock text block
        mock_text_block = MagicMock()
        mock_text_block.__class__.__name__ = "TextBlock"
        mock_text_block.text = "Here is some response text with content"

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_text_block]

        async def mock_receive():
            yield mock_assistant_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            assert response == "Here is some response text with content"
            # Verify log was called with TEXT type
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args[0]
            assert call_args[1] == LogEntryType.TEXT

    @pytest.mark.asyncio
    async def test_session_with_multiple_text_blocks(self, mock_spec_dir):
        """Test session with multiple text blocks accumulating response."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create multiple text blocks
        mock_text_block1 = MagicMock()
        mock_text_block1.__class__.__name__ = "TextBlock"
        mock_text_block1.text = "First part "

        mock_text_block2 = MagicMock()
        mock_text_block2.__class__.__name__ = "TextBlock"
        mock_text_block2.text = "second part"

        mock_text_block3 = MagicMock()
        mock_text_block3.__class__.__name__ = "TextBlock"
        mock_text_block3.text = " final part"

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_text_block1, mock_text_block2, mock_text_block3]

        async def mock_receive():
            yield mock_assistant_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            assert response == "First part second part final part"

    @pytest.mark.asyncio
    async def test_session_tool_detail_storing_for_supported_tools(self, mock_spec_dir):
        """Test that tool results are stored in detail for supported tools."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block for Read (supported tool)
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Read"
        mock_tool_use_block.input = {"file_path": "/test/file.txt"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        # Create mock success result with moderate content
        test_content = "x" * 1000  # Under 50KB limit
        mock_result_block = MagicMock()
        mock_result_block.__class__.__name__ = "ToolResultBlock"
        mock_result_block.content = test_content
        mock_result_block.is_error = False

        mock_user_message = MagicMock()
        mock_user_message.__class__.__name__ = "UserMessage"
        mock_user_message.content = [mock_result_block]

        async def mock_receive():
            yield mock_assistant_message
            yield mock_user_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"file_path": "/test/file.txt"}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            # Verify detail was stored for Read tool
            call_kwargs = mock_logger.tool_end.call_args[1]
            assert call_kwargs["detail"] == test_content

    @pytest.mark.asyncio
    async def test_session_tool_detail_not_stored_for_large_results(self, mock_spec_dir):
        """Test that tool results over 50KB are not stored in detail."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block for Bash
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Bash"
        mock_tool_use_block.input = {"command": "ls -R"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        # Create mock success result with huge content
        huge_content = "x" * 60000  # Over 50KB limit
        mock_result_block = MagicMock()
        mock_result_block.__class__.__name__ = "ToolResultBlock"
        mock_result_block.content = huge_content
        mock_result_block.is_error = False

        mock_user_message = MagicMock()
        mock_user_message.__class__.__name__ = "UserMessage"
        mock_user_message.content = [mock_result_block]

        async def mock_receive():
            yield mock_assistant_message
            yield mock_user_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"command": "ls -R"}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            # Verify detail was NOT stored for huge result
            call_kwargs = mock_logger.tool_end.call_args[1]
            assert call_kwargs["detail"] is None

    @pytest.mark.asyncio
    async def test_session_tool_detail_not_stored_for_unsupported_tools(self, mock_spec_dir):
        """Test that tool results are not stored in detail for unsupported tools."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block for Glob (not in supported list)
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Glob"
        mock_tool_use_block.input = {"pattern": "*.py"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        # Create mock success result
        mock_result_block = MagicMock()
        mock_result_block.__class__.__name__ = "ToolResultBlock"
        mock_result_block.content = "file1.py\nfile2.py"
        mock_result_block.is_error = False

        mock_user_message = MagicMock()
        mock_user_message.__class__.__name__ = "UserMessage"
        mock_user_message.content = [mock_result_block]

        async def mock_receive():
            yield mock_assistant_message
            yield mock_user_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"pattern": "*.py"}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            # Verify detail was NOT stored for Glob tool
            call_kwargs = mock_logger.tool_end.call_args[1]
            assert call_kwargs["detail"] is None

    @pytest.mark.asyncio
    async def test_session_with_no_task_logger(self, mock_spec_dir):
        """Test session behavior when no task logger is available."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Bash"
        mock_tool_use_block.input = {"command": "echo test"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        # Create mock success result
        mock_result_block = MagicMock()
        mock_result_block.__class__.__name__ = "ToolResultBlock"
        mock_result_block.content = "test"
        mock_result_block.is_error = False

        mock_user_message = MagicMock()
        mock_user_message.__class__.__name__ = "UserMessage"
        mock_user_message.content = [mock_result_block]

        async def mock_receive():
            yield mock_assistant_message
            yield mock_user_message

        mock_client.receive_response = mock_receive

        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=None), \
             patch("agents.session.get_safe_tool_input", return_value={"command": "echo test"}):

            # Should not raise error even without task logger
            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"

    @pytest.mark.asyncio
    async def test_session_with_tool_use_path(self, mock_spec_dir):
        """Test session with tool use containing path input."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block with path input
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Glob"
        mock_tool_use_block.input = {"path": "/test/path"}

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        async def mock_receive():
            yield mock_assistant_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"path": "/test/path"}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            mock_logger.tool_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_verbose_with_long_input(self, mock_spec_dir):
        """Test session in verbose mode with long tool input."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock tool use block with long input (>300 chars)
        long_input = "x" * 350
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Bash"
        mock_tool_use_block.input = {"command": long_input}
        mock_tool_use_block.__setattr__("input", {"command": long_input})

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        async def mock_receive():
            yield mock_assistant_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value={"command": long_input}):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=True,  # Enable verbose
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            mock_logger.tool_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_with_empty_text_block(self, mock_spec_dir):
        """Test session with empty/whitespace text blocks."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create mock text blocks with empty/whitespace content
        mock_text_block1 = MagicMock()
        mock_text_block1.__class__.__name__ = "TextBlock"
        mock_text_block1.text = "   "

        mock_text_block2 = MagicMock()
        mock_text_block2.__class__.__name__ = "TextBlock"
        mock_text_block2.text = ""

        mock_text_block3 = MagicMock()
        mock_text_block3.__class__.__name__ = "TextBlock"
        mock_text_block3.text = "Actual content"

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_text_block1, mock_text_block2, mock_text_block3]

        async def mock_receive():
            yield mock_assistant_message

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            # Empty text blocks should not be logged
            assert mock_logger.log.call_count <= 1  # Only non-empty text logged

    @pytest.mark.asyncio
    async def test_session_with_multiple_tools_same_name(self, mock_spec_dir):
        """Test session with multiple tool uses of the same tool."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create multiple tool use blocks for the same tool
        mock_tool_use_block1 = MagicMock()
        mock_tool_use_block1.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block1.name = "Read"
        mock_tool_use_block1.input = {"file_path": "file1.txt"}

        mock_tool_use_block2 = MagicMock()
        mock_tool_use_block2.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block2.name = "Read"
        mock_tool_use_block2.input = {"file_path": "file2.txt"}

        # Separate result blocks for each tool use
        mock_result_block1 = MagicMock()
        mock_result_block1.__class__.__name__ = "ToolResultBlock"
        mock_result_block1.content = "content1"
        mock_result_block1.is_error = False

        mock_result_block2 = MagicMock()
        mock_result_block2.__class__.__name__ = "ToolResultBlock"
        mock_result_block2.content = "content2"
        mock_result_block2.is_error = False

        # First assistant message with first tool use
        mock_assistant_message1 = MagicMock()
        mock_assistant_message1.__class__.__name__ = "AssistantMessage"
        mock_assistant_message1.content = [mock_tool_use_block1]

        # User message with first result
        mock_user_message1 = MagicMock()
        mock_user_message1.__class__.__name__ = "UserMessage"
        mock_user_message1.content = [mock_result_block1]

        # Second assistant message with second tool use
        mock_assistant_message2 = MagicMock()
        mock_assistant_message2.__class__.__name__ = "AssistantMessage"
        mock_assistant_message2.content = [mock_tool_use_block2]

        # User message with second result
        mock_user_message2 = MagicMock()
        mock_user_message2.__class__.__name__ = "UserMessage"
        mock_user_message2.content = [mock_result_block2]

        async def mock_receive():
            yield mock_assistant_message1
            yield mock_user_message1
            yield mock_assistant_message2
            yield mock_user_message2

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", side_effect=[
                 {"file_path": "file1.txt"},
                 {"file_path": "file2.txt"}
             ]):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            # Both tool uses should be logged
            assert mock_logger.tool_start.call_count == 2
            assert mock_logger.tool_end.call_count == 2

    @pytest.mark.asyncio
    async def test_session_with_very_long_response_text(self, mock_spec_dir):
        """Test session with very long response text accumulation."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create a text block with very long content
        long_text = "x" * 10000

        mock_text_block = MagicMock()
        mock_text_block.__class__.__name__ = "TextBlock"
        mock_text_block.text = long_text

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_text_block]

        async def mock_receive():
            yield mock_assistant_message

        mock_client.receive_response = mock_receive

        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=MagicMock()):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            # Response should accumulate all text
            assert len(response) == 10000

    @pytest.mark.asyncio
    async def test_session_handles_tool_without_input_attribute(self, mock_spec_dir):
        """Test session handling tool use block without input attribute."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create tool use block without input attribute
        mock_tool_use_block = MagicMock(spec=[])  # Empty spec
        mock_tool_use_block.__class__.__name__ = "ToolUseBlock"
        mock_tool_use_block.name = "Bash"
        # Deliberately not setting input attribute

        mock_assistant_message = MagicMock()
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        mock_assistant_message.content = [mock_tool_use_block]

        async def mock_receive():
            yield mock_assistant_message

        mock_client.receive_response = mock_receive

        mock_logger = MagicMock()
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=mock_logger), \
             patch("agents.session.get_safe_tool_input", return_value=None):

            # Should not crash even without input
            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"
            mock_logger.tool_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_handles_user_message_without_content(self, mock_spec_dir):
        """Test session handling UserMessage without content attribute."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create user message without content
        mock_user_message = MagicMock(spec=[])
        mock_user_message.__class__.__name__ = "UserMessage"
        # No content attribute

        async def mock_receive():
            yield mock_user_message

        mock_client.receive_response = mock_receive

        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=MagicMock()):

            # Should not crash
            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"

    @pytest.mark.asyncio
    async def test_session_handles_assistant_message_without_content(self, mock_spec_dir):
        """Test session handling AssistantMessage without content attribute."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Create assistant message without content
        mock_assistant_message = MagicMock(spec=[])
        mock_assistant_message.__class__.__name__ = "AssistantMessage"
        # No content attribute

        async def mock_receive():
            yield mock_assistant_message

        mock_client.receive_response = mock_receive

        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=MagicMock()):

            # Should not crash
            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "continue"

    @pytest.mark.asyncio
    async def test_session_with_query_error(self, mock_spec_dir):
        """Test session handling error during client.query()."""
        mock_client = AsyncMock()
        # query() raises an error
        mock_client.query.side_effect = RuntimeError("Query failed")

        with patch("agents.session.get_task_logger", return_value=MagicMock()):

            status, response, error_info = await run_agent_session(
                client=mock_client,
                message="Test prompt",
                spec_dir=mock_spec_dir,
                verbose=False,
                phase=LogPhase.CODING,
            )

            assert status == "error"
            assert error_info["type"] == "other"
            assert "Query failed" in error_info["message"]


class TestPostSessionProcessingEdgeCases:
    """Test post_session_processing edge cases."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_sync_spec_syncs_to_source(self, mock_spec_dir, mock_project_dir):
        """Test that sync_spec_to_source is called when source_spec_dir is provided."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=True) as mock_sync, \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=mock_spec_dir,  # Provide source_spec_dir
            )

            assert result is True
            mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_manager_propagates_exception(self, mock_spec_dir, mock_project_dir):
        """Test that status_manager exceptions are NOT caught (they propagate)."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()
        # update_subtasks raises exception
        status_manager.update_subtasks.side_effect = RuntimeError("Status update failed")

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            # Exception should propagate
            with pytest.raises(RuntimeError, match="Status update failed"):
                await post_session_processing(
                    spec_dir=mock_spec_dir,
                    project_dir=mock_project_dir,
                    subtask_id="subtask-1",
                    session_num=1,
                    commit_before="abc123",
                    commit_count_before=5,
                    recovery_manager=recovery_manager,
                    linear_enabled=False,
                    status_manager=status_manager,
                    source_spec_dir=None,
                )

    @pytest.mark.asyncio
    async def test_recovery_manager_propagates_exception(self, mock_spec_dir, mock_project_dir):
        """Test that recovery_manager exceptions propagate."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        # record_attempt raises exception
        recovery_manager.record_attempt.side_effect = RuntimeError("Recovery failed")
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "pending"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "pending"}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            # Exception should propagate
            with pytest.raises(RuntimeError, match="Recovery failed"):
                await post_session_processing(
                    spec_dir=mock_spec_dir,
                    project_dir=mock_project_dir,
                    subtask_id="subtask-1",
                    session_num=1,
                    commit_before="abc123",
                    commit_count_before=5,
                    recovery_manager=recovery_manager,
                    linear_enabled=False,
                    status_manager=status_manager,
                    source_spec_dir=None,
                )

    @pytest.mark.asyncio
    async def test_subtask_without_status_key(self, mock_spec_dir, mock_project_dir):
        """Test that very long subtask descriptions are handled."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        # Very long description (200 chars)
        long_desc = "x" * 200

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": long_desc}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": long_desc}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            # Should not crash on long description
            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            assert result is True
            # Verify description was truncated in approach
            recovery_manager.record_attempt.assert_called_once()
            call_args = recovery_manager.record_attempt.call_args
            approach = call_args[1]["approach"]
            assert len(approach) <= 200  # Should be truncated

    @pytest.mark.asyncio
    async def test_session_num_zero(self, mock_spec_dir, mock_project_dir):
        """Test handling session_num=0 (edge case)."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")) as mock_save:

            await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=0,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            # Should pass session_num=0 to save_session_memory
            mock_save.assert_called_once()
            # session_num should be 0
            # Use call_args to check the positional/keyword arguments
            assert mock_save.call_args.kwargs.get("session_num") == 0

    @pytest.mark.asyncio
    async def test_negative_commit_count(self, mock_spec_dir, mock_project_dir):
        """Test handling negative commit count (edge case)."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)
        status_manager = MagicMock()

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.get_latest_commit", return_value="def456"), \
             patch("agents.session.get_commit_count", return_value=-1), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=status_manager,
                source_spec_dir=None,
            )

            # Should calculate new_commits correctly even with negative
            assert result is True
            # new_commits would be -1 - 5 = -6, but we just check it doesn't crash
            recovery_manager.record_good_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_status_manager_provided(self, mock_spec_dir, mock_project_dir):
        """Test that None status_manager is handled."""
        from recovery import RecoveryManager

        recovery_manager = MagicMock(spec=RecoveryManager)

        with patch("agents.session.sync_spec_to_source", return_value=False), \
             patch("agents.session.load_implementation_plan", return_value={
                 "phases": [{"subtasks": [{"id": "subtask-1", "status": "completed", "description": "Test"}]}]
             }), \
             patch("agents.session.find_subtask_in_plan", return_value={"status": "completed", "description": "Test"}), \
             patch("agents.session.count_subtasks_detailed", return_value={"completed": 1, "total": 1}), \
             patch("agents.session.extract_session_insights", new_callable=AsyncMock, return_value={}), \
             patch("agents.session.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")):

            result = await post_session_processing(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_count_before=5,
                recovery_manager=recovery_manager,
                linear_enabled=False,
                status_manager=None,  # No status manager
                source_spec_dir=None,
            )

            # Should complete without status manager
            assert result is True


class TestIsToolConcurrencyErrorEdgeCases:
    """Test is_tool_concurrency_error function edge cases."""

    def test_error_with_none_message(self):
        """Test error with None as message."""
        # Some errors might have None as their message
        error = Exception(None)
        result = is_tool_concurrency_error(error)
        assert result is False

    def test_400_with_only_concurrency_keyword(self):
        """Test 400 error with only 'concurrency' keyword."""
        error = Exception("400: concurrency")
        # Should return False - needs "tool" AND "concurrency" or "concurrent tool"
        result = is_tool_concurrency_error(error)
        assert result is False

    def test_400_with_only_tool_keyword(self):
        """Test 400 error with only 'tool' keyword."""
        error = Exception("400: tool error")
        # Should return False - needs "tool" AND "concurrency"
        result = is_tool_concurrency_error(error)
        assert result is False

    def test_concurrency_error_without_400(self):
        """Test concurrency error without 400 status code."""
        error = Exception("tool concurrency limit exceeded")
        # Should return False - needs 400 status code
        result = is_tool_concurrency_error(error)
        assert result is False

    def test_400_in_middle_of_string(self):
        """Test 400 appearing in middle of error string."""
        error = Exception("Error 400 bad request: tool concurrency")
        result = is_tool_concurrency_error(error)
        assert result is True

    def test_400_with_whitespace_variations(self):
        """Test 400 with various whitespace patterns."""
        test_cases = [
            "400:tool concurrency",
            "400: tool\nconcurrency",
            "400:\ttool\tconcurrency",
        ]
        for error_str in test_cases:
            error = Exception(error_str)
            assert is_tool_concurrency_error(error) is True, f"Failed for: {error_str}"

    def test_unicode_in_error_message(self):
        """Test error message with unicode characters."""
        error = Exception("400: tool concurrency error \u2717")
        # Should handle unicode gracefully
        result = is_tool_concurrency_error(error)
        assert result is True

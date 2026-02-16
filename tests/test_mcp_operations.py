"""
Tests for mcp_server/operations.py
===================================

Tests the OperationTracker for creating, updating, cancelling,
listing, and cleaning up long-running operations.
"""

import sys
from pathlib import Path

# Add backend to sys.path
_backend = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Pre-mock SDK modules before any mcp_server imports
from unittest.mock import MagicMock

if "claude_agent_sdk" not in sys.modules:
    sys.modules["claude_agent_sdk"] = MagicMock()
    sys.modules["claude_agent_sdk.types"] = MagicMock()

import asyncio
import time
from unittest.mock import AsyncMock

from mcp_server.operations import Operation, OperationStatus, OperationTracker


class TestOperationCreation:
    """Tests for Operation dataclass and OperationTracker.create()."""

    def test_create_returns_operation_with_unique_id(self):
        """create() returns an Operation with a unique UUID."""
        tracker = OperationTracker()
        op1 = tracker.create("spec_create")
        op2 = tracker.create("build")
        assert op1.id != op2.id
        assert len(op1.id) == 36  # UUID format

    def test_create_sets_pending_status(self):
        """create() initializes operation with PENDING status."""
        tracker = OperationTracker()
        op = tracker.create("spec_create")
        assert op.status == OperationStatus.PENDING

    def test_create_sets_operation_type(self):
        """create() records the operation type."""
        tracker = OperationTracker()
        op = tracker.create("qa_review")
        assert op.type == "qa_review"

    def test_create_uses_default_message(self):
        """create() generates a default message from the operation type."""
        tracker = OperationTracker()
        op = tracker.create("build")
        assert op.message == "Starting build..."

    def test_create_uses_custom_message(self):
        """create() uses a custom message when provided."""
        tracker = OperationTracker()
        op = tracker.create("spec_create", message="Creating spec for feature X")
        assert op.message == "Creating spec for feature X"

    def test_create_stores_operation(self):
        """create() stores the operation so get() can find it."""
        tracker = OperationTracker()
        op = tracker.create("build")
        assert tracker.get(op.id) is op

    def test_create_sets_timestamps(self):
        """create() records created_at and updated_at timestamps."""
        tracker = OperationTracker()
        before = time.time()
        op = tracker.create("build")
        after = time.time()
        assert before <= op.created_at <= after
        assert before <= op.updated_at <= after


class TestOperationGet:
    """Tests for OperationTracker.get()."""

    def test_get_returns_none_for_unknown_id(self):
        """get() returns None for a nonexistent operation ID."""
        tracker = OperationTracker()
        assert tracker.get("nonexistent-id") is None

    def test_get_returns_operation_by_id(self):
        """get() returns the correct operation."""
        tracker = OperationTracker()
        op = tracker.create("build")
        result = tracker.get(op.id)
        assert result is op
        assert result.type == "build"


class TestOperationUpdate:
    """Tests for OperationTracker.update()."""

    def test_update_modifies_status(self):
        """update() changes the operation status."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(op.id, status=OperationStatus.RUNNING)
        assert op.status == OperationStatus.RUNNING

    def test_update_modifies_progress(self):
        """update() changes the progress value."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(op.id, progress=50)
        assert op.progress == 50

    def test_update_clamps_progress_to_zero(self):
        """update() clamps negative progress to 0."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(op.id, progress=-10)
        assert op.progress == 0

    def test_update_clamps_progress_to_hundred(self):
        """update() clamps progress above 100 to 100."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(op.id, progress=150)
        assert op.progress == 100

    def test_update_modifies_message(self):
        """update() changes the message."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(op.id, message="Building subtask 3/5...")
        assert op.message == "Building subtask 3/5..."

    def test_update_sets_result(self):
        """update() stores the result payload."""
        tracker = OperationTracker()
        op = tracker.create("build")
        result_data = {"files_changed": 5, "tests_passed": True}
        tracker.update(op.id, result=result_data)
        assert op.result == result_data

    def test_update_sets_error(self):
        """update() stores an error message."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(op.id, error="Build failed: syntax error in main.py")
        assert op.error == "Build failed: syntax error in main.py"

    def test_update_updates_timestamp(self):
        """update() refreshes the updated_at timestamp."""
        tracker = OperationTracker()
        op = tracker.create("build")
        old_time = op.updated_at
        time.sleep(0.01)
        tracker.update(op.id, progress=10)
        assert op.updated_at > old_time

    def test_update_returns_operation(self):
        """update() returns the updated operation."""
        tracker = OperationTracker()
        op = tracker.create("build")
        result = tracker.update(op.id, status=OperationStatus.RUNNING)
        assert result is op

    def test_update_returns_none_for_unknown_id(self):
        """update() returns None for a nonexistent operation."""
        tracker = OperationTracker()
        result = tracker.update("nonexistent", progress=50)
        assert result is None

    def test_update_multiple_fields_at_once(self):
        """update() can modify multiple fields in a single call."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(
            op.id,
            status=OperationStatus.RUNNING,
            progress=75,
            message="Almost done",
        )
        assert op.status == OperationStatus.RUNNING
        assert op.progress == 75
        assert op.message == "Almost done"


class TestOperationCancel:
    """Tests for OperationTracker.cancel()."""

    def test_cancel_pending_operation(self):
        """cancel() sets a PENDING operation to CANCELLED."""
        tracker = OperationTracker()
        op = tracker.create("build")
        result = tracker.cancel(op.id)
        assert result is True
        assert op.status == OperationStatus.CANCELLED
        assert op.message == "Operation cancelled by user"

    def test_cancel_running_operation(self):
        """cancel() sets a RUNNING operation to CANCELLED."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(op.id, status=OperationStatus.RUNNING)
        result = tracker.cancel(op.id)
        assert result is True
        assert op.status == OperationStatus.CANCELLED

    def test_cancel_completed_operation_returns_false(self):
        """cancel() returns False for COMPLETED operations."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(op.id, status=OperationStatus.COMPLETED)
        result = tracker.cancel(op.id)
        assert result is False
        assert op.status == OperationStatus.COMPLETED

    def test_cancel_failed_operation_returns_false(self):
        """cancel() returns False for FAILED operations."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(op.id, status=OperationStatus.FAILED)
        result = tracker.cancel(op.id)
        assert result is False
        assert op.status == OperationStatus.FAILED

    def test_cancel_unknown_id_returns_false(self):
        """cancel() returns False for a nonexistent operation."""
        tracker = OperationTracker()
        result = tracker.cancel("nonexistent")
        assert result is False

    def test_cancel_cancels_asyncio_task(self):
        """cancel() calls task.cancel() on the associated asyncio task."""
        tracker = OperationTracker()
        op = tracker.create("build")
        mock_task = MagicMock(spec=asyncio.Task)
        mock_task.done.return_value = False
        op._task = mock_task
        tracker.cancel(op.id)
        mock_task.cancel.assert_called_once()

    def test_cancel_does_not_cancel_done_task(self):
        """cancel() skips task.cancel() when the asyncio task is already done."""
        tracker = OperationTracker()
        op = tracker.create("build")
        mock_task = MagicMock(spec=asyncio.Task)
        mock_task.done.return_value = True
        op._task = mock_task
        tracker.cancel(op.id)
        mock_task.cancel.assert_not_called()

    def test_cancel_updates_timestamp(self):
        """cancel() refreshes the updated_at timestamp."""
        tracker = OperationTracker()
        op = tracker.create("build")
        old_time = op.updated_at
        time.sleep(0.01)
        tracker.cancel(op.id)
        assert op.updated_at > old_time


class TestListActive:
    """Tests for OperationTracker.list_active()."""

    def test_list_active_returns_pending_and_running(self):
        """list_active() returns PENDING and RUNNING operations."""
        tracker = OperationTracker()
        op1 = tracker.create("build")
        op2 = tracker.create("qa_review")
        tracker.update(op2.id, status=OperationStatus.RUNNING)
        active = tracker.list_active()
        assert len(active) == 2
        assert op1 in active
        assert op2 in active

    def test_list_active_excludes_terminal_states(self):
        """list_active() excludes COMPLETED, FAILED, and CANCELLED."""
        tracker = OperationTracker()
        op1 = tracker.create("build")
        op2 = tracker.create("qa_review")
        op3 = tracker.create("spec_create")
        tracker.update(op1.id, status=OperationStatus.COMPLETED)
        tracker.update(op2.id, status=OperationStatus.FAILED)
        tracker.cancel(op3.id)

        active = tracker.list_active()
        assert len(active) == 0

    def test_list_active_empty_tracker(self):
        """list_active() returns empty list when no operations exist."""
        tracker = OperationTracker()
        assert tracker.list_active() == []


class TestCleanupOld:
    """Tests for OperationTracker._cleanup_old()."""

    def test_cleanup_removes_oldest_completed(self):
        """_cleanup_old() removes oldest completed operations beyond max."""
        tracker = OperationTracker(max_completed=2)
        ops = []
        for i in range(4):
            op = tracker.create(f"build_{i}")
            op.created_at = i  # deterministic ordering
            tracker.update(op.id, status=OperationStatus.COMPLETED)
            ops.append(op)

        # Trigger cleanup by creating a new operation
        tracker.create("trigger")

        # Oldest two should have been removed
        assert tracker.get(ops[0].id) is None
        assert tracker.get(ops[1].id) is None
        # Newest two should remain
        assert tracker.get(ops[2].id) is not None
        assert tracker.get(ops[3].id) is not None

    def test_cleanup_does_not_remove_active_operations(self):
        """_cleanup_old() only removes terminal-state operations."""
        tracker = OperationTracker(max_completed=1)
        active_op = tracker.create("build")
        tracker.update(active_op.id, status=OperationStatus.RUNNING)

        completed_op = tracker.create("old_build")
        tracker.update(completed_op.id, status=OperationStatus.COMPLETED)

        # Trigger cleanup
        tracker.create("trigger")

        # Active operation should still exist
        assert tracker.get(active_op.id) is not None

    def test_cleanup_under_limit_keeps_all(self):
        """_cleanup_old() keeps all operations when under max_completed limit."""
        tracker = OperationTracker(max_completed=10)
        ops = []
        for i in range(3):
            op = tracker.create(f"build_{i}")
            tracker.update(op.id, status=OperationStatus.COMPLETED)
            ops.append(op)

        # All should still exist
        for op in ops:
            assert tracker.get(op.id) is not None


class TestOperationToDict:
    """Tests for Operation.to_dict() serialization."""

    def test_to_dict_contains_all_fields(self):
        """to_dict() includes all expected fields."""
        tracker = OperationTracker()
        op = tracker.create("spec_create", message="Creating spec")
        result = op.to_dict()

        expected_keys = {
            "id",
            "type",
            "status",
            "progress",
            "message",
            "result",
            "error",
            "created_at",
            "updated_at",
            "elapsed_seconds",
        }
        assert set(result.keys()) == expected_keys

    def test_to_dict_serializes_status_as_string(self):
        """to_dict() converts OperationStatus enum to its string value."""
        tracker = OperationTracker()
        op = tracker.create("build")
        result = op.to_dict()
        assert result["status"] == "pending"
        assert isinstance(result["status"], str)

    def test_to_dict_computes_elapsed_seconds(self):
        """to_dict() calculates elapsed time from creation."""
        op = Operation(id="test-id", type="build", created_at=time.time() - 5.0)
        result = op.to_dict()
        assert result["elapsed_seconds"] >= 4.9

    def test_to_dict_serializes_result_and_error(self):
        """to_dict() includes result and error fields."""
        tracker = OperationTracker()
        op = tracker.create("build")
        tracker.update(
            op.id,
            status=OperationStatus.FAILED,
            error="Connection timeout",
            result={"partial": True},
        )
        result = op.to_dict()
        assert result["error"] == "Connection timeout"
        assert result["result"] == {"partial": True}
        assert result["status"] == "failed"

    def test_to_dict_default_values(self):
        """to_dict() includes correct defaults for a fresh operation."""
        tracker = OperationTracker()
        op = tracker.create("build")
        result = op.to_dict()
        assert result["progress"] == 0
        assert result["result"] is None
        assert result["error"] is None


class TestOperationStatusEnum:
    """Tests for OperationStatus enum values."""

    def test_status_values(self):
        """OperationStatus has the expected string values."""
        assert OperationStatus.PENDING.value == "pending"
        assert OperationStatus.RUNNING.value == "running"
        assert OperationStatus.COMPLETED.value == "completed"
        assert OperationStatus.FAILED.value == "failed"
        assert OperationStatus.CANCELLED.value == "cancelled"

    def test_status_is_string_enum(self):
        """OperationStatus values are strings."""
        assert isinstance(OperationStatus.PENDING, str)
        assert OperationStatus.PENDING == "pending"
